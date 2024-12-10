from dataclasses import dataclass, field
from typing import List, Optional

from plugins.environments.execution_environment.config_schema import ExecutionEnvironmentConfig


@dataclass
class StraceConfig(ExecutionEnvironmentConfig):
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

