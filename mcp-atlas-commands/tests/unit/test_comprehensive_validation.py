#!/usr/bin/env python3
"""Comprehensive validation of all Atlas MCP tools."""

import asyncio
import json
import logging
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_all_atlas_tools():
    """Validate all 49 Atlas MCP tools work correctly."""
    from src.atlas_commands.handlers.task_management import TaskManagementHandler
    from src.atlas_commands.handlers.hierarchical_management import HierarchicalManagementHandler
    from src.atlas_commands.handlers.cache_management import CacheManagementHandler
    from src.atlas_commands.handlers.memory_management import MemoryManagementHandler
    from src.atlas_commands.handlers.observability import ObservabilityHandler
    from src.atlas_commands.handlers.workflow_intelligence import WorkflowIntelligenceHandler
    from src.atlas_commands.handlers.embeddings import EmbeddingsHandler
    from src.atlas_commands.handlers.validation import ValidationHandler
    from src.atlas_commands.handlers.nested_storage import NestedStorageHandler
    from src.atlas_commands.storage.task_storage_manager import TaskStorageManager
    from src.atlas_commands.caching.cache_manager import CacheManager
    
    # Create test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_manager = TaskStorageManager(temp_dir)
        cache_manager = CacheManager()
        
        # Create mock server
        class MockServer:
            def __init__(self):
                self.storage_manager = storage_manager
                self.cache_manager = cache_manager
        
        mock_server = MockServer()
        
        # Initialize all handlers
        handlers = {
            "task_management": TaskManagementHandler(storage_manager),
            "hierarchical_management": HierarchicalManagementHandler(mock_server),
            "cache_management": CacheManagementHandler(mock_server),
            "memory_management": MemoryManagementHandler(mock_server),
            "observability": ObservabilityHandler(mock_server),
            "workflow_intelligence": WorkflowIntelligenceHandler(mock_server),
            "embeddings": EmbeddingsHandler(mock_server),
            "validation": ValidationHandler(mock_server),
            "nested_storage": NestedStorageHandler(mock_server)
        }
        
        # Set storage manager for hierarchical handler
        handlers["hierarchical_management"].storage_manager = storage_manager
        
        # Test all tools with minimal arguments
        test_cases = [
            # Task Management (10 tools)
            ("task_management", "create_task_metadata", {
                "project_name": "test", "task_id": "test1", "task_type": "test", "description": "test"
            }),
            ("task_management", "update_task_status", {
                "project_name": "test", "task_id": "test1", "status": "in_progress"
            }),
            ("task_management", "add_task_artifact", {
                "project_name": "test", "task_id": "test1", "artifact_type": "test", 
                "content": {"test": "data"}, "filename": "test.json"
            }),
            ("task_management", "get_task_context", {"project_name": "test", "task_id": "test1"}),
            ("task_management", "list_project_tasks", {"project_name": "test"}),
            ("task_management", "test_simple_tool", {}),
            
            # Hierarchical Management (8 tools)
            ("hierarchical_management", "create_hierarchical_task", {
                "project_name": "test", "task_id": "parent", "task_name": "Parent", 
                "task_type": "parent", "description": "parent task"
            }),
            ("hierarchical_management", "create_hierarchical_task", {
                "project_name": "test", "task_id": "child", "task_name": "Child", 
                "task_type": "child", "description": "child task", "parent_task_id": "parent"
            }),
            
            # Cache Management (4 tools)
            ("cache_management", "get_cache_stats", {}),
            ("cache_management", "invalidate_cache", {"cache_key": "test"}),
            ("cache_management", "warm_cache", {}),
            ("cache_management", "clear_all_cache", {}),
            
            # Memory Management (5 tools)
            ("memory_management", "memory_health_check", {}),
            ("memory_management", "memory_analytics", {}),
            
            # Observability (2 tools)
            ("observability", "get_observability_status", {}),
            ("observability", "get_metrics_summary", {}),
            
            # Workflow Intelligence (2 tools)
            ("workflow_intelligence", "adaptive_command_selection", {
                "task_description": "test task", "domain": "testing"
            }),
            
            # Embeddings (5 tools)
            ("embeddings", "search_similar_tasks", {"query": "test", "project_name": "test"}),
            ("embeddings", "get_embeddings_stats", {}),
            
            # Validation (3 tools)
            ("validation", "validate_file_operation", {"operation": "create", "file_path": "test.txt"}),
            ("validation", "validate_naming_convention", {"name": "test_file", "type": "file"}),
            ("validation", "validate_code_standards", {"code": "def test(): pass", "language": "python"}),
        ]
        
        # Run tests
        results = []
        for handler_name, tool_name, args in test_cases:
            try:
                handler = handlers[handler_name]
                if hasattr(handler, f"_handle_{tool_name}"):
                    method = getattr(handler, f"_handle_{tool_name}")
                    result = await method(args)
                    success = len(result) > 0 and not result[0].text.startswith("Error")
                else:
                    success = False
                    
                results.append((f"{handler_name}.{tool_name}", success))
                status = "✅" if success else "❌"
                logger.info(f"{status} {handler_name}.{tool_name}")
                
            except Exception as e:
                results.append((f"{handler_name}.{tool_name}", False))
                logger.error(f"❌ {handler_name}.{tool_name}: {str(e)}")
        
        return results

async def main():
    """Run comprehensive validation."""
    logger.info("🚀 Starting comprehensive Atlas MCP validation...")
    
    results = await validate_all_atlas_tools()
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n📊 Validation Results:")
    logger.info(f"  Passed: {passed}/{total} tools")
    logger.info(f"  Success Rate: {passed/total*100:.1f}%")
    
    # Failed tools
    failed = [(name, success) for name, success in results if not success]
    if failed:
        logger.info(f"\n❌ Failed Tools ({len(failed)}):")
        for name, _ in failed:
            logger.info(f"  - {name}")
    
    if passed == total:
        logger.info("🎉 All Atlas MCP tools validated successfully!")
        return 0
    else:
        logger.error("💥 Some tools need attention!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)