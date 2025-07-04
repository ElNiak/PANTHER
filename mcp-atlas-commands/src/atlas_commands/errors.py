"""Error handling and recovery for ATLAS Commands MCP Server."""

from typing import Optional, Dict, Any, List
from enum import Enum
import traceback
import logging
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AtlasCommandError(Exception):
    """Base exception for ATLAS command errors."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery_suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.recovery_suggestions = recovery_suggestions or []
        self.context = context or {}
        self.timestamp = datetime.now()


class ChecklistError(AtlasCommandError):
    """Errors related to checklist operations."""
    pass


class TodoWriteError(AtlasCommandError):
    """Errors related to TodoWrite integration."""
    pass


class MemoryError(AtlasCommandError):
    """Errors related to memory graph operations."""
    pass


class WorkflowError(AtlasCommandError):
    """Errors related to workflow enforcement."""
    pass


class ValidationError(AtlasCommandError):
    """Errors related to validation failures."""
    pass


class ResourceError(AtlasCommandError):
    """Errors related to resource constraints."""
    pass


class ErrorRecovery:
    """Error recovery mechanisms for ATLAS commands."""
    
    def __init__(self):
        self.error_history: List[AtlasCommandError] = []
        self.recovery_strategies = self._define_recovery_strategies()
        self.logger = logging.getLogger(__name__)
    
    def _define_recovery_strategies(self) -> Dict[type, List[Dict[str, Any]]]:
        """Define recovery strategies for different error types."""
        
        return {
            ChecklistError: [
                {
                    "condition": lambda e: "not found" in str(e),
                    "action": "create_default_checklist",
                    "description": "Create a default checklist if none exists"
                },
                {
                    "condition": lambda e: "invalid format" in str(e),
                    "action": "repair_checklist_format",
                    "description": "Attempt to repair checklist formatting"
                }
            ],
            TodoWriteError: [
                {
                    "condition": lambda e: "sync failed" in str(e),
                    "action": "retry_sync",
                    "description": "Retry synchronization with exponential backoff"
                },
                {
                    "condition": lambda e: "task not found" in str(e),
                    "action": "recreate_task",
                    "description": "Recreate the TodoWrite task"
                }
            ],
            MemoryError: [
                {
                    "condition": lambda e: "entity exists" in str(e),
                    "action": "update_existing_entity",
                    "description": "Update the existing entity instead of creating"
                },
                {
                    "condition": lambda e: "graph full" in str(e),
                    "action": "compact_and_retry",
                    "description": "Compact memory graph and retry operation"
                }
            ],
            WorkflowError: [
                {
                    "condition": lambda e: "prerequisite failed" in str(e),
                    "action": "skip_optional_prerequisite",
                    "description": "Skip optional prerequisites and continue"
                },
                {
                    "condition": lambda e: "command not found" in str(e),
                    "action": "suggest_alternative_command",
                    "description": "Suggest alternative command or workflow"
                }
            ],
            ValidationError: [
                {
                    "condition": lambda e: "missing parameter" in str(e),
                    "action": "use_default_value",
                    "description": "Use default value for missing parameter"
                },
                {
                    "condition": lambda e: "invalid format" in str(e),
                    "action": "auto_correct_format",
                    "description": "Attempt to auto-correct format issues"
                }
            ],
            ResourceError: [
                {
                    "condition": lambda e: "memory limit" in str(e),
                    "action": "free_memory_and_retry",
                    "description": "Free up memory and retry operation"
                },
                {
                    "condition": lambda e: "disk space" in str(e),
                    "action": "cleanup_and_retry",
                    "description": "Clean up temporary files and retry"
                }
            ]
        }
    
    def handle_error(
        self,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle an error with appropriate recovery strategy."""
        
        # Convert to AtlasCommandError if needed
        if not isinstance(error, AtlasCommandError):
            error = AtlasCommandError(
                str(error),
                severity=ErrorSeverity.ERROR,
                context=context
            )
        
        # Log the error
        self.logger.error(
            f"Error in {operation}: {error}",
            extra={"context": context, "severity": error.severity.value}
        )
        
        # Add to history
        self.error_history.append(error)
        
        # Find recovery strategies
        recovery_options = self._find_recovery_strategies(error)
        
        # Attempt recovery
        recovery_result = self._attempt_recovery(error, recovery_options, context)
        
        return {
            "error": str(error),
            "severity": error.severity.value,
            "operation": operation,
            "recovery_attempted": recovery_result["attempted"],
            "recovery_successful": recovery_result["successful"],
            "recovery_action": recovery_result.get("action"),
            "suggestions": error.recovery_suggestions + recovery_result.get("suggestions", []),
            "context": context,
            "timestamp": error.timestamp.isoformat()
        }
    
    def _find_recovery_strategies(
        self,
        error: AtlasCommandError
    ) -> List[Dict[str, Any]]:
        """Find applicable recovery strategies for an error."""
        
        strategies = []
        error_type = type(error)
        
        if error_type in self.recovery_strategies:
            for strategy in self.recovery_strategies[error_type]:
                if strategy["condition"](error):
                    strategies.append(strategy)
        
        return strategies
    
    def _attempt_recovery(
        self,
        error: AtlasCommandError,
        strategies: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to recover from an error using available strategies."""
        
        if not strategies:
            return {
                "attempted": False,
                "successful": False,
                "suggestions": ["No automatic recovery available"]
            }
        
        for strategy in strategies:
            try:
                # Execute recovery action
                action_name = strategy["action"]
                recovery_method = getattr(self, f"_recover_{action_name}", None)
                
                if recovery_method:
                    success = recovery_method(error, context)
                    if success:
                        return {
                            "attempted": True,
                            "successful": True,
                            "action": action_name,
                            "description": strategy["description"]
                        }
            except Exception as recovery_error:
                self.logger.warning(
                    f"Recovery strategy {action_name} failed: {recovery_error}"
                )
        
        return {
            "attempted": True,
            "successful": False,
            "suggestions": [s["description"] for s in strategies]
        }
    
    def _recover_create_default_checklist(
        self,
        error: ChecklistError,
        context: Dict[str, Any]
    ) -> bool:
        """Recovery: Create a default checklist."""
        
        from .checklist.templates import ChecklistTemplates
        
        try:
            command_name = context.get("command_name", "unknown")
            task_id = context.get("task_id", "unknown")
            
            # Create default checklist
            default_items = ChecklistTemplates.get_template_by_command(
                command_name,
                task_id=task_id
            )
            
            # Store in context for retry
            context["recovery_items"] = default_items
            return True
        except Exception:
            return False
    
    def _recover_retry_sync(
        self,
        error: TodoWriteError,
        context: Dict[str, Any]
    ) -> bool:
        """Recovery: Retry synchronization with backoff."""
        
        import time
        
        max_retries = 3
        retry_count = context.get("retry_count", 0)
        
        if retry_count >= max_retries:
            return False
        
        # Exponential backoff
        wait_time = 2 ** retry_count
        time.sleep(wait_time)
        
        # Update context for next retry
        context["retry_count"] = retry_count + 1
        context["retry_scheduled"] = True
        
        return True
    
    def _recover_compact_and_retry(
        self,
        error: MemoryError,
        context: Dict[str, Any]
    ) -> bool:
        """Recovery: Compact memory graph and retry."""
        
        from .memory.graph_manager import MemoryGraphManager
        
        try:
            manager = context.get("memory_manager")
            if manager and isinstance(manager, MemoryGraphManager):
                # Compact old entities
                result = manager.compact_old_entities(days_old=7)
                
                if result["compacted_count"] > 0:
                    context["compaction_performed"] = True
                    context["entities_freed"] = result["compacted_count"]
                    return True
        except Exception:
            pass
        
        return False
    
    def get_error_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get summary of recent errors."""
        
        cutoff_time = datetime.now().timestamp() - (time_window_minutes * 60)
        recent_errors = [
            e for e in self.error_history
            if e.timestamp.timestamp() > cutoff_time
        ]
        
        # Group by type
        by_type = {}
        for error in recent_errors:
            error_type = type(error).__name__
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(error)
        
        # Calculate statistics
        return {
            "total_errors": len(recent_errors),
            "time_window_minutes": time_window_minutes,
            "errors_by_type": {
                error_type: len(errors)
                for error_type, errors in by_type.items()
            },
            "severity_distribution": {
                severity.value: len([
                    e for e in recent_errors
                    if e.severity == severity
                ])
                for severity in ErrorSeverity
            },
            "most_common_errors": self._get_most_common_errors(recent_errors),
            "recovery_success_rate": self._calculate_recovery_rate()
        }
    
    def _get_most_common_errors(
        self,
        errors: List[AtlasCommandError],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get most common error patterns."""
        
        from collections import Counter
        
        # Group by error message patterns
        error_patterns = Counter(str(e) for e in errors)
        
        return [
            {
                "pattern": pattern,
                "count": count,
                "percentage": (count / len(errors) * 100) if errors else 0
            }
            for pattern, count in error_patterns.most_common(limit)
        ]
    
    def _calculate_recovery_rate(self) -> float:
        """Calculate recovery success rate."""
        
        # This would track actual recovery attempts
        # For now, return a placeholder
        return 0.0


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise AtlasCommandError(
                    "Circuit breaker is open",
                    severity=ErrorSeverity.WARNING,
                    recovery_suggestions=["Wait for recovery timeout"]
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        
        return (
            self.last_failure_time and
            (datetime.now().timestamp() - self.last_failure_time) >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call."""
        
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call."""
        
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"