# Strace System Call Tracer

> **Plugin Type**: Environment (execution_environment)
> **Verified Source Location**: `plugins/environments/execution_environment/strace/`

## Purpose and Overview

The Strace Environment plugin enables system call tracing for PANTHER services. It leverages the Linux `strace` utility to track, log, and analyze system calls made by protocol implementations, providing deep insights into program behavior and interaction with the operating system.

<!-- src: /panther/plugins/environments/execution_environment/strace/strace.py -->

This execution environment plugin is valuable for:
- Debugging protocol implementation issues
- Analyzing interactions between applications and the operating system
- Understanding file and network operations performed by services
- Identifying performance bottlenecks related to system calls
- Security analysis and auditing of protocol implementations

Strace works by intercepting and recording system calls made by programs and the signals they receive, providing a low-level view of program execution.

## Requirements and Dependencies

The plugin requires:

- **strace**: Must be installed in the container or host system
- **Linux environment**: As strace is a Linux-specific tool
- **Python Dependencies**:
  - omegaconf
  - dataclasses

Services must be running in an environment where strace has permission to attach to processes.

## Configuration Options

The Strace environment accepts the following configuration parameters:

```yaml
execution_environment:
  - name: "syscall_tracer"
    type: "execution_environment"
    implementation: "strace"
    config:
      strace_binary: "/usr/bin/strace"     # Path to strace binary
      excluded_syscalls:                   # Syscalls to exclude from tracing
        - "nanosleep"
        - "getitimer"
        - "alarm"
      include_kernel_stack: true           # Include kernel stack in output
      trace_network_syscalls: true         # Focus on network-related syscalls
      timeout: 60                          # Timeout in seconds
      output_file: "/app/logs/strace.log"  # Output file path
      additional_parameters: []            # Additional strace parameters
```

<!-- src: /panther/plugins/environments/execution_environment/strace/config_schema.py -->

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Name for this execution environment |
| `type` | string | Yes | - | Must be "execution_environment" |
| `implementation` | string | Yes | - | Must be "strace" |
| `config.strace_binary` | string | No | "/usr/bin/strace" | Path to strace executable |
| `config.excluded_syscalls` | list | No | [nanosleep, ...] | Syscalls to exclude from tracing |
| `config.include_kernel_stack` | boolean | No | true | Include kernel stack trace |
| `config.trace_network_syscalls` | boolean | No | true | Focus on network syscalls |
| `config.timeout` | integer | No | 60 | Timeout in seconds |
| `config.output_file` | string | No | "/app/logs/strace.log" | Output file path |
| `config.additional_parameters` | list | No | [] | Additional strace parameters |
| `config.monitored_process` | string | No | null | Specific process to monitor |
| `config.network_focus` | boolean | No | true | Emphasis on network calls |

## Usage Examples

### Basic Usage

```yaml
tests:
  - name: "Basic Syscall Tracing Test"
    execution_environment:
      - name: "syscall_tracer"
        type: "execution_environment"
        implementation: "strace"
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
```

### Advanced Configuration with Filtered Syscalls

```yaml
tests:
  - name: "Network Syscalls Analysis"
    execution_environment:
      - name: "network_syscall_tracer"
        type: "execution_environment"
        implementation: "strace"
        config:
          trace_network_syscalls: true
          excluded_syscalls:
            - "nanosleep"
            - "getitimer"
            - "alarm"
            - "setitimer"
            - "gettimeofday"
          additional_parameters:
            - "-e trace=network"
            - "-s 1024"  # Capture 1024 bytes of strings
            - "-f"       # Follow forks
    services:
      server:
        name: "http_server"
        implementation:
          name: "nginx"
          type: "iut"
      client:
        name: "http_client"
        implementation:
          name: "curl"
          type: "tester"
```

## Extension Points

The Strace environment plugin can be extended in several ways:

### Custom Analysis Tools

You can extend the plugin to provide custom analysis of strace output:

```python
from panther.plugins.environments.execution_environment.strace.strace import StraceEnvironment

class EnhancedStraceAnalyzer(StraceEnvironment):
    """Extended strace environment with analysis capabilities."""

    def setup_environment(self, services_managers, test_config, global_config, timestamp, plugin_loader):
        """Set up with custom analysis options."""
        super().setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader)

        for service in self.services_managers:
            # Add post-processing commands for analysis
            service.run_cmd["post_run_cmds"].append(
                f"grep 'socket\\|connect\\|accept' /app/logs/strace.log > /app/logs/network_calls.log"
            )
```

### System Call Filtering

Customize the system call filtering logic:

```python
def customize_syscall_filters(self, service_type):
    """Generate custom syscall filters based on service type."""
    if service_type == "database":
        return "-e trace=file,network,process"  # Focus on file and network operations
    elif service_type == "crypto":
        return "-e trace=memory,signal"  # Focus on memory operations
    else:
        return "-e trace=all"  # Trace all system calls
```

## Testing and Verification

To test the Strace environment plugin:

1. **Unit Tests**: Located in `/tests/unit/plugins/environments/execution_environment/strace/`
2. **Integration Tests**: Run a test configuration with the plugin enabled:
   ```bash
   python -m panther -c experiment-config/experiment_config_strace.yaml
   ```

3. **Verification Metrics**:
   - Check if strace logs are generated in the specified location
   - Verify that the logs contain expected system call patterns
   - Compare system call patterns across different runs for consistency

## Troubleshooting

### Common Issues

#### Permission Denied

**Problem**: "Permission denied" errors when strace tries to attach to processes
**Solution**: Ensure the container is running with appropriate capabilities:

```yaml
network_environment:
  type: "docker_compose"
  services:
    your_service:
      privileged: true  # Or use specific capability: CAP_SYS_PTRACE
```

#### Missing Strace Binary

**Problem**: "Command not found" errors when trying to run strace
**Solution**: Ensure strace is installed in your container:

```yaml
services:
  server:
    name: "server"
    implementation:
      pre_run_cmds:
        - "apt-get update && apt-get install -y strace"
```

#### High System Load

**Problem**: System becomes very slow when tracing all system calls
**Solution**: Filter system calls to only trace those relevant to your analysis:

```yaml
execution_environment:
  - name: "strace_env"
    type: "execution_environment"
    implementation: "strace"
    config:
      excluded_syscalls:
        - "clock_gettime"
        - "gettimeofday"
        - "futex"
```

### Debugging Tips

1. Start with a limited set of traced system calls to avoid overwhelming output
2. Use grep and other tools to filter the strace log for relevant information
3. Compare strace output between working and non-working scenarios
4. Look for ENOENT, EPERM, or other error codes in the strace output
5. For timing issues, check patterns of sleep, select, and poll system calls
