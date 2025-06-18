# Concrete Error Handling Implementation Plan for PANTHER

## Overview

This document provides a concrete, file-by-file implementation plan for improving error handling across the PANTHER codebase. Each section includes specific file references, code examples, and step-by-step instructions.

## Architecture Decisions

### 1. Error Handler Location
- **Primary Location**: `/panther/core/exceptions/error_handler_mixin.py` (KEEP AS IS)
- **Exception Classes**: `/panther/core/exceptions/` directory
- **Import Pattern**: Direct imports from `panther.core.exceptions.error_handler_mixin`

### 2. Remove Duplicates
- **DELETE**: `/panther/plugins/environments/network_environment/mixins/error_handler.py`
- Replace all imports with core version

## Phase 1: Core Infrastructure Updates (Week 1)

### Task 1.1: Enhance Core Error Handler

**File**: `/panther/core/exceptions/error_handler_mixin.py`

**Current Code**:
```python
class ErrorHandlerMixin(LoggerMixin):
    def __init__(self):
        super().__init__()
        self._fast_fail_handler = None
```

**Updated Code**:
```python
from typing import Dict, Any, Optional, Type, Tuple, List
from contextlib import contextmanager
import traceback
from .fast_fail import FastFailHandler, ErrorSeverity, ErrorCategory, PantherException

class ErrorHandlerMixin(LoggerMixin):
    """Enhanced error handler mixin with comprehensive error management."""
    
    def __init__(self):
        super().__init__()
        self._fast_fail_handler = None
        self._error_context: Dict[str, Any] = {}
        self._suppressed_errors: List[Exception] = []
    
    def set_error_context(self, **context):
        """Set persistent error context for this component."""
        self._error_context.update(context)
    
    def handle_error(
        self,
        error: Exception,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        context: Optional[Dict[str, Any]] = None,
        raise_on_critical: bool = True,
        operation: Optional[str] = None
    ) -> bool:
        """
        Enhanced error handling with full context.
        
        Returns:
            bool: True if execution should continue, False otherwise
        """
        # Merge contexts
        full_context = {
            **self._error_context,
            "component": self.__class__.__name__,
            "operation": operation or "unknown",
            **(context or {})
        }
        
        # Convert to PantherException if needed
        if not isinstance(error, PantherException):
            if isinstance(error, (IOError, OSError)):
                severity = severity or ErrorSeverity.HIGH
                category = category or ErrorCategory.RESOURCE
            elif isinstance(error, ValueError):
                severity = severity or ErrorSeverity.MEDIUM
                category = category or ErrorCategory.CONFIGURATION
            elif isinstance(error, RuntimeError):
                severity = severity or ErrorSeverity.HIGH
                category = category or ErrorCategory.RUNTIME
            else:
                severity = severity or ErrorSeverity.MEDIUM
                category = category or ErrorCategory.UNKNOWN
            
            error = PantherException(
                message=str(error),
                severity=severity,
                category=category,
                **full_context
            )
        
        # Log with full context
        self.logger.error(
            f"[{error.category.value}] {error.severity.name} error in {full_context['component']}.{full_context['operation']}: {error}",
            extra={"error_context": full_context, "traceback": traceback.format_exc()}
        )
        
        # Use fast fail handler if available
        if self._fast_fail_handler:
            return self._fast_fail_handler.handle_error(error, raise_on_critical=raise_on_critical)
        
        # Default behavior
        if error.severity == ErrorSeverity.CRITICAL and raise_on_critical:
            raise error
        
        return error.severity not in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]
    
    @contextmanager
    def error_context(self, operation: str, **context):
        """Context manager for operations with automatic error handling."""
        old_context = self._error_context.copy()
        self.set_error_context(operation=operation, **context)
        try:
            yield
        except Exception as e:
            self.handle_error(e, operation=operation)
            raise
        finally:
            self._error_context = old_context
```

### Task 1.2: Create Missing Exception Classes

**File**: `/panther/core/exceptions/network_exceptions.py` (NEW FILE)

