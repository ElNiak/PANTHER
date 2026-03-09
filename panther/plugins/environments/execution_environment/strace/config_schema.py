"""Strace system call tracer configuration schema."""

from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.field_coercion import validate_integer_field
from panther.config.core.models.environment import ExecutionEnvironmentConfig


class StraceConfig(ExecutionEnvironmentConfig):
    """Strace configuration for system call tracing.

    Strace traces system calls and signals made by a process, recording
    each syscall's name, arguments, and return value. Use when diagnosing
    I/O issues, analyzing network behavior at the syscall level, or
    understanding how a service interacts with the kernel.

    Particularly useful for protocol testing: the ``network_focus`` and
    ``trace_network_syscalls`` options filter output to network-relevant
    syscalls (connect, send, recv, socket, etc.), making it easier to
    trace protocol handshakes and data transfer at the OS level.

    Related execution environments:
        - GDB: Interactive debugging with stack traces (complementary).
        - GPerf CPU: Statistical CPU profiling (higher level than strace).
        - Memcheck: Memory error detection (application level, not syscall).

    Inherited fields from ``ExecutionEnvironmentConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: strace
            trace_network_syscalls: true
            network_focus: true
            trace_children: true
            timestamps: true
            timestamp_format: relative
            output_file: /app/logs/strace.log
    """

    # -- Binary and process configuration --

    strace_binary: str = Field(
        default="/usr/bin/strace",
        description=(
            "Absolute path to the strace binary. Override if strace "
            "is installed in a non-standard location. "
            "Default: '/usr/bin/strace'."
        ),
    )
    excluded_syscalls: List[str] = Field(
        default_factory=lambda: [],
        description=(
            "List of syscall names to exclude from tracing. Use to "
            "reduce noise from high-frequency, uninteresting calls. "
            "Example: ['clock_gettime', 'gettimeofday']. "
            "Default: [] (trace all)."
        ),
    )
    include_kernel_stack: bool = Field(
        default=True,
        description=(
            "Include the kernel stack in trace output when supported "
            "by the strace version (requires strace >= 4.9 with "
            "-k flag). Default: True."
        ),
    )
    trace_all_syscalls: bool = Field(
        default=True,
        description=(
            "Trace all syscalls, including those not typically "
            "monitored. When False, only selected categories are "
            "traced. Default: True."
        ),
    )
    trace_network_syscalls: bool = Field(
        default=False,
        description=(
            "Filter tracing to network-related syscalls only "
            "(connect, bind, listen, accept, send, recv, socket, "
            "etc.). Reduces output volume for network-focused "
            "analysis. Default: False."
        ),
    )
    timeout: Optional[int] = Field(
        default=100,
        description=(
            "Maximum duration in seconds for strace execution. The "
            "traced process is terminated if it exceeds this limit. "
            "Set to None for unlimited. Default: 100."
        ),
    )
    output_file: str = Field(
        default="/app/logs/strace.log",
        description=(
            "Path inside the container where strace writes its log. "
            "Default: '/app/logs/strace.log'."
        ),
    )
    additional_parameters: List[str] = Field(
        default_factory=list,
        description=(
            "Additional command-line parameters passed verbatim to "
            "strace. Example: ['-e', 'trace=memory']. "
            "Default: [] (empty)."
        ),
    )
    monitored_process: Optional[str] = Field(
        default=None,
        description=(
            "Name of the process to attach to by name lookup (instead "
            "of PID-based attachment). Default: None (attach to the "
            "service's main process)."
        ),
    )
    network_focus: bool = Field(
        default=False,
        description=(
            "High-level flag indicating strace should emphasize "
            "network protocol syscalls in its output formatting. "
            "Works in conjunction with trace_network_syscalls. "
            "Default: False."
        ),
    )

    # -- Output format and detail options --

    output_format: str = Field(
        default="verbose",
        description=(
            "Output verbosity level. Options: 'normal' (standard "
            "output), 'raw' (undecoded arguments, hex values), "
            "'verbose' (decoded structures, named constants). "
            "Default: 'verbose'."
        ),
    )
    decode_fds: bool = Field(
        default=True,
        description=(
            "Decode file descriptor numbers to show associated file "
            "names, socket addresses, or pipe endpoints where "
            "possible. Default: True."
        ),
    )
    timestamps: bool = Field(
        default=True,
        description=(
            "Include timestamps in strace output. Essential for "
            "performance analysis and correlating with other logs. "
            "Default: True."
        ),
    )
    timestamp_format: str = Field(
        default="relative",
        description=(
            "Timestamp format. Options: 'none' (disabled), 'time' "
            "(wall-clock HH:MM:SS), 'relative' (seconds since "
            "previous syscall), 'unix' (epoch seconds), 'us' "
            "(microsecond precision). Default: 'relative'."
        ),
    )

    # -- Performance and filtering options --

    buffer_size: int = Field(
        default=4096,
        description=(
            "Internal buffer size in bytes for syscall capture. "
            "Larger values may improve performance for "
            "high-throughput services. Default: 4096."
        ),
    )
    trace_children: bool = Field(
        default=True,
        description=(
            "Follow fork(), vfork(), and clone() calls to trace "
            "child processes. Essential for services that spawn "
            "worker processes. Default: True."
        ),
    )
    trace_file_syscalls: bool = Field(
        default=False,
        description=(
            "Include file-related syscalls (open, read, write, stat, "
            "etc.) in trace output. Default: False."
        ),
    )

    # -- Advanced options --

    string_limit: Optional[int] = Field(
        default=32,
        description=(
            "Maximum number of characters printed for string "
            "arguments. Set to None for unlimited output (may produce "
            "very large logs). Default: 32."
        ),
    )
    stack_traces: bool = Field(
        default=False,
        description=(
            "Print a user-space stack trace after each syscall. "
            "Requires strace >= 4.9 compiled with libunwind support. "
            "Default: False."
        ),
    )
    inject_errors: Optional[str] = Field(
        default=None,
        description=(
            "Inject errors into syscalls for fault-injection testing. "
            "Format: 'syscall:error=ERRNO:when=SPEC'. Example: "
            "'connect:error=ECONNREFUSED:when=1'. "
            "Default: None (no injection)."
        ),
    )

    # -- Environment-specific fields --

    type: str = Field(default="strace", description="Execution environment type")

    # -- Override: strace uses a higher failure threshold than the base default --

    failure_threshold_count: int = Field(
        default=3,
        description=(
            "Number of consecutive health-check failures before the "
            "service is marked unhealthy. Default: 3 (overrides base default of 1)."
        ),
    )

    # Universal validators for flexible type conversion
    @validator("timeout", pre=True)
    def validate_timeout(cls, v):
        """Convert string/float to integer for timeout."""
        return validate_integer_field(v, "timeout")

    @validator("buffer_size", pre=True)
    def validate_buffer_size(cls, v):
        """Convert string/float to integer for buffer size."""
        return validate_integer_field(v, "buffer_size")

    @validator("string_limit", pre=True)
    def validate_string_limit(cls, v):
        """Convert string/float to integer for optional string limit."""
        if v is None:
            return v
        return validate_integer_field(v, "string_limit")
