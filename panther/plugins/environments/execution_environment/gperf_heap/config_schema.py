"""Google Performance Tools heap profiler configuration schema."""

from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.environment import ExecutionEnvironmentConfig


class GperfHeapConfig(ExecutionEnvironmentConfig):
    """Google Performance Tools (gperftools) heap profiling configuration.

    Uses ``libtcmalloc.so`` from gperftools to profile heap memory allocation
    patterns: where memory is allocated, how much is in use, and where leaks
    occur. Use when investigating memory growth, allocation hotspots, or
    comparing memory usage across protocol implementations.

    Note: This is gperftools (the Google performance library), not GNU gperf
    (the perfect hash function generator).

    GPerf Heap profiles *where memory is allocated*, while GPerf CPU profiles
    *where CPU time is spent*. They use different libraries (``libtcmalloc``
    vs. ``libprofiler``) and produce different output formats. For memory
    *error* detection (use-after-free, buffer overflows), use Valgrind
    Memcheck instead.

    Related execution environments:
        - GPerf CPU: CPU time profiling (also gperftools-based).
        - Memcheck: Memory error detection (Valgrind, slower but finds bugs).
        - GDB: Crash debugging with AddressSanitizer integration.

    Inherited fields from ``ExecutionEnvironmentPluginConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: gperf_heap
            heap_profile_allocation_interval: 524288
            heap_check_type: normal
            enable_leak_check: true
            generate_pdf: true
            output_format: heap
    """

    # Plugin type identifier -- do not change.
    type: str = Field(default="gperf_heap", description="Execution environment type")

    # -- Profiler library configuration --

    tcmalloc_library: Optional[str] = Field(
        default=None,
        description=(
            "Absolute path to libtcmalloc.so. When None, the system "
            "default location is used (typically discovered via "
            "LD_PRELOAD or LD_LIBRARY_PATH). Default: None."
        ),
    )

    # -- Heap profiling options --

    heap_profile_allocation_interval: Optional[int] = Field(
        default=None,
        description=(
            "Number of bytes allocated between heap profile snapshots. "
            "Smaller values produce more snapshots (higher resolution) "
            "at the cost of increased overhead. When None, gperftools "
            "uses its built-in default of 524288 (512 KB). "
            "Default: None."
        ),
    )
    heap_profile_inuse_interval: Optional[int] = Field(
        default=None,
        description=(
            "Number of bytes of in-use memory change that triggers a "
            "new heap profile snapshot. Complements allocation_interval "
            "by tracking net memory usage rather than gross allocations. "
            "Default: None (not set, gperftools default applies)."
        ),
    )
    heap_profile_time_interval: Optional[int] = Field(
        default=None,
        description=(
            "Interval in seconds between automatic heap profile "
            "snapshots. Useful for fixed-interval monitoring regardless "
            "of allocation rate. Default: None (time-based snapshots "
            "disabled)."
        ),
    )
    heap_check_type: Optional[str] = Field(
        default=None,
        description=(
            "Type of heap checking to apply. Options: 'normal' "
            "(standard checks), 'strict' (stricter checking), "
            "'draconian' (most aggressive, may report more false "
            "positives). Default: None (heap checking disabled)."
        ),
    )

    # -- Output configuration --

    output_format: str = Field(
        default="heap",
        description=(
            "Output format for the heap profile. Options: 'heap' "
            "(binary protobuf, viewable with pprof), 'text' "
            "(human-readable), 'pdf' (graphical allocation graph). "
            "Default: 'heap'."
        ),
    )
    generate_pdf: bool = Field(
        default=True,
        description=(
            "Generate a PDF allocation-graph visualization from the "
            "profile data using pprof after profiling completes. "
            "Requires graphviz to be installed. Default: True."
        ),
    )
    generate_text_report: bool = Field(
        default=False,
        description=(
            "Generate an additional human-readable text report from "
            "the heap profile. Useful for quick inspection without "
            "pprof. Default: False."
        ),
    )

    # -- Memory leak detection --

    enable_leak_check: bool = Field(
        default=False,
        description=(
            "Enable tcmalloc-based memory leak checking. Lighter "
            "weight than Valgrind Memcheck but less detailed. "
            "Default: False."
        ),
    )
    leak_check_at_exit: bool = Field(
        default=True,
        description=(
            "Perform a leak check when the profiled program exits. "
            "Only effective when enable_leak_check is True. "
            "Default: True."
        ),
    )

    # -- Performance options --

    profile_mmap: bool = Field(
        default=False,
        description=(
            "Include mmap()-based allocations in the heap profile. "
            "Captures memory not managed by malloc/free. "
            "Default: False."
        ),
    )
    only_mmap_profile: bool = Field(
        default=False,
        description=(
            "Profile only mmap() allocations, ignoring malloc/free. "
            "Use for programs that rely primarily on mmap for memory "
            "management. Default: False."
        ),
    )
    deep_heap_profile: int = Field(
        default=0,
        description=(
            "Deep heap profiling level. Range: 0 (disabled) to 9 "
            "(maximum detail). Higher levels track more internal "
            "allocator metadata at increased overhead. Default: 0."
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
            "['--nodecount=50', '--inuse_space']. Default: [] (empty)."
        ),
    )

    # Universal validators for flexible type conversion
    @validator("heap_profile_allocation_interval", pre=True)
    def validate_allocation_interval(cls, v):
        """Convert string/float to integer for allocation interval."""
        if v is None:
            return v
        return validate_integer_field(v, "heap_profile_allocation_interval")

    @validator("heap_profile_inuse_interval", pre=True)
    def validate_inuse_interval(cls, v):
        """Convert string/float to integer for inuse interval."""
        if v is None:
            return v
        return validate_integer_field(v, "heap_profile_inuse_interval")

    @validator("heap_profile_time_interval", pre=True)
    def validate_time_interval(cls, v):
        """Convert string/float to integer for time interval."""
        if v is None:
            return v
        return validate_integer_field(v, "heap_profile_time_interval")

    @validator("deep_heap_profile", pre=True)
    def validate_deep_heap_profile(cls, v):
        """Convert string/float to integer for deep heap profile level."""
        return validate_integer_field(v, "deep_heap_profile")