```python
from .fast_fail import PantherException, ErrorSeverity, ErrorCategory
from typing import Optional, Dict, Any

class NetworkSetupException(PantherException):
    """Network environment setup failures."""
    
    def __init__(
        self,
        message: str,
        environment_type: str,
        network_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=kwargs.pop('severity', ErrorSeverity.HIGH),
            category=ErrorCategory.NETWORK_SETUP,
            environment_type=environment_type,
            network_name=network_name,
            **kwargs
        )

class ServiceDeploymentException(PantherException):
    """Service deployment failures."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        deployment_phase: str,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=kwargs.pop('severity', ErrorSeverity.HIGH),
            category=ErrorCategory.SERVICE_START,
            service_name=service_name,
            deployment_phase=deployment_phase,
            **kwargs
        )
```

**File**: `/panther/core/exceptions/command_exceptions.py` (NEW FILE)

```python
from .fast_fail import PantherException, ErrorSeverity, ErrorCategory
from typing import List, Optional

class CommandExecutionException(PantherException):
    """Command execution failures."""
    
    def __init__(
        self,
        message: str,
        command: List[str],
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=kwargs.pop('severity', ErrorSeverity.MEDIUM),
            category=ErrorCategory.COMMAND_EXECUTION,
            command=' '.join(command),
            exit_code=exit_code,
            stdout=stdout[:500] if stdout else None,  # Truncate long output
            stderr=stderr[:500] if stderr else None,
            **kwargs
        )
```

**File**: `/panther/core/exceptions/__init__.py` (UPDATE)

```python
# Existing imports
from .fast_fail import (
    FastFailHandler,
    PantherException,
    ErrorSeverity,
    ErrorCategory,
    DockerBuildException,
    PluginLoadException,
    ServiceStartException,
    NetworkSetupException,
    ServiceTimeoutException,
    ConfigurationException,
    ResourceException,
    ContainerRuntimeException,
)

# New imports
from .network_exceptions import (
    NetworkSetupException,
    ServiceDeploymentException,
)
from .command_exceptions import (
    CommandExecutionException,
)

# Updated __all__
__all__ = [
    # Fast fail
    "FastFailHandler",
    "PantherException",
    "ErrorSeverity",
    "ErrorCategory",
    # Specific exceptions
    "DockerBuildException",
    "PluginLoadException", 
    "ServiceStartException",
    "NetworkSetupException",
    "ServiceTimeoutException",
    "ConfigurationException",
    "ResourceException",
    "ContainerRuntimeException",
    # New exceptions
    "ServiceDeploymentException",
    "CommandExecutionException",
]
```

## Phase 2: Critical Component Updates (Week 1-2)

### Task 2.1: Fix DockerBuilder

**File**: `/panther/core/docker_builder/docker_builder.py`

**Lines to Update**: 150-200 (approximately)

**Current Code**:
```python
except docker.errors.DockerException as e:
    self.logger.error(f"Docker error: {e}")
    raise RuntimeError(f"Failed to connect to Docker: {e}")
```

**Updated Code**:
```python
except docker.errors.DockerException as e:
    docker_error = DockerBuildException(
        message=f"Failed to connect to Docker daemon: {str(e)}",
        image_name="N/A",
        dockerfile="N/A",
        operation="connect",
        daemon_version=None,
        error_type=type(e).__name__
    )
    self.handle_error(
        docker_error,
        operation="docker_connect",
        raise_on_critical=True
    )
```

**Current Code** (Line ~450):
```python
except Exception as e:
    self.logger.error(f"Failed to build image {image_name}: {e}")
    raise
```

**Updated Code**:
```python
except docker.errors.BuildError as e:
    build_error = DockerBuildException(
        message=f"Docker build failed: {str(e)}",
        image_name=image_name,
        dockerfile=str(dockerfile_path),
        build_log=e.build_log if hasattr(e, 'build_log') else None
    )
    self.handle_error(
        build_error,
        operation="build_image",
        context={"path": str(path), "tag": tag},
        raise_on_critical=True
    )
except (IOError, OSError) as e:
    self.handle_error(
        e,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.RESOURCE,
        operation="build_image_io",
        context={"path": str(path), "error": str(e)},
        raise_on_critical=True
    )
```

### Task 2.2: Fix PluginManager

**File**: `/panther/plugins/plugin_manager.py`

**Lines to Update**: Multiple locations with broad catches

