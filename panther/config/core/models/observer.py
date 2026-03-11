"""Observer configuration models."""

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from ..base import BaseConfig
from ..validators import create_enum_validator


class StorageFormat(str, Enum):
    """Storage data format."""

    JSON = "json"
    SQLITE = "sqlite"
    CSV = "csv"


class ReportFormat(str, Enum):
    """Experiment report format."""

    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class BaseObserverConfig(BaseConfig):
    """Base configuration for all observers."""

    enabled: bool = Field(True, description="Whether this observer is enabled")
    priority: int = Field(
        100,
        ge=0,
        le=1000,
        description="Observer priority (lower executes first)",
        examples=[0, 50, 100, 200],
    )
    auto_register: bool = Field(
        False, description="Whether to automatically register with event manager"
    )


class LoggerObserverConfig(BaseObserverConfig):
    """Logger observer configuration."""

    log_level: str = Field("INFO", description="Log level for this observer")
    enable_colors: bool = Field(True, description="Enable colored output")
    correlation_tracking: bool = Field(
        False, description="Enable correlation ID tracking"
    )
    log_to_file: bool = Field(True, description="Log to file")
    log_to_console: bool = Field(True, description="Log to console")
    file_rotation: bool = Field(True, description="Enable log file rotation")
    max_file_size: str = Field("10MB", description="Maximum log file size")
    backup_count: int = Field(
        5, ge=0, le=100, description="Number of backup files to keep"
    )
    include_data: bool = Field(True, description="Include data in log events")
    include_event_id: bool = Field(True, description="Include event ID in log messages")
    include_timestamp: bool = Field(
        True, description="Include timestamp in log messages"
    )
    output_file: Optional[str] = Field(None, description="Output file for logger")
    structured_output: bool = Field(
        False, description="Enable structured output format"
    )
    max_data_length: int = Field(
        1000, description="Maximum length of data fields in log messages"
    )


class MetricsObserverConfig(BaseObserverConfig):
    """Metrics observer configuration."""

    log_level: str = Field("INFO", description="Log level for this observer")
    collect_system_metrics: bool = Field(True, description="Collect system metrics")
    publish_interval: int = Field(
        30,
        ge=1,
        le=3600,
        description="Metrics publish interval (seconds)",
        json_schema_extra={"unit": "seconds"},
    )
    export_format: str = Field("json", description="Export format (json, prometheus)")
    export_path: Optional[str] = Field(None, description="Path to export metrics")
    include_histograms: bool = Field(True, description="Include histogram data")
    include_percentiles: bool = Field(True, description="Include percentile data")
    percentiles: list = Field([50, 90, 95, 99], description="Percentiles to calculate")
    publish_metrics: bool = Field(True, description="Enable metrics publishing")
    enable_real_time_monitoring: bool = Field(
        True, description="Enable real-time metrics monitoring"
    )
    resource_collection_interval: int = Field(
        5,
        ge=1,
        le=3600,
        description="Resource collection interval (seconds)",
        json_schema_extra={"unit": "seconds"},
    )
    metric_collection_interval: int = Field(
        10,
        ge=1,
        le=3600,
        description="Metric collection interval (seconds)",
        json_schema_extra={"unit": "seconds"},
    )


class StorageObserverConfig(BaseObserverConfig):
    """Storage observer configuration."""

    log_level: str = Field("INFO", description="Log level for this observer")
    storage_path: str = Field("outputs/storage", description="Storage path")
    enable_compression: bool = Field(False, description="Enable data compression")
    retention_days: int = Field(
        30,
        ge=1,
        le=365,
        description="Data retention period (days)",
        json_schema_extra={"unit": "days"},
    )
    storage_format: StorageFormat = Field(
        StorageFormat.JSON,
        description="Storage format",
        examples=["json", "sqlite", "csv"],
    )
    buffer_size: int = Field(
        1000,
        ge=1,
        le=100000,
        description="Event buffer size",
    )
    flush_interval: int = Field(
        60,
        ge=1,
        le=86400,
        description="Buffer flush interval (seconds)",
        json_schema_extra={"unit": "seconds"},
    )
    create_indexes: bool = Field(True, description="Create indexes for fast queries")
    auto_backup: bool = Field(True, description="Whether to automatically backup data")
    backup_interval: int = Field(
        3600,
        ge=60,
        le=604800,
        description="Backup interval in seconds (default 1 hour)",
        json_schema_extra={"unit": "seconds"},
    )
    max_storage_size: Optional[int] = Field(
        None, description="Maximum storage size in bytes"
    )
    batch_size: int = Field(
        100,
        ge=1,
        le=10000,
        description="Number of events to batch before writing",
    )

    @field_validator("storage_format", mode="before")
    @classmethod
    def validate_storage_format(cls, v):
        """Convert string to StorageFormat enum."""
        return create_enum_validator(StorageFormat)(cls, v)


class ExperimentObserverConfig(BaseObserverConfig):
    """Experiment observer configuration."""

    log_level: str = Field("INFO", description="Log level for this observer")
    track_timing: bool = Field(True, description="Track timing information")
    track_steps: bool = Field(True, description="Track experiment steps")
    generate_report: bool = Field(True, description="Generate experiment report")
    report_format: ReportFormat = Field(
        ReportFormat.MARKDOWN,
        description="Report format",
        examples=["markdown", "html", "json"],
    )

    @field_validator("report_format", mode="before")
    @classmethod
    def validate_report_format(cls, v):
        """Convert string to ReportFormat enum."""
        return create_enum_validator(ReportFormat)(cls, v)

    include_graphs: bool = Field(True, description="Include graphs in report")
    capture_screenshots: bool = Field(
        False, description="Capture screenshots during execution"
    )
    detailed_errors: bool = Field(
        True, description="Include detailed error information"
    )
    output_dir: Optional[str] = Field(
        None, description="Output directory for experiment results"
    )
    test_name: Optional[str] = Field(
        None, description="Name of the test being observed"
    )


class ObserversConfig(BaseConfig):
    """Container for all observer configurations."""

    logger: Optional[LoggerObserverConfig] = Field(
        default_factory=LoggerObserverConfig,
        description="Logger observer configuration",
    )
    metrics: Optional[MetricsObserverConfig] = Field(
        default_factory=MetricsObserverConfig,
        description="Metrics observer configuration",
    )
    storage: Optional[StorageObserverConfig] = Field(
        default_factory=StorageObserverConfig,
        description="Storage observer configuration",
    )
    experiment: Optional[ExperimentObserverConfig] = Field(
        default_factory=ExperimentObserverConfig,
        description="Experiment observer configuration",
    )

    def get_enabled_observers(self) -> dict:
        """Get only enabled observers.

        Returns:
            Dictionary of enabled observer configurations
        """
        enabled = {}

        for name in ["logger", "metrics", "storage", "experiment"]:
            observer = getattr(self, name, None)
            if observer and observer.enabled:
                enabled[name] = observer

        return enabled

    def get_observers_by_priority(self) -> list:
        """Get observers sorted by priority.

        Returns:
            List of (name, config) tuples sorted by priority
        """
        observers = []

        for name in ["logger", "metrics", "storage", "experiment"]:
            observer = getattr(self, name, None)
            if observer and observer.enabled:
                observers.append((name, observer))

        # Sort by priority (lower number = higher priority)
        observers.sort(key=lambda x: x[1].priority)

        return observers
