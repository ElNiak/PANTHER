# Priority Error Handling Fixes

## CRITICAL - Fix These First (Week 1)

### 1. DockerBuilder - Prevents All Docker Operations
**File**: `/panther/core/docker_builder/docker_builder.py`

**Line 158-160**: Docker connection
```python
# CURRENT (BAD)
except docker.errors.DockerException as e:
    self.logger.error(f"Docker error: {e}")
    raise RuntimeError(f"Failed to connect to Docker: {e}")

# FIXED (GOOD)
except docker.errors.DockerException as e:
    docker_error = DockerBuildException(
        message=f"Failed to connect to Docker daemon: {str(e)}",
        image_name="N/A",
        dockerfile="N/A"
    )
    self.handle_error(docker_error, raise_on_critical=True)
```

**Line 450-453**: Build failures
```python
# CURRENT (BAD)
except Exception as e:
    self.logger.error(f"Failed to build image {image_name}: {e}")
    raise

# FIXED (GOOD)
except docker.errors.BuildError as e:
    build_error = DockerBuildException(
        message=f"Docker build failed: {str(e)}",
        image_name=image_name,
        dockerfile=str(dockerfile_path)
    )
    self.handle_error(build_error, raise_on_critical=True)
```

### 2. PluginManager - Blocks Plugin Loading
**File**: `/panther/plugins/plugin_manager.py`

**Line 229-233**: Service manager creation
```python
# CURRENT (BAD)
except Exception as e:  # pylint: disable=broad-exception-caught
    self.logger.error(f"Error creating service manager for {plugin_name}: {e}")
    return None

# FIXED (GOOD)
except (ImportError, AttributeError) as e:
    plugin_error = PluginLoadException(
        message=f"Failed to create service manager: {str(e)}",
        plugin_name=plugin_name,
        plugin_type="service",
        severity=ErrorSeverity.HIGH
    )
    if not self.handle_error(plugin_error, raise_on_critical=False):
        return None
```

**Line 341-345**: Docker build in plugin
```python
# CURRENT (BAD)
except Exception as e:  # pylint: disable=broad-exception-caught
    self.logger.error("Error building Docker image from path %s: %s", path, e)

# FIXED (GOOD)
except docker.errors.BuildError as e:
    docker_error = DockerBuildException(
        message=f"Plugin Docker build failed: {str(e)}",
        image_name=service_manager.docker_image_name,
        dockerfile=str(dockerfile_path)
    )
    self.handle_error(docker_error, raise_on_critical=True)
```

### 3. Docker Compose Environment - Service Deployment
**File**: `/panther/plugins/environments/network_environment/docker_compose/docker_compose.py`

**Line 631-633**: Service launch
```python
# CURRENT (BAD)
except Exception as e:
    self.logger.error(f"Error launching Docker Compose services: {e}")
    self.teardown_environment()

# FIXED (GOOD)
except subprocess.CalledProcessError as e:
    compose_error = CommandExecutionException(
        message=f"Docker Compose launch failed: {e.stderr or str(e)}",
        command=compose_up_cmd,
        exit_code=e.returncode
    )
    self.teardown_environment()
    self.handle_error(compose_error, severity=ErrorSeverity.HIGH, raise_on_critical=True)
```

### 4. ExperimentManager - Test Execution
**File**: `/panther/core/experiment_manager.py`

**Line 525-533**: Test execution catch-all
```python
# CURRENT (BAD)
except Exception as test_error:  # pylint: disable=broad-except
    failed_tests += 1
    self._handle_test_error(test_case, test_error)

# FIXED (GOOD)
except PantherExperimentError as test_error:
    # Already properly typed
    failed_tests += 1
    self._handle_test_error(test_case, test_error)
except Exception as test_error:
    # Log unexpected exception type for future handling
    self.logger.error(f"Unexpected exception type {type(test_error).__name__} in test execution")
    # Convert to PantherException
    panther_error = TestExecutionError(
        f"Unexpected error: {str(test_error)}",
        test_name=test_case.test_config.name,
        error_type=type(test_error).__name__
    )
    failed_tests += 1
    self._handle_test_error(test_case, panther_error)
```

## HIGH PRIORITY - Fix in Week 2

### 5. BaseNetworkEnvironment
**File**: `/panther/plugins/environments/network_environment/base_network_environment.py`

Multiple locations with bare error handling need context and proper exception types.

### 6. Service Base Classes
**Files**: 
- `/panther/plugins/services/base/quic_service_base.py`
- `/panther/plugins/services/base/python_quic_base.py`
- `/panther/plugins/services/base/rust_quic_base.py`

