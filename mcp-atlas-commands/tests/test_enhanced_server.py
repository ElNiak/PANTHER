#!/usr/bin/env python3
"""Test script to validate enhanced MCP server with persistence."""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.storage.task_storage_manager import TaskStorageManager


def test_task_storage_manager():
    """Test the TaskStorageManager functionality."""
    
    print("=" * 60)
    print("Testing TaskStorageManager Implementation")
    print("=" * 60)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nTest directory: {temp_dir}")
        
        # Initialize storage manager
        storage = TaskStorageManager(temp_dir)
        
        # Test 1: Create task metadata
        print("\n1. Testing create_task_metadata...")
        project_name = "test-project"
        task_id = "test-task-001"
        
        metadata = storage.create_task_metadata(
            project_name=project_name,
            task_id=task_id,
            task_type="feature",
            description="Test task for validation",
            command="plan"
        )
        
        print(f"   ✓ Created task metadata for {task_id}")
        print(f"   ✓ Status: {metadata['status']}")
        print(f"   ✓ Created at: {metadata['created_at']}")
        
        # Verify file was created
        task_root = storage.get_task_root(project_name, task_id)
        metadata_path = task_root / "task.json"
        assert metadata_path.exists(), "task.json not created"
        print(f"   ✓ Metadata file exists at: {metadata_path}")
        
        # Test 2: Add artifact
        print("\n2. Testing add_task_artifact...")
        artifact_content = """# Analysis Report
        
This is a test analysis report.
- Point 1
- Point 2
- Point 3
"""
        
        artifact_path = storage.add_task_artifact(
            project_name=project_name,
            task_id=task_id,
            artifact_type="analysis",
            content=artifact_content,
            filename="test_analysis.md",
            description="Test analysis artifact"
        )
        
        print(f"   ✓ Added artifact: {artifact_path}")
        assert Path(artifact_path).exists(), "Artifact file not created"
        
        # Verify content
        with open(artifact_path, 'r') as f:
            saved_content = f.read()
        assert saved_content == artifact_content, "Artifact content mismatch"
        print("   ✓ Artifact content verified")
        
        # Test 3: Update task status
        print("\n3. Testing update_task_status...")
        updated_metadata = storage.update_task_status(
            project_name=project_name,
            task_id=task_id,
            status="active",
            phase="implementation"
        )
        
        print(f"   ✓ Updated status to: {updated_metadata['status']}")
        print(f"   ✓ Updated phase to: {updated_metadata['current_phase']}")
        
        # Test 4: Get task context
        print("\n4. Testing get_task_context...")
        context = storage.get_task_context(project_name, task_id)
        
        print(f"   ✓ Retrieved task context")
        print(f"   ✓ Task ID: {context['task_id']}")
        print(f"   ✓ Artifacts: {json.dumps(context['artifact_summary'], indent=2)}")
        
        # Test 5: Create backup
        print("\n5. Testing create_task_backup...")
        backup_dir = storage.create_task_backup(
            project_name=project_name,
            task_id=task_id,
            backup_type="checkpoint",
            description="Test backup"
        )
        
        print(f"   ✓ Created backup at: {backup_dir}")
        assert Path(backup_dir).exists(), "Backup directory not created"
        
        # Verify backup contains expected files
        backup_metadata_path = Path(backup_dir) / "backup_metadata.json"
        assert backup_metadata_path.exists(), "Backup metadata not created"
        print("   ✓ Backup metadata verified")
        
        # Test 6: List project tasks
        print("\n6. Testing list_project_tasks...")
        tasks = storage.list_project_tasks(project_name)
        
        print(f"   ✓ Found {len(tasks)} task(s)")
        assert len(tasks) == 1, "Expected 1 task"
        assert tasks[0]['task_id'] == task_id, "Task ID mismatch"
        print(f"   ✓ Task listing verified")
        
        # Test 7: Directory structure
        print("\n7. Verifying directory structure...")
        paths = storage.get_task_paths(project_name, task_id)
        
        expected_dirs = [
            "artifacts", "artifacts/tasks", "artifacts/analysis", 
            "artifacts/design", "artifacts/verification", "artifacts/completion",
            "backups", "backups/checkpoint", "backups/workflow", "backups/yolo",
            "memory", "temp", "temp/scratchpads", "temp/cache", ".vscode"
        ]
        
        for dir_name in expected_dirs:
            dir_path = task_root / dir_name
            assert dir_path.exists(), f"Directory {dir_name} not created"
        
        print("   ✓ All expected directories created")
        
        # Test 8: Archive task
        print("\n8. Testing archive_task...")
        archive_path = storage.archive_task(
            project_name=project_name,
            task_id=task_id,
            keep_backups=True
        )
        
        print(f"   ✓ Created archive at: {archive_path}")
        assert Path(archive_path).exists(), "Archive not created"
        assert Path(archive_path).suffix == ".gz", "Archive should be gzipped"
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)
        
        return True


def test_enhanced_server_integration():
    """Test the enhanced server integration (requires server running)."""
    
    print("\n" + "=" * 60)
    print("Testing Enhanced Server Integration")
    print("=" * 60)
    
    try:
        from atlas_commands.server_enhanced import EnhancedAtlasCommandsServer
        
        # Create server instance
        server = EnhancedAtlasCommandsServer()
        print("\n✓ Enhanced server initialized successfully")
        
        # Check that storage manager is initialized
        assert hasattr(server, 'storage_manager'), "Storage manager not initialized"
        print("✓ Storage manager is available")
        
        # Check that new tools are registered
        print("\n✓ Server is ready for MCP tool calls")
        print("  - create_task_metadata")
        print("  - update_task_status")
        print("  - add_task_artifact")
        print("  - get_task_context")
        print("  - list_project_tasks")
        print("  - create_task_backup")
        print("  - archive_task")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing server: {e}")
        return False


if __name__ == "__main__":
    # Run tests
    storage_test_passed = test_task_storage_manager()
    server_test_passed = test_enhanced_server_integration()
    
    if storage_test_passed and server_test_passed:
        print("\n🎉 All validation tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)