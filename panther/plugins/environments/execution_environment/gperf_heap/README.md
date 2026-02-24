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

<!-- Source: config_schema.py -->

```yaml
execution_environment:
  - type: "gperf_heap"
    heap_profile_allocation_interval: 524288
    heap_check_type: normal
    enable_leak_check: true
    generate_pdf: true
    output_format: heap
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | str | "gperf_heap" | Execution environment type |
| `tcmalloc_library` | Optional[str] | None | Absolute path to libtcmalloc.so. When None, the system default location is used. |
| `heap_profile_allocation_interval` | Optional[int] | None | Number of bytes allocated between heap profile snapshots. When None, gperftools uses its built-in default of 524288 (512 KB). |
| `heap_profile_inuse_interval` | Optional[int] | None | Number of bytes of in-use memory change that triggers a new snapshot. |
| `heap_profile_time_interval` | Optional[int] | None | Interval in seconds between automatic heap profile snapshots. |
| `heap_check_type` | Optional[str] | None | Type of heap checking: 'normal', 'strict', or 'draconian'. |
| `output_format` | str | "heap" | Output format for the heap profile. Options: 'heap', 'text', 'pdf'. |
| `generate_pdf` | bool | True | Generate a PDF allocation-graph visualization from the profile data using pprof. |
| `generate_text_report` | bool | False | Generate an additional human-readable text report from the heap profile. |
| `enable_leak_check` | bool | False | Enable tcmalloc-based memory leak checking. |
| `leak_check_at_exit` | bool | True | Perform a leak check when the profiled program exits. Only effective when enable_leak_check is True. |
| `profile_mmap` | bool | False | Include mmap()-based allocations in the heap profile. |
| `only_mmap_profile` | bool | False | Profile only mmap() allocations, ignoring malloc/free. |
| `deep_heap_profile` | int | 0 | Deep heap profiling level. Range: 0 (disabled) to 9 (maximum detail). |
| `exclude_functions` | List[str] | [] | List of function names (or patterns) to exclude from profiling output. |
| `include_only_functions` | List[str] | [] | List of function names (or patterns) to include exclusively in profiling output. |
| `pprof_options` | List[str] | [] | Additional command-line options passed to the pprof tool during post-processing. |

Inherited from `ExecutionEnvironmentPluginConfig` / `BasePluginConfig`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Whether the plugin is enabled |
| `collect_metrics` | bool | True | Whether to collect metrics |
| `version` | Optional[str] | None | Plugin version |
| `priority` | int | 100 | Plugin execution priority |

## Usage Examples

### Basic Usage with Default Settings

```yaml
tests:
  - name: "Memory Profiling Test"
    execution_environment:
      - type: "gperf_heap"
        generate_pdf: true
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
```

### Advanced Configuration with Custom Settings

```yaml
tests:
  - name: "Advanced Memory Profiling"
    execution_environment:
      - type: "gperf_heap"
        heap_profile_allocation_interval: 262144
        heap_check_type: "normal"
        enable_leak_check: true
        generate_pdf: true
        generate_text_report: true
        deep_heap_profile: 3
        pprof_options: ["--nodecount=50", "--inuse_space"]
    services:
      server:
        name: "http_server"
        implementation:
          name: "picoquic"
          type: "iut"
      client:
        name: "http_client"
        implementation:
          name: "aioquic"
          type: "iut"
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
**Solution**: The service might be using non-standard memory allocation functions. Enable mmap profiling and increase snapshot frequency:

```yaml
execution_environment:
  - type: "gperf_heap"
    profile_mmap: true
    heap_profile_allocation_interval: 131072
```

#### PDF Generation Errors

**Problem**: PDF visualization fails to generate
**Solution**: Ensure that pprof and graphviz are properly installed in the Docker environment. The container should include graphviz for PDF generation to work.

### Debugging Tips

1. Check the service's compatible status with GPerf using `ldd` to verify dynamic linking
2. Use `HEAPCHECK=normal` environment variable to enable additional heap checking
3. For large applications, focus profiling on specific areas with custom start/stop APIs
4. Examine raw `.prof` files with `pprof --text` for detailed allocation information
