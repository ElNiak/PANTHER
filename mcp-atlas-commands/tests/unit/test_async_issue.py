#!/usr/bin/env python3
"""
Test script to verify if async/await issues exist in ATLAS MCP handlers.
"""

import asyncio
import sys
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, './src')

from atlas_commands.handlers.task_management import TaskManagementHandler
from atlas_commands.storage.task_storage_manager import TaskStorageManager


async def test_add_task_artifact():
    """Test if add_task_artifact returns coroutine or result."""
    print("Testing add_task_artifact...")
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_mgr = TaskStorageManager(base_path=temp_dir)
        handler = TaskManagementHandler(storage_mgr)
        
        # First create a task
        task_args = {
            "project_name": "test_project",
            "task_id": "test_task_123", 
            "task_type": "test",
            "description": "Test task for async verification"
        }
        
        try:
            # Create task first
            create_result = await handler._handle_create_task_metadata(task_args)
            print(f"Task creation result type: {type(create_result)}")
            
            # Now test add_task_artifact
            artifact_args = {
                "project_name": "test_project",
                "task_id": "test_task_123",
                "artifact_type": "analysis", 
                "content": "Test artifact content",
                "filename": "test_artifact.txt"
            }
            
            result = await handler._handle_add_task_artifact(artifact_args)
            print(f"add_task_artifact result type: {type(result)}")
            print(f"Result: {result}")
            
            # Check if it's a coroutine (which would be the bug)
            if asyncio.iscoroutine(result):
                print("❌ BUG CONFIRMED: add_task_artifact returned a coroutine!")
                return False
            else:
                print("✅ add_task_artifact working correctly - returns result, not coroutine")
                return True
                
        except Exception as e:
            print(f"Error during add_task_artifact test: {e}")
            return False


async def test_get_task_context():
    """Test if get_task_context returns coroutine or result."""
    print("\nTesting get_task_context...")
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_mgr = TaskStorageManager(base_path=temp_dir)
        handler = TaskManagementHandler(storage_mgr)
        
        # First create a task
        task_args = {
            "project_name": "test_project",
            "task_id": "test_task_456", 
            "task_type": "test",
            "description": "Test task for context verification"
        }
        
        try:
            # Create task first
            create_result = await handler._handle_create_task_metadata(task_args)
            print(f"Task creation result type: {type(create_result)}")
            
            # Now test get_task_context
            context_args = {
                "project_name": "test_project",
                "task_id": "test_task_456"
            }
            
            result = await handler._handle_get_task_context(context_args)
            print(f"get_task_context result type: {type(result)}")
            print(f"Result: {result}")
            
            # Check if it's a coroutine (which would be the bug)
            if asyncio.iscoroutine(result):
                print("❌ BUG CONFIRMED: get_task_context returned a coroutine!")
                return False
            else:
                print("✅ get_task_context working correctly - returns result, not coroutine")
                return True
                
        except Exception as e:
            print(f"Error during get_task_context test: {e}")
            return False


async def main():
    """Run all async tests."""
    print("=== ATLAS MCP Async Issues Test ===\n")
    
    test1_result = await test_add_task_artifact()
    test2_result = await test_get_task_context()
    
    print(f"\n=== SUMMARY ===")
    print(f"add_task_artifact test: {'PASS' if test1_result else 'FAIL'}")
    print(f"get_task_context test: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("\n✅ NO ASYNC ISSUES FOUND - Both methods work correctly!")
        return True
    else:
        print("\n❌ ASYNC ISSUES CONFIRMED - Need to fix!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)