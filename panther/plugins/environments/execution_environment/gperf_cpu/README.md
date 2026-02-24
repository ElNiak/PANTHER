# GPerf CPU Profiling Environment

> **Plugin Type**: Execution Environment
> **Source Location**: `plugins/environments/execution_environment/gperf_cpu/`

## Overview

The GPerf CPU Profiling Environment plugin provides CPU usage monitoring and profiling capabilities for services running within PANTHER. It uses Google's gperftools to collect detailed CPU profiling information, helping identify performance bottlenecks and optimization opportunities in implementations under test.

## Configuration Options

<!-- src: config_schema.py -->

### GPerf CPU Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | `str` | `"gperf_cpu"` | Execution environment type |
| `profiler_library` | `Optional[str]` | `None` | Absolute path to libprofiler.so. When None, the system default location is used. |
| `sampling_frequency` | `Optional[int]` | `None` | CPU profiling sampling frequency in Hz. When None, gperftools uses its built-in default of 100 Hz. |
| `use_realtime_signal` | `bool` | `False` | Use a POSIX realtime signal instead of SIGPROF for sampling. |
| `output_format` | `str` | `"prof"` | Output format for the CPU profile. Options: `prof`, `text`, `pdf`. |
| `generate_pdf` | `bool` | `True` | Generate a PDF call-graph visualization from the profile data using pprof. |
| `profile_children` | `bool` | `True` | Also profile child processes forked by the main service. |
| `start_profiling_delay` | `int` | `0` | Delay in seconds before starting CPU profiling. |
| `exclude_functions` | `List[str]` | `[]` | List of function names (or patterns) to exclude from profiling output. |
| `include_only_functions` | `List[str]` | `[]` | List of function names (or patterns) to include exclusively in profiling output. |
| `pprof_options` | `List[str]` | `[]` | Additional command-line options passed to the pprof tool during post-processing. |

### Inherited Fields (from ExecutionEnvironmentPluginConfig / BasePluginConfig)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether the plugin is enabled |
| `collect_metrics` | `bool` | `True` | Whether to collect metrics |
| `version` | `Optional[str]` | `None` | Plugin version |
| `priority` | `int` | `100` | Plugin execution priority |

## Usage Example

```yaml
execution_environments:
  - type: gperf_cpu
    sampling_frequency: 200
    generate_pdf: true
    profile_children: true
    output_format: prof
```

## Integration

- **Service Managers** -- Injects gperftools CPU profiler library into service execution via `LD_PRELOAD`.
- **Result Collection** -- Profile data files (`.prof`) and PDF visualizations are included in test outputs.
- **Post-Processing** -- Uses `pprof` to convert raw profiles into human-readable or visual formats.
- **Dependencies** -- Requires `google-perftools`, `pprof`, and optionally `graphviz` for PDF generation.

## Troubleshooting

### Missing Profile Output

Ensure gperftools is installed and properly configured. The service must be dynamically linked for `LD_PRELOAD` injection to work.

### High Overhead

Adjust sampling frequency to a lower value. The default of 100 Hz is usually acceptable, but higher values increase overhead.

### Visualization Errors

Install the `graphviz` package for proper PDF rendering. On Ubuntu/Debian:

```bash
apt-get install google-perftools libgoogle-perftools-dev graphviz
```

## References

- [gperftools CPU Profiler](https://github.com/gperftools/gperftools/wiki)
- [pprof Documentation](https://github.com/google/pprof)