Add error context and proper exception handling to command generation.

### 7. Shadow NS Environment
**File**: `/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py`

Has multiple broad catches that need specific handling.

## MEDIUM PRIORITY - Fix in Week 3

### 8. Command Processor
**File**: `/panther/core/command_processor/command_processor.py`

Improve error messages and add CommandExecutionException.

### 9. Execution Environments
**Files in**: `/panther/plugins/environments/execution_environment/`

Each execution environment (strace, gperf, memcheck) needs proper error handling.

### 10. Service Implementations
**Files in**: `/panther/plugins/services/iut/`

Each service implementation needs to properly handle and propagate errors.

## Quick Wins - Can Fix Anytime

### Remove Duplicate Error Handler
```bash
rm panther/plugins/environments/network_environment/mixins/error_handler.py
```

### Update All Imports
```bash
# Find files using the duplicate
grep -r "from panther.plugins.environments.network_environment.mixins import ErrorHandlerMixin" --include="*.py" panther/

# Update them to use core version
find . -name "*.py" -exec sed -i '' 's/from panther.plugins.environments.network_environment.mixins import ErrorHandlerMixin/from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin/g' {} \;
```

### Find Remaining Broad Catches
```bash
# Count broad exception catches
grep -r "except Exception" --include="*.py" panther/ | grep -v "test_" | wc -l

# Find bare except clauses
grep -r "except:" --include="*.py" panther/ | grep -v "test_"

# Find RuntimeError usage
grep -r "raise RuntimeError" --include="*.py" panther/
```

## Testing Each Fix

After each component fix, run:

```bash
# Unit tests for the component
pytest tests/unit/test_core/test_docker_builder.py -v
pytest tests/unit/test_plugins/test_plugin_manager.py -v

# Integration tests
pytest tests/integration/test_fast_fail_integration.py -v

# Full test suite (before committing)
pytest tests/ -v
```

## Validation Script

Create `/dev/scripts/validate_error_handling.py`:

```python
#!/usr/bin/env python3
"""Validate error handling improvements."""

import subprocess
import sys
from pathlib import Path

def check_broad_exceptions():
    """Check for remaining broad exception catches."""
    result = subprocess.run(
        ['grep', '-r', 'except Exception', '--include=*.py', 'panther/'],
        capture_output=True,
        text=True
    )
    
    # Filter out test files and allowed cases
    bad_catches = []
    for line in result.stdout.split('\n'):
        if line and 'test_' not in line and '# allowed' not in line:
            bad_catches.append(line)
    
    return bad_catches

def check_runtime_errors():
    """Check for RuntimeError usage."""
    result = subprocess.run(
        ['grep', '-r', 'raise RuntimeError', '--include=*.py', 'panther/'],
        capture_output=True,
        text=True
    )
    
    return [line for line in result.stdout.split('\n') if line]

def main():
    """Run all validation checks."""
    print("Validating error handling improvements...")
    
    # Check broad exceptions
    broad_catches = check_broad_exceptions()
    if broad_catches:
        print(f"\n❌ Found {len(broad_catches)} broad exception catches:")
        for catch in broad_catches[:5]:  # Show first 5
            print(f"  {catch}")
        if len(broad_catches) > 5:
            print(f"  ... and {len(broad_catches) - 5} more")
    else:
        print("✅ No broad exception catches found")
    
    # Check RuntimeErrors
    runtime_errors = check_runtime_errors()
    if runtime_errors:
        print(f"\n❌ Found {len(runtime_errors)} RuntimeError uses:")
        for error in runtime_errors[:5]:
            print(f"  {error}")
    else:
        print("✅ No RuntimeError usage found")
    
    # Check imports
    result = subprocess.run(
        ['grep', '-r', 'from panther.plugins.environments.network_environment.mixins import ErrorHandlerMixin', '--include=*.py', '.'],
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        print("\n❌ Found imports of duplicate ErrorHandlerMixin")
    else:
        print("✅ All imports use core ErrorHandlerMixin")
    
    # Final result
    if broad_catches or runtime_errors or result.stdout:
        print("\n❌ Error handling validation FAILED")
        return 1
    else:
        print("\n✅ Error handling validation PASSED")
        return 0

if __name__ == '__main__':
    sys.exit(main())
```

Run validation:
```bash
chmod +x dev/scripts/validate_error_handling.py
./dev/scripts/validate_error_handling.py
```

This priority list focuses on the most critical error handling issues that directly impact system reliability and user experience.