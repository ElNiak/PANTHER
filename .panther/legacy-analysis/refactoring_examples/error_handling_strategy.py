"""
Error Management Strategy for PANTHER
Addresses the critical TODO in experiment_manager.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import logging
import time
import traceback
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""
    CRITICAL = "critical"  # Experiment must stop
    HIGH = "high"         # Test fails, but experiment continues  
    MEDIUM = "medium"     # Recoverable error with retry
    LOW = "low"           # Warning, no action needed


class ErrorCategory(Enum):
    """Error categories for proper handling."""
    NETWORK = "network"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    ASSERTION = "assertion"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    test_name: str
    step_name: str
    attempt: int = 1
    max_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def increment_attempt(self) -> None:
        """Increment attempt counter."""
        self.attempt += 1
        
    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.attempt < self.max_attempts


@dataclass
class ErrorInfo:
    """Comprehensive error information."""
    error: Exception
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    timestamp: float = field(default_factory=time.time)
    traceback: str = field(default_factory=lambda: traceback.format_exc())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "severity": self.severity.value,
            "category": self.category.value,
            "test_name": self.context.test_name,
            "step_name": self.context.step_name,
            "attempt": self.context.attempt,
            "timestamp": self.timestamp,
            "traceback": self.traceback,
            "metadata": self.context.metadata,
        }


class ErrorHandler(ABC):
    """Base class for error handlers."""
    
    @abstractmethod
    def can_handle(self, error_info: ErrorInfo) -> bool:
        """Check if this handler can handle the error."""
        pass
    
    @abstractmethod
    def handle(self, error_info: ErrorInfo) -> bool:
        """
        Handle the error.
        Returns True if error was handled and execution can continue.
        """
        pass


class NetworkErrorHandler(ErrorHandler):
    """Handles network-related errors."""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.category == ErrorCategory.NETWORK
    
    def handle(self, error_info: ErrorInfo) -> bool:
        logger.warning(f"Network error in {error_info.context.test_name}: {error_info.error}")
        
        if error_info.context.can_retry():
            wait_time = 2 ** error_info.context.attempt  # Exponential backoff
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            return True
        
        return False


class TimeoutErrorHandler(ErrorHandler):
    """Handles timeout errors."""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.category == ErrorCategory.TIMEOUT
    
    def handle(self, error_info: ErrorInfo) -> bool:
        logger.error(f"Timeout in {error_info.context.test_name}: {error_info.error}")
        
        # For timeouts, we might want to extend the timeout on retry
        if error_info.context.can_retry():
            error_info.context.metadata["timeout_extension"] = 1.5
            return True
        
        return False


class ResourceErrorHandler(ErrorHandler):
    """Handles resource-related errors."""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.category == ErrorCategory.RESOURCE
    
    def handle(self, error_info: ErrorInfo) -> bool:
        logger.error(f"Resource error: {error_info.error}")
        
        # Try to free resources
        if "cleanup_callback" in error_info.context.metadata:
            cleanup = error_info.context.metadata["cleanup_callback"]
            cleanup()
            
        # Resource errors usually need human intervention
        return False


class ErrorManagementStrategy:
    """
    Main error management strategy for PANTHER.
    Implements the Chain of Responsibility pattern.
    """
    
    def __init__(self):
        self.handlers: List[ErrorHandler] = [
            NetworkErrorHandler(),
            TimeoutErrorHandler(),
            ResourceErrorHandler(),
        ]
        self.error_history: List[ErrorInfo] = []
        self.fail_fast = True
        
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and message."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Network errors
        if any(keyword in error_msg for keyword in ["connection", "network", "socket"]):
            return ErrorCategory.NETWORK
            
        # Timeout errors
        if "timeout" in error_msg or error_type == "TimeoutError":
            return ErrorCategory.TIMEOUT
            
        # Resource errors
        if any(keyword in error_msg for keyword in ["memory", "disk", "resource"]):
            return ErrorCategory.RESOURCE
            
        # Configuration errors
        if any(keyword in error_msg for keyword in ["config", "missing", "invalid"]):
            return ErrorCategory.CONFIGURATION
            
        # Assertion errors
        if error_type == "AssertionError":
            return ErrorCategory.ASSERTION
            
        # System errors
        if error_type in ["OSError", "SystemError", "IOError"]:
            return ErrorCategory.SYSTEM
            
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on error type and category."""
        # Critical errors that must stop execution
        if category in [ErrorCategory.CONFIGURATION, ErrorCategory.SYSTEM]:
            return ErrorSeverity.CRITICAL
            
        # High severity - test fails but experiment continues
        if category in [ErrorCategory.ASSERTION, ErrorCategory.RESOURCE]:
            return ErrorSeverity.HIGH
            
        # Medium severity - can retry
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
            
        return ErrorSeverity.LOW
    
    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        custom_severity: Optional[ErrorSeverity] = None
    ) -> bool:
        """
        Handle an error with the appropriate strategy.
        Returns True if execution can continue.
        """
        # Categorize and create error info
        category = self.categorize_error(error)
        severity = custom_severity or self.determine_severity(error, category)
        
        error_info = ErrorInfo(
            error=error,
            severity=severity,
            category=category,
            context=context
        )
        
        # Log error
        self._log_error(error_info)
        
        # Store in history
        self.error_history.append(error_info)
        
        # Check fail-fast mode
        if self.fail_fast and severity == ErrorSeverity.CRITICAL:
            logger.critical("Fail-fast mode: Stopping execution due to critical error")
            raise error
        
        # Try handlers in order
        for handler in self.handlers:
            if handler.can_handle(error_info):
                if handler.handle(error_info):
                    context.increment_attempt()
                    return True
        
        # No handler could resolve the error
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            raise error
            
        return False
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error with appropriate level."""
        log_method = {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.LOW: logger.info,
        }[error_info.severity]
        
        log_method(
            f"[{error_info.severity.value}] {error_info.category.value} error in "
            f"{error_info.context.test_name}/{error_info.context.step_name}: "
            f"{error_info.error}"
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors."""
        summary = {
            "total_errors": len(self.error_history),
            "by_severity": {},
            "by_category": {},
            "by_test": {},
        }
        
        for error_info in self.error_history:
            # By severity
            sev = error_info.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
            
            # By category
            cat = error_info.category.value
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1
            
            # By test
            test = error_info.context.test_name
            summary["by_test"][test] = summary["by_test"].get(test, 0) + 1
        
        return summary


