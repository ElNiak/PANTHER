# GPerf Heap Profiling Environment

> **Plugin Type**: Execution Environment
> **Source Location**: `plugins/environments/execution_environment/gperf_heap/`

## Overview

The GPerf Heap Environment plugin provides heap memory profiling capabilities for PANTHER services. It leverages Google's gperftools heap profiler to track memory allocations and identify memory usage patterns, leaks, and inefficiencies in protocol implementations.

## Configuration Options

<!-- src: config_schema.py -->

### GPerf Heap Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | `str` | `"gperf_heap"` | Execution environment type |
| `tcmalloc_library` | `Optional[str]` | `None` | Absolute path to libtcmalloc.so. When None, the system default location is used. |
| `heap_profile_allocation_interval` | `Optional[int]` | `None` | Number of bytes allocated between heap profile snapshots. When None, gperftools uses its built-in default of 524288 (512 KB). |
| `heap_profile_inuse_interval` | `Optional[int]` | `None` | Number of bytes of in-use memory change that triggers a new snapshot. |
| `heap_profile_time_interval` | `Optional[int]` | `None` | Interval in seconds between automatic heap profile snapshots. |
| `heap_check_type` | `Optional[str]` | `None` | Type of heap checking: `normal`, `strict`, or `draconian`. |
| `output_format` | `str` | `"heap"` | Output format for the heap profile. Options: `heap`, `text`, `pdf`. |
| `generate_pdf` | `bool` | `True` | Generate a PDF allocation-graph visualization from the profile data using pprof. |
| `generate_text_report` | `bool` | `False` | Generate an additional human-readable text report from the heap profile. |
| `enable_leak_check` | `bool` | `False` | Enable tcmalloc-based memory leak checking. |
| `leak_check_at_exit` | `bool` | `True` | Perform a leak check when the profiled program exits. Only effective when `enable_leak_check` is True. |
| `profile_mmap` | `bool` | `False` | Include mmap()-based allocations in the heap profile. |
| `only_mmap_profile` | `bool` | `False` | Profile only mmap() allocations, ignoring malloc/free. |
| `deep_heap_profile` | `int` | `0` | Deep heap profiling level. Range: 0 (disabled) to 9 (maximum detail). |
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
  - type: gperf_heap
    heap_profile_allocation_interval: 262144
    heap_check_type: normal
    enable_leak_check: true
    generate_pdf: true
    output_format: heap
```

## Integration

- **Service Managers** -- Injects tcmalloc library into service execution via `LD_PRELOAD` for heap profiling.
- **Result Collection** -- Heap profile files (`.prof`) and PDF visualizations are included in test outputs.
- **Post-Processing** -- Uses `pprof` to convert raw heap profiles into human-readable or visual formats.
- **Compatibility** -- Services must be dynamically linked and set `gperf_compatible: true` in their configuration.

## Troubleshooting

### Missing Profiling Output

Ensure the service is marked as `gperf_compatible: true` and is dynamically linked. Check with `ldd` to verify dynamic linking.

### Incomplete Profiling Data

The service might be using non-standard memory allocation functions. Enable mmap profiling and increase snapshot frequency:

```yaml
execution_environments:
  - type: gperf_heap
    profile_mmap: true
    heap_profile_allocation_interval: 131072
```

### PDF Generation Errors

Ensure that `pprof` and `graphviz` are properly installed in the Docker environment. The container should include graphviz for PDF generation to work.

## References

- [gperftools Heap Profiler](https://github.com/gperftools/gperftools/wiki)
- [pprof Documentation](https://github.com/google/pprof)
