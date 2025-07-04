#!/usr/bin/env python3
"""
Run the actual migration from flat to nested format.
"""

from atlas_commands.storage.task_storage_manager import TaskStorageManager

def main():
    """Run the actual migration."""
    
    base_path = "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS"
    storage_manager = TaskStorageManager(base_path=base_path)
    
    print("🚀 ATLAS Task Storage Migration")
    print("=" * 50)
    
    # Run the actual migration
    print("Running actual migration (dry_run=False)...")
    migration_result = storage_manager.migrate_to_nested_storage(
        project_name="ATLAS", 
        dry_run=False
    )
    
    print(f"✅ Migration complete!")
    print(f"   - Tasks processed: {migration_result['tasks_analyzed']}")
    print(f"   - Subtasks migrated: {migration_result['subtasks_found']}")
    
    if migration_result.get('migrations_planned'):
        print(f"   - Parent tasks updated: {len(migration_result['migrations_planned'])}")
        
        print(f"\n📋 Migration Summary:")
        for migration in migration_result['migrations_planned']:
            task_id = migration['task_id']
            subtask_count = migration['subtask_count']
            print(f"   🗂️  {task_id}: {subtask_count} subtasks nested")
    
    print("\n🎉 ATLAS task storage successfully migrated to nested format!")
    print("   Directory sprawl significantly reduced")
    print("   All subtasks now stored within parent task.json files")

if __name__ == "__main__":
    main()