# ========== Decorators for Easy Integration ==========

def with_error_handling(
    test_name: str,
    step_name: str,
    max_attempts: int = 3,
    fail_fast: bool = True
):
    """Decorator to add error handling to functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            strategy = ErrorManagementStrategy()
            strategy.fail_fast = fail_fast
            
            context = ErrorContext(
                test_name=test_name,
                step_name=step_name,
                max_attempts=max_attempts
            )
            
            while context.attempt <= context.max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if not strategy.handle_error(e, context):
                        raise
            
            raise RuntimeError(f"Max attempts ({max_attempts}) reached for {test_name}/{step_name}")
        
        return wrapper
    return decorator


@contextmanager
def error_context(test_name: str, step_name: str, strategy: ErrorManagementStrategy):
    """Context manager for error handling."""
    context = ErrorContext(test_name=test_name, step_name=step_name)
    
    try:
        yield context
    except Exception as e:
        if not strategy.handle_error(e, context):
            raise


# ========== Integration with ExperimentManager ==========

class ExperimentManagerWithErrorHandling:
    """Example integration with ExperimentManager."""
    
    def __init__(self):
        self.error_strategy = ErrorManagementStrategy()
        self.logger = logging.getLogger(__name__)
    
    @with_error_handling("experiment", "initialization", max_attempts=1)
    def initialize_experiment(self, config: Dict[str, Any]) -> None:
        """Initialize experiment with error handling."""
        # Validation that might fail
        if not config.get("name"):
            raise ValueError("Experiment name is required")
        
        self.config = config
        self.logger.info(f"Initialized experiment: {config['name']}")
    
    def run_tests(self, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests with comprehensive error handling."""
        results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
        }
        
        for test in tests:
            test_name = test["name"]
            
            try:
                # Setup phase
                with error_context(test_name, "setup", self.error_strategy) as ctx:
                    ctx.metadata["cleanup_callback"] = lambda: self._cleanup_test(test_name)
                    self._setup_test(test)
                
                # Execution phase
                with error_context(test_name, "execution", self.error_strategy) as ctx:
                    ctx.max_attempts = test.get("retry_count", 3)
                    self._execute_test(test)
                
                # Verification phase
                with error_context(test_name, "verification", self.error_strategy):
                    self._verify_test(test)
                
                results["passed"] += 1
                
            except Exception as e:
                self.logger.error(f"Test {test_name} failed: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "test": test_name,
                    "error": str(e),
                    "type": type(e).__name__,
                })
                
                if self.error_strategy.fail_fast:
                    break
        
        # Add error summary
        results["error_summary"] = self.error_strategy.get_error_summary()
        
        return results
    
    def _setup_test(self, test: Dict[str, Any]) -> None:
        """Setup test environment."""
        # Simulate potential setup errors
        if test.get("requires_docker") and not self._check_docker():
            raise RuntimeError("Docker is not available")
    
    def _execute_test(self, test: Dict[str, Any]) -> None:
        """Execute the test."""
        # Simulate test execution
        pass
    
    def _verify_test(self, test: Dict[str, Any]) -> None:
        """Verify test results."""
        # Simulate assertions
        if test.get("expected_result") != test.get("actual_result"):
            raise AssertionError("Test assertion failed")
    
    def _cleanup_test(self, test_name: str) -> None:
        """Cleanup test resources."""
        self.logger.info(f"Cleaning up test: {test_name}")
    
    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        # Simulate Docker check
        return True


# ========== Usage Example ==========

def example_usage():
    """Demonstrate error handling usage."""
    
    # Create experiment manager with error handling
    manager = ExperimentManagerWithErrorHandling()
    
    # Configure experiment
    experiment_config = {
        "name": "QUIC Performance Test",
        "timeout": 300,
    }
    
    # Initialize with automatic retry for configuration errors
    manager.initialize_experiment(experiment_config)
    
    # Define tests
    tests = [
        {
            "name": "test_quic_handshake",
            "retry_count": 3,
            "requires_docker": True,
        },
        {
            "name": "test_data_transfer",
            "retry_count": 5,  # Network tests get more retries
            "timeout": 60,
        },
    ]
    
    # Run tests with comprehensive error handling
    results = manager.run_tests(tests)
    
    print(f"Test Results: {results['passed']} passed, {results['failed']} failed")
    print(f"Error Summary: {results['error_summary']}")


"""
Benefits of this Error Management Strategy:

1. Categorized Error Handling:
   - Different strategies for different error types
   - Appropriate retry logic based on error category

2. Configurable Severity:
   - Critical errors stop execution
   - Medium errors get retried
   - Low severity errors are logged but don't stop execution

3. Context Preservation:
   - Full error context including test name, step, and attempt
   - Metadata support for custom error handling

4. Easy Integration:
   - Decorators for simple function wrapping
   - Context managers for fine-grained control
   - Minimal changes to existing code

5. Comprehensive Reporting:
   - Error history tracking
   - Summary statistics by category/severity/test
   - Full tracebacks for debugging
"""