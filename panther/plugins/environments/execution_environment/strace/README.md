# Strace Execution Environment Plugin

> **Plugin Type**: Execution Environment
> **Source Location**: `plugins/environments/execution_environment/strace/`

## Overview

The Strace Environment plugin enables system call tracing for PANTHER services. It leverages the Linux `strace` utility to track, log, and analyze system calls made by protocol implementations, providing deep insights into program behavior and interaction with the operating system.

> [!WARNING]
> "Linux-Only Tool"
> Strace is a Linux-specific tool and requires appropriate permissions (e.g., `CAP_SYS_PTRACE`) to attach to processes. Ensure the execution environment has strace installed and accessible.

## Configuration Options

<!-- src: config_schema.py -->

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | `str` | `"strace"` | Execution environment type |
| `strace_binary` | `str` | `"/usr/bin/strace"` | Path to strace executable |
| `excluded_syscalls` | `List[str]` | `["nanosleep", ...]` | Syscalls to exclude from tracing |
| `include_kernel_stack` | `bool` | `True` | Include kernel stack trace in output |
| `trace_network_syscalls` | `bool` | `True` | Focus on network-related syscalls |
| `timeout` | `int` | `60` | Timeout in seconds |
| `output_file` | `str` | `"/app/logs/strace.log"` | Output file path |
| `additional_parameters` | `List[str]` | `[]` | Additional strace parameters |
| `monitored_process` | `Optional[str]` | `None` | Specific process to monitor |
| `network_focus` | `bool` | `True` | Emphasis on network calls |

Inherited from `ExecutionEnvironmentPluginConfig` / `BasePluginConfig`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether the plugin is enabled |
| `collect_metrics` | `bool` | `True` | Whether to collect metrics |

## Usage Example

```yaml
execution_environments:
  - type: strace
    trace_network_syscalls: true
    excluded_syscalls:
      - nanosleep
      - getitimer
      - alarm
    additional_parameters:
      - "-e trace=network"
      - "-s 1024"
      - "-f"
```

## Integration

- **Service Managers** -- Prepends the `strace` command to service execution for transparent system call capture.
- **Result Collection** -- Strace logs are saved to the configured output path and included in test results.
- **Security Auditing** -- Monitors file and network operations for protocol security analysis.
- **Performance Analysis** -- Identifies system call bottlenecks in protocol implementations.

## Troubleshooting

### Permission Denied

Ensure the container is running with appropriate capabilities. Add `CAP_SYS_PTRACE` or use `privileged: true` in the Docker Compose configuration.

### Missing Strace Binary

Ensure strace is installed in the container. Add to your Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y strace
```

### High System Load

Filter system calls to only trace those relevant to your analysis by populating `excluded_syscalls` with high-frequency calls like `clock_gettime`, `gettimeofday`, and `futex`.

## References

- [strace Manual](https://strace.io/)
- PANTHER Execution Environment Interface
