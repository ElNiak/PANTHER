"""Tests for Validation modules."""

import pytest
from datetime import datetime

from atlas_commands.validation import (
    InputValidator, OutputValidator, SemanticValidator,
    ValidationType, ValidationRule
)


class TestInputValidator:
    """Test suite for InputValidator."""
    
    def test_validate_create_checklist_valid(self):
        """Test validating valid create_checklist arguments."""
        validator = InputValidator()
        
        args = {
            "command_name": "plan",
            "task_id": "feature-auth-20250620",
            "items": [
                {"id": "1", "title": "Task 1", "status": "PENDING"}
            ]
        }
        
        result = validator.validate("create_unified_checklist", args)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
    
    def test_validate_missing_required_field(self):
        """Test validation with missing required field."""
        validator = InputValidator()
        
        args = {
            "task_id": "feature-123"
            # Missing command_name
        }
        
        result = validator.validate("create_unified_checklist", args)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "command_name is required" in result["errors"][0]
    
    def test_validate_invalid_command_name(self):
        """Test validation with invalid command name."""
        validator = InputValidator()
        
        args = {
            "command_name": "invalid-command",
            "task_id": "feature-123"
        }
        
        result = validator.validate("create_unified_checklist", args)
        
        assert result["valid"] is True  # Warning, not error
        assert len(result["warnings"]) > 0
        assert "valid ATLAS command" in result["warnings"][0]
    
    def test_auto_fix_task_id(self):
        """Test auto-fixing task ID format."""
        validator = InputValidator()
        
        args = {
            "command_name": "plan",
            "task_id": "my task with spaces!"  # Invalid format
        }
        
        result = validator.validate("create_unified_checklist", args)
        
        assert result["valid"] is True
        assert result["fixed_arguments"] is not None
        assert result["fixed_arguments"]["task_id"] == f"my-task-with-spaces-{datetime.now().strftime('%Y%m%d')}"
    
    def test_validate_status_values(self):
        """Test validating status values."""
        validator = InputValidator()
        
        # Valid status
        args = {
            "checklist_id": "test-123",
            "item_id": "item-1",
            "status": "COMPLETED"
        }
        
        result = validator.validate("update_checklist_item", args)
        assert result["valid"] is True
        
        # Invalid status
        args["status"] = "INVALID_STATUS"
        result = validator.validate("update_checklist_item", args)
        
        assert result["valid"] is False
        assert "must be one of" in result["errors"][0]
    
    def test_validate_memory_entity_observations(self):
        """Test validating memory entity observations."""
        validator = InputValidator()
        
        # Valid observations
        args = {
            "command_type": "plan",
            "target": "feature",
            "observations": ["First observation", "Second observation"]
        }
        
        result = validator.validate("create_memory_entity", args)
        assert result["valid"] is True
        
        # Empty observations
        args["observations"] = []
        result = validator.validate("create_memory_entity", args)
        
        assert result["valid"] is False
        assert "observations must not be empty" in result["errors"][0]
    
    def test_validate_range_constraint(self):
        """Test validating range constraints."""
        validator = InputValidator()
        
        # Valid range
        args = {"days_old": 30}
        result = validator.validate("compact_memory_graph", args)
        assert result["valid"] is True
        
        # Out of range - should auto-fix
        args = {"days_old": 500}
        result = validator.validate("compact_memory_graph", args)
        
        assert result["valid"] is True
        assert result["fixed_arguments"]["days_old"] == 365  # Clamped to max
    
    def test_custom_validation_rule(self):
        """Test adding custom validation rules."""
        validator = InputValidator()
        
        # Add custom rule
        custom_rule = ValidationRule(
            name="custom_check",
            validation_type=ValidationType.BUSINESS_RULE,
            check=lambda args: args.get("custom_field", "") == "expected",
            error_message="custom_field must be 'expected'"
        )
        
        validator.add_custom_rule("create_unified_checklist", custom_rule)
        
        # Test with custom field
        args = {
            "command_name": "plan",
            "task_id": "test",
            "custom_field": "wrong"
        }
        
        result = validator.validate("create_unified_checklist", args)
        assert len(result["errors"]) > 0
        assert "custom_field must be 'expected'" in result["errors"][0]


