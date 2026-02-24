# GPerf CPU Profiling Environment

The GPerf CPU Profiling Environment plugin provides CPU usage monitoring and profiling capabilities for services running within PANTHER. It uses Google's gperftools to collect detailed CPU profiling information, helping identify performance bottlenecks and optimization opportunities in implementations under test.

!!! info "Plugin Information"
    **Plugin Type**: Execution Environment
    **Source Location**: `plugins/environments/execution_environment/gperf_cpu/`

!!! tip "Performance Analysis"
    This plugin is particularly useful for:

    - **Identifying Bottlenecks**: Find CPU-intensive operations in protocol implementations
    - **Benchmarking**: Compare performance across different implementation strategies
    - **Regression Detection**: Monitor performance changes across versions
    - **Resource Optimization**: Optimize CPU usage in protocol stacks

## Requirements and Dependencies

The plugin requires:

- **gperftools**: Google Performance Tools library (often available as `google-perftools` package)
- **pprof**: Performance analysis tool for visualization (included with gperftools)
- **graphviz**: (Optional) For generating visual profile reports

System dependencies can be installed on Ubuntu/Debian systems with:

```bash
sudo apt-get install google-perftools libgoogle-perftools-dev graphviz
```

## Configuration Options

<!-- Source: config_schema.py -->

```yaml
execution_environment:
  - type: "gperf_cpu"
    sampling_frequency: 200
    generate_pdf: true
    profile_children: true
    output_format: prof
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | str | "gperf_cpu" | Execution environment type |
| `profiler_library` | Optional[str] | None | Absolute path to libprofiler.so. When None, the system default location is used. |
| `sampling_frequency` | Optional[int] | None | CPU profiling sampling frequency in Hz. When None, gperftools uses its built-in default of 100 Hz. |
| `use_realtime_signal` | bool | False | Use a POSIX realtime signal instead of SIGPROF for sampling. |
| `output_format` | str | "prof" | Output format for the CPU profile. Options: 'prof', 'text', 'pdf'. |
| `generate_pdf` | bool | True | Generate a PDF call-graph visualization from the profile data using pprof. |
| `profile_children` | bool | True | Also profile child processes forked by the main service. |
| `start_profiling_delay` | int | 0 | Delay in seconds before starting CPU profiling. |
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

### Basic CPU Profiling

```yaml
tests:
  - name: "Basic CPU Profiling"
    execution_environment:
      - type: "gperf_cpu"
        generate_pdf: true
    services:
      server:
        name: "http_server"
        implementation:
          name: "nginx"
          type: "iut"
```

### Advanced Profiling with Custom Settings

```yaml
tests:
  - name: "Advanced CPU Profiling"
    execution_environment:
      - type: "gperf_cpu"
        sampling_frequency: 200
        generate_pdf: true
        profile_children: true
        start_profiling_delay: 5
        exclude_functions: ["__libc_start_main"]
        pprof_options: ["--nodecount=50", "--focus=quic_"]
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
```

## Extension Points

The GPerf CPU environment plugin can be extended in several ways:

### Custom Profiling Metrics

You can extend the plugin to collect additional metrics:

```python
from panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu import GperfCpuEnvironment

class EnhancedCpuProfiler(GperfCpuEnvironment):
    """Enhanced CPU profiler with additional metrics."""

    def start_monitoring(self):
        """Start CPU profiling with additional metrics."""
        super().start_monitoring()
        # Add custom metric collection

    def get_metrics(self):
        """Return enhanced metrics."""
        base_metrics = super().get_metrics()
        # Add custom metrics
        return enhanced_metrics
```

### Integration with Visualization Tools

The plugin can be extended to automatically generate visualizations:

```python
def generate_visualization(self, profile_file):
    """Generate visualization from profile data."""
    # Implementation using pprof and graphviz
    pass
```

## Testing and Verification

To test the GPerf CPU environment plugin:

1. **Unit Tests**: Located in `/panther/plugins/environments/execution_environment/gperf_cpu/tests/`
2. **Integration Tests**: Run the following test to verify CPU profiling:

```bash
python -m pytest tests/integration/test_gperf_cpu_environment.py
```

3. **Manual Verification**:
   - Run an experiment with the GPerf CPU environment
   - Verify profile output is generated correctly
   - Analyze the profile with pprof

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Missing profile output | Ensure gperftools is installed and properly configured |
| Permission issues | Check file permissions for output directory |
| High overhead | Adjust sampling rate or profile only specific operations |
| Visualization errors | Install graphviz package for proper rendering |

### Debugging

For more detailed debugging information:

```yaml
logging:
  level: DEBUG
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
```

Use `pprof --text` to view a text summary of profile data for quick analysis.
