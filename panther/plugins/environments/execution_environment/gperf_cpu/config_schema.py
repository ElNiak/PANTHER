from dataclasses import dataclass, field
from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class GperfCpuConfig(ExecutionEnvironmentConfig):
    """
    Configuration for Google Performance Tools CPU profiling.

    This configuration controls CPU profiling using gperftools (libprofiler),
    not the gperf perfect hash function generator.
    """

    # Profiler library configuration
    profiler_library: str | None = None  # Path to libprofiler.so (defaults to system location)

    # Profiling options
    sampling_frequency: int | None = None  # CPU profiling frequency in Hz (default: 100)
    use_realtime_signal: bool = False  # Use realtime signal for profiling

    # Output configuration
    output_format: str = "prof"  # Output format: prof (default), text, pdf
    generate_pdf: bool = True  # Generate PDF visualization after profiling

    # Performance options
    profile_children: bool = True  # Profile child processes
    start_profiling_delay: int = 0  # Delay in seconds before starting profiling

    # Filtering options
    exclude_functions: list[str] = field(
        default_factory=list
    )  # Functions to exclude from profiling
    include_only_functions: list[str] = field(default_factory=list)  # Include only these functions

    # Additional pprof options for post-processing
    pprof_options: list[str] = field(default_factory=list)  # Additional options for pprof tool
