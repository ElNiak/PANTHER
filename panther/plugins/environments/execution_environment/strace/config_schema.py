from dataclasses import dataclass, field

from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class StraceConfig(ExecutionEnvironmentConfig):
    """
    StraceConfig is a configuration class for setting up and running strace in a specific execution environment.

    Attributes:
        strace_binary (str): Path to the strace binary. Default is "/usr/bin/strace".
        excluded_syscalls (List[str]): List of syscalls to exclude from tracing. Default includes various time-related syscalls.
        include_kernel_stack (bool): Whether to include the kernel stack in the trace output. Default is True.
        trace_network_syscalls (bool): Whether to focus on network-related syscalls (e.g., connect, send, recv). Default is True.
        timeout (Optional[int]): Timeout for strace execution in seconds. Default is 60 seconds.
        output_file (str): Path to the strace log output file. Default is "/app/logs/strace.log".
        additional_parameters (List[str]): Additional parameters to pass to strace. Default is an empty list.
        monitored_process (Optional[str]): Name of the process to monitor, if not using PID-based monitoring. Default is None.
        network_focus (bool): Indicates if strace should emphasize network protocol syscalls. Default is True.
    """

    strace_binary: str = "/usr/bin/strace"  # Path to the strace binary
    excluded_syscalls: list[str] = field(
        default_factory=lambda: [
            "nanosleep",
            "getitimer",
            "alarm",
            "setitimer",
            "gettimeofday",
            "times",
            "rt_sigtimedwait",
            "utime",
            "adjtimex",
            "settimeofday",
            "time",
        ]
    )  # List of syscalls to exclude
    include_kernel_stack: bool = False  # Include kernel stack in the trace output
    trace_network_syscalls: bool = (
        True  # Focus on network-related syscalls (connect, send, recv, etc.)
    )
    timeout: int | None = 60  # Timeout for strace execution in seconds
    output_file: str = "/app/logs/strace.log"  # Path to the strace log output
    additional_parameters: list[str] = field(
        default_factory=list
    )  # Additional parameters for strace
    monitored_process: str | None = None  # Process name to monitor (if not PID-based)
    network_focus: bool = True  # Indicate if strace should emphasize network protocol syscalls

    # Output format and detail options
    output_format: str = field(
        default="normal",
        metadata={
            "description": "Output format. Options: normal, raw, verbose. Default is normal."
        },
    )
    decode_fds: bool = field(
        default=True,
        metadata={"description": "Decode file descriptors to show file names when possible."},
    )
    timestamps: bool = field(
        default=True,
        metadata={"description": "Include timestamps in output. Useful for performance analysis."},
    )
    timestamp_format: str = field(
        default="relative",
        metadata={
            "description": "Timestamp format. Options: none, time, relative, unix, us. Default is relative."
        },
    )

    # Performance and filtering options
    buffer_size: int = field(
        default=4096,
        metadata={
            "description": "Internal buffer size for syscall capture. Larger values may improve performance."
        },
    )
    trace_children: bool = field(
        default=True,
        metadata={"description": "Follow forks and trace child processes."},
    )
    trace_file_syscalls: bool = field(
        default=True,
        metadata={"description": "Include file-related syscalls in trace."},
    )

    # Advanced options
    string_limit: int | None = field(
        default=32,
        metadata={"description": "Limit for string output length. None for unlimited."},
    )
    stack_traces: bool = field(
        default=False,
        metadata={"description": "Print stack trace after each syscall."},
    )
    inject_errors: str | None = field(
        default=None,
        metadata={
            "description": "Inject errors for testing. Format: 'syscall:error=errno:when=when_spec'"
        },
    )
