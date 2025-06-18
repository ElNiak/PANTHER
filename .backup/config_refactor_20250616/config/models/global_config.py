"""Global configuration models for PANTHER."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from panther.config.models.base import ConfigModel
from panther.config.models.experiment import ExperimentConfigModel


class LoggingLevel(str, Enum):
    """Logging levels supported by PANTHER."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfigModel(ConfigModel):
    """Logging configuration model."""
    
    level: LoggingLevel = Field(
        LoggingLevel.INFO,
        description="Global logging level"
    )
    format: str = Field(
        "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
        description="Log message format string"
    )
    enable_colors: bool = Field(
        True,
        description="Enable colored log output"
    )
    correlation_tracking: bool = Field(
        False,
        description="Enable correlation ID tracking across log messages"
    )
    
    # File logging configuration
    log_to_file: bool = Field(
        True,
        description="Whether to log to files"
    )
    max_file_size: str = Field(
        "100MB",
        description="Maximum log file size before rotation"
    )
    backup_count: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of backup log files to keep"
    )


class PathsConfigModel(ConfigModel):
    """Paths configuration model."""
    
    output_dir: str = Field(
        "outputs",
        description="Base output directory for experiment results"
    )
    log_dir: str = Field(
        "outputs/logs",
        description="Directory for log files"
    )
    plugin_dir: str = Field(
        "panther/plugins",
        description="Directory containing plugin definitions"
    )
    cache_dir: str = Field(
        "cache",
        description="Directory for caching intermediate results"
    )
    
    # Additional path configurations
    template_dir: Optional[str] = Field(
        None,
        description="Directory for custom templates"
    )
    certificate_dir: Optional[str] = Field(
        None,
        description="Directory for SSL/TLS certificates"
    )
    
    @validator("output_dir", "log_dir", "plugin_dir", "cache_dir")
    def validate_path_exists_or_creatable(cls, v):
        """Validate that paths exist or can be created."""
        path = Path(v)
        if not path.exists():
            try:
                # Check if parent exists and we can create the directory
                path.parent.mkdir(parents=True, exist_ok=True)
                # Don't actually create it here, just validate we can
            except OSError as e:
                raise ValueError(f"Cannot create directory {v}: {e}")
        return v


class DockerUserMapping(ConfigModel):
    """Docker user mapping configuration."""
    
    run_as_host_user: bool = Field(
        False,
        description="Run containers with host user UID/GID"
    )
    custom_uid: Optional[int] = Field(
        None,
        ge=0,
        description="Custom UID for container processes"
    )
    custom_gid: Optional[int] = Field(
        None,
        ge=0,
        description="Custom GID for container processes"
    )
    user_name: str = Field(
        "panther",
        description="Username in containers"
    )
    fallback_to_root: bool = Field(
        True,
        description="Fallback to root if user mapping fails"
    )


class DockerConfigModel(ConfigModel):
    """Docker configuration model."""
    
    # Build configuration
    build_docker_image: bool = Field(
        False,
        description="Whether to build Docker images (set to true for first run)"
    )
    force_rebuild: bool = Field(
        False,
        description="Force rebuild even if images exist"
    )
    
    # Registry configuration
    registry: Optional[str] = Field(
        None,
        description="Docker registry URL"
    )
    namespace: str = Field(
        "panther",
        description="Docker image namespace"
    )
    
    # User mapping
    user_mapping: DockerUserMapping = Field(
        default_factory=DockerUserMapping,
        description="User mapping configuration for containers"
    )
    
    # Resource limits
    memory_limit: Optional[str] = Field(
        None,
        description="Memory limit for containers (e.g., '1G', '512M')"
    )
    cpu_limit: Optional[float] = Field(
        None,
        ge=0.1,
        le=16.0,
        description="CPU limit for containers (number of cores)"
    )
    
    # Network configuration
    network_name: str = Field(
        "panther_network",
        description="Docker network name for experiments"
    )
    cleanup_networks: bool = Field(
        True,
        description="Clean up networks after experiments"
    )


class ObserverConfigModel(ConfigModel):
    """Base observer configuration."""
    
    enabled: bool = Field(
        True,
        description="Whether this observer is enabled"
    )
    priority: int = Field(
        100,
        ge=1,
        le=200,
        description="Observer priority (lower = higher priority)"
    )


class LoggerObserverConfigModel(ObserverConfigModel):
    """Logger observer configuration."""
    
    log_level: LoggingLevel = Field(
        LoggingLevel.INFO,
        description="Log level for this observer"
    )
    enable_colors: bool = Field(
        True,
        description="Enable colored output"
    )
    correlation_tracking: bool = Field(
        False,
        description="Enable correlation tracking"
    )


class MetricsObserverConfigModel(ObserverConfigModel):
    """Metrics observer configuration."""
    
    collect_system_metrics: bool = Field(
        True,
        description="Collect system metrics (CPU, memory, disk)"
    )
    collect_docker_metrics: bool = Field(
        True,
        description="Collect Docker container metrics"
    )
    publish_interval: int = Field(
        30,
        ge=1,
        le=300,
        description="Metrics collection interval in seconds"
    )
    retention_days: int = Field(
        30,
        ge=1,
        le=365,
        description="Metrics retention in days"
    )


class StorageObserverConfigModel(ObserverConfigModel):
    """Storage observer configuration."""
    
    storage_path: str = Field(
        "outputs/storage",
        description="Path for storing observer data"
    )
    enable_compression: bool = Field(
        True,
        description="Enable compression for stored data"
    )
    retention_days: int = Field(
        30,
        ge=1,
        le=365,
        description="Storage retention in days"
    )


