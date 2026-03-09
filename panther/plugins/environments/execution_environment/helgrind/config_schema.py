"""Helgrind thread error detector configuration schema."""

from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.models.environment import ExecutionEnvironmentConfig


class HelgrindConfig(ExecutionEnvironmentConfig):
    """Valgrind Helgrind configuration for thread error detection.

    Helgrind detects synchronization errors in multithreaded C/C++ programs:
    data races, lock-order violations (potential deadlocks), and misuse of the
    POSIX threads API. Use when debugging concurrency issues in multithreaded
    services (e.g., Picoquic server with multiple connections).

    Both Helgrind and Memcheck are Valgrind tools but serve different purposes:
    Memcheck finds memory errors; Helgrind finds threading errors. They share
    the suppression-file concept, but suppression entries are tool-specific and
    cannot be used interchangeably.

    Related execution environments:
        - Memcheck: Memory error detection (also Valgrind-based, different
          focus).
        - GDB: Crash debugging with stack traces (complementary).
        - Strace: Syscall tracing for I/O and synchronization analysis.

    Inherited fields from ``ExecutionEnvironmentConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: helgrind
            history_level: full
            track_lockorders: true
            check_stack_refs: true
            suppression_file: /path/to/helgrind.supp
            output_format: xml
    """

    # -- Basic configuration --

    valgrind_binary: str = Field(
        default="/usr/bin/valgrind",
        description=(
            "Absolute path to the Valgrind binary. Override if "
            "Valgrind is installed in a non-standard location. "
            "Default: '/usr/bin/valgrind'."
        ),
    )
    output_format: str = Field(
        default="text",
        description=(
            "Output format for Helgrind reports. Options: 'text' "
            "(human-readable), 'xml' (machine-parseable). "
            "Default: 'text'."
        ),
    )

    # -- History and detection options --

    history_level: str = Field(
        default="full",
        description=(
            "Level of detail for race-detection history. Options: "
            "'none' (fastest, no history), 'approx' (approximate, "
            "moderate overhead), 'full' (complete history, slowest "
            "but most accurate). Default: 'full'."
        ),
    )
    conflict_cache_size: int = Field(
        default=1000000,
        description=(
            "Number of entries in the conflict cache. Larger values "
            "may detect more races at the cost of higher memory usage. "
            "Default: 1000000."
        ),
    )

    # -- Lock order checking --

    track_lockorders: bool = Field(
        default=True,
        description=(
            "Track lock acquisition order to detect potential "
            "deadlocks caused by inconsistent locking. "
            "Default: True."
        ),
    )

    # -- Data race detection options --

    check_stack_refs: bool = Field(
        default=True,
        description=(
            "Check for data races on stack-allocated variables. May "
            "produce false positives for thread-local storage patterns. "
            "Default: True."
        ),
    )
    ignore_thread_creation: bool = Field(
        default=False,
        description=(
            "Ignore potential races during thread creation and "
            "initialization. Reduces false positives in programs with "
            "safe initialization patterns. Default: False."
        ),
    )

    # -- Synchronization checking --

    free_is_write: bool = Field(
        default=False,
        description=(
            "Treat heap deallocation (free) as a write operation for "
            "race-detection purposes. Finds more races but increases "
            "false positives. Default: False."
        ),
    )

    # -- Performance options --

    cache_size: int = Field(
        default=32,
        description=(
            "Size of the internal cache in MB. Larger values may "
            "improve performance for programs with many memory "
            "accesses. Default: 32."
        ),
    )

    # -- Filtering options --

    suppression_file: Optional[str] = Field(
        default=None,
        description=(
            "Path to a Valgrind suppression file (.supp) to filter "
            "known threading issues. Suppression entries are "
            "Helgrind-specific and not interchangeable with Memcheck "
            "suppressions. Default: None (not set)."
        ),
    )

    # -- Additional Valgrind options --

    show_below_main: bool = Field(
        default=False,
        description=(
            "Show stack frames below main() in stack traces. Usually "
            "not needed unless debugging runtime startup code. "
            "Default: False."
        ),
    )
    track_fds: bool = Field(
        default=False,
        description=(
            "Track file descriptor operations and report leaks at "
            "exit. Useful for detecting resource leaks alongside "
            "threading errors. Default: False."
        ),
    )
    time_stamp: bool = Field(
        default=True,
        description=(
            "Add wall-clock timestamps to Valgrind log entries. "
            "Helpful for correlating errors with external events. "
            "Default: True."
        ),
    )

    # -- Additional CLI parameters --

    additional_parameters: List[str] = Field(
        default_factory=list,
        description=(
            "Additional command-line parameters passed verbatim to "
            "'valgrind --tool=helgrind'. Example: "
            "['--fair-sched=yes', '--read-var-info=yes']."
        ),
    )

    # -- Verbosity --

    verbosity: int = Field(
        default=1,
        description=(
            "Valgrind verbosity level. Range: 0 (minimal) to 3 "
            "(maximum detail including internal debugging). "
            "Default: 1."
        ),
    )

    # -- Environment-specific fields --

    type: str = Field(default="helgrind", description="Execution environment type")

    # -- Override: helgrind uses a higher failure threshold than the base default --

    failure_threshold_count: int = Field(
        default=3,
        description=(
            "Number of consecutive health-check failures before the "
            "service is marked unhealthy. Default: 3 (overrides base default of 1)."
        ),
    )

    @validator("output_format")
    def validate_output_format(cls, v):
        """Validate output format."""
        valid_formats = ["text", "xml"]
        if v not in valid_formats:
            raise ValueError(f"Output format must be one of {valid_formats}")
        return v

    @validator("history_level")
    def validate_history_level(cls, v):
        """Validate history level."""
        valid_levels = ["none", "approx", "full"]
        if v not in valid_levels:
            raise ValueError(f"History level must be one of {valid_levels}")
        return v

    @validator("verbosity")
    def validate_verbosity(cls, v):
        """Validate verbosity level."""
        if not 0 <= v <= 3:
            raise ValueError("Verbosity must be between 0 and 3")
        return v
