"""Memcheck memory error detector configuration schema."""

from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.field_coercion import validate_integer_field
from panther.config.core.models.environment import ExecutionEnvironmentConfig


class MemcheckConfig(ExecutionEnvironmentConfig):
    """Valgrind Memcheck configuration for memory error detection.

    Memcheck detects memory management errors in C/C++ programs: uninitialized
    reads, use-after-free, memory leaks, invalid heap operations, and mismatched
    allocation/deallocation calls. Use when debugging native services (e.g.,
    Picoquic, LSQUIC) for memory safety issues.

    Related execution environments:
        - Helgrind: Thread safety and data race detection (also Valgrind-based).
        - GPerf Heap: Heap profiling for allocation patterns and memory usage
          (lighter weight, no error detection).
        - GDB: Crash debugging with stack traces (complementary to Memcheck).

    Inherited fields from ``ExecutionEnvironmentConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: memcheck
            leak_check: full
            track_origins: true
            show_leak_kinds: definite,possible,indirect
            output_format: xml
            suppression_file: /path/to/suppressions.supp
    """

    # Plugin type identifier -- do not change.
    type: str = Field(default="memcheck", description="Execution environment type")

    # -- Leak detection options --

    leak_check: str = Field(
        default="summary",
        description=(
            "Search for memory leaks when the client program finishes. "
            "Options: 'no', 'summary', 'yes', 'full'. "
            "'summary' gives a count per leak kind; 'full' lists each "
            "individual leak in detail."
        ),
    )
    leak_resolution: str = Field(
        default="high",
        description=(
            "How strictly Memcheck merges multiple leaks into a single "
            "report based on call-stack similarity. Options: 'low' "
            "(aggressive merging), 'med', 'high' (least merging, most "
            "detail)."
        ),
    )
    show_leak_kinds: str = Field(
        default="definite,possible",
        description=(
            "Comma-separated leak kinds to display in a full leak "
            "search. Values: 'definite', 'indirect', 'possible', "
            "'reachable', 'all', 'none'. Example: "
            "'definite,indirect,possible'."
        ),
    )
    errors_for_leak_kinds: str = Field(
        default="definite,possible",
        description=(
            "Comma-separated leak kinds to count as errors (affecting "
            "the exit code). Same values as show_leak_kinds."
        ),
    )
    leak_check_heuristics: str = Field(
        default="all",
        description=(
            "Comma-separated heuristics for identifying interior "
            "pointers to heap blocks. Values: 'stdstring', 'length64', "
            "'newarray', 'multipleinheritance', 'all', 'none'."
        ),
    )
    show_reachable: Optional[str] = Field(
        default=None,
        description=(
            "Alternative way to control display of reachable blocks. "
            "Values: 'yes', 'no'. When set, overrides show_leak_kinds "
            "for the 'reachable' category. Default: None (not set)."
        ),
    )
    show_possibly_lost: Optional[str] = Field(
        default=None,
        description=(
            "Alternative way to control display of possibly-lost "
            "blocks. Values: 'yes', 'no'. When set, overrides "
            "show_leak_kinds for the 'possible' category. "
            "Default: None (not set)."
        ),
    )
    xtree_leak: bool = Field(
        default=False,
        description=(
            "Output leak search results as a Callgrind-format "
            "execution tree file, viewable in KCachegrind."
        ),
    )
    xtree_leak_file: str = Field(
        default="xtleak.kcg.%p",
        description=(
            "Filename for the xtree leak report. The '%p' placeholder "
            "is replaced with the process PID. "
            "Default: 'xtleak.kcg.%p'."
        ),
    )

    # -- Undefined value detection options --

    undef_value_errors: bool = Field(
        default=True,
        description=(
            "Report uses of undefined (uninitialized) value errors. "
            "Disable to reduce noise when only leak checking is needed."
        ),
    )
    track_origins: bool = Field(
        default=False,
        description=(
            "Track the origin of uninitialized values back to their "
            "point of creation. Increases memory overhead (~100MB) and "
            "slows execution (~1.5x), but produces more actionable "
            "error reports."
        ),
    )
    partial_loads_ok: bool = Field(
        default=True,
        description=(
            "Allow partial loads from addresses where some bytes are "
            "addressable and others are not. Set to False for stricter "
            "checking."
        ),
    )
    expensive_definedness_checks: str = Field(
        default="auto",
        description=(
            "Use more precise but expensive instrumentation for "
            "bit-level definedness tracking. Options: 'no' (fastest), "
            "'auto' (Valgrind decides), 'yes' (most precise)."
        ),
    )

    # -- Stack trace and free-list options --

    keep_stacktraces: str = Field(
        default="alloc-and-free",
        description=(
            "Which stack traces to keep for malloc'd/free'd blocks. "
            "Options: 'alloc', 'free', 'alloc-and-free' (both), "
            "'alloc-then-free' (alloc until free), 'none'. More traces "
            "use more memory but give better error context."
        ),
    )
    freelist_vol: int = Field(
        default=20000000,
        description=(
            "Maximum total size in bytes of blocks in the free queue. "
            "Larger values delay actual deallocation, increasing the "
            "chance of detecting dangling-pointer accesses. "
            "Default: 20000000 (~20 MB)."
        ),
    )
    freelist_big_blocks: int = Field(
        default=1000000,
        description=(
            "Size threshold in bytes above which freed blocks are "
            "prioritized for retention in the free queue. "
            "Default: 1000000 (~1 MB)."
        ),
    )

    # -- Compatibility and edge-case options --

    workaround_gcc296_bugs: bool = Field(
        default=False,
        description=(
            "Assume some reads/writes below the stack pointer are due "
            "to GCC 2.96 bugs rather than real errors. Only needed for "
            "very old compiled code."
        ),
    )
    ignore_range_below_sp: Optional[str] = Field(
        default=None,
        description=(
            "Range of offsets below the stack pointer to ignore, as "
            "'<size>-<delta>'. Example: '8192-8189'. "
            "Default: None (not set)."
        ),
    )
    show_mismatched_frees: bool = Field(
        default=True,
        description=(
            "Report when heap blocks are deallocated with a function "
            "that does not match the allocator (e.g., malloc/delete "
            "mismatch)."
        ),
    )
    show_realloc_size_zero: bool = Field(
        default=True,
        description=(
            "Report calls to realloc() with size zero, which is "
            "implementation-defined behavior."
        ),
    )
    ignore_ranges: Optional[str] = Field(
        default=None,
        description=(
            "Comma-separated address ranges to exclude from checking. "
            "Format: '0xPP-0xQQ,0xRR-0xSS'. "
            "Default: None (not set)."
        ),
    )
    malloc_fill: Optional[str] = Field(
        default=None,
        description=(
            "Fill newly malloc'd blocks with this byte value (hex, "
            "e.g. '0xAA'). Useful for detecting use of uninitialized "
            "heap memory. Default: None (not set)."
        ),
    )
    free_fill: Optional[str] = Field(
        default=None,
        description=(
            "Fill freed blocks with this byte value (hex, e.g. "
            "'0xBB'). Useful for detecting use-after-free. "
            "Default: None (not set)."
        ),
    )

    # -- Output configuration --

    output_format: str = Field(
        default="xml",
        description=(
            "Output format for Memcheck reports. Options: 'text' "
            "(human-readable), 'xml' (machine-parseable). "
            "Default: 'xml'."
        ),
    )
    generate_suppressions: bool = Field(
        default=False,
        description=(
            "Generate suppression entries for each detected error. "
            "Useful for building a suppression file to filter known "
            "issues in subsequent runs."
        ),
    )
    suppression_file: Optional[str] = Field(
        default=None,
        description=(
            "Path to a Valgrind suppression file (.supp) to ignore "
            "known issues. Can be absolute or relative to the working "
            "directory. Shared concept with Helgrind, but suppression "
            "entries are tool-specific. Default: None (not set)."
        ),
    )
    xml_user_comment: Optional[str] = Field(
        default=None,
        description=(
            "Arbitrary user comment embedded in XML output. Useful for "
            "tagging runs with test identifiers or build versions. "
            "Default: None (not set)."
        ),
    )

    # -- Additional CLI parameters --

    additional_parameters: List[str] = Field(
        default_factory=list,
        description=(
            "Additional command-line parameters passed verbatim to "
            "'valgrind --tool=memcheck'. Example: "
            "['--vgdb=yes', '--vgdb-error=0']."
        ),
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
