from dataclasses import dataclass, field
from typing import List, Optional

from panther.plugins.environments.execution_environment.config_schema import ExecutionEnvironmentConfig


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
    excluded_syscalls: List[str] = field(
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
    include_kernel_stack: bool = True  # Include kernel stack in the trace output
    trace_network_syscalls: bool = True  # Focus on network-related syscalls (connect, send, recv, etc.)
    timeout: Optional[int] = 60  # Timeout for strace execution in seconds
    output_file: str = "/app/logs/strace.log"  # Path to the strace log output
    additional_parameters: List[str] = field(default_factory=list)  # Additional parameters for strace
    monitored_process: Optional[str] = None  # Process name to monitor (if not PID-based)
    network_focus: bool = True  # Indicate if strace should emphasize network protocol syscalls

