#!/usr/bin/env python3
"""Test script for nested storage functionality."""

import json
from pathlib import Path
from atlas_commands.storage.task_storage_manager import TaskStorageManager

def test_nested_storage():
    """Test the nested storage implementation."""
    
    # Initialize storage manager
    storage = TaskStorageManager("/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS")
    
    print("🔍 Testing Nested Storage Implementation")
    print("=" * 50)
    
    # Test 1: Migration dry run
    print("\n1️⃣ Running migration analysis (dry run)...")
    try:
        report = storage.migrate_to_nested_storage("ATLAS", dry_run=True)
        print(f"✅ Migration analysis complete:")
        print(f"   - Tasks analyzed: {report.get('tasks_analyzed', 0)}")
        print(f"   - Subtasks found: {report.get('subtasks_found', 0)}")
        
        if 'storage_optimization' in report:
            opt = report['storage_optimization']
            print(f"   - Current directories: {opt.get('current_directories', 0)}")
            print(f"   - After migration: {opt.get('directories_after_migration', 0)}")
            print(f"   - Reduction: {opt.get('reduction_percentage', 0)}%")
    except Exception as e:
        print(f"❌ Migration analysis failed: {e}")
    
    # Test 2: Create nested subtask
    print("\n2️⃣ Testing nested subtask creation...")
    test_parent_id = "ATLAS_TASK_infrastructure_mcp-enhancement-implementation_20250622_031755"
    
    try:
        # First check if parent exists
        parent_root = storage.get_task_root("ATLAS", test_parent_id)
        if not (parent_root / "task.json").exists():
            print(f"⚠️  Parent task {test_parent_id} not found")
        else:
            # Create a test subtask
            subtask_data = {
                "task_name": "test-nested-subtask",
                "description": "Test subtask for nested storage validation",
                "priority": "low",
                "estimated_hours": 0.5
            }
            
            subtask_id = storage.create_nested_task("ATLAS", test_parent_id, subtask_data)
            print(f"✅ Created nested subtask: {subtask_id}")
            
            # Verify it was added to parent
            with open(parent_root / "task.json", 'r') as f:
                parent_data = json.load(f)
            
            subtasks = parent_data.get("subtasks", [])
            print(f"   - Parent now has {len(subtasks)} subtasks")
            
            # Test retrieving the subtask
            retrieved = storage.get_nested_task("ATLAS", test_parent_id, [subtask_id])
            print(f"✅ Retrieved subtask: {retrieved.get('task_id')}")
            
    except Exception as e:
        print(f"❌ Nested subtask test failed: {e}")
    
    # Test 3: Count task hierarchy
    print("\n3️⃣ Testing hierarchy counting...")
    try:
        hierarchy = storage.get_full_hierarchy("ATLAS", test_parent_id)
        counts = storage.count_nested_tasks(hierarchy)
        print(f"✅ Hierarchy counts:")
        print(f"   - Tasks: {counts.get('tasks', 0)}")
        print(f"   - Subtasks: {counts.get('subtasks', 0)}")
        print(f"   - Subsubtasks: {counts.get('subsubtasks', 0)}")
    except Exception as e:
        print(f"❌ Hierarchy counting failed: {e}")
    
    print("\n" + "=" * 50)
    print("✨ Nested storage testing complete!")

if __name__ == "__main__":
    test_nested_storage()