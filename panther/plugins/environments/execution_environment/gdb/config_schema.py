from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class GdbConfig(ExecutionEnvironmentPluginConfig):
    """
    Configuration for GDB debugging execution environment.

    This configuration enables systematic debugging with automatic stack traces,
    debug symbols, and comprehensive error reporting for crash analysis.
    """

    # Plugin type
    type: str = Field(default="gdb", description="Execution environment type")

    # GDB binary configuration
    gdb_binary: str = Field(
        default="/usr/bin/gdb", description="Path to the GDB binary"
    )

    # Debugging options
    enable_core_dumps: bool = Field(
        default=True, description="Enable core dump generation for post-mortem analysis"
    )
    auto_backtrace: bool = Field(
        default=True, description="Automatically print stack trace on crashes"
    )
    backtrace_full: bool = Field(
        default=True, description="Include local variables in stack traces"
    )
    max_backtrace_depth: int = Field(
        default=50, description="Maximum depth for stack traces"
    )

    # Compilation flags for debug symbols
    debug_symbols: bool = Field(
        default=True, description="Add debug symbols (-g) to compilation"
    )
    optimization_level: str = Field(
        default="O0",
        description="Optimization level (O0, O1, O2, O3) - O0 recommended for debugging",
    )
    frame_pointer: bool = Field(
        default=True,
        description="Keep frame pointers (-fno-omit-frame-pointer) for better stack traces",
    )
    rdynamic: bool = Field(
        default=True,
        description="Add -rdynamic for dynamic symbol resolution in backtraces",
    )

    # AddressSanitizer integration
    enable_asan: bool = Field(
        default=False, description="Enable AddressSanitizer for memory error detection"
    )
    asan_options: List[str] = Field(
        default_factory=lambda: [
            "symbolize=1",
            "print_stacktrace=1",
            "check_initialization_order=1",
            "strict_init_order=1",
        ],
        description="AddressSanitizer options",
    )

    # GDB automation options
    run_command: str = Field(
        default="run", description="Initial GDB command to execute"
    )
    break_on_signals: List[str] = Field(
        default_factory=lambda: ["SIGSEGV", "SIGABRT", "SIGFPE"],
        description="Signals to break on automatically",
    )
    break_on_exceptions: bool = Field(
        default=True, description="Break on C++ exceptions"
    )

    # Output configuration
    output_format: str = Field(
        default="detailed", description="Output format: minimal, standard, detailed"
    )
    save_gdb_log: bool = Field(default=True, description="Save GDB session log to file")
    save_core_dump: bool = Field(
        default=True, description="Save core dumps for later analysis"
    )

    # Timeout configuration
    execution_timeout: int = Field(
        default=300,
        description="Maximum execution time in seconds before killing process",
    )
    gdb_timeout: int = Field(
        default=60, description="Maximum time to wait for GDB commands in seconds"
    )

    # Additional GDB commands
    init_commands: List[str] = Field(
        default_factory=list, description="Custom GDB commands to run at startup"
    )
    post_crash_commands: List[str] = Field(
        default_factory=lambda: [
            "info registers",
            "info locals",
            "info args",
            "disassemble",
            "thread apply all bt",
        ],
        description="Commands to execute after a crash",
    )

    # Environment variables for debugging
    debug_env_vars: dict = Field(
        default_factory=lambda: {
            "MALLOC_CHECK_": "2",
            "LIBC_FATAL_STDERR_": "1",
            "SEGFAULT_SIGNALS": "all",
        },
        description="Environment variables to set for enhanced debugging",
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
