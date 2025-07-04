#!/usr/bin/env python3
"""Test migration for a single PANTHER task."""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the path
sys.path.append('src')
from atlas_commands.storage.task_storage_manager import TaskStorageManager

def test_single_task_migration():
    """Test migration on a single task to verify the logic."""
    
    # Create a temporary copy to test on
    source_dir = Path("/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_repos = Path(temp_dir) / "REPOS"
        temp_repos.mkdir()
        
        # Copy just one parent task and its subtasks
        target_task = "PANTHER_TASK_configuration_comprehensive-configuration-validation-enhancement_20250621_033504"
        
        source_tasks_dir = source_dir / "PANTHER_TASKS"
        temp_tasks_dir = temp_repos / "PANTHER_TASKS"
        temp_tasks_dir.mkdir()
        
        # Copy the parent task
        parent_source = source_tasks_dir / target_task
        parent_dest = temp_tasks_dir / target_task
        shutil.copytree(parent_source, parent_dest)
        
        # Copy the subtasks
        subtask_pattern = f"PANTHER_SUBTASK_{target_task}_"
        for item in source_tasks_dir.iterdir():
            if item.is_dir() and item.name.startswith(subtask_pattern):
                dest = temp_tasks_dir / item.name
                shutil.copytree(item, dest)
                print(f"Copied subtask: {item.name}")
        
        # Create storage manager for temp directory
        storage = TaskStorageManager(str(temp_repos))
        
        # Test dry run first
        print("\n=== DRY RUN ===")
        dry_result = storage.migrate_to_nested_storage("PANTHER", dry_run=True)
        print(f"Tasks analyzed: {dry_result['tasks_analyzed']}")
        print(f"Subtasks found: {dry_result['subtasks_found']}")
        print(f"Migrations planned: {len(dry_result['migrations_planned'])}")
        
        if dry_result['migrations_planned']:
            migration = dry_result['migrations_planned'][0]
            print(f"Task to migrate: {migration['task_id']}")
            print(f"Subtask count: {migration['subtask_count']}")
        
        # Run actual migration
        print("\n=== ACTUAL MIGRATION ===")
        result = storage.migrate_to_nested_storage("PANTHER", dry_run=False)
        print(f"Migration completed: {result['tasks_analyzed']} tasks, {result['subtasks_found']} subtasks")
        
        # Check the result
        parent_task_path = temp_tasks_dir / target_task / "task.json"
        with open(parent_task_path, 'r') as f:
            parent_task = json.load(f)
        
        print(f"\nParent task after migration:")
        print(f"- nested_storage_enabled: {parent_task.get('nested_storage_enabled', False)}")
        print(f"- has subtasks array: {'subtasks' in parent_task}")
        if 'subtasks' in parent_task:
            print(f"- subtasks count: {len(parent_task['subtasks'])}")
            for i, subtask in enumerate(parent_task['subtasks'][:2]):
                print(f"  {i+1}. {subtask.get('task_id', 'no-id')}: {subtask.get('description', 'no-desc')[:50]}...")
        
        # Check if .migrated directory was created
        migrated_dir = temp_tasks_dir / ".migrated"
        if migrated_dir.exists():
            migrated_items = list(migrated_dir.iterdir())
            print(f"\nMigrated directories: {len(migrated_items)}")
            for item in migrated_items[:3]:
                print(f"  - {item.name}")
        else:
            print("\nNo .migrated directory created")

if __name__ == "__main__":
    test_single_task_migration()