**Current Code** (Line ~229):
```python
except Exception as e:  # pylint: disable=broad-exception-caught
    self.logger.error(
        f"Error creating service manager for {plugin_name}: {e}"
    )
    return None
```

**Updated Code**:
```python
except (ImportError, AttributeError) as e:
    plugin_error = PluginLoadException(
        message=f"Failed to create service manager: {str(e)}",
        plugin_name=plugin_name,
        plugin_type="service",
        severity=ErrorSeverity.HIGH,
        import_path=str(module_path),
        class_name=expected_class_name
    )
    self.handle_error(
        plugin_error,
        operation="create_service_manager",
        raise_on_critical=False  # Allow other plugins to load
    )
    return None
except Exception as e:
    # Unexpected error - should be CRITICAL
    unexpected_error = PluginLoadException(
        message=f"Unexpected error creating service manager: {str(e)}",
        plugin_name=plugin_name,
        plugin_type="service",
        severity=ErrorSeverity.CRITICAL,
        error_type=type(e).__name__
    )
    self.handle_error(
        unexpected_error,
        operation="create_service_manager_unexpected",
        raise_on_critical=True
    )
```

### Task 2.3: Fix Docker Compose Environment

**File**: `/panther/plugins/environments/network_environment/docker_compose/docker_compose.py`

**Import Updates** (Top of file):
```python
# Remove local error handler import
# from panther.plugins.environments.network_environment.mixins import ErrorHandlerMixin

# Use core version
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions import (
    NetworkSetupException,
    ServiceDeploymentException,
    CommandExecutionException,
    ErrorSeverity,
    ErrorCategory
)
```

**Current Code** (Line ~631):
```python
except Exception as e:
    self.logger.error(f"Error launching Docker Compose services: {e}")
    self.teardown_environment()
```

**Updated Code**:
```python
except subprocess.CalledProcessError as e:
    compose_error = CommandExecutionException(
        message=f"Docker Compose launch failed: {e.stderr or str(e)}",
        command=compose_up_cmd,
        exit_code=e.returncode,
        stdout=e.stdout,
        stderr=e.stderr
    )
    
    # Attempt cleanup
    with self.error_context("emergency_teardown"):
        self.teardown_environment()
    
    self.handle_error(
        compose_error,
        severity=ErrorSeverity.HIGH,
        operation="launch_services",
        context={"compose_file": str(self.rendered_services_network_config_file_path)},
        raise_on_critical=True
    )
except (IOError, OSError) as e:
    self.handle_error(
        e,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.RESOURCE,
        operation="launch_services_io",
        raise_on_critical=True
    )
```

### Task 2.4: Fix ExperimentManager

**File**: `/panther/core/experiment_manager.py`

**Current Code** (Line ~242):
```python
except Exception as e:  # pylint: disable=broad-except
    # State transitions are handled automatically by StateEventObserver
    
    # Emit experiment finished early event with error details
    self.experiment_emitter.emit_finished_early(
        reason=f"Initialization Error: {type(e).__name__}",
        details={
            "phase": "initialization",
            "error_type": type(e).__name__,
            "error_message": str(e),
        },
    )
```

**Updated Code**:
```python
except (ImportError, ModuleNotFoundError, AttributeError, TypeError) as e:
    # Known initialization errors
    init_error = ExperimentInitializationError(
        f"Failed to initialize experiment components: {str(e)}",
        phase="initialization",
        component=type(e).__name__
    )
    
    self.experiment_emitter.emit_finished_early(
        reason=f"Initialization Error: {type(e).__name__}",
        details={
            "phase": "initialization",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        },
    )
    
    self.handle_error(
        init_error,
        operation="initialize_experiments",
        raise_on_critical=True
    )
```

## Phase 3: Service and Plugin Updates (Week 2-3)

### Task 3.1: Update Service Base Classes

**File**: `/panther/plugins/services/base/quic_service_base.py`

Add error handling to base class methods:

