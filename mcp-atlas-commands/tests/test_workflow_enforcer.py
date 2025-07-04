"""Tests for Workflow Enforcer module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from atlas_commands.workflow.enforcer import WorkflowEnforcer, CommandValidator


class TestWorkflowEnforcer:
    """Test suite for WorkflowEnforcer."""
    
    def test_create_workflow(self, sample_workflow_steps):
        """Test creating a new workflow."""
        enforcer = WorkflowEnforcer()
        
        result = enforcer.create_workflow(
            workflow_id="test-workflow-123",
            pattern="explore-plan-code-commit",
            target="refactoring-task",
            steps=sample_workflow_steps
        )
        
        assert result["workflow_id"] == "test-workflow-123"
        assert result["pattern"] == "explore-plan-code-commit"
        assert result["target"] == "refactoring-task"
        assert result["step_count"] == 3
        assert result["current_step"] == 0
    
    def test_execute_workflow_step(self, sample_workflow_steps):
        """Test executing workflow steps."""
        enforcer = WorkflowEnforcer()
        
        # Create workflow
        create_result = enforcer.create_workflow(
            workflow_id="exec-test",
            pattern="explore-plan-code-commit",
            target="feature",
            steps=sample_workflow_steps
        )
        
        # Execute first step
        exec_result = enforcer.execute_step(
            workflow_id="exec-test",
            step_index=0
        )
        
        assert exec_result["success"] is True
        assert exec_result["executed_step"]["command"] == "explore"
        assert exec_result["next_step"] == 1
        assert exec_result["workflow_complete"] is False
    
    def test_complete_workflow(self, sample_workflow_steps):
        """Test completing entire workflow."""
        enforcer = WorkflowEnforcer()
        
        # Create workflow
        enforcer.create_workflow(
            workflow_id="complete-test",
            pattern="explore-plan-code-commit",
            target="feature",
            steps=sample_workflow_steps
        )
        
        # Execute all steps
        for i in range(len(sample_workflow_steps)):
            result = enforcer.execute_step("complete-test", i)
            
            if i < len(sample_workflow_steps) - 1:
                assert result["workflow_complete"] is False
            else:
                assert result["workflow_complete"] is True
    
    def test_workflow_validation(self):
        """Test workflow step validation."""
        enforcer = WorkflowEnforcer()
        
        # Invalid pattern
        result = enforcer.create_workflow(
            workflow_id="invalid-test",
            pattern="invalid-pattern",
            target="test",
            steps=[]
        )
        
        assert "error" in result or "warning" in result
    
    def test_parallel_workflow_execution(self):
        """Test executing multiple workflows in parallel."""
        enforcer = WorkflowEnforcer()
        
        # Create multiple workflows
        workflow_ids = []
        for i in range(3):
            result = enforcer.create_workflow(
                workflow_id=f"parallel-{i}",
                pattern="quick-fix",
                target=f"bug-{i}",
                steps=[
                    {"command": "analyze", "target": f"bug-{i}"},
                    {"command": "fix", "target": f"bug-{i}"}
                ]
            )
            workflow_ids.append(result["workflow_id"])
        
        # Execute steps in different workflows
        enforcer.execute_step(workflow_ids[0], 0)
        enforcer.execute_step(workflow_ids[1], 0)
        enforcer.execute_step(workflow_ids[0], 1)
        
        # Check states
        assert enforcer.workflows[workflow_ids[0]]["current_step"] == 2
        assert enforcer.workflows[workflow_ids[1]]["current_step"] == 1
        assert enforcer.workflows[workflow_ids[2]]["current_step"] == 0
    
    def test_workflow_with_options(self):
        """Test workflow with additional options."""
        enforcer = WorkflowEnforcer()
        
        result = enforcer.create_workflow(
            workflow_id="options-test",
            pattern="explore-plan-code-commit",
            target="complex-feature",
            steps=[{"command": "plan", "target": "feature"}],
            options={
                "auto_advance": True,
                "parallel": True,
                "yolo_mode": True
            }
        )
        
        assert result["options"]["auto_advance"] is True
        assert result["options"]["parallel"] is True
        assert result["options"]["yolo_mode"] is True
    
    def test_get_workflow_status(self, sample_workflow_steps):
        """Test getting workflow status."""
        enforcer = WorkflowEnforcer()
        
        # Create and partially execute workflow
        enforcer.create_workflow(
            workflow_id="status-test",
            pattern="explore-plan-code-commit",
            target="feature",
            steps=sample_workflow_steps
        )
        
        enforcer.execute_step("status-test", 0)
        
        status = enforcer.get_workflow_status("status-test")
        
        assert status["workflow_id"] == "status-test"
        assert status["current_step"] == 1
        assert status["total_steps"] == 3
        assert status["progress_percentage"] == pytest.approx(33.33, 0.01)
        assert status["is_complete"] is False


class TestCommandValidator:
    """Test suite for CommandValidator."""
    
    def test_validate_valid_command(self):
        """Test validating a valid command."""
        validator = CommandValidator()
        
        result = validator.validate_command(
            command="plan",
            parameters={
                "task_type": "feature",
                "description": "New authentication system",
                "computational_depth": 3
            }
        )
        
        assert result["valid"] is True
        assert result["can_execute"] is True
        assert len(result["warnings"]) == 0
    
    def test_validate_command_with_prerequisites(self):
        """Test command with unmet prerequisites."""
        validator = CommandValidator()
        
        # Try to execute without planning
        result = validator.validate_command(
            command="execute",
            parameters={
                "task_id": "feature-123"
            }
        )
        
        # Should get warning about missing plan
        assert result["valid"] is True  # Still valid
        assert len(result["warnings"]) > 0
        assert any("plan" in w.lower() for w in result["warnings"])
    
    def test_validate_command_sequence(self):
        """Test validating command sequence."""
        validator = CommandValidator()
        
        # Track command execution
        validator.mark_command_executed("plan", {"task_id": "test-123"})
        
        # Now execute should have no warnings
        result = validator.validate_command(
            command="execute",
            parameters={"task_id": "test-123"}
        )
        
        assert result["valid"] is True
        assert len(result["warnings"]) == 0
    
    def test_validate_invalid_parameters(self):
        """Test validating command with invalid parameters."""
        validator = CommandValidator()
        
        result = validator.validate_command(
            command="plan",
            parameters={
                "computational_depth": "invalid"  # Should be int
            }
        )
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_command_compatibility_check(self):
        """Test checking command compatibility."""
        validator = CommandValidator()
        
        # Check if commands can run in parallel
        compat1 = validator.check_compatibility("plan", "analyze")
        assert compat1["compatible"] is True
        
        # Check conflicting commands
        compat2 = validator.check_compatibility("execute", "execute")
        assert compat2["compatible"] is False
        assert "reason" in compat2
    
    def test_get_command_history(self):
        """Test retrieving command execution history."""
        validator = CommandValidator()
        
        # Execute several commands
        commands = [
            ("plan", {"task_id": "task-1"}),
            ("analyze", {"target": "codebase"}),
            ("execute", {"task_id": "task-1"})
        ]
        
        for cmd, params in commands:
            validator.mark_command_executed(cmd, params)
        
        history = validator.get_command_history()
        
        assert len(history) == 3
        assert history[0]["command"] == "plan"
        assert history[-1]["command"] == "execute"
        assert all("timestamp" in h for h in history)