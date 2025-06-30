from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class GperfHeapConfig(ExecutionEnvironmentPluginConfig):
    """
    Configuration for Google Performance Tools heap profiling.

    This configuration controls heap profiling and memory analysis using
    gperftools (libtcmalloc), not the gperf perfect hash function generator.
    """

    # Plugin type
    type: str = Field(default="gperf_heap", description="Execution environment type")

    # Profiler library configuration
    tcmalloc_library: Optional[str] = Field(
        default=None, description="Path to libtcmalloc.so (defaults to system location)"
    )

    # Heap profiling options
    heap_profile_allocation_interval: Optional[int] = Field(
        default=None, description="Bytes between heap samples (default: 512*1024)"
    )
    heap_profile_inuse_interval: Optional[int] = Field(
        default=None, description="Bytes of in-use memory between samples"
    )
    heap_profile_time_interval: Optional[int] = Field(
        default=None, description="Seconds between heap samples"
    )
    heap_check_type: Optional[str] = Field(
        default=None, description="Type of heap checking: normal, strict, draconian"
    )

    # Output configuration
    output_format: str = Field(
        default="heap", description="Output format: heap (default), text, pdf"
    )
    generate_pdf: bool = Field(
        default=True, description="Generate PDF visualization after profiling"
    )
    generate_text_report: bool = Field(
        default=False, description="Generate text report from heap profile"
    )

    # Memory leak detection
    enable_leak_check: bool = Field(
        default=False, description="Enable memory leak checking"
    )
    leak_check_at_exit: bool = Field(
        default=True, description="Check for leaks at program exit"
    )

    # Performance options
    profile_mmap: bool = Field(default=False, description="Profile mmap operations")
    only_mmap_profile: bool = Field(
        default=False, description="Only profile mmap (no malloc)"
    )
    deep_heap_profile: int = Field(
        default=0, description="Deep heap profiling level (0=disabled, 1-9=enabled)"
    )

    # Filtering options
    exclude_functions: List[str] = Field(
        default_factory=list, description="Functions to exclude from profiling"
    )
    include_only_functions: List[str] = Field(
        default_factory=list, description="Include only these functions"
    )

    # Additional pprof options for post-processing
    pprof_options: List[str] = Field(
        default_factory=list, description="Additional options for pprof tool"
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
