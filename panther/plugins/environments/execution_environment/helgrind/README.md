# Helgrind Execution Environment Plugin

!!! info "Thread Error Detection Plugin"
    Helgrind integrates Valgrind's thread error detector for finding race conditions, deadlocks, and synchronization errors in multi-threaded applications during PANTHER experiments.

> **Plugin Type**: Execution Environment

> **Verified Source Location**: `plugins/environments/execution_environment/helgrind/`

## Overview

The Helgrind Execution Environment plugin integrates Valgrind's Helgrind tool into the PANTHER testing framework. Helgrind is a thread error detector designed to find synchronization errors in C, C++, and other threaded applications.

## Features

!!! warning "System Requirements"
    Helgrind requires Valgrind to be installed on the host system and may significantly impact application performance during analysis. Use only for debugging and testing scenarios.

- Detects race conditions in multi-threaded programs
- Identifies lock order violations that could lead to deadlocks
- Detects incorrect use of POSIX pthreads API
- Full history tracking for comprehensive thread interaction analysis
- Child process tracking for complete application threading analysis

## Configuration Options

<!-- src: config_schema.py -->

### Inherited Fields (from BasePluginConfig / ExecutionEnvironmentPluginConfig)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether the plugin is enabled |
| `version` | `Optional[str]` | `None` | Plugin version |
| `priority` | `int` | `100` | Plugin execution priority |
| `collect_metrics` | `bool` | `True` | Whether to collect metrics |

### Helgrind-Specific Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | `"helgrind"` | Execution environment type |
| `valgrind_binary` | `str` | `"/usr/bin/valgrind"` | Absolute path to the Valgrind binary. Override if Valgrind is installed in a non-standard location. |
| `output_format` | `str` | `"text"` | Output format for Helgrind reports. Options: `text` (human-readable), `xml` (machine-parseable). |
| `history_level` | `str` | `"full"` | Level of detail for race-detection history. Options: `none` (fastest, no history), `approx` (approximate, moderate overhead), `full` (complete history, slowest but most accurate). |
| `conflict_cache_size` | `int` | `1000000` | Number of entries in the conflict cache. Larger values may detect more races at the cost of higher memory usage. |
| `track_lockorders` | `bool` | `True` | Track lock acquisition order to detect potential deadlocks caused by inconsistent locking. |
| `check_stack_refs` | `bool` | `True` | Check for data races on stack-allocated variables. May produce false positives for thread-local storage patterns. |
| `ignore_thread_creation` | `bool` | `False` | Ignore potential races during thread creation and initialization. Reduces false positives in programs with safe initialization patterns. |
| `free_is_write` | `bool` | `False` | Treat heap deallocation (free) as a write operation for race-detection purposes. Finds more races but increases false positives. |
| `cache_size` | `int` | `32` | Size of the internal cache in MB. Larger values may improve performance for programs with many memory accesses. |
| `suppression_file` | `Optional[str]` | `None` | Path to a Valgrind suppression file (.supp) to filter known threading issues. Suppression entries are Helgrind-specific and not interchangeable with Memcheck suppressions. |
| `show_below_main` | `bool` | `False` | Show stack frames below main() in stack traces. Usually not needed unless debugging runtime startup code. |
| `track_fds` | `bool` | `False` | Track file descriptor operations and report leaks at exit. Useful for detecting resource leaks alongside threading errors. |
| `time_stamp` | `bool` | `True` | Add wall-clock timestamps to Valgrind log entries. Helpful for correlating errors with external events. |
| `additional_parameters` | `List[str]` | `[]` | Additional command-line parameters passed verbatim to `valgrind --tool=helgrind`. Example: `['--fair-sched=yes', '--read-var-info=yes']`. |
| `verbosity` | `int` | `1` | Valgrind verbosity level. Range: 0 (minimal) to 3 (maximum detail including internal debugging). |

### Background Monitoring Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_background_monitoring` | `bool` | `True` | Enable background monitoring for non-blocking service health checks. |
| `monitoring_interval_seconds` | `int` | `5` | Health-check polling interval in seconds. |
| `failure_threshold_count` | `int` | `3` | Number of consecutive health-check failures before the service is marked unhealthy. |
| `allow_partial_deployment` | `bool` | `False` | Allow experiment deployment to proceed even if some non-critical services fail to start. |
| `critical_services` | `List[str]` | `[]` | List of service names that must be running for the deployment to be considered successful. |

## Usage Example

```yaml
execution_environments:
  - type: helgrind
    history_level: full
    track_lockorders: true
    check_stack_refs: true
    suppression_file: /path/to/helgrind.supp
    output_format: xml
```

## Integration

The Helgrind Execution Environment integrates with:

1. **Service Managers** - Prepends Valgrind Helgrind commands to service execution
2. **Test Framework** - Captures and reports thread synchronization errors during test execution
3. **Result Collection** - Helgrind logs can be included in test results

## Implementation Details

The plugin works by prepending Valgrind Helgrind commands to the service execution chain:

```bash
valgrind --tool=helgrind --trace-children=yes --history-level=full <service-command>
```

This configuration provides comprehensive detection of thread synchronization issues in the applications being tested.

## Troubleshooting

### Common Issues

1. **Performance Degradation**
   - Helgrind significantly slows down program execution
   - Consider using smaller test cases when using Helgrind

2. **Large Number of Reported Issues**
   - Complex multithreaded programs may generate numerous reports
   - Focus on recurring patterns in the output

3. **False Positives**
   - Some custom synchronization mechanisms may trigger false positives
   - Consider using suppression files for known acceptable patterns

## Extension Points

- Custom Valgrind options can be added through configuration
- Integration with thread visualization tools could be added in future versions

## References

- [Valgrind Helgrind Documentation](https://valgrind.org/docs/manual/hg-manual.html)
- [PANTHER Execution Environment Interface](panther/docs/environments/execution_environment/index.md)
