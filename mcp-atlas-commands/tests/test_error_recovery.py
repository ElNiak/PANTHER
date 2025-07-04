"""Tests for Error Recovery and Circuit Breaker modules."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from atlas_commands.errors import (
    AtlasCommandError, ChecklistError, TodoWriteError,
    MemoryError, WorkflowError, ValidationError, ResourceError,
    ErrorSeverity, ErrorRecovery, CircuitBreaker
)


class TestAtlasCommandError:
    """Test suite for AtlasCommandError base class."""
    
    def test_error_creation(self):
        """Test creating custom error with all attributes."""
        error = AtlasCommandError(
            message="Test error occurred",
            severity=ErrorSeverity.WARNING,
            recovery_suggestions=["Try again", "Check configuration"],
            context={"operation": "test", "user": "test-user"}
        )
        
        assert str(error) == "Test error occurred"
        assert error.severity == ErrorSeverity.WARNING
        assert len(error.recovery_suggestions) == 2
        assert error.context["operation"] == "test"
        assert isinstance(error.timestamp, datetime)
    
    def test_error_hierarchy(self):
        """Test error class hierarchy."""
        checklist_err = ChecklistError("Checklist not found")
        todo_err = TodoWriteError("Sync failed")
        memory_err = MemoryError("Entity exists")
        
        assert isinstance(checklist_err, AtlasCommandError)
        assert isinstance(todo_err, AtlasCommandError)
        assert isinstance(memory_err, AtlasCommandError)


class TestErrorRecovery:
    """Test suite for ErrorRecovery class."""
    
    def test_handle_checklist_error(self):
        """Test handling checklist errors with recovery."""
        recovery = ErrorRecovery()
        
        error = ChecklistError(
            "Checklist not found",
            recovery_suggestions=["Create new checklist"]
        )
        
        result = recovery.handle_error(
            error=error,
            operation="update_checklist",
            context={"command_name": "plan", "task_id": "test-123"}
        )
        
        assert result["error"] == "Checklist not found"
        assert result["severity"] == "error"
        assert result["operation"] == "update_checklist"
        assert len(result["suggestions"]) > 0
    
    def test_auto_recovery_create_checklist(self):
        """Test automatic recovery by creating default checklist."""
        recovery = ErrorRecovery()
        
        error = ChecklistError("Checklist not found for task")
        
        with patch.object(recovery, '_recover_create_default_checklist', return_value=True):
            result = recovery.handle_error(
                error=error,
                operation="get_checklist",
                context={"command_name": "plan", "task_id": "test-123"}
            )
            
            assert result["recovery_attempted"] is True
            assert result["recovery_successful"] is True
            assert result["recovery_action"] == "create_default_checklist"
    
    def test_retry_sync_with_backoff(self):
        """Test retry sync with exponential backoff."""
        recovery = ErrorRecovery()
        
        error = TodoWriteError("TodoWrite sync failed - connection timeout")
        
        # First attempt
        result1 = recovery.handle_error(
            error=error,
            operation="sync_todos",
            context={"checklist_id": "test-123"}
        )
        
        assert result1["recovery_attempted"] is True
        
        # Check retry count in context
        recovery_strategy = recovery._find_recovery_strategies(error)[0]
        assert recovery_strategy["action"] == "retry_sync"
    
    def test_memory_compaction_recovery(self):
        """Test recovery by compacting memory graph."""
        recovery = ErrorRecovery()
        
        error = MemoryError("Memory graph full - cannot add entity")
        
        with patch('atlas_commands.memory.graph_manager.MemoryGraphManager') as mock_manager:
            mock_instance = Mock()
            mock_instance.compact_old_entities.return_value = {
                "compacted_count": 10,
                "space_freed": "5MB"
            }
            
            context = {"memory_manager": mock_instance}
            
            result = recovery.handle_error(
                error=error,
                operation="create_entity",
                context=context
            )
            
            # Should attempt compaction
            assert "compact_and_retry" in str(result.get("recovery_action", ""))
    
    def test_validation_error_auto_fix(self):
        """Test auto-fixing validation errors."""
        recovery = ErrorRecovery()
        
        error = ValidationError("Invalid format for task_id")
        
        result = recovery.handle_error(
            error=error,
            operation="create_checklist",
            context={"task_id": "invalid format!"}
        )
        
        assert result["recovery_attempted"] is True
        assert any("auto_correct_format" in s for s in result["suggestions"])
    
    def test_resource_error_cleanup(self):
        """Test resource error recovery through cleanup."""
        recovery = ErrorRecovery()
        
        error = ResourceError("Disk space low - need 100MB")
        
        result = recovery.handle_error(
            error=error,
            operation="create_backup",
            context={"required_space": 100}
        )
        
        assert result["recovery_attempted"] is True
        assert any("cleanup" in s.lower() for s in result["suggestions"])
    
    def test_error_history_tracking(self):
        """Test error history tracking."""
        recovery = ErrorRecovery()
        
        # Generate multiple errors
        errors = [
            ChecklistError("Error 1"),
            ChecklistError("Error 2"),
            TodoWriteError("Error 3"),
            MemoryError("Error 4")
        ]
        
        for error in errors:
            recovery.handle_error(error, "test_op", {})
        
        assert len(recovery.error_history) == 4
        
        # Test summary
        summary = recovery.get_error_summary(time_window_minutes=60)
        
        assert summary["total_errors"] == 4
        assert summary["errors_by_type"]["ChecklistError"] == 2
        assert summary["errors_by_type"]["TodoWriteError"] == 1
        assert summary["errors_by_type"]["MemoryError"] == 1
    
    def test_most_common_errors(self):
        """Test identifying most common error patterns."""
        recovery = ErrorRecovery()
        
        # Generate repeated errors
        for i in range(5):
            recovery.handle_error(
                ChecklistError("Checklist not found"),
                "get_checklist",
                {}
            )
        
        for i in range(3):
            recovery.handle_error(
                TodoWriteError("Sync timeout"),
                "sync",
                {}
            )
        
        summary = recovery.get_error_summary()
        common_errors = summary["most_common_errors"]
        
        assert len(common_errors) > 0
        assert common_errors[0]["pattern"] == "Checklist not found"
        assert common_errors[0]["count"] == 5


class TestCircuitBreaker:
    """Test suite for CircuitBreaker pattern."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed (normal) state."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60
        )
        
        def success_function():
            return "success"
        
        # Should work normally
        result = breaker.call(success_function)
        assert result == "success"
        assert breaker.state == "closed"
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opening after threshold failures."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=ValueError
        )
        
        def failing_function():
            raise ValueError("Test failure")
        
        # Fail up to threshold
        for i in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_function)
        
        # Circuit should be open
        assert breaker.state == "open"
        assert breaker.failure_count == 3
        
        # Further calls should fail immediately
        with pytest.raises(AtlasCommandError) as exc_info:
            breaker.call(failing_function)
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,  # 1 second for testing
            expected_exception=RuntimeError
        )
        
        def failing_function():
            raise RuntimeError("Still failing")
        
        def success_function():
            return "recovered"
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_function)
        
        assert breaker.state == "open"
        
        # Wait for recovery timeout
        import time
        time.sleep(1.1)
        
        # Should try half-open
        result = breaker.call(success_function)
        assert result == "recovered"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_reopen_on_half_open_failure(self):
        """Test circuit breaker reopening if half-open test fails."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=Exception
        )
        
        def failing_function():
            raise Exception("Persistent failure")
        
        # Open circuit
        for i in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_function)
        
        # Wait and try again
        import time
        time.sleep(1.1)
        
        # Half-open test fails
        with pytest.raises(Exception):
            breaker.call(failing_function)
        
        # Should be open again
        assert breaker.state == "open"
    
    def test_circuit_breaker_with_different_exceptions(self):
        """Test circuit breaker only counts expected exceptions."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=ValueError
        )
        
        def mixed_failures(error_type):
            if error_type == "expected":
                raise ValueError("Expected error")
            else:
                raise TypeError("Unexpected error")
        
        # Unexpected exception shouldn't count
        with pytest.raises(TypeError):
            breaker.call(mixed_failures, "unexpected")
        
        assert breaker.failure_count == 0
        assert breaker.state == "closed"
        
        # Expected exceptions should count
        for i in range(2):
            with pytest.raises(ValueError):
                breaker.call(mixed_failures, "expected")
        
        assert breaker.state == "open"