class TestOutputValidator:
    """Test suite for OutputValidator."""
    
    def test_validate_checklist_output(self):
        """Test validating checklist creation output."""
        validator = OutputValidator()
        
        output = {
            "checklist_markdown": "## Checklist (0/3 complete)\n- [ ] Task 1",
            "checklist_id": "plan_test-123",
            "item_count": 3
        }
        
        result = validator.validate_output("create_unified_checklist", output)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_missing_output_field(self):
        """Test validation with missing required output field."""
        validator = OutputValidator()
        
        output = {
            "checklist_markdown": "## Checklist",
            # Missing checklist_id and item_count
        }
        
        result = validator.validate_output("create_unified_checklist", output)
        
        assert result["valid"] is False
        assert len(result["errors"]) == 2
        assert any("checklist_id" in e for e in result["errors"])
        assert any("item_count" in e for e in result["errors"])
    
    def test_validate_output_constraints(self):
        """Test validating output constraints."""
        validator = OutputValidator()
        
        # Invalid item count
        output = {
            "checklist_markdown": "## Checklist",
            "checklist_id": "test-123",
            "item_count": 0  # Should be > 0
        }
        
        result = validator.validate_output("create_unified_checklist", output)
        
        assert result["valid"] is True  # Constraint is warning
        assert len(result["warnings"]) > 0
        assert "item_count failed constraint" in result["warnings"][0]
    
    def test_validate_memory_entity_output(self):
        """Test validating memory entity output."""
        validator = OutputValidator()
        
        output = {
            "entity_name": "workflow_plan_feature_initial",
            "command_type": "plan",
            "target": "feature",
            "observation_count": 2
        }
        
        result = validator.validate_output("create_memory_entity", output)
        
        assert result["valid"] is True
        
        # Check naming convention
        output["entity_name"] = "badname"  # No underscores
        result = validator.validate_output("create_memory_entity", output)
        
        assert len(result["warnings"]) > 0


class TestSemanticValidator:
    """Test suite for SemanticValidator."""
    
    def test_validate_checklist_consistency(self):
        """Test validating checklist dependency consistency."""
        validator = SemanticValidator()
        
        context = {
            "checklist_items": [
                {"id": "1", "dependencies": []},
                {"id": "2", "dependencies": ["1"]},
                {"id": "3", "dependencies": ["2", "nonexistent"]}  # Invalid
            ]
        }
        
        result = validator.validate_semantic_context("create_checklist", context)
        
        assert result["valid"] is False
        assert "inconsistent dependencies" in result["errors"][0]
    
    def test_validate_workflow_step_order(self):
        """Test validating workflow step order."""
        validator = SemanticValidator()
        
        context = {
            "workflow_pattern": "explore-plan-code-commit",
            "steps": [
                {"command": "explore"},
                {"command": "plan"},
                {"command": "code"},
                {"command": "commit"}
            ]
        }
        
        result = validator.validate_semantic_context("create_workflow", context)
        
        assert result["valid"] is True
    
    def test_get_context_suggestions(self):
        """Test getting context-specific suggestions."""
        validator = SemanticValidator()
        
        # Large checklist
        context = {
            "item_count": 25,
            "checklist_items": []
        }
        
        result = validator.validate_semantic_context("create_unified_checklist", context)
        
        assert len(result["suggestions"]) > 0
        assert "smaller checklists" in result["suggestions"][0]
        
        # Complex workflow
        context = {
            "step_count": 15,
            "workflow_pattern": "custom"
        }
        
        result = validator.validate_semantic_context("create_workflow", context)
        
        assert len(result["suggestions"]) > 0
        assert "sub-workflows" in result["suggestions"][0]