class ExperimentObserverConfigModel(ObserverConfigModel):
    """Experiment observer configuration."""
    
    track_timing: bool = Field(
        True,
        description="Track timing information"
    )
    track_steps: bool = Field(
        True,
        description="Track step execution"
    )
    track_service_health: bool = Field(
        True,
        description="Monitor service health"
    )


class ObserversConfigModel(ConfigModel):
    """Configuration for all observers."""
    
    logger: LoggerObserverConfigModel = Field(
        default_factory=LoggerObserverConfigModel,
        description="Logger observer configuration"
    )
    metrics: MetricsObserverConfigModel = Field(
        default_factory=MetricsObserverConfigModel,
        description="Metrics observer configuration"
    )
    storage: StorageObserverConfigModel = Field(
        default_factory=StorageObserverConfigModel,
        description="Storage observer configuration"
    )
    experiment: ExperimentObserverConfigModel = Field(
        default_factory=ExperimentObserverConfigModel,
        description="Experiment observer configuration"
    )


class FastFailConfigModel(ConfigModel):
    """Fast-fail system configuration."""
    
    # Global control
    enabled: bool = Field(
        True,
        description="Enable fast-fail globally"
    )
    test_level: bool = Field(
        False,
        description="Allow tests to override fast-fail settings"
    )
    
    # Error category controls
    docker_build_failures: bool = Field(
        True,
        description="Fail fast on Docker build failures"
    )
    service_start_failures: bool = Field(
        True,
        description="Fail fast on service startup failures"
    )
    ivy_compilation_failures: bool = Field(
        False,
        description="Fail fast on Ivy compilation failures"
    )
    network_failures: bool = Field(
        True,
        description="Fail fast on network setup failures"
    )
    
    # Threshold controls
    timeout_cascade_threshold: int = Field(
        3,
        ge=1,
        le=10,
        description="Number of consecutive timeouts before failing fast"
    )
    error_rate_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Error rate threshold (0.0-1.0) for failing fast"
    )
    
    # Timing controls
    grace_period: int = Field(
        30,
        ge=0,
        le=300,
        description="Grace period in seconds before fast-fail can trigger"
    )


class ProgressConfigModel(ConfigModel):
    """Progress reporting configuration."""
    
    enable_progress_bar: bool = Field(
        True,
        description="Enable progress bars in CLI"
    )
    redirect_logging: bool = Field(
        True,
        description="Redirect logging when progress bars are active"
    )
    update_interval: float = Field(
        0.1,
        ge=0.01,
        le=5.0,
        description="Progress update interval in seconds"
    )


class FeatureConfigModel(ConfigModel):
    """Feature flags and experimental features."""
    
    # Performance features
    parallel_execution: bool = Field(
        False,
        description="Enable parallel test execution"
    )
    aggressive_caching: bool = Field(
        False,
        description="Enable aggressive caching"
    )
    
    # Debugging features
    detailed_tracing: bool = Field(
        False,
        description="Enable detailed execution tracing"
    )
    debug_output: bool = Field(
        False,
        description="Enable debug output"
    )
    
    # Experimental features
    ai_assistance: bool = Field(
        False,
        description="Enable AI-powered assistance features"
    )


class GlobalConfigModel(ConfigModel):
    """Root global configuration model combining all settings."""
    
    # Core configuration sections
    logging: LoggingConfigModel = Field(
        default_factory=LoggingConfigModel,
        description="Logging configuration"
    )
    paths: PathsConfigModel = Field(
        default_factory=PathsConfigModel,
        description="Path configuration"
    )
    docker: DockerConfigModel = Field(
        default_factory=DockerConfigModel,
        description="Docker configuration"
    )
    observers: ObserversConfigModel = Field(
        default_factory=ObserversConfigModel,
        description="Observer configuration"
    )
    fast_fail: FastFailConfigModel = Field(
        default_factory=FastFailConfigModel,
        description="Fast-fail configuration"
    )
    progress: ProgressConfigModel = Field(
        default_factory=ProgressConfigModel,
        description="Progress reporting configuration"
    )
    features: FeatureConfigModel = Field(
        default_factory=FeatureConfigModel,
        description="Feature flags and experimental features"
    )
    
    # Additional global settings
    debug_override: bool = Field(
        False,
        description="Global debug override flag"
    )
    dry_run: bool = Field(
        False,
        description="Enable dry-run mode (no actual execution)"
    )
    
    @validator("logging", "observers")
    def validate_log_level_consistency(cls, v, values, field):
        """Ensure logging levels are consistent across global and observer configs."""
        if field.name == "observers" and "logging" in values:
            global_level = values["logging"].level
            observer_level = v.logger.log_level
            
            # If global level is more restrictive, it takes precedence
            level_values = {
                LoggingLevel.DEBUG: 10,
                LoggingLevel.INFO: 20,
                LoggingLevel.WARNING: 30,
                LoggingLevel.ERROR: 40,
                LoggingLevel.CRITICAL: 50,
            }
            
            if level_values[global_level] > level_values[observer_level]:
                # Global is more restrictive, observer will be overridden at runtime
                pass
                
        return v


class CompleteConfigModel(ConfigModel):
    """Complete configuration combining global and experiment configs."""
    
    global_config: GlobalConfigModel = Field(
        default_factory=GlobalConfigModel,
        description="Global configuration settings"
    )
    experiment_config: ExperimentConfigModel = Field(
        ...,
        description="Experiment configuration"
    )
    
    def validate_complete_config(self) -> None:
        """Perform complete configuration validation."""
        # Validate port conflicts
        self.experiment_config.validate_port_conflicts()
        
        # Additional cross-section validation can be added here
        pass