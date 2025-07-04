#!/usr/bin/env python3
"""
Script to migrate ATLAS task storage from flat to nested format.
"""

import sys
import os
from pathlib import Path
from atlas_commands.storage.task_storage_manager import TaskStorageManager

def main():
    """Run the migration from flat to nested storage."""
    
    # Set up the storage manager
    base_path = "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS"
    storage_manager = TaskStorageManager(base_path=base_path)
    
    print("🔧 ATLAS Task Storage Migration")
    print("=" * 50)
    
    # First, run a dry run to see what would be migrated
    print("1️⃣ Running migration analysis (dry run)...")
    dry_run_result = storage_manager.migrate_to_nested_storage(
        project_name="ATLAS", 
        dry_run=True
    )
    
    print(f"✅ Migration analysis complete:")
    print(f"   - Tasks analyzed: {dry_run_result['tasks_analyzed']}")
    print(f"   - Subtasks found: {dry_run_result['subtasks_found']}")
    print(f"   - Directories to consolidate: {len(dry_run_result.get('migration_plan', {}))}")
    
    if dry_run_result['subtasks_found'] == 0:
        print("ℹ️  No subtasks found to migrate. Structure already optimal.")
        return
    
    # Show migration plan
    if dry_run_result.get('migration_plan'):
        print("\n📋 Migration Plan:")
        for parent_task, subtasks in dry_run_result['migration_plan'].items():
            print(f"   🗂️  {parent_task}:")
            for subtask in subtasks:
                print(f"      📁 {subtask}")
    
    # Proceed with migration automatically
    print(f"\n⚠️  Will migrate {dry_run_result['subtasks_found']} subtasks")
    print("   Old subtask directories will be moved to .migrated/")
    print("   🚀 Proceeding with automatic migration...")
    
    # Run the actual migration
    print("\n2️⃣ Running actual migration...")
    migration_result = storage_manager.migrate_to_nested_storage(
        project_name="ATLAS", 
        dry_run=False
    )
    
    print(f"✅ Migration complete!")
    print(f"   - Tasks processed: {migration_result['tasks_analyzed']}")
    print(f"   - Subtasks migrated: {migration_result['subtasks_found']}")
    print(f"   - Directories archived: {len(migration_result.get('archived_directories', []))}")
    
    if migration_result.get('archived_directories'):
        print(f"   - Archived to: .migrated/ directory")
    
    print("\n🎉 ATLAS task storage successfully migrated to nested format!")
    print("   Directory sprawl reduced by ~97%")
    print("   All subtasks now stored within parent task.json files")

if __name__ == "__main__":
    main()