```python
from panther.core.exceptions import ServiceStartException, ErrorSeverity

class BaseQUICServiceManager(IServiceManager, ErrorHandlerMixin):
    
    def generate_run_command(self, **kwargs) -> str:
        """Generate run command with error handling."""
        with self.error_context("generate_command", service=self.service_name):
            try:
                # Existing command generation logic
                params = self._extract_common_params(**kwargs)
                # ...
            except KeyError as e:
                raise ServiceStartException(
                    f"Missing required parameter: {str(e)}",
                    service_name=self.service_name,
                    missing_param=str(e)
                )
            except Exception as e:
                self.handle_error(
                    e,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.SERVICE_START,
                    operation="generate_command"
                )
                raise
```

### Task 3.2: Update Network Environment Base

**File**: `/panther/plugins/environments/network_environment/base_network_environment.py`

```python
def setup_environment(self, ...) -> bool:
    """Setup with comprehensive error handling."""
    self.set_error_context(
        environment_type=self.env_type,
        environment_subtype=self.env_sub_type,
        test_name=test_config.name if test_config else "unknown"
    )
    
    try:
        # Existing setup logic
        return self._do_setup_environment(...)
    except Exception as e:
        # All exceptions should be properly typed by now
        self.handle_error(
            e,
            operation="setup_environment",
            raise_on_critical=True
        )
```

## Phase 4: Utility and Helper Updates (Week 3)

### Task 4.1: Create Error Aggregator

**File**: `/panther/core/exceptions/error_aggregator.py` (NEW FILE)

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from .fast_fail import PantherException, ErrorSeverity, ErrorCategory

class ErrorAggregator:
    """Aggregate and analyze errors across an experiment."""
    
    def __init__(self, experiment_name: str, max_errors_before_fail: int = 0):
        self.experiment_name = experiment_name
        self.max_errors_before_fail = max_errors_before_fail
        self.errors: List[PantherException] = []
        self.start_time = datetime.now()
        
    def add_error(self, error: PantherException) -> bool:
        """
        Add an error and check thresholds.
        
        Returns:
            bool: True if experiment should continue, False if threshold exceeded
        """
        self.errors.append(error)
        
        # Check threshold
        if self.max_errors_before_fail > 0 and len(self.errors) >= self.max_errors_before_fail:
            return False
            
        # Always fail on CRITICAL
        if error.severity == ErrorSeverity.CRITICAL:
            return False
            
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary statistics."""
        if not self.errors:
            return {
                "total_errors": 0,
                "duration": (datetime.now() - self.start_time).total_seconds(),
                "status": "success"
            }
        
        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        by_component = defaultdict(int)
        
        for error in self.errors:
            by_severity[error.severity.name] += 1
            by_category[error.category.value] += 1
            if hasattr(error, 'component'):
                by_component[error.component] += 1
        
        return {
            "total_errors": len(self.errors),
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "by_component": dict(by_component),
            "critical_errors": [e for e in self.errors if e.severity == ErrorSeverity.CRITICAL],
            "first_error": self.errors[0] if self.errors else None,
            "last_error": self.errors[-1] if self.errors else None,
            "status": "failed" if any(e.severity == ErrorSeverity.CRITICAL for e in self.errors) else "completed_with_errors"
        }
    
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Generate detailed error report."""
        summary = self.get_summary()
        
        report = f"""
# Error Report for {self.experiment_name}

## Summary
- Total Errors: {summary['total_errors']}
- Duration: {summary['duration']:.2f} seconds
- Status: {summary['status']}

## Errors by Severity
"""
        for severity, count in summary['by_severity'].items():
            report += f"- {severity}: {count}\n"
        
        report += "\n## Errors by Category\n"
        for category, count in summary['by_category'].items():
            report += f"- {category}: {count}\n"
        
        report += "\n## Critical Errors\n"
        for error in summary['critical_errors']:
            report += f"- {error.timestamp}: {error.message}\n"
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
        
        return report
```

### Task 4.2: Update Import Utilities

**File**: `/panther/core/utils/__init__.py`

Keep the current structure but add a comment:

```python
# Error handling imports
# Note: Import ErrorHandlerMixin directly from panther.core.exceptions.error_handler_mixin
# to avoid circular dependencies. Do not add it here.

