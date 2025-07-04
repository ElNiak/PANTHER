#!/usr/bin/env python3
"""Test all the behavior fixes comprehensively."""

import asyncio
import json
import logging
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_json_serialization():
    """Test 1: JSON serialization fix for dict content."""
    from src.atlas_commands.handlers.task_management import TaskManagementHandler
    from src.atlas_commands.storage.task_storage_manager import TaskStorageManager
    
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_manager = TaskStorageManager(temp_dir)
        handler = TaskManagementHandler(storage_manager)
        
        # Create task and test dict content
        create_args = {
            "project_name": "test-project",
            "task_id": "json-test-task",
            "task_type": "testing",
            "description": "Test JSON serialization fix"
        }
        
        test_args = {
            "project_name": "test-project",
            "task_id": "json-test-task",
            "artifact_type": "test_results",
            "content": {"passed": 5, "failed": 2},
            "filename": "results.json"
        }
        
        try:
            await handler._handle_create_task_metadata(create_args)
            result = await handler._handle_add_task_artifact(test_args)
            
            result_data = json.loads(result[0].text)
            success = result_data.get("status") == "success"
            logger.info(f"✅ JSON serialization: {'PASS' if success else 'FAIL'}")
            return success
        except Exception as e:
            logger.error(f"❌ JSON serialization failed: {str(e)}")
            return False

async def test_hierarchical_tasks():
    """Test 2: Hierarchical tasks showing in list_project_tasks."""
    from src.atlas_commands.handlers.task_management import TaskManagementHandler
    from src.atlas_commands.handlers.hierarchical_management import HierarchicalManagementHandler
    from src.atlas_commands.storage.task_storage_manager import TaskStorageManager
    
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_manager = TaskStorageManager(temp_dir)
        task_handler = TaskManagementHandler(storage_manager)
        hierarchical_handler = HierarchicalManagementHandler(None)
        hierarchical_handler.storage_manager = storage_manager
        
        try:
            # Create parent task
            parent_args = {
                "project_name": "test-project",
                "task_id": "parent-task",
                "task_name": "Parent Task",
                "task_type": "parent",
                "description": "Parent task for hierarchy test"
            }
            
            # Create child task
            child_args = {
                "project_name": "test-project",
                "task_id": "child-task",
                "task_name": "Child Task", 
                "task_type": "child",
                "description": "Child task for hierarchy test",
                "parent_task_id": "parent-task"
            }
            
            # Create both tasks
            await hierarchical_handler._handle_create_hierarchical_task(parent_args)
            await hierarchical_handler._handle_create_hierarchical_task(child_args)
            
            # List tasks and check if both show up
            list_args = {"project_name": "test-project"}
            result = await task_handler._handle_list_project_tasks(list_args)
            
            result_data = json.loads(result[0].text)
            total_tasks = result_data.get("total_tasks", 0)
            success = total_tasks >= 2  # Should have both parent and child
            
            logger.info(f"✅ Hierarchical listing: {'PASS' if success else 'FAIL'} (found {total_tasks} tasks)")
            return success
        except Exception as e:
            logger.error(f"❌ Hierarchical listing failed: {str(e)}")
            return False

async def test_search_similar_tasks():
    """Test 3: search_similar_tasks handler implementation."""
    from src.atlas_commands.handlers.embeddings import EmbeddingsHandler
    from src.atlas_commands.storage.task_storage_manager import TaskStorageManager
    
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_manager = TaskStorageManager(temp_dir)
        # Create mock server object with storage_manager
        class MockServer:
            def __init__(self):
                self.storage_manager = storage_manager
        
        mock_server = MockServer()
        handler = EmbeddingsHandler(mock_server)
        
        try:
            # Create some test tasks first
            task1_meta = storage_manager.create_task_metadata(
                "test-project", "task1", "testing", "Test task about authentication"
            )
            task2_meta = storage_manager.create_task_metadata(
                "test-project", "task2", "debugging", "Debug authentication issues"  
            )
            
            # Search for similar tasks
            search_args = {
                "query": "authentication",
                "project_name": "test-project",
                "limit": 10
            }
            
            result = await handler._handle_search_similar_tasks(search_args)
            result_data = json.loads(result[0].text)
            
            # Should find similar tasks
            total_found = result_data.get("total_found", 0)
            success = total_found > 0
            
            logger.info(f"✅ Search similar tasks: {'PASS' if success else 'FAIL'} (found {total_found} matches)")
            return success
        except Exception as e:
            logger.error(f"❌ Search similar tasks failed: {str(e)}")
            return False

async def test_cache_statistics():
    """Test 4: Cache statistics tracking fix."""
    from src.atlas_commands.handlers.cache_management import CacheManagementHandler
    from src.atlas_commands.caching.cache_manager import CacheManager
    
    try:
        # Create mock server with cache manager
        class MockServer:
            def __init__(self):
                self.cache_manager = CacheManager()
        
        mock_server = MockServer()
        handler = CacheManagementHandler(mock_server)
        
        # Test getting cache stats
        result = await handler._handle_get_cache_stats({})
        
        # Should return cache statistics, not "not available"
        success = "not available" not in result[0].text.lower()
        
        logger.info(f"✅ Cache statistics: {'PASS' if success else 'FAIL'}")
        return success
    except Exception as e:
        logger.error(f"❌ Cache statistics failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    logger.info("🚀 Testing all Atlas MCP behavior fixes...")
    
    tests = [
        ("JSON Serialization", test_json_serialization),
        ("Hierarchical Tasks", test_hierarchical_tasks),
        ("Search Similar Tasks", test_search_similar_tasks),
        ("Cache Statistics", test_cache_statistics)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        success = await test_func()
        results.append((test_name, success))
    
    # Summary
    logger.info("\n📊 Test Results Summary:")
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    logger.info(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        logger.info("🎉 All fixes working correctly!")
        return 0
    else:
        logger.error("💥 Some fixes still need work!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)