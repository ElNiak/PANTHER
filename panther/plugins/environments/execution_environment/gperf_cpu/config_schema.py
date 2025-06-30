from typing import List, Optional

from pydantic import Field

from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class GperfCpuConfig(ExecutionEnvironmentPluginConfig):
    """
    Configuration for Google Performance Tools CPU profiling.

    This configuration controls CPU profiling using gperftools (libprofiler),
    not the gperf perfect hash function generator.
    """

    # Plugin type
    type: str = Field(
        default="gperf_cpu",
        description="Execution environment type"
    )
    
    # Profiler library configuration
    profiler_library: Optional[str] = Field(
        default=None,
        description="Path to libprofiler.so (defaults to system location)"
    )

    # Profiling options
    sampling_frequency: Optional[int] = Field(
        default=None,
        description="CPU profiling frequency in Hz (default: 100)"
    )
    use_realtime_signal: bool = Field(
        default=False,
        description="Use realtime signal for profiling"
    )

    # Output configuration
    output_format: str = Field(
        default="prof",
        description="Output format: prof (default), text, pdf"
    )
    generate_pdf: bool = Field(
        default=True,
        description="Generate PDF visualization after profiling"
    )

    # Performance options
    profile_children: bool = Field(
        default=True,
        description="Profile child processes"
    )
    start_profiling_delay: int = Field(
        default=0,
        description="Delay in seconds before starting profiling"
    )

    # Filtering options
    exclude_functions: List[str] = Field(
        default_factory=list,
        description="Functions to exclude from profiling"
    )
    include_only_functions: List[str] = Field(
        default_factory=list,
        description="Include only these functions"
    )

    # Additional pprof options for post-processing
    pprof_options: List[str] = Field(
        default_factory=list,
        description="Additional options for pprof tool"
    )