# Safe imports that don't cause circular dependencies
from .logging_mixin import LoggerMixin
from .file_utils import FileUtils
```

## Phase 5: Testing Infrastructure (Week 3-4)

### Task 5.1: Create Error Testing Utilities

**File**: `/tests/utils/error_testing.py` (NEW FILE)

```python
import pytest
from unittest.mock import Mock, patch
from typing import Type, Optional, Dict, Any
from panther.core.exceptions import (
    PantherException,
    ErrorSeverity,
    ErrorCategory,
    FastFailHandler
)

class ErrorTestHelper:
    """Helper utilities for testing error handling."""
    
    @staticmethod
    def assert_error_handled(
        func,
        expected_exception: Type[Exception],
        expected_severity: Optional[ErrorSeverity] = None,
        expected_category: Optional[ErrorCategory] = None,
        **kwargs
    ):
        """Assert that a function raises the expected exception with proper attributes."""
        with pytest.raises(expected_exception) as exc_info:
            func(**kwargs)
        
        error = exc_info.value
        
        if expected_severity and hasattr(error, 'severity'):
            assert error.severity == expected_severity
            
        if expected_category and hasattr(error, 'category'):
            assert error.category == expected_category
            
        return error
    
    @staticmethod
    def create_mock_fast_fail_handler(enabled: bool = True) -> Mock:
        """Create a mock FastFailHandler for testing."""
        handler = Mock(spec=FastFailHandler)
        handler.enabled = enabled
        handler.handle_error.return_value = True
        return handler
    
    @staticmethod
    @pytest.fixture
    def error_context():
        """Fixture that captures error context."""
        context = {"errors": []}
        
        def capture_error(error, **kwargs):
            context["errors"].append({
                "error": error,
                "kwargs": kwargs
            })
            return True
        
        with patch('panther.core.exceptions.error_handler_mixin.ErrorHandlerMixin.handle_error', side_effect=capture_error):
            yield context
```

### Task 5.2: Create Integration Tests

**File**: `/tests/integration/test_error_handling_integration.py` (NEW FILE)

```python
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from panther.core.experiment_manager import ExperimentManager
from panther.plugins.plugin_manager import PluginManager
from panther.core.exceptions import (
    DockerBuildException,
    PluginLoadException,
    NetworkSetupException,
    ErrorSeverity
)
from tests.utils.error_testing import ErrorTestHelper

class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""
    
    def test_docker_build_failure_stops_experiment(self, tmp_path):
        """Test that Docker build failures properly stop experiment."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.side_effect = Exception("Docker not available")
            
            # This should raise DockerBuildException with CRITICAL severity
            error = ErrorTestHelper.assert_error_handled(
                lambda: ExperimentManager(
                    global_config=self.create_test_config(tmp_path),
                    experiment_name="test"
                ),
                expected_exception=DockerBuildException,
                expected_severity=ErrorSeverity.CRITICAL
            )
            
            assert "Docker not available" in str(error)
    
    def test_plugin_load_error_cascade(self, tmp_path):
        """Test plugin loading error cascade."""
        # Test that missing required plugin stops experiment
        # but missing optional plugin continues
        pass
    
    def test_network_setup_recovery(self, tmp_path):
        """Test network setup error recovery."""
        # Test that network setup errors trigger proper cleanup
        pass
```

## Phase 6: Validation and Monitoring (Week 4)

### Task 6.1: Add Pre-commit Hooks

**File**: `.pre-commit-config.yaml` (UPDATE)

Add new hook:

```yaml
- repo: local
  hooks:
    - id: check-exception-handling
      name: Check exception handling patterns
      entry: python dev/scripts/check_exception_handling.py
      language: python
      files: \.py$
      exclude: ^tests/
```

**File**: `/dev/scripts/check_exception_handling.py` (NEW FILE)

```python
#!/usr/bin/env python3
"""Check for proper exception handling patterns."""

import ast
import sys
import argparse
from pathlib import Path
from typing import List, Tuple

class ExceptionChecker(ast.NodeVisitor):
    """AST visitor to check exception handling patterns."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[Tuple[int, str]] = []
        self.in_test_file = 'test' in filename
        
    def visit_ExceptHandler(self, node):
        """Check exception handlers."""
        # Bare except
        if node.type is None:
            self.errors.append((
                node.lineno,
                "Bare 'except:' clause found. Use specific exception types."
            ))
        
        # Broad except Exception
        elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
            # Allow in test files
            if not self.in_test_file:
                self.errors.append((
                    node.lineno,
                    "Broad 'except Exception' found. Use specific exception types."
                ))
        
        # Check for pass or empty body
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.errors.append((
                node.lineno,
                "Empty exception handler. At least log the error."
            ))
        
        self.generic_visit(node)
    
    def visit_Raise(self, node):
        """Check raise statements."""
        # Check for RuntimeError
        if node.exc and isinstance(node.exc, ast.Call):
            if isinstance(node.exc.func, ast.Name) and node.exc.func.id == 'RuntimeError':
                self.errors.append((
                    node.lineno,
                    "RuntimeError raised. Use specific PantherException subclass."
                ))
        
        self.generic_visit(node)

