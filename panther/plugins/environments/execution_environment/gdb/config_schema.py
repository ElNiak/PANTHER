from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class GdbConfig(ExecutionEnvironmentPluginConfig):
    """GDB debugging configuration for automated crash analysis.

    Wraps GDB (GNU Debugger) to provide systematic, automated debugging of
    C/C++ services: automatic stack traces on crashes, core dump collection,
    debug-symbol compilation flags, and optional AddressSanitizer integration.
    Use when investigating crashes, segfaults, or assertion failures in native
    protocol implementations (e.g., Picoquic, LSQUIC).

    GDB focuses on *crash debugging and post-mortem analysis*, whereas
    Valgrind tools (Memcheck, Helgrind) detect runtime errors during
    execution. GDB can run alongside sanitizers (ASan) for combined coverage.

    Related execution environments:
        - Memcheck: Memory error detection without recompilation (slower).
        - Helgrind: Thread safety analysis (also requires no recompilation).
        - Strace: Syscall-level tracing (no debugging symbols needed).
        - GPerf CPU: CPU profiling (performance, not correctness).

    Inherited fields from ``ExecutionEnvironmentPluginConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: gdb
            auto_backtrace: true
            backtrace_full: true
            enable_core_dumps: true
            debug_symbols: true
            optimization_level: O0
            enable_asan: false
            output_format: detailed
    """

    # Plugin type identifier -- do not change.
    type: str = Field(default="gdb", description="Execution environment type")

    # -- GDB binary configuration --

    gdb_binary: str = Field(
        default="/usr/bin/gdb",
        description=(
            "Absolute path to the GDB binary. Override if GDB is "
            "installed in a non-standard location. "
            "Default: '/usr/bin/gdb'."
        ),
    )

    # -- Debugging options --

    enable_core_dumps: bool = Field(
        default=True,
        description=(
            "Enable core dump generation so crashes can be analyzed "
            "post-mortem with 'gdb <binary> <core>'. Default: True."
        ),
    )
    auto_backtrace: bool = Field(
        default=True,
        description=(
            "Automatically print a stack trace (backtrace) when the "
            "program crashes. Default: True."
        ),
    )
    backtrace_full: bool = Field(
        default=True,
        description=(
            "Include local variable values in stack traces (uses "
            "'bt full' instead of 'bt'). More verbose but more "
            "informative. Default: True."
        ),
    )
    max_backtrace_depth: int = Field(
        default=50,
        description=(
            "Maximum number of stack frames to include in a " "backtrace. Default: 50."
        ),
    )

    # -- Compilation flags for debug symbols --

    debug_symbols: bool = Field(
        default=True,
        description=(
            "Add debug symbols (-g flag) during compilation. "
            "Required for meaningful stack traces with source "
            "file/line information. Default: True."
        ),
    )
    optimization_level: str = Field(
        default="O0",
        description=(
            "Compiler optimization level. Options: 'O0' (no "
            "optimization, best for debugging), 'O1', 'O2', 'O3' "
            "(maximum optimization), 'Os' (optimize for size), 'Og' "
            "(optimize for debugging). Default: 'O0'."
        ),
    )
    frame_pointer: bool = Field(
        default=True,
        description=(
            "Keep frame pointers by adding -fno-omit-frame-pointer "
            "during compilation. Produces more reliable stack traces. "
            "Default: True."
        ),
    )
    rdynamic: bool = Field(
        default=True,
        description=(
            "Add -rdynamic linker flag for dynamic symbol resolution "
            "in backtraces. Ensures function names appear in stack "
            "traces for dynamically loaded code. Default: True."
        ),
    )

    # -- AddressSanitizer integration --

    enable_asan: bool = Field(
        default=False,
        description=(
            "Enable AddressSanitizer (ASan) for memory error "
            "detection. Detects buffer overflows, use-after-free, and "
            "other memory errors with lower overhead than Valgrind. "
            "Requires recompilation with -fsanitize=address. "
            "Default: False."
        ),
    )
    asan_options: List[str] = Field(
        default_factory=lambda: [
            "symbolize=1",
            "print_stacktrace=1",
            "check_initialization_order=1",
            "strict_init_order=1",
        ],
        description=(
            "AddressSanitizer runtime options passed via the "
            "ASAN_OPTIONS environment variable. Each entry is a "
            "'key=value' pair. Default: symbolize, print_stacktrace, "
            "check_initialization_order, strict_init_order."
        ),
    )

    # -- GDB automation options --

    run_command: str = Field(
        default="run",
        description=(
            "Initial GDB command to execute when the session starts. "
            "Default: 'run' (start the program immediately)."
        ),
    )
    break_on_signals: List[str] = Field(
        default_factory=lambda: ["SIGSEGV", "SIGABRT", "SIGFPE"],
        description=(
            "List of signal names that GDB should automatically break "
            "on. Default: ['SIGSEGV', 'SIGABRT', 'SIGFPE']."
        ),
    )
    break_on_exceptions: bool = Field(
        default=True,
        description=(
            "Set a catchpoint to break on C++ exceptions. Useful for "
            "catching thrown exceptions before stack unwinding. "
            "Default: True."
        ),
    )

    # -- Output configuration --

    output_format: str = Field(
        default="detailed",
        description=(
            "Level of detail in GDB output reports. Options: "
            "'minimal' (crash summary only), 'standard' (backtrace "
            "and registers), 'detailed' (full backtrace, locals, "
            "registers, disassembly). Default: 'detailed'."
        ),
    )
    save_gdb_log: bool = Field(
        default=True,
        description=(
            "Save the complete GDB session log to a file for later "
            "review. Default: True."
        ),
    )
    save_core_dump: bool = Field(
        default=True,
        description=(
            "Preserve core dump files for post-mortem analysis. "
            "Core dumps can be large; disable to save disk space. "
            "Default: True."
        ),
    )

    # -- Timeout configuration --

    execution_timeout: int = Field(
        default=300,
        description=(
            "Maximum execution time in seconds for the debugged "
            "process before it is forcefully terminated. "
            "Default: 300 (5 minutes)."
        ),
    )
    gdb_timeout: int = Field(
        default=60,
        description=(
            "Maximum time in seconds to wait for individual GDB "
            "commands to complete. Default: 60."
        ),
    )

    # -- Additional GDB commands --

    init_commands: List[str] = Field(
        default_factory=list,
        description=(
            "Custom GDB commands to run at session startup, before "
            "the program is launched. Example: "
            "['set pagination off', 'set print pretty on']. "
            "Default: [] (empty)."
        ),
    )
    post_crash_commands: List[str] = Field(
        default_factory=lambda: [
            "info registers",
            "info locals",
            "info args",
            "disassemble",
            "thread apply all bt",
        ],
        description=(
            "GDB commands to execute automatically after a crash is "
            "detected. Default: info registers, info locals, info "
            "args, disassemble, thread apply all bt."
        ),
    )

    # -- Environment variables for debugging --

    debug_env_vars: dict = Field(
        default_factory=lambda: {
            "MALLOC_CHECK_": "2",
            "LIBC_FATAL_STDERR_": "1",
            "SEGFAULT_SIGNALS": "all",
        },
        description=(
            "Environment variables injected into the debugged "
            "process for enhanced error reporting. "
            "MALLOC_CHECK_=2: abort on glibc malloc corruption. "
            "LIBC_FATAL_STDERR_=1: print fatal errors to stderr. "
            "SEGFAULT_SIGNALS=all: catch all segfault variants."
        ),
    )

    # Universal validators for flexible type conversion
    @validator("max_backtrace_depth", pre=True)
    def validate_backtrace_depth(cls, v):
        """Convert string/float to integer for backtrace depth."""
        return validate_integer_field(v, "max_backtrace_depth")

    @validator("execution_timeout", pre=True)
    def validate_execution_timeout(cls, v):
        """Convert string/float to integer for execution timeout."""
        return validate_integer_field(v, "execution_timeout")

    @validator("gdb_timeout", pre=True)
    def validate_gdb_timeout(cls, v):
        """Convert string/float to integer for GDB timeout."""
        return validate_integer_field(v, "gdb_timeout")

    @validator("optimization_level")
    def validate_optimization_level(cls, v):
        """Validate optimization level."""
        valid_levels = ["O0", "O1", "O2", "O3", "Os", "Og"]
        if v not in valid_levels:
            raise ValueError(f"Optimization level must be one of {valid_levels}")
        return v

    @validator("output_format")
    def validate_output_format(cls, v):
        """Validate output format."""
        valid_formats = ["minimal", "standard", "detailed"]
        if v not in valid_formats:
            raise ValueError(f"Output format must be one of {valid_formats}")
        return v
