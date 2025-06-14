from dataclasses import dataclass, field

from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class HelgrindConfig(ExecutionEnvironmentConfig):
    """
    Configuration for Helgrind thread error detection using Valgrind.

    Helgrind is a Valgrind tool for detecting synchronization errors in multithreaded programs.
    It can detect data races, lock order violations, misuse of the POSIX threads API, and more.
    """

    # Basic configuration
    valgrind_binary: str = "/usr/bin/valgrind"  # Path to the valgrind binary
    output_format: str = field(
        default="text",
        metadata={"description": "Output format. Options: text, xml. Default is text."},
    )

    # History and detection options
    history_level: str = field(
        default="full",
        metadata={
            "description": "History level for race detection. Options: none, approx, full. Default is full."
        },
    )
    conflict_cache_size: int = field(
        default=1000000,
        metadata={
            "description": "Size of the conflict cache in bytes. Larger values may find more races but use more memory."
        },
    )

    # Lock order checking
    track_lockorders: bool = field(
        default=True,
        metadata={"description": "Track lock acquisition order to detect potential deadlocks."},
    )

    # Data race detection options
    check_stack_refs: bool = field(
        default=True,
        metadata={
            "description": "Check for races on stack variables. May produce false positives."
        },
    )
    ignore_thread_creation: bool = field(
        default=False,
        metadata={
            "description": "Ignore races during thread creation. Reduces false positives in some cases."
        },
    )

    # Synchronization checking
    free_is_write: bool = field(
        default=False,
        metadata={
            "description": "Treat heap deallocation as a write operation. Can find more races but increases false positives."
        },
    )

    # Performance options
    cache_size: int = field(
        default=32,
        metadata={"description": "Size of the cache in MB. Larger values may improve performance."},
    )

    # Filtering options
    suppression_file: str | None = field(
        default=None,
        metadata={"description": "Path to a Valgrind suppression file to filter known issues."},
    )

    # Additional Valgrind options
    show_below_main: bool = field(
        default=False,
        metadata={"description": "Show stack traces below main(). Usually not needed."},
    )
    track_fds: bool = field(
        default=False,
        metadata={"description": "Track file descriptor operations."},
    )
    time_stamp: bool = field(
        default=True,
        metadata={"description": "Add timestamps to log entries."},
    )

    # General options inherited from base
    additional_parameters: list[str] = field(
        default_factory=list,
        metadata={"description": "Additional parameters to pass to valgrind --tool=helgrind"},
    )

    # Verbosity and debugging
    verbosity: int = field(
        default=1,
        metadata={"description": "Verbosity level (0-3). Higher values provide more detail."},
    )
