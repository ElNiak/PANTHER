# GPerf Heap Profiler

> **Plugin Type**: Environment (execution_environment)
> **Verified Source Location**: `plugins/environments/execution_environment/gperf_heap/`

## Purpose and Overview

The GPerf Heap Environment plugin provides heap memory profiling capabilities for PANTHER services. It leverages Google's gperftools heap profiler to track memory allocations and identify memory usage patterns, leaks, and inefficiencies in protocol implementations.

<!-- src: /panther/plugins/environments/execution_environment/gperf_heap/gperf_heap.py -->

This execution environment plugin is valuable for:
- Analyzing memory usage patterns of protocol implementations
- Identifying and diagnosing memory leaks
- Optimizing memory usage in protocol stacks
- Generating visual representations of heap memory allocations

The GPerf Heap profiler works by intercepting memory allocation calls and tracking their usage throughout the application execution, providing insights into memory consumption over time.

## Requirements and Dependencies

The plugin requires:

- **Google Performance Tools (gperftools)**: Including libgperftools and libprofiler
- **pprof**: For analyzing and visualizing profiling data
- **Python Dependencies**:
  - omegaconf
  - dataclasses

Services being profiled must be compatible with GPerf heap profiling:
- Implementations must set `gperf_compatible: true` in their configuration
- Services must be dynamically linked (for gperftools to intercept memory allocations)

## Configuration Options

The GPerf Heap environment accepts the following configuration parameters:

```yaml
execution_environment:
  - name: "gperf_heap"
    type: "execution_environment"
    implementation: "gperf_heap"
    config:
      input_file: null       # Input file for gperf (optional)
      output_file: null      # Output file for gperf (optional)
      language: "C"          # Language of the output (C, C++, etc.)
      keyword_only: false    # Generate keyword-only lookup
      readonly_tables: false # Generate read-only tables
      includes: []           # List of includes to add
      other_flags: []        # Additional gperf flags
```

<!-- src: /panther/plugins/environments/execution_environment/gperf_heap/config_schema.py -->

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Name for this execution environment |
| `type` | string | Yes | - | Must be "execution_environment" |
| `implementation` | string | Yes | - | Must be "gperf_heap" |
| `config.input_file` | string | No | null | Input file for gperf |
| `config.output_file` | string | No | null | Output file for gperf |
| `config.language` | string | No | "C" | Output language (C, C++) |
| `config.keyword_only` | boolean | No | false | Generate keyword-only lookup |
| `config.readonly_tables` | boolean | No | false | Generate read-only tables |
| `config.switch` | boolean | No | false | Generate switch statements |
| `config.compare_strncmp` | boolean | No | false | Use strncmp for comparisons |
| `config.includes` | list | No | [] | List of include files |
| `config.other_flags` | list | No | [] | Additional flags for gperf |

## Usage Examples

### Basic Usage with Default Settings

```yaml
tests:
  - name: "Memory Profiling Test"
    execution_environment:
      - name: "heap_profiler"
        type: "execution_environment"
        implementation: "gperf_heap"
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
          gperf_compatible: true  # Must be set for profiling
```

### Advanced Configuration with Custom Settings

```yaml
tests:
  - name: "Advanced Memory Profiling"
    execution_environment:
      - name: "custom_heap_profiler"
        type: "execution_environment"
        implementation: "gperf_heap"
        config:
          language: "C++"
          readonly_tables: true
          other_flags: ["--debug", "--verbose"]
    services:
      server:
        name: "http_server"
        implementation:
          name: "nginx"
          type: "iut"
          gperf_compatible: true
      client:
        name: "http_client"
        implementation:
          name: "curl"
          type: "tester"
          gperf_compatible: true
```

## Extension Points

The GPerf Heap environment plugin can be extended in several ways:

### Custom Profiling Visualization

You can extend the plugin to provide custom visualization of profiling data:

```python
from panther.plugins.environments.execution_environment.gperf_heap.gperf_heap import GperfHeapEnvironment

class CustomHeapVisualizer(GperfHeapEnvironment):
    """Custom heap profiler with enhanced visualization."""

    def setup_environment(self, services_managers, test_config, global_config, timestamp, plugin_loader):
        """Set up with custom visualization options."""
        super().setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader)

        for service in self.services_managers:
            if service.service_config_to_test.implementation.gperf_compatible:
                # Add custom visualization commands
                service.run_cmd["post_run_cmds"].append(
                    f"pprof --web /app/logs/{service.service_name}_heap.prof"
                )
```

### Extended Analysis Tools

Add additional analysis capabilities:

```python
def add_leak_analysis(self):
    """Add specialized leak detection analysis."""
    for service in self.services_managers:
        if service.service_config_to_test.implementation.gperf_compatible:
            service.run_cmd["post_run_cmds"].append(
                f"pprof --text --focus=leak /app/logs/{service.service_name}_heap.prof > /app/logs/{service.service_name}_leaks.txt"
            )
```

## Testing and Verification

To test the GPerf Heap environment plugin:

1. **Unit Tests**: Located in `/tests/unit/plugins/environments/execution_environment/gperf_heap/`
2. **Integration Tests**: Run a test configuration with the plugin enabled:
   ```bash
   python -m panther -c experiment-config/experiment_config_memory_profiling.yaml
   ```

3. **Verification Metrics**:
   - Check if heap profiling files are generated in the logs directory
   - Verify PDF visualization is created
   - Analyze heap usage patterns for expected behavior

## Troubleshooting

### Common Issues

#### Missing Profiling Output

**Problem**: No `.prof` files are generated in the output
**Solution**: Ensure the service is marked as `gperf_compatible: true` and is dynamically linked.

#### Incomplete Profiling Data

**Problem**: Profiling data is incomplete or missing allocations
**Solution**: The service might be using non-standard memory allocation functions. Set environment variables to capture all allocation types:

```yaml
execution_environment:
  - name: "heap_profiler"
    type: "execution_environment"
    implementation: "gperf_heap"
    config:
      other_flags: ["--trace-all"]
```

#### PDF Generation Errors

**Problem**: PDF visualization fails to generate
**Solution**: Ensure that pprof and graphviz are properly installed in the environment:

```yaml
services:
  server:
    name: "server"
    implementation:
      pre_run_cmds:
        - "apt-get update && apt-get install -y graphviz"
```

### Debugging Tips

1. Check the service's compatible status with GPerf using `ldd` to verify dynamic linking
2. Use `HEAPCHECK=normal` environment variable to enable additional heap checking
3. For large applications, focus profiling on specific areas with custom start/stop APIs
4. Examine raw `.prof` files with `pprof --text` for detailed allocation information
