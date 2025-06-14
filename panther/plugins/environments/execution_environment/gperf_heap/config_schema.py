from dataclasses import dataclass, field
from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class GperfHeapConfig(ExecutionEnvironmentConfig):
    """
    Configuration for Google Performance Tools heap profiling.

    This configuration controls heap profiling and memory analysis using
    gperftools (libtcmalloc), not the gperf perfect hash function generator.
    """

    # Profiler library configuration
    tcmalloc_library: str | None = None  # Path to libtcmalloc.so (defaults to system location)

    # Heap profiling options
    heap_profile_allocation_interval: int | None = (
        None  # Bytes between heap samples (default: 512*1024)
    )
    heap_profile_inuse_interval: int | None = None  # Bytes of in-use memory between samples
    heap_profile_time_interval: int | None = None  # Seconds between heap samples
    heap_check_type: str | None = None  # Type of heap checking: normal, strict, draconian

    # Output configuration
    output_format: str = "heap"  # Output format: heap (default), text, pdf
    generate_pdf: bool = True  # Generate PDF visualization after profiling
    generate_text_report: bool = False  # Generate text report from heap profile

    # Memory leak detection
    enable_leak_check: bool = False  # Enable memory leak checking
    leak_check_at_exit: bool = True  # Check for leaks at program exit

    # Performance options
    profile_mmap: bool = False  # Profile mmap operations
    only_mmap_profile: bool = False  # Only profile mmap (no malloc)
    deep_heap_profile: int = 0  # Deep heap profiling level (0=disabled, 1-9=enabled)

    # Filtering options
    exclude_functions: list[str] = field(
        default_factory=list
    )  # Functions to exclude from profiling
    include_only_functions: list[str] = field(default_factory=list)  # Include only these functions

    # Additional pprof options for post-processing
    pprof_options: list[str] = field(default_factory=list)  # Additional options for pprof tool
