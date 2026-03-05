"""CPU profiling execution environment via Google Performance Tools.

Uses gperftools `libprofiler.so` to collect CPU profiling data
from services under test. Generates flame graphs and call-graph
PDF visualizations via `pprof`.

Key features:
    - Configurable sampling frequency
    - Child process profiling
    - Start delay for warm-up periods
    - Function include/exclude filters
    - PDF call-graph generation

See `GperfCpuConfig` for all configuration options.
"""
