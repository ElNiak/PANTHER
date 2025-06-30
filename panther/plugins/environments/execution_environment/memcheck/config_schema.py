from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class MemcheckConfig(ExecutionEnvironmentPluginConfig):
    """
    Configuration schema for Memcheck execution environment.
    """

    # Plugin type
    type: str = Field(default="memcheck", description="Execution environment type")

    leak_check: str = Field(
        default="summary",
        description="Search for memory leaks when the client program finishes. Options: no, summary, yes, full.",
    )
    leak_resolution: str = Field(
        default="high",
        description="How strictly Memcheck merges multiple leaks into a single report. Options: low, med, high.",
    )
    show_leak_kinds: str = Field(
        default="definite,possible",
        description="Leak kinds to show in a full leak search. Comma separated: definite,indirect,possible,reachable,all,none.",
    )
    errors_for_leak_kinds: str = Field(
        default="definite,possible",
        description="Leak kinds to count as errors in a full leak search. Same format as show_leak_kinds.",
    )
    leak_check_heuristics: str = Field(
        default="all",
        description="Set of leak check heuristics. Comma separated: stdstring,length64,newarray,multipleinheritance,all,none.",
    )
    show_reachable: Optional[str] = Field(
        default=None,
        description="Alternative way to specify leak kinds to show. yes or no.",
    )
    show_possibly_lost: Optional[str] = Field(
        default=None,
        description="Alternative way to specify leak kinds to show. yes or no.",
    )
    xtree_leak: bool = Field(
        default=False,
        description="Output leak search results in Callgrind Format execution tree file.",
    )
    xtree_leak_file: str = Field(
        default="xtleak.kcg.%p", description="Filename for xtree leak report."
    )
    undef_value_errors: bool = Field(
        default=True, description="Report uses of undefined value errors."
    )
    track_origins: bool = Field(
        default=False, description="Track the origin of uninitialized values."
    )
    partial_loads_ok: bool = Field(
        default=True,
        description="Allow partial loads from addresses with some bytes addressable and others not.",
    )
    expensive_definedness_checks: str = Field(
        default="auto",
        description="Use more precise but expensive instrumentation. Options: no, auto, yes.",
    )
    keep_stacktraces: str = Field(
        default="alloc-and-free",
        description="Which stack traces to keep for malloc'd and/or free'd blocks. Options: alloc, free, alloc-and-free, alloc-then-free, none.",
    )
    freelist_vol: int = Field(
        default=20000000,
        description="Maximum total size (bytes) of blocks in the free queue.",
    )
    freelist_big_blocks: int = Field(
        default=1000000,
        description="Size threshold for prioritizing big blocks in the free queue.",
    )
    workaround_gcc296_bugs: bool = Field(
        default=False,
        description="Assume some stack accesses are due to GCC 2.96 bugs.",
    )
    ignore_range_below_sp: Optional[str] = Field(
        default=None,
        description="Range of offsets below the stack pointer to ignore, e.g. '8192-8189'.",
    )
    show_mismatched_frees: bool = Field(
        default=True,
        description="Check that heap blocks are deallocated with the correct function.",
    )
    show_realloc_size_zero: bool = Field(
        default=True, description="Check for uses of realloc with a size of zero."
    )
    ignore_ranges: Optional[str] = Field(
        default=None,
        description="Comma separated address ranges to ignore, e.g. '0xPP-0xQQ,0xRR-0xSS'.",
    )
    malloc_fill: Optional[str] = Field(
        default=None, description="Fill malloc'd blocks with the specified byte (hex)."
    )
    free_fill: Optional[str] = Field(
        default=None, description="Fill freed blocks with the specified byte (hex)."
    )

    # Output configuration options
    output_format: str = Field(
        default="xml",
        description="Output format for reports. Options: text, xml. Default is xml for machine-readable output.",
    )
    generate_suppressions: bool = Field(
        default=False,
        description="Generate suppression entries for detected errors. Useful for creating suppression files.",
    )
    suppression_file: Optional[str] = Field(
        default=None,
        description="Path to suppression file to ignore known issues. Can be absolute or relative path.",
    )
    xml_user_comment: Optional[str] = Field(
        default=None,
        description="User comment to include in XML output. Useful for tagging test runs.",
    )

    # Additional parameters for command line
    additional_parameters: List[str] = Field(
        default_factory=list,
        description="Additional command line parameters to pass to valgrind memcheck.",
    )

    # Universal validators for flexible type conversion
    @validator("freelist_vol", pre=True)
    def validate_freelist_vol(cls, v):
        """Convert string/float to integer for freelist volume."""
        return validate_integer_field(v, "freelist_vol")

    @validator("freelist_big_blocks", pre=True)
    def validate_freelist_big_blocks(cls, v):
        """Convert string/float to integer for freelist big blocks."""
        return validate_integer_field(v, "freelist_big_blocks")
