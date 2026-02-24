from typing import List, Optional

from pydantic import Field

from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class GperfCpuConfig(ExecutionEnvironmentPluginConfig):
    """Google Performance Tools (gperftools) CPU profiling configuration.

    Uses ``libprofiler.so`` from gperftools to perform statistical CPU profiling
    of C/C++ services. The profiler periodically samples the call stack to
    identify CPU-intensive code paths and hot functions. Use when investigating
    performance bottlenecks or comparing CPU usage across protocol
    implementations.

    Note: This is gperftools (the Google performance library), not GNU gperf
    (the perfect hash function generator).

    GPerf CPU profiles *where time is spent*, while GPerf Heap profiles *where
    memory is allocated*. They use different libraries (``libprofiler`` vs.
    ``libtcmalloc``) and produce different output formats.

    Related execution environments:
        - GPerf Heap: Memory allocation profiling (also gperftools-based).
        - Memcheck: Memory error detection (Valgrind, much slower).
        - Strace: Syscall-level tracing for I/O bottleneck analysis.

    Inherited fields from ``ExecutionEnvironmentPluginConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: gperf_cpu
            sampling_frequency: 200
            generate_pdf: true
            profile_children: true
            output_format: prof
    """

    # Plugin type identifier -- do not change.
    type: str = Field(
        default="gperf_cpu",
        description="Execution environment type",
    )

    # -- Profiler library configuration --

    profiler_library: Optional[str] = Field(
        default=None,
        description=(
            "Absolute path to libprofiler.so. When None, the system "
            "default location is used (typically discovered via "
            "LD_LIBRARY_PATH). Default: None."
        ),
    )

    # -- Profiling options --

    sampling_frequency: Optional[int] = Field(
        default=None,
        description=(
            "CPU profiling sampling frequency in Hz. Higher values "
            "give finer granularity but increase overhead. "
            "When None, gperftools uses its built-in default of 100 Hz. "
            "Example: 200 for higher resolution. Default: None."
        ),
    )
    use_realtime_signal: bool = Field(
        default=False,
        description=(
            "Use a POSIX realtime signal (SIGRTMIN+N) instead of "
            "SIGPROF for sampling. Avoids conflicts when the "
            "profiled program also uses SIGPROF. Default: False."
        ),
    )

    # -- Output configuration --

    output_format: str = Field(
        default="prof",
        description=(
            "Output format for the CPU profile. Options: 'prof' "
            "(binary protobuf, viewable with pprof), 'text' "
            "(human-readable), 'pdf' (graphical call graph). "
            "Default: 'prof'."
        ),
    )
    generate_pdf: bool = Field(
        default=True,
        description=(
            "Generate a PDF call-graph visualization from the profile "
            "data using pprof after profiling completes. Requires "
            "graphviz to be installed. Default: True."
        ),
    )

    # -- Performance options --

    profile_children: bool = Field(
        default=True,
        description=(
            "Also profile child processes forked by the main service. " "Default: True."
        ),
    )
    start_profiling_delay: int = Field(
        default=0,
        description=(
            "Delay in seconds before starting CPU profiling. Use to "
            "skip initialization overhead and focus on steady-state "
            "behavior. Default: 0 (start immediately)."
        ),
    )

    # -- Filtering options --

    exclude_functions: List[str] = Field(
        default_factory=list,
        description=(
            "List of function names (or patterns) to exclude from "
            "profiling output during pprof post-processing. "
            "Default: [] (empty)."
        ),
    )
    include_only_functions: List[str] = Field(
        default_factory=list,
        description=(
            "List of function names (or patterns) to include "
            "exclusively in profiling output. When non-empty, only "
            "matching functions appear. Default: [] (include all)."
        ),
    )

    # -- Post-processing options --

    pprof_options: List[str] = Field(
        default_factory=list,
        description=(
            "Additional command-line options passed to the pprof tool "
            "during post-processing. Example: "
            "['--nodecount=50', '--focus=quic_']. Default: [] (empty)."
        ),
    )
