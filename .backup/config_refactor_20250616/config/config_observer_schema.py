"""
Observer Configuration Schema Module

This module provides dataclass-based schemas for configuring various observer types.
These schemas can be used with OmegaConf for configuration validation and management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """Enum defining supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class BaseObserverConfig:
    """
    Base configuration for all observer types.

    Attributes:
        enabled (bool): Whether this observer is enabled.
        auto_register (bool): Whether to automatically register with the event manager.
        priority (int): Priority level for event processing (lower is higher priority).
    """

    enabled: bool = True
    auto_register: bool = True
    priority: int = 0


@dataclass
class LoggerObserverConfig(BaseObserverConfig):
    """
    Configuration for LoggerObserver.

    Attributes:
        log_level (str): Logging level to use.
        include_data (bool): Whether to include event data in log output.
        include_event_id (bool): Whether to include event IDs in logs.
        include_timestamp (bool): Whether to include timestamps in logs.
        enable_colors (bool): Whether to use colored output for console logs.
        output_file (str): Path to log file for file logging.
        correlation_tracking (bool): Track related events with correlation IDs.
        structured_output (bool): Output logs in structured format (e.g., JSON).
        max_data_length (int): Maximum length for event data in logs.
    """

    log_level: str = "INFO"
    include_data: bool = True
    include_event_id: bool = True
    include_timestamp: bool = True
    enable_colors: bool = True
    output_file: Optional[str] = None
    correlation_tracking: bool = True
    structured_output: bool = False
    max_data_length: int = 500


@dataclass
class MetricsObserverConfig(BaseObserverConfig):
    """
    Configuration for MetricsObserver.

    Attributes:
        log_level (str): Logging level to use for metrics observer.
        publish_metrics (bool): Whether to publish collected metrics as events.
        collect_system_metrics (bool): Whether to collect system resource metrics.
        publish_interval (int): Frequency in seconds for collecting and publishing metrics samples.
        enable_real_time_monitoring (bool): Enable real-time monitoring of resources.
    """

    log_level: str = "INFO"
    publish_metrics: bool = True
    collect_system_metrics: bool = True
    publish_interval: int = 30
    enable_real_time_monitoring: bool = True
    resource_collection_interval: int = (
        10  # Interval for resource collection in seconds
    )
    metric_collection_interval: int = 10  # Interval for metric collection in seconds


@dataclass
class StorageObserverConfig(BaseObserverConfig):
    """
    Configuration for StorageObserver.

    Attributes:
        log_level (str): Logging level to use for storage observer.
        storage_path (str): Base path for storing data.
        enable_compression (bool): Whether to compress stored data.
        max_storage_size (int): Maximum storage size in bytes (0 for unlimited).
        auto_backup (bool): Whether to automatically backup data.
        backup_interval (int): Time between backups in seconds.
        retention_days (int): Number of days to retain old data.
        batch_size (int): Number of events to process in a batch.
        async_storage (bool): Enable asynchronous storage operations.
    """

    log_level: str = "INFO"
    storage_path: Optional[str] = None
    enable_compression: bool = True
    max_storage_size: int = 0  # 0 means unlimited
    auto_backup: bool = True
    backup_interval: int = 3600  # 1 hour
    retention_days: int = 30
    batch_size: int = 100
    async_storage: bool = False


@dataclass
class ExperimentObserverConfig(BaseObserverConfig):
    """
    Configuration for ExperimentObserver.

    Attributes:
        log_level (str): Logging level to use for experiment observer.
        output_dir (str): Directory for experiment outputs.
        test_name (str): Name of the test being observed.
        track_timing (bool): Whether to track timing metrics.
        track_steps (bool): Whether to track step completion.
    """

    log_level: str = "INFO"
    output_dir: Optional[str] = None
    test_name: Optional[str] = None
    track_timing: bool = True
    track_steps: bool = True


@dataclass
class ObserverConfig:
    """
    Complete observer configuration for the application.

    Attributes:
        logger (LoggerObserverConfig): Configuration for the logger observer.
        metrics (MetricsObserverConfig): Configuration for the metrics observer.
        storage (StorageObserverConfig): Configuration for the storage observer.
        experiment (ExperimentObserverConfig): Configuration for the experiment observer.
        resource (ResourceObserverConfig): Configuration for the resource observer.
    """

    logger: LoggerObserverConfig = field(default_factory=LoggerObserverConfig)
    metrics: MetricsObserverConfig = field(default_factory=MetricsObserverConfig)
    storage: StorageObserverConfig = field(default_factory=StorageObserverConfig)
    experiment: ExperimentObserverConfig = field(
        default_factory=ExperimentObserverConfig
    )
