from typing import List, Optional

from pydantic import Field

from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class StraceConfig(ExecutionEnvironmentPluginConfig):
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

    strace_binary: str = Field(
        default="/usr/bin/strace",
        description="Path to the strace binary"
    )
    excluded_syscalls: List[str] = Field(
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
        ],
        description="List of syscalls to exclude from tracing"
    )
    include_kernel_stack: bool = Field(
        default=False,
        description="Include kernel stack in the trace output"
    )
    trace_network_syscalls: bool = Field(
        default=True,
        description="Focus on network-related syscalls (connect, send, recv, etc.)"
    )
    timeout: Optional[int] = Field(
        default=60,
        description="Timeout for strace execution in seconds"
    )
    output_file: str = Field(
        default="/app/logs/strace.log",
        description="Path to the strace log output file"
    )
    additional_parameters: List[str] = Field(
        default_factory=list,
        description="Additional parameters to pass to strace"
    )
    monitored_process: Optional[str] = Field(
        default=None,
        description="Process name to monitor (if not PID-based)"
    )
    network_focus: bool = Field(
        default=True,
        description="Indicate if strace should emphasize network protocol syscalls"
    )

    # Output format and detail options
    output_format: str = Field(
        default="normal",
        description="Output format. Options: normal, raw, verbose. Default is normal."
    )
    decode_fds: bool = Field(
        default=True,
        description="Decode file descriptors to show file names when possible."
    )
    timestamps: bool = Field(
        default=True,
        description="Include timestamps in output. Useful for performance analysis."
    )
    timestamp_format: str = Field(
        default="relative",
        description="Timestamp format. Options: none, time, relative, unix, us. Default is relative."
    )

    # Performance and filtering options
    buffer_size: int = Field(
        default=4096,
        description="Internal buffer size for syscall capture. Larger values may improve performance."
    )
    trace_children: bool = Field(
        default=True,
        description="Follow forks and trace child processes."
    )
    trace_file_syscalls: bool = Field(
        default=True,
        description="Include file-related syscalls in trace."
    )

    # Advanced options
    string_limit: Optional[int] = Field(
        default=32,
        description="Limit for string output length. None for unlimited."
    )
    stack_traces: bool = Field(
        default=False,
        description="Print stack trace after each syscall."
    )
    inject_errors: Optional[str] = Field(
        default=None,
        description="Inject errors for testing. Format: 'syscall:error=errno:when=when_spec'"
    )

    # Environment-specific fields from parent
    type: str = Field(default="strace", description="Execution environment type")

    # Background monitoring configuration (from EnvironmentConfig)
    enable_background_monitoring: bool = Field(
        default=True,
        description="Enable background monitoring for non-blocking service health checks"
    )
    monitoring_interval_seconds: int = Field(
        default=5,
        description="Monitoring interval in seconds"
    )
    failure_threshold_count: int = Field(
        default=3,
        description="Number of failures before considering service unhealthy"
    )
    allow_partial_deployment: bool = Field(
        default=False,
        description="Allow deployment even if some services fail"
    )
    critical_services: List[str] = Field(
        default_factory=list,
        description="List of critical services that must be running"
    )
