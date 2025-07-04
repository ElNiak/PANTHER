#!/usr/bin/env python3
"""
Test script to verify if missing handler methods actually exist.
"""

import asyncio
import sys
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, './src')

from atlas_commands.handlers.embeddings import EmbeddingsHandler
from atlas_commands.handlers.validation import ValidationHandler  
from atlas_commands.handlers.nested_storage import NestedStorageHandler


async def test_embeddings_stats():
    """Test if get_embeddings_stats handler exists and works."""
    print("Testing get_embeddings_stats...")
    
    try:
        handler = EmbeddingsHandler()
        args = {}
        
        result = await handler._handle_get_embeddings_stats(args)
        print(f"get_embeddings_stats result type: {type(result)}")
        print(f"Result: {result}")
        
        if asyncio.iscoroutine(result):
            print("❌ BUG: get_embeddings_stats returned a coroutine!")
            return False
        else:
            print("✅ get_embeddings_stats working correctly")
            return True
            
    except Exception as e:
        print(f"Error during get_embeddings_stats test: {e}")
        return False


async def test_validate_file_operation():
    """Test if validate_file_operation handler exists and works."""
    print("\nTesting validate_file_operation...")
    
    try:
        handler = ValidationHandler()
        args = {
            "operation": "read",
            "file_path": "/tmp/test.txt",
            "context": "test"
        }
        
        result = await handler._handle_validate_file_operation(args)
        print(f"validate_file_operation result type: {type(result)}")
        print(f"Result: {result}")
        
        if asyncio.iscoroutine(result):
            print("❌ BUG: validate_file_operation returned a coroutine!")
            return False
        else:
            print("✅ validate_file_operation working correctly")
            return True
            
    except Exception as e:
        print(f"Error during validate_file_operation test: {e}")
        return False


async def test_create_nested_subtask():
    """Test if create_nested_subtask handler exists and works."""
    print("\nTesting create_nested_subtask...")
    
    try:
        handler = NestedStorageHandler()
        args = {
            "parent_task_id": "test-parent",
            "subtask_data": {"name": "test-subtask", "type": "analysis"}
        }
        
        result = await handler._handle_create_nested_subtask(args)
        print(f"create_nested_subtask result type: {type(result)}")
        print(f"Result: {result}")
        
        if asyncio.iscoroutine(result):
            print("❌ BUG: create_nested_subtask returned a coroutine!")
            return False
        else:
            print("✅ create_nested_subtask working correctly")
            return True
            
    except Exception as e:
        print(f"Error during create_nested_subtask test: {e}")
        return False


async def main():
    """Run all missing handler tests."""
    print("=== ATLAS MCP Missing Handler Test ===\n")
    
    test1_result = await test_embeddings_stats()
    test2_result = await test_validate_file_operation()
    test3_result = await test_create_nested_subtask()
    
    print(f"\n=== SUMMARY ===")
    print(f"get_embeddings_stats test: {'PASS' if test1_result else 'FAIL'}")
    print(f"validate_file_operation test: {'PASS' if test2_result else 'FAIL'}")
    print(f"create_nested_subtask test: {'PASS' if test3_result else 'FAIL'}")
    
    if test1_result and test2_result and test3_result:
        print("\n✅ ALL HANDLERS EXIST AND WORK - No missing handlers!")
        return True
    else:
        print("\n❌ SOME HANDLERS MISSING OR BROKEN - Need to fix!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)