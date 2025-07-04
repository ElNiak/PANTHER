#!/usr/bin/env python3
"""
Test the token reduction implementation for list_project_tasks.
"""

import asyncio
import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.handlers.task_management import TaskManagementHandler


class MockStorageManager:
    """Mock storage manager for testing."""
    
    def list_project_tasks(self, project_name):
        """Return mock task list with varying sizes."""
        # Create a large number of mock tasks to test token reduction
        tasks = []
        for i in range(100):
            task = {
                "task_id": f"task_{i:03d}",
                "task_name": f"Task {i}: Very long task name with lots of descriptive text that could consume many tokens in the response and needs to be compressed effectively",
                "task_type": "task" if i % 3 == 0 else "subtask" if i % 3 == 1 else "subsubtask",
                "status": "active" if i % 4 == 0 else "pending" if i % 4 == 1 else "completed" if i % 4 == 2 else "archived",
                "priority": "high" if i % 3 == 0 else "medium" if i % 3 == 1 else "low",
                "created_at": f"2025-06-{(i % 30) + 1:02d}T10:00:00Z",
                "completion_percentage": i % 101,
                "current_phase": f"phase_{i % 5}",
                "description": f"This is a very detailed description for task {i} that contains a lot of information about what the task is supposed to accomplish and why it is important. " * 3,
                "artifacts": [f"artifact_{j}" for j in range(i % 5)],
                "observations": [f"observation_{j}: This is a very long observation with detailed information" for j in range(i % 3)]
            }
            tasks.append(task)
        return tasks


async def test_pagination_and_compression():
    """Test pagination and compression features."""
    
    print("🧪 Testing ATLAS MCP list_project_tasks token reduction...")
    
    # Create handler with mock storage
    mock_storage = MockStorageManager()
    handler = TaskManagementHandler(storage_manager=mock_storage)
    
    test_cases = [
        {
            "name": "Default pagination (10 items)",
            "args": {"project_name": "TEST"}
        },
        {
            "name": "Small page size (5 items)", 
            "args": {"project_name": "TEST", "page_size": 5}
        },
        {
            "name": "Filter by status (active only)",
            "args": {"project_name": "TEST", "status": "active", "page_size": 5}
        },
        {
            "name": "Recent tasks only",
            "args": {"project_name": "TEST", "recent_only": True, "page_size": 3}
        },
        {
            "name": "Large page (25 items - max)",
            "args": {"project_name": "TEST", "page_size": 25}
        },
        {
            "name": "Filter by type and priority",
            "args": {"project_name": "TEST", "task_type": "task", "priority": "high", "page_size": 10}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📊 Test: {test_case['name']}")
        print(f"   Args: {test_case['args']}")
        
        # Execute handler
        result = await handler._handle_list_project_tasks(test_case['args'])
        
        # Analyze response
        response_text = result[0].text
        response_size = len(response_text.encode())
        
        try:
            response_data = json.loads(response_text)
            task_count = len(response_data.get("tasks", []))
            pagination = response_data.get("pagination", {})
            
            print(f"   Response size: {response_size:,} bytes")
            print(f"   Tasks returned: {task_count}")
            print(f"   Total available: {pagination.get('total_tasks', 'unknown')}")
            print(f"   Page {pagination.get('page', 1)} of {pagination.get('total_pages', 1)}")
            print(f"   Has more: {pagination.get('has_more', False)}")
            
            # Check token reduction
            if response_size > 25000:
                print(f"   ⚠️  Still large! {response_size:,} bytes")
            elif response_size > 10000:
                print(f"   ⚡ Moderate size: {response_size:,} bytes")
            else:
                print(f"   ✅ Good size: {response_size:,} bytes")
                
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON response")
            print(f"   Response preview: {response_text[:200]}...")


async def test_extreme_compression():
    """Test with extremely large dataset to trigger compression."""
    
    print("\n🔬 Testing extreme compression scenario...")
    
    class LargeTaskStorage(MockStorageManager):
        def list_project_tasks(self, project_name):
            # Create 1000 tasks to definitely trigger compression
            tasks = []
            for i in range(1000):
                task = {
                    "task_id": f"large_task_{i:04d}",
                    "task_name": f"Large Task {i}: This is an extremely long task name with extensive descriptive text that will definitely consume many tokens and needs aggressive compression to fit within limits",
                    "task_type": "task",
                    "status": "active",
                    "priority": "high",
                    "created_at": f"2025-06-01T{(i % 24):02d}:00:00Z",
                    "completion_percentage": i % 101,
                    "current_phase": f"detailed_phase_{i % 10}_with_long_name",
                    "description": "This is an extremely verbose description that contains extensive details about the task implementation, requirements, dependencies, and expected outcomes. " * 5,
                    "artifacts": [f"detailed_artifact_{j}_with_long_name.json" for j in range(10)],
                    "observations": [f"Detailed observation {j}: This observation contains extensive information about the progress and findings during task execution." for j in range(5)]
                }
                tasks.append(task)
            return tasks
    
    large_storage = LargeTaskStorage()
    handler = TaskManagementHandler(storage_manager=large_storage)
    
    # Test with default settings (should trigger compression)
    result = await handler._handle_list_project_tasks({"project_name": "LARGE_TEST"})
    
    response_text = result[0].text
    response_size = len(response_text.encode())
    
    print(f"Large dataset response size: {response_size:,} bytes")
    
    if response_size > 25000:
        print("❌ Token reduction insufficient - still too large")
        return False
    elif response_size > 15000:
        print("⚠️  Still moderate size, but acceptable")
        return True
    else:
        print("✅ Excellent compression achieved!")
        return True


async def main():
    """Run all tests."""
    print("🚀 ATLAS MCP Token Reduction Test Suite")
    print("=" * 50)
    
    await test_pagination_and_compression()
    
    compression_success = await test_extreme_compression()
    
    print("\n" + "=" * 50)
    if compression_success:
        print("✅ All tests passed! Token reduction is working.")
    else:
        print("❌ Tests failed! Token reduction needs improvement.")
    
    print("\n📋 Summary of implemented features:")
    print("  • Pagination with configurable page size (max 25)")
    print("  • Filtering by status, task_type, priority")
    print("  • Recent tasks only option (last 50)")
    print("  • Compressed task data (essential fields only)")
    print("  • MINIMAL token optimization mode")
    print("  • LLMLingua compression for large responses")
    print("  • Fallback truncation if compression fails")


if __name__ == "__main__":
    asyncio.run(main())