from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
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
        default="/usr/bin/strace", description="Path to the strace binary"
    )
    excluded_syscalls: List[str] = Field(
        default_factory=lambda: [],
        description="List of syscalls to exclude from tracing",
    )
    include_kernel_stack: bool = Field(
        default=True,
        description="Include kernel stack in the trace output (if supported by strace)",
    )
    trace_all_syscalls: bool = Field(
        default=True,  # TODO link to experiment config
        description="Trace all syscalls, including those not typically monitored",
    )
    trace_network_syscalls: bool = Field(
        default=False,
        description="Focus on network-related syscalls (connect, send, recv, etc.)",
    )
    timeout: Optional[int] = Field(
        default=100,  # TODO should be set by experiment
        description="Timeout for strace execution in seconds",
    )
    output_file: str = Field(
        default="/app/logs/strace.log", description="Path to the strace log output file"
    )
    additional_parameters: List[str] = Field(
        default_factory=list, description="Additional parameters to pass to strace"
    )
    monitored_process: Optional[str] = Field(
        default=None, description="Process name to monitor (if not PID-based)"
    )
    network_focus: bool = Field(
        default=False,
        description="Indicate if strace should emphasize network protocol syscalls",
    )

    # Output format and detail options
    output_format: str = Field(
        default="verbose",
        description="Output format. Options: normal, raw, verbose. Default is normal.",
    )
    decode_fds: bool = Field(
        default=True,
        description="Decode file descriptors to show file names when possible.",
    )
    timestamps: bool = Field(
        default=True,
        description="Include timestamps in output. Useful for performance analysis.",
    )
    timestamp_format: str = Field(
        default="relative",
        description="Timestamp format. Options: none, time, relative, unix, us. Default is relative.",
    )

    # Performance and filtering options
    buffer_size: int = Field(
        default=4096,
        description="Internal buffer size for syscall capture. Larger values may improve performance.",
    )
    trace_children: bool = Field(
        default=True, description="Follow forks and trace child processes."
    )
    trace_file_syscalls: bool = Field(
        default=False, description="Include file-related syscalls in trace."
    )

    # Advanced options
    string_limit: Optional[int] = Field(
        default=32, description="Limit for string output length. None for unlimited."
    )
    stack_traces: bool = Field(
        default=False,
        description="Print stack trace after each syscall. (Note: may not work with all strace versions)",
    )
    inject_errors: Optional[str] = Field(
        default=None,
        description="Inject errors for testing. Format: 'syscall:error=errno:when=when_spec'",
    )

    # Environment-specific fields from parent
    type: str = Field(default="strace", description="Execution environment type")

    # Background monitoring configuration (from EnvironmentConfig)
    enable_background_monitoring: bool = Field(
        default=True,
        description="Enable background monitoring for non-blocking service health checks",
    )
    monitoring_interval_seconds: int = Field(
        default=5, description="Monitoring interval in seconds"
    )
    failure_threshold_count: int = Field(
        default=3, description="Number of failures before considering service unhealthy"
    )
    allow_partial_deployment: bool = Field(
        default=False, description="Allow deployment even if some services fail"
    )
    critical_services: List[str] = Field(
        default_factory=list,
        description="List of critical services that must be running",
    )

    # Universal validators for flexible type conversion
    @validator("timeout", pre=True)
    def validate_timeout(cls, v):
        """Convert string/float to integer for timeout."""
        return validate_integer_field(v, "timeout")

    @validator("monitoring_interval_seconds", pre=True)
    def validate_monitoring_interval(cls, v):
        """Convert string/float to integer for monitoring interval."""
        return validate_integer_field(v, "monitoring_interval_seconds")

    @validator("failure_threshold_count", pre=True)
    def validate_failure_threshold(cls, v):
        """Convert string/float to integer for failure threshold."""
        return validate_integer_field(v, "failure_threshold_count")

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
