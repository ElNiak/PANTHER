"""Global configuration schema for PANTHER framework.

This module defines the global configuration structures for PANTHER.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from panther.config.config_observer_schema import ObserverConfig

# Logging Configuration
LoggingLevel = Enum(
    "LoggingLevel", ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
)


@dataclass
class FeatureLogLevelsConfig:
    """Granular logging levels for different PANTHER features."""

    # Core Components
    command_generation: LoggingLevel = LoggingLevel.INFO
    template_rendering: LoggingLevel = LoggingLevel.INFO
    docker_operations: LoggingLevel = LoggingLevel.INFO
    config_processing: LoggingLevel = LoggingLevel.INFO
    event_system: LoggingLevel = LoggingLevel.INFO
    file_operations: LoggingLevel = LoggingLevel.INFO

    # Service Management
    service_managers: LoggingLevel = LoggingLevel.INFO
    ivy_operations: LoggingLevel = LoggingLevel.INFO
    quic_services: LoggingLevel = LoggingLevel.INFO
    plugin_loading: LoggingLevel = LoggingLevel.INFO
    service_coordination: LoggingLevel = LoggingLevel.INFO

    # Environment Management
    network_environments: LoggingLevel = LoggingLevel.INFO
    execution_environments: LoggingLevel = LoggingLevel.INFO
    docker_compose: LoggingLevel = LoggingLevel.INFO
    shadow_ns: LoggingLevel = LoggingLevel.INFO
    localhost_container: LoggingLevel = LoggingLevel.INFO

    # Event System
    event_emission: LoggingLevel = LoggingLevel.INFO
    event_processing: LoggingLevel = LoggingLevel.INFO
    state_management: LoggingLevel = LoggingLevel.INFO
    observer_operations: LoggingLevel = LoggingLevel.INFO

    # Protocol Operations
    certificate_management: LoggingLevel = LoggingLevel.INFO
    network_setup: LoggingLevel = LoggingLevel.INFO
    port_management: LoggingLevel = LoggingLevel.INFO
    protocol_communication: LoggingLevel = LoggingLevel.INFO

    # Data and Metrics
    metrics_collection: LoggingLevel = LoggingLevel.INFO
    data_storage: LoggingLevel = LoggingLevel.INFO
    result_processing: LoggingLevel = LoggingLevel.INFO
    output_aggregation: LoggingLevel = LoggingLevel.INFO

    # Development and Debugging
    test_execution: LoggingLevel = LoggingLevel.INFO
    experiment_workflow: LoggingLevel = LoggingLevel.INFO
    validation_checks: LoggingLevel = LoggingLevel.INFO
    error_handling: LoggingLevel = LoggingLevel.INFO


@dataclass
class EventLogFormatConfig:
    """
    Configuration class for event log formatting.

    Attributes:
        include_priority (bool): Whether to include priority level in event logs
        custom_format (str): Optional custom format string for event logs with
                            placeholders
                            {type}, {id}, {timestamp}, {priority}
        consistent_indentation (bool): Whether to ensure consistent indentation in logs
        indent_size (int): Number of spaces to use for indentation
    """

    include_priority: bool = False  # Avoid duplicate log levels
    custom_format: str = "{timestamp} {type} {id} {priority}"  # Default format
    consistent_indentation: bool = True
    indent_size: int = 0


@dataclass
class LogStatisticsConfig:
    """
    Configuration class for log statistics collection and reporting.

    Attributes:
        enabled (bool): Whether to enable log statistics collection
        collection_interval (int): Interval in seconds for real-time statistics updates
        buffer_size (int): Maximum number of log messages to keep in memory buffer
        real_time_display (bool): Whether to display real-time statistics during execution
        generate_reports (bool): Whether to generate comprehensive reports after execution
        export_formats (List[str]): List of export formats for statistics reports
        track_performance (bool): Whether to track performance metrics of logging system
        track_features (bool): Whether to track feature-specific logging activity
        track_modules (bool): Whether to track module-specific logging activity
        handler_type (str): Type of statistics handler ('standard' or 'buffered')
        handler_buffer_size (int): Buffer size for buffered handler (if used)
        flush_interval (float): Flush interval in seconds for buffered handler
        output_file (Optional[str]): Optional file path for statistics output
    """

    enabled: bool = False
    collection_interval: int = 10  # seconds
    buffer_size: int = 1000
    real_time_display: bool = False
    generate_reports: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["json"])
    track_performance: bool = True
    track_features: bool = True
    track_modules: bool = True
    handler_type: str = "standard"  # 'standard' or 'buffered'
    handler_buffer_size: int = 100
    flush_interval: float = 1.0
    output_file: Optional[str] = None


@dataclass
class LoggingConfig:
    """
    Configuration class for logging settings.

    Attributes:
        level (LoggingLevel): The logging level, with limited valid values.
        format (str): The format string for log messages.
        enable_colors (bool): Whether to enable colored output for logs.
        event_format (EventLogFormatConfig): Configuration for event log formatting
        feature_levels (FeatureLogLevelsConfig): Granular logging levels for different features
        statistics (LogStatisticsConfig): Configuration for log statistics collection and reporting
    """

    level: LoggingLevel = LoggingLevel.DEBUG  # Limited valid values
    format: str = "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
    enable_colors: bool = True  # Enable colored output by default
    event_format: EventLogFormatConfig = field(default_factory=EventLogFormatConfig)
    feature_levels: FeatureLogLevelsConfig = field(
        default_factory=FeatureLogLevelsConfig
    )
    statistics: LogStatisticsConfig = field(default_factory=LogStatisticsConfig)


# Paths Configuration
@dataclass
class PathsConfig:
    """
    PathsConfig is a configuration class that defines various directory paths
    used in the application.

    Attributes:
        output_dir (str): Directory path where output files are stored.
            Default is "panther/outputs".
        log_dir (str): Directory path where log files are stored.
            Default is "panther/outputs/logs".
        config_dir (str): Directory path where configuration files are stored.
            Default is "panther/configs".
        plugin_dir (str): Directory path where plugin files are stored.
            Default is "panther/plugins".
        services_dir (str): Directory path where service files are stored.
            Default is "services".
        iut_dir (str): Directory path where IUT (Implementation Under Test)
            files are stored. Default is "iut".
        testers_dir (str): Directory path where tester files are stored.
            Default is "testers".
    """

    output_dir: str = "panther/outputs"
    log_dir: str = "panther/outputs"
    config_dir: str = "panther/configs"
    plugin_dir: str = "plugins"
    services_dir: str = "services"
    iut_dir: str = "iut"
    testers_dir: str = "testers"


@dataclass
class AdditionalPathsConfig:
    """
    AdditionalPathsConfig is a configuration class that holds directory paths
    for various environments.

    Attributes:
        exec_env_dir (str): Path to the execution environment directory.
        net_env_dir (str): Path to the network environment directory.
        iut_dir (str): Path to the IUT (Implementation Under Test) directory.
        testers_dir (str): Path to the testers directory.
    """

    exec_env_dir: str = ""
    net_env_dir: str = ""
    iut_dir: str = ""
    testers_dir: str = ""


# Docker Configuration
@dataclass
class DockerUserMappingConfig:
    """
    Configuration for Docker container user mapping.

    Attributes:
        run_as_host_user (bool): Map container user to host user for volume compatibility
        fallback_to_root (bool): Fallback to root if host user mapping fails
        custom_uid (Optional[int]): Custom user ID to use in containers
        custom_gid (Optional[int]): Custom group ID to use in containers
        user_name (str): Username to use for custom user creation
    """

    run_as_host_user: bool = False
    fallback_to_root: bool = True
    custom_uid: Optional[int] = None
    custom_gid: Optional[int] = None
    user_name: str = "panther"


@dataclass
class DockerConfig:
    """
    Configuration settings for Docker operations.

    # TODO: enforce the use of DockerConfig in all plugins that require Docker
    # operations.

    Attributes:
        build_docker_image (bool): Flag to determine if the Docker image should be built.
        remove_docker_image (bool): Flag to determine if the Docker image should be removed.
        remove_docker_container (bool): Flag to determine if the Docker container should be removed.
        remove_docker_network (bool): Flag to determine if the Docker network should be removed.
        remove_docker_volume (bool): Flag to determine if the Docker volume should be removed.
        user_mapping (DockerUserMappingConfig): Configuration for container user mapping
    """

    # TODO: rename: force_build_docker_image
    build_docker_image: bool = True
    log_docker_image_build: bool = True
    remove_docker_image: bool = False
    remove_docker_container: bool = False
    remove_docker_network: bool = True
    remove_docker_volume: bool = True
    remove_dangling_images: bool = False
    user_mapping: DockerUserMappingConfig = field(
        default_factory=DockerUserMappingConfig
    )


# Progress Display Configuration
@dataclass
class ProgressDisplayConfig:
    """
    Configuration for progress display and terminal output during experiments.

    Attributes:
        enable_progress_bar (bool): Whether to show tqdm progress bar during test execution
        show_test_status (bool): Whether to show test start/completion status messages
        show_docker_events (bool): Whether to show Docker build/deployment status
        use_emojis (bool): Whether to use emoji icons in status messages
        redirect_logging (bool): Whether to redirect logging through tqdm to prevent interference
    """

    enable_progress_bar: bool = True
    show_test_status: bool = True
    show_docker_events: bool = True
    use_emojis: bool = False
    redirect_logging: bool = True


# Fast Fail Configuration
@dataclass
class FastFailConfig:
    """
    Configuration for fast-fail behavior in PANTHER.

    Attributes:
        enabled (bool): Whether fast-fail is enabled globally
        test_level (bool): Whether to enable per-test fast-fail control
        docker_build_failures (bool): Whether to fail fast on Docker build errors
        docker_runtime_failures (bool): Whether to fail fast on Docker runtime errors
        plugin_load_failures (bool): Whether to fail fast on plugin loading errors
        service_start_failures (bool): Whether to fail fast on service startup errors
        network_setup_failures (bool): Whether to fail fast on network setup errors
        port_conflict_failures (bool): Whether to fail fast on port conflicts
        ivy_compilation_failures (bool): Whether to fail fast on Ivy compilation errors
        resource_exhaustion (bool): Whether to fail fast on resource exhaustion
        certificate_failures (bool): Whether to fail fast on certificate errors
        configuration_failures (bool): Whether to fail fast on configuration errors
        timeout_cascades (bool): Whether to fail fast on timeout cascades
        critical_only (bool): Whether to only fail fast on CRITICAL severity errors
        max_errors_before_fail (int): Maximum number of errors before failing (0 = unlimited)
        timeout_cascade_threshold (int): Number of consecutive timeouts before cascade failure
        disk_space_threshold_gb (float): Minimum disk space required in GB
    """

    enabled: bool = True
    test_level: bool = False
    docker_build_failures: bool = True
    docker_runtime_failures: bool = True
    plugin_load_failures: bool = True
    service_start_failures: bool = True
    network_setup_failures: bool = True
    port_conflict_failures: bool = True
    ivy_compilation_failures: bool = True
    resource_exhaustion: bool = True
    certificate_failures: bool = True
    configuration_failures: bool = True
    timeout_cascades: bool = True
    critical_only: bool = False
    max_errors_before_fail: int = 10
    timeout_cascade_threshold: int = 3
    disk_space_threshold_gb: float = 2.0


# Feature Configuration
@dataclass
class FeatureConfig:
    """
    FeatureConfig class is used to configure global features for the application.

    Attributes:
        logger_observer (bool): Indicates whether the logger observer feature is enabled. Default is True.
        storage_handler (bool): Indicates whether the storage handler feature is enabled. Default is True.
    """

    logger_observer: bool = True
    storage_handler: bool = True


@dataclass
class GlobalConfig:
    """
    GlobalConfig class holds the configuration settings for the application.

    Attributes:
        logging (LoggingConfig): Configuration for logging.
        paths (PathsConfig): Configuration for paths.
        optional_paths (AdditionalPathsConfig): Configuration for optional paths.
        docker (DockerConfig): Configuration for Docker.
        features (FeatureConfig): Configuration for features.
        progress (ProgressDisplayConfig): Configuration for progress display and terminal output.
        observers (ObserverConfig): Configuration for application observers.
        fast_fail (FastFailConfig): Configuration for fast-fail behavior.
    """

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    optional_paths: AdditionalPathsConfig = field(default_factory=AdditionalPathsConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    progress: ProgressDisplayConfig = field(default_factory=ProgressDisplayConfig)
    observers: ObserverConfig = field(default_factory=ObserverConfig)
    fast_fail: FastFailConfig = field(default_factory=FastFailConfig)
