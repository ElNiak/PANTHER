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

The GPerf CPU environment accepts the following configuration parameters:

```yaml
execution_environment:
  - type: "gperf_cpu"
    input_file: "input.txt"        # Optional input for the profiled application
    output_file: "cpu.profile"     # Output profile file name
    language: "C++"                # Programming language
    readonly_tables: true          # Generate read-only tables
    includes: ["<string>", "<vector>"] # Include files
    other_flags: ["-v", "--debug"] # Additional gperf flags
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be "gperf_cpu" |
| `input_file` | string | No | None | Input file for the profiled application |
| `output_file` | string | No | None | Name of the output profile file |
| `language` | string | No | "C" | Programming language of the application |
| `keyword_only` | boolean | No | false | Generate keyword-only lookup |
| `readonly_tables` | boolean | No | false | Generate read-only tables |
| `switch` | boolean | No | false | Generate switch statements |
| `compare_strncmp` | boolean | No | false | Use strncmp for comparisons |
| `hash_function` | string | No | None | Hash function to use |
| `compare_function` | string | No | None | Comparison function to use |
| `includes` | list | No | [] | List of includes to add |
| `other_flags` | list | No | [] | Additional gperf command flags |

<!-- src: /panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py -->

## Usage Examples

### Basic CPU Profiling

```yaml
tests:
  - name: "Basic CPU Profiling"
    execution_environment:
      - type: "gperf_cpu"
        output_file: "cpu_profile.out"
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
        output_file: "cpu_profile.out"
        language: "C++"
        readonly_tables: true
        includes: ["<string>", "<vector>"]
        other_flags: ["-v", "--debug"]
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
