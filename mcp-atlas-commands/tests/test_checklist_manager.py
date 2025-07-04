"""Tests for the Checklist Manager module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from atlas_commands.checklist.manager import ChecklistManager
from atlas_commands.checklist.templates import ChecklistTemplates


class TestChecklistManager:
    """Test suite for ChecklistManager."""
    
    def test_create_checklist_with_items(self, sample_checklist_items):
        """Test creating a checklist with provided items."""
        manager = ChecklistManager()
        
        result = manager.create_checklist(
            command_name="plan",
            task_id="test-feature-123",
            items=sample_checklist_items
        )
        
        assert result["checklist_id"] == "plan_test-feature-123"
        assert result["item_count"] == 3
        assert "(0/3 complete)" in result["checklist_markdown"]
        assert "Initialize project" in result["checklist_markdown"]
        assert "Write core implementation" in result["checklist_markdown"]
        assert "Add tests" in result["checklist_markdown"]
    
    def test_create_checklist_from_template(self):
        """Test creating a checklist from template."""
        manager = ChecklistManager()
        
        result = manager.create_checklist(
            command_name="plan",
            task_id="test-feature-456",
            template_type="standard"
        )
        
        assert result["checklist_id"] == "plan_test-feature-456"
        assert result["item_count"] > 0
        assert "complete)" in result["checklist_markdown"]
    
    def test_update_item_status(self, sample_checklist_items):
        """Test updating checklist item status."""
        manager = ChecklistManager()
        
        # Create checklist first
        create_result = manager.create_checklist(
            command_name="plan",
            task_id="test-update",
            items=sample_checklist_items
        )
        
        # Update item status
        update_result = manager.update_item(
            checklist_id=create_result["checklist_id"],
            item_id="item-1",
            status="COMPLETED"
        )
        
        assert update_result["success"] is True
        assert update_result["new_status"] == "COMPLETED"
        assert update_result["progress"]["completed"] == 1
        assert update_result["progress"]["total"] == 3
    
    def test_update_nonexistent_checklist(self):
        """Test updating item in nonexistent checklist."""
        manager = ChecklistManager()
        
        update_result = manager.update_item(
            checklist_id="nonexistent-checklist",
            item_id="item-1",
            status="COMPLETED"
        )
        
        assert update_result["success"] is False
        assert "not found" in update_result["error"]
    
    def test_get_checklist_progress(self, sample_checklist_items):
        """Test getting checklist progress."""
        manager = ChecklistManager()
        
        # Create and update checklist
        create_result = manager.create_checklist(
            command_name="plan",
            task_id="test-progress",
            items=sample_checklist_items
        )
        
        manager.update_item(
            checklist_id=create_result["checklist_id"],
            item_id="item-1",
            status="COMPLETED"
        )
        
        manager.update_item(
            checklist_id=create_result["checklist_id"],
            item_id="item-2",
            status="IN_PROGRESS"
        )
        
        progress = manager.get_progress(create_result["checklist_id"])
        
        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert progress["in_progress"] == 1
        assert progress["pending"] == 1
        assert progress["completion_percentage"] == pytest.approx(33.33, 0.01)
    
    def test_dependency_validation(self, sample_checklist_items):
        """Test that dependencies are validated when updating status."""
        manager = ChecklistManager()
        
        create_result = manager.create_checklist(
            command_name="plan",
            task_id="test-deps",
            items=sample_checklist_items
        )
        
        # Try to complete item-2 without completing item-1
        update_result = manager.update_item(
            checklist_id=create_result["checklist_id"],
            item_id="item-2",
            status="COMPLETED"
        )
        
        # Should succeed but with warning
        assert update_result["success"] is True
        assert len(update_result.get("warnings", [])) > 0
        assert "dependency" in update_result["warnings"][0].lower()
    
    def test_checklist_markdown_formatting(self):
        """Test markdown formatting of checklist."""
        manager = ChecklistManager()
        
        items = [
            {
                "id": "1",
                "title": "Task with **bold** text",
                "status": "COMPLETED",
                "priority": "HIGH"
            },
            {
                "id": "2",
                "title": "Task with `code` blocks",
                "status": "IN_PROGRESS",
                "priority": "MEDIUM"
            },
            {
                "id": "3",
                "title": "Normal task",
                "status": "PENDING",
                "priority": "LOW"
            }
        ]
        
        result = manager.create_checklist(
            command_name="test",
            task_id="format-test",
            items=items
        )
        
        markdown = result["checklist_markdown"]
        
        # Check progress indicator
        assert "(1/3 complete)" in markdown
        
        # Check status indicators
        assert "- [x]" in markdown  # COMPLETED
        assert "- [~]" in markdown  # IN_PROGRESS
        assert "- [ ]" in markdown  # PENDING
        
        # Check priority indicators
        assert "🔴" in markdown  # HIGH
        assert "🟡" in markdown  # MEDIUM
        assert "🟢" in markdown  # LOW
        
        # Check markdown preservation
        assert "**bold**" in markdown
        assert "`code`" in markdown
    
    def test_multiple_checklists(self):
        """Test managing multiple checklists simultaneously."""
        manager = ChecklistManager()
        
        # Create multiple checklists
        checklist1 = manager.create_checklist(
            command_name="plan",
            task_id="feature-1",
            items=[{"id": "1", "title": "Plan task", "status": "PENDING"}]
        )
        
        checklist2 = manager.create_checklist(
            command_name="execute",
            task_id="feature-2",
            items=[{"id": "1", "title": "Execute task", "status": "PENDING"}]
        )
        
        # Verify they're independent
        assert checklist1["checklist_id"] != checklist2["checklist_id"]
        assert len(manager.checklists) == 2
        
        # Update one shouldn't affect the other
        manager.update_item(
            checklist_id=checklist1["checklist_id"],
            item_id="1",
            status="COMPLETED"
        )
        
        progress1 = manager.get_progress(checklist1["checklist_id"])
        progress2 = manager.get_progress(checklist2["checklist_id"])
        
        assert progress1["completed"] == 1
        assert progress2["completed"] == 0
    
    def test_export_import_checklist(self, sample_checklist_items):
        """Test exporting and importing checklist state."""
        manager1 = ChecklistManager()
        
        # Create and modify checklist
        create_result = manager1.create_checklist(
            command_name="plan",
            task_id="export-test",
            items=sample_checklist_items
        )
        
        manager1.update_item(
            checklist_id=create_result["checklist_id"],
            item_id="item-1",
            status="COMPLETED"
        )
        
        # Export state
        exported = manager1.export_checklist(create_result["checklist_id"])
        
        # Import into new manager
        manager2 = ChecklistManager()
        import_result = manager2.import_checklist(exported)
        
        assert import_result["success"] is True
        assert import_result["checklist_id"] == create_result["checklist_id"]
        
        # Verify state preserved
        progress = manager2.get_progress(create_result["checklist_id"])
        assert progress["completed"] == 1
        assert progress["total"] == 3