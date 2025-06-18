from typing import List, Optional

from pydantic import Field, validator

from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class HelgrindConfig(ExecutionEnvironmentPluginConfig):
    """
    Configuration for Helgrind thread error detection using Valgrind.

    Helgrind is a Valgrind tool for detecting synchronization errors in multithreaded programs.
    It can detect data races, lock order violations, misuse of the POSIX threads API, and more.
    """

    # Basic configuration
    valgrind_binary: str = Field(
        default="/usr/bin/valgrind",
        description="Path to the valgrind binary"
    )
    output_format: str = Field(
        default="text",
        description="Output format. Options: text, xml. Default is text."
    )

    # History and detection options
    history_level: str = Field(
        default="full",
        description="History level for race detection. Options: none, approx, full. Default is full."
    )
    conflict_cache_size: int = Field(
        default=1000000,
        description="Size of the conflict cache in bytes. Larger values may find more races but use more memory."
    )

    # Lock order checking
    track_lockorders: bool = Field(
        default=True,
        description="Track lock acquisition order to detect potential deadlocks."
    )

    # Data race detection options
    check_stack_refs: bool = Field(
        default=True,
        description="Check for races on stack variables. May produce false positives."
    )
    ignore_thread_creation: bool = Field(
        default=False,
        description="Ignore races during thread creation. Reduces false positives in some cases."
    )

    # Synchronization checking
    free_is_write: bool = Field(
        default=False,
        description="Treat heap deallocation as a write operation. Can find more races but increases false positives."
    )

    # Performance options
    cache_size: int = Field(
        default=32,
        description="Size of the cache in MB. Larger values may improve performance."
    )

    # Filtering options
    suppression_file: Optional[str] = Field(
        default=None,
        description="Path to a Valgrind suppression file to filter known issues."
    )

    # Additional Valgrind options
    show_below_main: bool = Field(
        default=False,
        description="Show stack traces below main(). Usually not needed."
    )
    track_fds: bool = Field(
        default=False,
        description="Track file descriptor operations."
    )
    time_stamp: bool = Field(
        default=True,
        description="Add timestamps to log entries."
    )

    # General options inherited from base
    additional_parameters: List[str] = Field(
        default_factory=list,
        description="Additional parameters to pass to valgrind --tool=helgrind"
    )

    # Verbosity and debugging
    verbosity: int = Field(
        default=1,
        description="Verbosity level (0-3). Higher values provide more detail."
    )
    
    # Environment-specific fields
    type: str = Field(default="helgrind", description="Execution environment type")
    
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
    
    @validator('output_format')
    def validate_output_format(cls, v):
        """Validate output format."""
        valid_formats = ['text', 'xml']
        if v not in valid_formats:
            raise ValueError(f"Output format must be one of {valid_formats}")
        return v
    
    @validator('history_level')
    def validate_history_level(cls, v):
        """Validate history level."""
        valid_levels = ['none', 'approx', 'full']
        if v not in valid_levels:
            raise ValueError(f"History level must be one of {valid_levels}")
        return v
    
    @validator('verbosity')
    def validate_verbosity(cls, v):
        """Validate verbosity level."""
        if not 0 <= v <= 3:
            raise ValueError("Verbosity must be between 0 and 3")
        return v
