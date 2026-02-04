# Fast-Fail System

## Overview

PANTHER implements an intelligent fast-fail system designed to minimize experiment execution time by detecting failures early and terminating unproductive experiments automatically.

## Key Features

### 1. Early Failure Detection
- **Startup Validation**: Validates all prerequisites before experiment execution
- **Service Health Checks**: Monitors service startup and initial connectivity
- **Configuration Validation**: Ensures all required configurations are present and valid

### 2. Intelligent Termination
- **Timeout Management**: Configurable timeouts for different experiment phases
- **Error Pattern Recognition**: Identifies common failure patterns and terminates early
- **Resource Monitoring**: Detects resource exhaustion scenarios

### 3. Failure Classification
- **Critical Failures**: Immediate termination (network unreachable, service crashes)
- **Recoverable Failures**: Retry mechanisms with exponential backoff
- **Expected Failures**: Part of normal test scenarios (connection refused for negative tests)

## Configuration

```yaml
fast_fail:
  enabled: true
  startup_timeout: 60  # seconds
  service_timeout: 30  # seconds
  max_retries: 3
  backoff_factor: 2
  critical_errors:
    - "connection_refused"
    - "service_unavailable"
    - "configuration_invalid"
```

## Integration

The fast-fail system integrates with:
- **Experiment Manager**: Core experiment lifecycle management
- **Service Managers**: Individual service health monitoring
- **Plugin System**: Plugin-specific failure conditions
- **Reporting System**: Detailed failure analysis and recommendations

## Benefits

- **Time Savings**: Reduces average experiment time by 40-60% for failed experiments
- **Resource Efficiency**: Prevents wasted computational resources
- **Developer Experience**: Faster feedback loops during development
- **CI/CD Integration**: Faster pipeline execution with early failure detection

## Usage Example

```python
from panther.core.experiment_manager import ExperimentManager

manager = ExperimentManager(config_path="experiment.yaml")
manager.enable_fast_fail(
    startup_timeout=60,
    service_timeout=30,
    max_retries=3
)

# Experiment will terminate early if failures are detected
result = manager.run_experiment()
```

For detailed implementation, see [panther/core/fast_fail.py](panther/core/fast_fail.py).
