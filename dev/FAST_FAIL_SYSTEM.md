# PANTHER Fast-Fail System Documentation

## Overview

The PANTHER fast-fail system provides intelligent experiment termination when critical errors occur, preventing resource waste and enabling rapid feedback during protocol testing. The system supports both global and test-level configuration with comprehensive error categorization and cascade detection.

## Table of Contents

- [Expected Behavior](#expected-behavior)
- [Configuration Guide](#configuration-guide)
- [Implementation Details](#implementation-details)
- [Future Work](#future-work)
- [Migration Guide](#migration-guide)

## Expected Behavior

### Decision Logic Flow

The fast-fail system uses a hierarchical decision model:

1. **Global Configuration**: `fast_fail.enabled` sets the default behavior
2. **Test-Level Control**: `fast_fail.test_level` enables per-test overrides
3. **Test-Specific Settings**: Individual tests can specify `fast_fail_enabled`

### Behavior Matrix

| Global Enabled | Test Level | Test Setting | Result | Notes |
|---------------|------------|--------------|---------|-------|
| `true` | `false` | N/A | ✅ **Enabled** | All tests use global setting |
| `false` | `false` | N/A | ❌ **Disabled** | All tests use global setting |
| `true` | `true` | `null` | ✅ **Enabled** | Test inherits global setting |
| `true` | `true` | `true` | ✅ **Enabled** | Test overrides to enabled |
| `true` | `true` | `false` | ❌ **Disabled** | Test overrides to disabled |
| `false` | `true` | `null` | ❌ **Disabled** | Test inherits global setting |
| `false` | `true` | `true` | ✅ **Enabled** | Test overrides to enabled |
| `false` | `true` | `false` | ❌ **Disabled** | Test overrides to disabled |

### Default Behavior Examples

#### Scenario 1: Global Fast-Fail Only
```yaml
fast_fail:
  enabled: true
  test_level: false  # No per-test control

tests:
  - name: "Test A"
    # Result: ENABLED (inherits global)
  - name: "Test B" 
    fast_fail_enabled: false  # IGNORED - test_level is false
    # Result: ENABLED (inherits global)
```

#### Scenario 2: Test-Level Control Enabled
```yaml
fast_fail:
  enabled: true
  test_level: true   # Enable per-test control

tests:
  - name: "Test A"
    # No fast_fail_enabled specified
    # Result: ENABLED (inherits global default)
    
  - name: "Test B"
    fast_fail_enabled: false
    # Result: DISABLED (test override)
    
  - name: "Test C"
    fast_fail_enabled: true
    # Result: ENABLED (test override)
```

#### Scenario 3: Global Disabled, Selective Enabling
```yaml
fast_fail:
  enabled: false     # Global disabled
  test_level: true

tests:
  - name: "Standard Test"
    # Result: DISABLED (inherits global)
    
  - name: "Critical Test"
    fast_fail_enabled: true
    # Result: ENABLED (test override for critical tests)
```

## Configuration Guide

### Global Configuration

The `FastFailConfig` class provides comprehensive control over fast-fail behavior:

```yaml
fast_fail:
  # Core Settings
  enabled: true                      # Global fast-fail enable/disable
  test_level: false                  # Enable per-test control
  
  # Error Type Controls
  docker_build_failures: true       # Fail on Docker build errors
  docker_runtime_failures: true     # Fail on Docker runtime errors
  plugin_load_failures: true        # Fail on plugin loading errors
  service_start_failures: true      # Fail on service startup errors
  network_setup_failures: true      # Fail on network setup errors
  port_conflict_failures: true      # Fail on port conflicts
  ivy_compilation_failures: true    # Fail on Ivy compilation errors
  resource_exhaustion: true         # Fail on resource exhaustion
  certificate_failures: true        # Fail on certificate errors
  configuration_failures: true      # Fail on configuration errors
  timeout_cascades: true           # Fail on timeout cascades
  
  # Advanced Settings
  critical_only: false              # Only fail on CRITICAL severity errors
  max_errors_before_fail: 10        # Maximum errors before cascade failure
  timeout_cascade_threshold: 3      # Consecutive timeouts before cascade
  disk_space_threshold_gb: 2.0      # Minimum disk space in GB
```

### Test-Level Configuration

Individual tests can override global settings when `test_level: true`:

```yaml
tests:
  - name: "Production Validation"
    description: "Critical test that must fail fast"
    fast_fail_enabled: true
    network_environment:
      type: docker_compose
    services:
      # ... service configuration
      
  - name: "Experimental Feature"
    description: "Allow this test to continue on errors"
    fast_fail_enabled: false
    # ... rest of test configuration
    
  - name: "Standard Test"
    description: "Uses global fast-fail setting"
    # fast_fail_enabled not specified - inherits global
    # ... rest of test configuration
```

### Error Category Configuration

Fine-tune which error types trigger fast-fail:

```yaml
fast_fail:
  enabled: true
  test_level: true
  
  # Critical infrastructure errors - always fail fast
  docker_build_failures: true
  docker_runtime_failures: true
  resource_exhaustion: true
  
  # Service-level errors - configurable
  service_start_failures: true
  port_conflict_failures: true
  
  # Test-specific errors - may want to continue
  ivy_compilation_failures: false   # Let Ivy tests continue
  certificate_failures: true       # Stop on cert issues
  
  # Cascade prevention
  timeout_cascades: true
  timeout_cascade_threshold: 2     # Fail after 2 consecutive timeouts
```

## Implementation Details

### Architecture Overview

The fast-fail system consists of several key components:

```
ExperimentManager
├── FastFailHandler (global)
├── TestCase[]
│   ├── FastFailHandler (per-test)
│   └── Error Detection & Handling
└── Error Classification & Cascade Detection
```

### Key Classes

#### FastFailHandler (`panther/core/exceptions/fast_fail.py`)

```python
class FastFailHandler:
    def __init__(self, enabled: bool = True, logger: Optional[logging.Logger] = None):
        self.enabled = enabled
        self.error_count = 0
        self.critical_error: Optional[PantherException] = None
        self.error_history: List[Tuple[datetime, PantherException]] = []
        self.cascade_thresholds = {
            ErrorCategory.TIMEOUT: 3,
            ErrorCategory.DOCKER_RUNTIME: 2,
            ErrorCategory.SERVICE_START: 3,
        }
    
    def handle_error(self, error: PantherException, raise_on_critical: bool = True) -> bool:
        """Handle an error and determine if execution should continue."""
        
    def detect_cascade(self, error: PantherException) -> Optional[ErrorCascadeException]:
        """Detect if we're in an error cascade situation."""
```

**Key Features:**
- Error counting and history tracking
- Cascade detection for repeated failures
- Configurable thresholds per error category
- Integration with logging system

#### Error Exception Hierarchy

```python
PantherException (base)
├── DockerComposeException        # CRITICAL - Docker orchestration failures
├── PortConflictException         # HIGH - Network conflicts
├── IvyCompilationException       # MEDIUM - Formal verification failures
├── ResourceExhaustionException   # CRITICAL - System resource issues
├── CertificateException          # HIGH - TLS/Certificate problems
├── ConfigurationException        # HIGH - Invalid configurations
├── TimeoutCascadeException       # CRITICAL - Repeated timeout failures
├── PluginLoadException          # HIGH - Plugin system failures
├── ServiceStartException        # MEDIUM - Service startup issues
├── NetworkSetupException        # HIGH - Network infrastructure
├── TestExecutionException       # MEDIUM - Test-specific failures
├── ExperimentInitializationException  # CRITICAL - Core system
└── ErrorCascadeException        # CRITICAL - Detected error cascades
```

### Error Severity Levels

```python
class ErrorSeverity(Enum):
    LOW = "low"           # Continue execution, log warning
    MEDIUM = "medium"     # Continue with caution, increment counter
    HIGH = "high"         # Stop current test, continue experiment
    CRITICAL = "critical" # Stop entire experiment immediately
```

### Error Categories

```python
class ErrorCategory(Enum):
    DOCKER_BUILD = "docker_build"
    DOCKER_RUNTIME = "docker_runtime"
    PLUGIN_LOAD = "plugin_load"
    SERVICE_START = "service_start"
    NETWORK_SETUP = "network_setup"
    PORT_CONFLICT = "port_conflict"
    IVY_COMPILATION = "ivy_compilation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CERTIFICATE = "certificate"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    TEST_EXECUTION = "test_execution"
```

### Integration Points

#### 1. Experiment Manager Integration

```python
# panther/core/experiment_manager.py
class ExperimentManager:
    def __init__(self, global_config: GlobalConfig, ...):
        # Configure fast fail handler based on global config
        fast_fail_config = global_config.fast_fail
        self.fast_fail_handler = FastFailHandler(
            enabled=fast_fail_enabled and fast_fail_config.enabled,
            logger=self.logger
        )
    
    def run_tests(self):
        # Handle critical errors that should terminate experiment
        except (DockerComposeException, PortConflictException, ...) as test_error:
            should_continue = self.fast_fail_handler.handle_error(
                test_error, raise_on_critical=False
            )
            if not should_continue:
                self.logger.critical("Critical error, terminating experiment")
                raise test_error
```

#### 2. Test Case Integration

```python
# panther/core/test_cases/test_case_impl.py
class TestCase:
    def _init_fast_fail_handler(self, test_config: TestConfig, global_config: GlobalConfig):
        """Initialize test-level fast-fail handler based on configuration."""
        fast_fail_config = global_config.fast_fail
        
        # Determine if fast-fail should be enabled for this test
        if fast_fail_config.test_level and test_config.fast_fail_enabled is not None:
            fast_fail_enabled = test_config.fast_fail_enabled
        else:
            fast_fail_enabled = fast_fail_config.enabled
        
        self.fast_fail_handler = FastFailHandler(
            enabled=fast_fail_enabled,
            logger=self.logger
        )
```

#### 3. Error Classification System

```python
# panther/plugins/environments/network_environment/mixins/error_handler.py
class ErrorClassifier:
    ERROR_PATTERNS = {
        r".*address already in use.*": (PortConflictException, {
            "category": ErrorCategory.PORT_CONFLICT,
            "severity": ErrorSeverity.HIGH
        }),
        r".*no space left on device.*": (ResourceExhaustionException, {
            "category": ErrorCategory.RESOURCE_EXHAUSTION,
            "severity": ErrorSeverity.CRITICAL
        }),
        # ... 20+ error patterns
    }
    
    def classify_error(self, error_output: str) -> Optional[PantherException]:
        """Classify error based on output patterns."""
```

### Cascade Detection Algorithm

The system detects error cascades to prevent infinite retry loops:

```python
def detect_cascade(self, error: PantherException) -> Optional[ErrorCascadeException]:
    """Detect if we're in an error cascade situation."""
    category = error.category
    threshold = self.cascade_thresholds.get(category, 5)
    
    # Count recent errors of the same category
    recent_errors = [
        e for timestamp, e in self.error_history[-10:]
        if e.category == category and 
           (datetime.now() - timestamp).total_seconds() < 300  # 5 minutes
    ]
    
    if len(recent_errors) >= threshold:
        return ErrorCascadeException(
            f"Detected {category.value} error cascade: {len(recent_errors)} errors in 5 minutes",
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.CRITICAL
        )
    
    return None
```

## Future Work

### Planned Enhancements

#### 1. Service-Level Fast-Fail Control
```yaml
tests:
  - name: "Multi-Service Test"
    fast_fail_enabled: true
    services:
      critical_service:
        implementation: {name: picoquic, type: iut}
        fast_fail_enabled: true      # Fail fast for this service
      experimental_service:
        implementation: {name: aioquic, type: iut}  
        fast_fail_enabled: false     # Allow this service to fail
```

#### 2. Dynamic Fast-Fail Configuration
- Runtime configuration updates via API
- Conditional fast-fail based on test results
- Machine learning-based error prediction

#### 3. Enhanced Error Recovery
```yaml
fast_fail:
  recovery_strategies:
    docker_build_failures:
      retry_count: 3
      retry_delay: 30
      cleanup_before_retry: true
    port_conflicts:
      auto_resolve: true
      port_range: "4400-4500"
```

#### 4. Advanced Cascade Detection
- Pattern-based cascade detection
- Cross-test cascade analysis  
- Predictive failure modeling
- Resource usage correlation

#### 5. Integration with External Systems
- Prometheus metrics integration
- Slack/Teams notifications for critical failures
- JIRA ticket creation for recurring failures
- Integration with CI/CD pipeline controls

### Known Limitations

1. **Configuration Complexity**: The current system has many configuration options that may be overwhelming for new users
2. **Error Pattern Maintenance**: Manual maintenance of error patterns requires ongoing updates
3. **Resource Cleanup**: Failed experiments may leave Docker containers/networks in inconsistent states
4. **Cross-Test Dependencies**: Cascade detection doesn't account for dependencies between tests

### Proposed Solutions

#### 1. Configuration Presets
```yaml
fast_fail:
  preset: "production"  # predefined: development, testing, production, research
  # Automatically configures appropriate settings for each use case
```

#### 2. Intelligent Error Pattern Learning
- Automatic pattern extraction from error logs
- Community-shared error pattern database
- Machine learning-based error classification

#### 3. Comprehensive Cleanup Coordinator
```python
class ExperimentCleanupCoordinator:
    def cleanup_failed_experiment(self, experiment_id: str):
        """Comprehensive cleanup for failed experiments."""
        self.stop_all_containers(experiment_id)
        self.remove_networks(experiment_id)
        self.cleanup_volumes(experiment_id)
        self.release_ports(experiment_id)
        self.notify_observers(experiment_id)
```

#### 4. Dependency-Aware Cascade Detection
```yaml
tests:
  - name: "Setup Test"
    dependencies: []
  - name: "Main Test"  
    dependencies: ["Setup Test"]
    fast_fail_cascade_scope: "dependent_tests"  # Fail dependent tests too
```

## Migration Guide

### From `features.fast_fail`

The old `features.fast_fail` configuration is deprecated. Here's how to migrate:

#### Old Configuration (Deprecated)
```yaml
features:
  fast_fail: true  # DEPRECATED - will show warning
```

#### New Configuration
```yaml
fast_fail:
  enabled: true
  test_level: false  # Same behavior as old system
```

#### Advanced Migration
```yaml
# Old: Simple global control
features:
  fast_fail: true

# New: Granular control
fast_fail:
  enabled: true
  test_level: true                 # Enable per-test control
  docker_build_failures: true     # Explicit error type control
  ivy_compilation_failures: false # Allow Ivy tests to continue
  timeout_cascade_threshold: 2    # Faster cascade detection
```

### Deprecation Timeline

- **Current**: `features.fast_fail` shows deprecation warnings
- **Next Release**: Remove `features.fast_fail` support entirely
- **Future**: Enhanced fast-fail features require new configuration

## Best Practices

### 1. Development vs Production Configuration

**Development:**
```yaml
fast_fail:
  enabled: false              # Let all tests run for debugging
  test_level: true           # Enable selective testing
  max_errors_before_fail: 50 # Higher tolerance
```

**Production:**
```yaml
fast_fail:
  enabled: true              # Fail fast to save resources
  test_level: false          # Consistent behavior
  critical_only: true        # Only fail on critical errors
  timeout_cascade_threshold: 2  # Quick cascade detection
```

### 2. Test Design Recommendations

- Use `fast_fail_enabled: true` for critical infrastructure tests
- Use `fast_fail_enabled: false` for experimental or research tests
- Group related tests to minimize cascade effects
- Design tests with proper cleanup in teardown phases

### 3. Error Handling Guidelines

- Implement proper logging in service managers
- Use structured error messages for better classification
- Include context information in exception details
- Test error scenarios explicitly in test suites

### 4. Monitoring and Observability

- Enable metrics collection for fast-fail events
- Monitor cascade detection frequency
- Track experiment failure rates by error category
- Set up alerts for critical error patterns

## Troubleshooting

### Common Issues

1. **Fast-fail not working**: Check that `enabled: true` and error types are configured
2. **Test-level settings ignored**: Verify `test_level: true` in global config
3. **Unexpected experiment termination**: Review error logs for cascade detection
4. **Configuration validation errors**: Check YAML syntax and field types

### Debug Configuration

```yaml
fast_fail:
  enabled: true
  test_level: true
  
# Enable detailed logging
logging:
  level: DEBUG
  
observers:
  logger:
    enabled: true
    log_level: DEBUG
```

This will provide detailed information about fast-fail decisions and error handling.