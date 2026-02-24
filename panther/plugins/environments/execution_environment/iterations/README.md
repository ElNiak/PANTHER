# Iterations Execution Environment Plugin

> **Plugin Type**: Execution Environment
> **Source Location**: `plugins/environments/execution_environment/iterations/`

## Overview

The Iterations Execution Environment plugin provides a framework for running test scenarios multiple times with varying parameters. This plugin is essential for collecting statistical data, performing stress tests, and evaluating system behavior under consistent or varying conditions over multiple execution cycles.

## Configuration Options

<!-- src: config_schema.py -->

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `iterations` | `int` | `1` | Number of times to repeat the test |
| `parallel` | `bool` | `false` | Whether to run iterations in parallel |
| `vary_parameters` | `bool` | `false` | Whether to vary parameters between iterations |
| `parameter_sets` | `List` | `[]` | Sets of parameters to use for different iterations |
| `aggregate_results` | `bool` | `true` | Whether to aggregate results across iterations |

## Usage Example

```yaml
execution_environments:
  - type: iterations
    iterations: 10
    parallel: false
    vary_parameters: true
    parameter_sets:
      - { timeout: 1000, packet_size: 512 }
      - { timeout: 2000, packet_size: 1024 }
      - { timeout: 3000, packet_size: 2048 }
    aggregate_results: true
```

## Integration

- **Test Manager** -- Controls the execution flow of multiple test iterations.
- **Results Collector** -- Aggregates results from multiple iterations for statistical analysis.
- **Other Execution Environments** -- Can wrap other execution environments to repeat their testing.

## Troubleshooting

### Resource Contention in Parallel Mode

When running iterations in parallel, monitor system resource usage. Consider reducing parallelism if resource constraints are observed.

### Inconsistent Results

Check for external factors affecting the test environment between iterations. Ensure clean state between test iterations for reproducibility.

### Long Execution Times

Balance the number of iterations with time constraints. Consider sampling approaches for very large iteration counts.

## References

- PANTHER Execution Environment Interface
