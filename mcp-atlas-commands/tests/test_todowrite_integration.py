"""Tests for TodoWrite Integration module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, call

from atlas_commands.todowrite.integration import TodoWriteIntegration, TodoWriteManager


class TestTodoWriteIntegration:
    """Test suite for TodoWrite Integration."""
    
    def test_sync_checklist_to_todos(self, sample_checklist_items):
        """Test syncing checklist items to TodoWrite."""
        integration = TodoWriteIntegration()
        
        checklist = {
            "id": "test-checklist",
            "command": "plan",
            "items": sample_checklist_items
        }
        
        result = integration.sync_checklist_to_todos(checklist)
        
        assert result["success"] is True
        assert result["todos_created"] == 3
        assert result["todos_updated"] == 0
        assert len(result["todo_ids"]) == 3
    
    def test_sync_with_existing_todos(self, sample_checklist_items):
        """Test syncing when todos already exist."""
        integration = TodoWriteIntegration()
        
        # First sync
        checklist = {
            "id": "test-checklist",
            "command": "plan",
            "items": sample_checklist_items
        }
        
        first_result = integration.sync_checklist_to_todos(checklist)
        
        # Modify checklist
        checklist["items"][0]["status"] = "COMPLETED"
        checklist["items"][1]["status"] = "IN_PROGRESS"
        
        # Second sync
        second_result = integration.sync_checklist_to_todos(checklist)
        
        assert second_result["success"] is True
        assert second_result["todos_created"] == 0
        assert second_result["todos_updated"] == 2
    
    def test_create_milestone(self):
        """Test creating TodoWrite milestone."""
        integration = TodoWriteIntegration()
        
        result = integration.create_milestone(
            command="execute",
            phase="implementation",
            description="Core feature implementation"
        )
        
        assert result["success"] is True
        assert "milestone_id" in result
        assert result["milestone_id"].startswith("execute-implementation")
    
    def test_update_milestone_progress(self):
        """Test updating milestone progress."""
        integration = TodoWriteIntegration()
        
        # Create milestone
        milestone_result = integration.create_milestone(
            command="execute",
            phase="testing",
            description="Test implementation"
        )
        
        # Update progress
        update_result = integration.update_milestone_progress(
            milestone_id=milestone_result["milestone_id"],
            completed=5,
            total=10
        )
        
        assert update_result["success"] is True
        assert update_result["percentage"] == 50.0
        assert update_result["status"] == "in_progress"
    
    def test_milestone_completion(self):
        """Test milestone completion detection."""
        integration = TodoWriteIntegration()
        
        milestone_result = integration.create_milestone(
            command="verify",
            phase="validation",
            description="Final validation"
        )
        
        # Complete all tasks
        update_result = integration.update_milestone_progress(
            milestone_id=milestone_result["milestone_id"],
            completed=5,
            total=5
        )
        
        assert update_result["success"] is True
        assert update_result["percentage"] == 100.0
        assert update_result["status"] == "completed"
    
    def test_status_mapping(self):
        """Test checklist status to TodoWrite status mapping."""
        integration = TodoWriteIntegration()
        
        assert integration._map_status_to_todo("PENDING") == "pending"
        assert integration._map_status_to_todo("IN_PROGRESS") == "in_progress"
        assert integration._map_status_to_todo("COMPLETED") == "completed"
        assert integration._map_status_to_todo("BLOCKED") == "pending"
    
    def test_priority_mapping(self):
        """Test checklist priority to TodoWrite priority mapping."""
        integration = TodoWriteIntegration()
        
        assert integration._map_priority_to_todo("HIGH") == "high"
        assert integration._map_priority_to_todo("MEDIUM") == "medium"
        assert integration._map_priority_to_todo("LOW") == "low"
        assert integration._map_priority_to_todo("UNKNOWN") == "medium"


class TestTodoWriteManager:
    """Test suite for TodoWriteManager."""
    
    def test_singleton_pattern(self):
        """Test that TodoWriteManager follows singleton pattern."""
        manager1 = TodoWriteManager()
        manager2 = TodoWriteManager()
        
        assert manager1 is manager2
    
    def test_track_sync(self):
        """Test tracking sync operations."""
        manager = TodoWriteManager()
        manager.sync_history.clear()  # Clear any previous history
        
        manager.track_sync(
            checklist_id="test-checklist",
            todos_created=3,
            todos_updated=1
        )
        
        assert len(manager.sync_history) == 1
        assert manager.sync_history[0]["checklist_id"] == "test-checklist"
        assert manager.sync_history[0]["todos_created"] == 3
        assert manager.sync_history[0]["todos_updated"] == 1
    
    def test_get_sync_statistics(self):
        """Test getting sync statistics."""
        manager = TodoWriteManager()
        manager.sync_history.clear()
        
        # Add multiple sync operations
        manager.track_sync("checklist-1", todos_created=5, todos_updated=0)
        manager.track_sync("checklist-2", todos_created=0, todos_updated=3)
        manager.track_sync("checklist-3", todos_created=2, todos_updated=1)
        
        stats = manager.get_sync_statistics()
        
        assert stats["total_syncs"] == 3
        assert stats["total_todos_created"] == 7
        assert stats["total_todos_updated"] == 4
        assert stats["unique_checklists"] == 3
        assert stats["average_todos_per_sync"] == pytest.approx(3.67, 0.01)
    
    def test_batch_sync_operations(self, sample_checklist_items):
        """Test batch sync operations."""
        manager = TodoWriteManager()
        integration = TodoWriteIntegration()
        
        # Create multiple checklists
        checklists = [
            {
                "id": f"checklist-{i}",
                "command": "plan",
                "items": sample_checklist_items[:i+1]  # Varying sizes
            }
            for i in range(3)
        ]
        
        # Batch sync
        results = []
        for checklist in checklists:
            result = integration.sync_checklist_to_todos(checklist)
            results.append(result)
            manager.track_sync(
                checklist["id"],
                result["todos_created"],
                result["todos_updated"]
            )
        
        # Verify all synced
        assert all(r["success"] for r in results)
        assert manager.get_sync_statistics()["total_syncs"] == 3
    
    def test_error_handling_in_sync(self):
        """Test error handling during sync operations."""
        integration = TodoWriteIntegration()
        
        # Invalid checklist
        invalid_checklist = {
            "id": None,  # Invalid
            "items": []  # Empty
        }
        
        result = integration.sync_checklist_to_todos(invalid_checklist)
        
        assert result["success"] is False
        assert "error" in result
    
    def test_concurrent_milestone_updates(self):
        """Test handling concurrent milestone updates."""
        integration = TodoWriteIntegration()
        
        # Create milestone
        milestone = integration.create_milestone(
            command="execute",
            phase="parallel",
            description="Parallel execution"
        )
        
        milestone_id = milestone["milestone_id"]
        
        # Simulate concurrent updates
        updates = []
        for i in range(5):
            update = integration.update_milestone_progress(
                milestone_id=milestone_id,
                completed=i+1,
                total=5
            )
            updates.append(update)
        
        # All updates should succeed
        assert all(u["success"] for u in updates)
        
        # Final state should be correct
        assert updates[-1]["percentage"] == 100.0
        assert updates[-1]["status"] == "completed"