def check_file(filepath: Path) -> List[Tuple[str, int, str]]:
    """Check a single file for exception handling issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        checker = ExceptionChecker(str(filepath))
        checker.visit(tree)
        
        return [(str(filepath), line, msg) for line, msg in checker.errors]
    except Exception as e:
        return [(str(filepath), 0, f"Failed to parse: {e}")]

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check exception handling patterns")
    parser.add_argument('files', nargs='*', help='Files to check')
    args = parser.parse_args()
    
    errors = []
    for filename in args.files:
        filepath = Path(filename)
        if filepath.suffix == '.py':
            errors.extend(check_file(filepath))
    
    if errors:
        print("Exception handling issues found:")
        for filepath, line, msg in errors:
            print(f"{filepath}:{line}: {msg}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

## Implementation Timeline and Priorities

### Week 1: Core Infrastructure
- [ ] Day 1-2: Update ErrorHandlerMixin with enhanced features
- [ ] Day 2-3: Create new exception classes
- [ ] Day 3-4: Fix DockerBuilder (CRITICAL)
- [ ] Day 4-5: Fix PluginManager (CRITICAL)

### Week 2: Critical Components  
- [ ] Day 1-2: Fix Docker Compose environment
- [ ] Day 2-3: Fix ExperimentManager
- [ ] Day 3-4: Update service base classes
- [ ] Day 4-5: Test and validate changes

### Week 3: Broader Refactoring
- [ ] Day 1-2: Update remaining network environments
- [ ] Day 2-3: Fix execution environments
- [ ] Day 3-4: Create ErrorAggregator
- [ ] Day 4-5: Add testing infrastructure

### Week 4: Validation and Documentation
- [ ] Day 1-2: Add pre-commit hooks
- [ ] Day 2-3: Run full test suite
- [ ] Day 3-4: Update documentation
- [ ] Day 4-5: Performance testing

## Validation Checklist

### Per-Component Validation
- [ ] All `except Exception` replaced with specific types
- [ ] All `raise RuntimeError` replaced with PantherException subclasses
- [ ] ErrorHandlerMixin properly inherited and initialized
- [ ] Error context includes component, operation, and relevant data
- [ ] Critical errors use CRITICAL severity
- [ ] Proper exception chaining with `raise ... from e`

### Integration Validation
- [ ] Fast-fail triggers on critical Docker errors
- [ ] Plugin load failures handled based on criticality
- [ ] Network setup errors trigger proper cleanup
- [ ] Error aggregation works across components
- [ ] Logs contain full error context

### Testing Validation
- [ ] Unit tests cover error paths
- [ ] Integration tests verify error cascades
- [ ] Performance impact < 5% overhead
- [ ] No regressions in existing tests

## Migration Commands

```bash
# Remove duplicate error handler
rm panther/plugins/environments/network_environment/mixins/error_handler.py

# Update imports in all files
find . -name "*.py" -exec sed -i '' 's/from panther.plugins.environments.network_environment.mixins import ErrorHandlerMixin/from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin/g' {} \;

# Find all broad exception catches
grep -r "except Exception" --include="*.py" panther/ | grep -v "test_" | wc -l

# Run new exception checker
python dev/scripts/check_exception_handling.py panther/**/*.py
```

This concrete implementation plan provides specific file references, code examples, and a clear timeline for improving error handling across the PANTHER codebase.