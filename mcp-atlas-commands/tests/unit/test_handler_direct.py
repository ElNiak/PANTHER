#!/usr/bin/env python3
"""Test the task management handler directly."""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_json_serialization():
    """Test JSON serialization fix for dict content."""
    from src.atlas_commands.handlers.task_management import TaskManagementHandler
    from src.atlas_commands.storage.task_storage_manager import TaskStorageManager
    
    # Create temporary storage
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_manager = TaskStorageManager(temp_dir)
        handler = TaskManagementHandler(storage_manager)
        
        # Test data with dictionary content
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
            "content": {
                "test_results": {
                    "passed": 5,
                    "failed": 2,
                    "skipped": 1
                },
                "timestamp": datetime.now().isoformat(),
                "environment": "test"
            },
            "filename": "test_results.json"
        }
        
        try:
            # First create task metadata
            logger.info("Creating test task metadata...")
            result = await handler._handle_create_task_metadata(create_args)
            logger.info(f"Task created: {result[0].text}")
            
            # Now test adding artifact with dict content
            logger.info("Testing add_task_artifact with dict content...")
            result = await handler._handle_add_task_artifact(test_args)
            
            logger.info(f"Result: {result[0].text}")
            
            # Parse result to check for success
            try:
                result_data = json.loads(result[0].text)
                if result_data.get("status") == "success":
                    logger.info("✅ JSON serialization fix successful!")
                    return True
                else:
                    logger.error(f"❌ Test failed: {result_data}")
                    return False
            except json.JSONDecodeError:
                # If it's not JSON, it might be an error message
                if "Error" in result[0].text:
                    logger.error(f"❌ Test failed with error: {result[0].text}")
                    return False
                else:
                    logger.info("✅ Non-JSON response but no error detected")
                    return True
            
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Run the test."""
    logger.info("Testing JSON serialization fix...")
    success = await test_json_serialization()
    
    if success:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)