from dataclasses import dataclass, field
from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class MemcheckConfig(ExecutionEnvironmentConfig):
    """
    Configuration schema for Memcheck execution environment.

    Attributes:
        leak_check (str): Search for memory leaks when the client program finishes. Options: "no", "summary", "yes", "full". Default is "summary".
        leak_resolution (str): How strictly Memcheck merges multiple leaks into a single report. Options: "low", "med", "high". Default is "high".
        show_leak_kinds (str): Leak kinds to show in a full leak search. Comma separated: "definite", "indirect", "possible", "reachable", "all", "none". Default is "definite,possible".
        errors_for_leak_kinds (str): Leak kinds to count as errors in a full leak search. Same format as show_leak_kinds. Default is "definite,possible".
        leak_check_heuristics (str): Set of leak check heuristics. Comma separated: "stdstring", "length64", "newarray", "multipleinheritance", "all", "none". Default is "all".
        show_reachable (str): Alternative way to specify leak kinds to show. "yes" or "no". Default is None.
        show_possibly_lost (str): Alternative way to specify leak kinds to show. "yes" or "no". Default is None.
        xtree_leak (bool): Output leak search results in Callgrind Format execution tree file. Default is False.
        xtree_leak_file (str): Filename for xtree leak report. Default is "xtleak.kcg.%p".
        undef_value_errors (bool): Report uses of undefined value errors. Default is True.
        track_origins (bool): Track the origin of uninitialized values. Default is False.
        partial_loads_ok (bool): Allow partial loads from addresses with some bytes addressable and others not. Default is True.
        expensive_definedness_checks (str): Use more precise but expensive instrumentation. Options: "no", "auto", "yes". Default is "auto".
        keep_stacktraces (str): Which stack traces to keep for malloc'd and/or free'd blocks. Options: "alloc", "free", "alloc-and-free", "alloc-then-free", "none". Default is "alloc-and-free".
        freelist_vol (int): Maximum total size (bytes) of blocks in the free queue. Default is 20000000.
        freelist_big_blocks (int): Size threshold for prioritizing big blocks in the free queue. Default is 1000000.
        workaround_gcc296_bugs (bool): Assume some stack accesses are due to GCC 2.96 bugs. Default is False.
        ignore_range_below_sp (str): Range of offsets below the stack pointer to ignore, e.g. "8192-8189". Default is None.
        show_mismatched_frees (bool): Check that heap blocks are deallocated with the correct function. Default is True.
        show_realloc_size_zero (bool): Check for uses of realloc with a size of zero. Default is True.
        ignore_ranges (str): Comma separated address ranges to ignore, e.g. "0xPP-0xQQ,0xRR-0xSS". Default is None.
        malloc_fill (str): Fill malloc'd blocks with the specified byte (hex). Default is None.
        free_fill (str): Fill freed blocks with the specified byte (hex). Default is None.
    """
    leak_check: str = field(
        default="summary",
        metadata={
            "description": "Search for memory leaks when the client program finishes. Options: no, summary, yes, full."
        },
    )
    leak_resolution: str = field(
        default="high",
        metadata={
            "description": "How strictly Memcheck merges multiple leaks into a single report. Options: low, med, high."
        },
    )
    show_leak_kinds: str = field(
        default="definite,possible",
        metadata={
            "description": "Leak kinds to show in a full leak search. Comma separated: definite,indirect,possible,reachable,all,none."
        },
    )
    errors_for_leak_kinds: str = field(
        default="definite,possible",
        metadata={
            "description": "Leak kinds to count as errors in a full leak search. Same format as show_leak_kinds."
        },
    )
    leak_check_heuristics: str = field(
        default="all",
        metadata={
            "description": "Set of leak check heuristics. Comma separated: stdstring,length64,newarray,multipleinheritance,all,none."
        },
    )
    show_reachable: str = field(
        default=None,
        metadata={
            "description": "Alternative way to specify leak kinds to show. yes or no."
        },
    ) # type: ignore
    show_possibly_lost: str = field(
        default=None,
        metadata={
            "description": "Alternative way to specify leak kinds to show. yes or no."
        },
    ) # type: ignore
    xtree_leak: bool = field(
        default=False,
        metadata={
            "description": "Output leak search results in Callgrind Format execution tree file."
        },
    )
    xtree_leak_file: str = field(
        default="xtleak.kcg.%p",
        metadata={
            "description": "Filename for xtree leak report."
        },
    )
    undef_value_errors: bool = field(
        default=True,
        metadata={
            "description": "Report uses of undefined value errors."
        },
    )
    track_origins: bool = field(
        default=False,
        metadata={
            "description": "Track the origin of uninitialized values."
        },
    )
    partial_loads_ok: bool = field(
        default=True,
        metadata={
            "description": "Allow partial loads from addresses with some bytes addressable and others not."
        },
    )
    expensive_definedness_checks: str = field(
        default="auto",
        metadata={
            "description": "Use more precise but expensive instrumentation. Options: no, auto, yes."
        },
    )
    keep_stacktraces: str = field(
        default="alloc-and-free",
        metadata={
            "description": "Which stack traces to keep for malloc'd and/or free'd blocks. Options: alloc, free, alloc-and-free, alloc-then-free, none."
        },
    )
    freelist_vol: int = field(
        default=20000000,
        metadata={
            "description": "Maximum total size (bytes) of blocks in the free queue."
        },
    )
    freelist_big_blocks: int = field(
        default=1000000,
        metadata={
            "description": "Size threshold for prioritizing big blocks in the free queue."
        },
    )
    workaround_gcc296_bugs: bool = field(
        default=False,
        metadata={
            "description": "Assume some stack accesses are due to GCC 2.96 bugs."
        },
    )
    ignore_range_below_sp: str = field(
        default=None,
        metadata={
            "description": "Range of offsets below the stack pointer to ignore, e.g. '8192-8189'."
        },
    ) # type: ignore
    show_mismatched_frees: bool = field(
        default=True,
        metadata={
            "description": "Check that heap blocks are deallocated with the correct function."
        },
    )
    show_realloc_size_zero: bool = field(
        default=True,
        metadata={
            "description": "Check for uses of realloc with a size of zero."
        },
    )
    ignore_ranges: str = field(
        default=None,
        metadata={
            "description": "Comma separated address ranges to ignore, e.g. '0xPP-0xQQ,0xRR-0xSS'."
        },
    ) # type: ignore
    malloc_fill: str = field(
        default=None,
        metadata={
            "description": "Fill malloc'd blocks with the specified byte (hex)."
        },
    ) # type: ignore
    free_fill: str = field(
        default=None,
        metadata={
            "description": "Fill freed blocks with the specified byte (hex)."
        },
    ) # type: ignore
