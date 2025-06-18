"""Global configuration models."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from .base_model import BaseUnifiedModel
from .observer import ObserversConfig


class LoggingLevel(str, Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FeatureLogLevelsConfig(BaseUnifiedModel):
    """Feature-specific log level configuration.""" 
    docker_build: Optional[str] = Field(None, description="Docker build operations")
    service_start: Optional[str] = Field(None, description="Service startup operations")
    environment_setup: Optional[str] = Field(None, description="Environment setup")
    test_execution: Optional[str] = Field(None, description="Test execution")
    metrics_collection: Optional[str] = Field(None, description="Metrics collection")
    event_processing: Optional[str] = Field(None, description="Event processing")
    plugin_loading: Optional[str] = Field(None, description="Plugin loading")
    configuration: Optional[str] = Field(None, description="Configuration operations")
    validation: Optional[str] = Field(None, description="Validation operations")
    command_generation: Optional[str] = Field(None, description="Command generation")
    output_collection: Optional[str] = Field(None, description="Output collection")
    error_handling: Optional[str] = Field(None, description="Error handling")
    fast_fail: Optional[str] = Field(None, description="Fast-fail system")
    observer: Optional[str] = Field(None, description="Observer system")
    state_management: Optional[str] = Field(None, description="State management")
    
    @field_validator('*', mode='before')
    def validate_log_level(cls, v):
        """Validate log level values."""
        if v is not None and isinstance(v, str):
            try:
                LoggingLevel(v.upper())
            except ValueError:
                raise ValueError(f"Invalid log level: {v}")
        return v
    
    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = super().to_dict(**kwargs)
        # Filter out None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}


class LoggingConfig(BaseUnifiedModel):
    """Logging configuration."""
    
    level: LoggingLevel = Field(LoggingLevel.INFO, description="Global log level")
    format: str = Field(
        "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
        description="Log format string"
    )
    enable_colors: bool = Field(True, description="Enable colored output")
    feature_levels: Optional[FeatureLogLevelsConfig] = Field(
        default_factory=FeatureLogLevelsConfig,
        description="Feature-specific log levels"
    )
    
    @field_validator('level', mode='before')
    def validate_level(cls, v):
        """Convert string to LoggingLevel enum."""
        if isinstance(v, str):
            return LoggingLevel(v.upper())
        return v


class PathsConfig(BaseUnifiedModel):
    """Paths configuration."""
    
    output_dir: str = Field("outputs", description="Output directory")
    log_dir: str = Field("${paths.output_dir}/logs", description="Log directory")
    plugin_dir: str = Field("panther/plugins", description="Plugin directory")
    cert_dir: Optional[str] = Field(None, description="Certificate directory")
    temp_dir: Optional[str] = Field("/tmp/panther", description="Temporary directory")


class DockerUserMappingConfig(BaseUnifiedModel):
    """Docker user mapping configuration."""
    
    run_as_host_user: bool = Field(False, description="Run containers as host user")
    custom_uid: Optional[int] = Field(None, description="Custom user ID")
    custom_gid: Optional[int] = Field(None, description="Custom group ID")
    user_name: str = Field("panther", description="Container user name")
    fallback_to_root: bool = Field(True, description="Fallback to root if user creation fails")


class DockerConfig(BaseUnifiedModel):
    """Docker configuration."""
    
    build_docker_image: bool = Field(True, description="Build Docker images")
    log_docker_image_build: bool = Field(True, description="Log Docker image build process")
    user_mapping: DockerUserMappingConfig = Field(
        default_factory=DockerUserMappingConfig,
        description="User mapping configuration"
    )
    registry: Optional[str] = Field(None, description="Docker registry URL")
    build_args: Dict[str, str] = Field(default_factory=dict, description="Build arguments")
    cache_from: Optional[str] = Field(None, description="Cache source for builds")
    network_mode: str = Field("bridge", description="Docker network mode")


class ProgressConfig(BaseUnifiedModel):
    """Progress display configuration."""
    
    enable_progress_bar: bool = Field(True, description="Enable progress bars")
    redirect_logging: bool = Field(True, description="Redirect logs to files")
    show_spinner: bool = Field(True, description="Show activity spinner")
    show_test_status: bool = Field(True, description="Show test status information")
    use_emojis: bool = Field(True, description="Use emojis in progress display")
    update_interval: float = Field(0.1, description="Progress update interval (seconds)")


class FastFailConfig(BaseUnifiedModel):
    """Fast-fail configuration."""
    
    enabled: bool = Field(True, description="Enable fast-fail system")
    test_level: bool = Field(False, description="Enable per-test configuration")
    docker_build_failures: bool = Field(True, description="Fail on Docker build errors")
    service_start_failures: bool = Field(True, description="Fail on service start errors")
    ivy_compilation_failures: bool = Field(False, description="Fail on Ivy compilation errors")
    timeout_cascade_threshold: int = Field(3, description="Consecutive timeouts before failing")
    critical_only: bool = Field(False, description="Only fail on critical errors")


class MetricsConfig(BaseUnifiedModel):
    """Metrics collection configuration."""
    
    enabled: bool = Field(True, description="Enable metrics collection")
    collect_system_metrics: bool = Field(True, description="Collect system metrics")
    publish_interval: int = Field(30, description="Metrics publish interval (seconds)")
    export_format: str = Field("json", description="Export format")
    retention_days: int = Field(30, description="Metrics retention period")


class GlobalConfig(BaseUnifiedModel):
    """Global configuration container."""
    
    version: str = Field("1.0", description="Configuration version")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    paths: PathsConfig = Field(default_factory=PathsConfig, description="Paths configuration")
    docker: DockerConfig = Field(default_factory=DockerConfig, description="Docker configuration")
    progress: ProgressConfig = Field(default_factory=ProgressConfig, description="Progress configuration")
    fast_fail: FastFailConfig = Field(default_factory=FastFailConfig, description="Fast-fail configuration")
    metrics: MetricsConfig = Field(default_factory=MetricsConfig, description="Metrics configuration")
    observers: ObserversConfig = Field(default_factory=ObserversConfig, description="Observer configurations")
    
    def resolve_paths(self) -> 'GlobalConfig':
        """Resolve path interpolations.
        
        Returns:
            GlobalConfig with resolved paths
        """
        # Use OmegaConf to resolve interpolations
        resolved = self.interpolate()
        return resolved
    
    def apply_overrides(self, overrides: Dict[str, Any]) -> 'GlobalConfig':
        """Apply configuration overrides.
        
        Args:
            overrides: Dictionary of overrides
            
        Returns:
            New GlobalConfig with overrides applied
        """
        return self.update_from_dict(overrides)
    
    def get_feature_log_level(self, feature: str) -> Optional[str]:
        """Get log level for a specific feature.
        
        Args:
            feature: Feature name
            
        Returns:
            Log level or None
        """
        if self.logging and self.logging.feature_levels:
            return getattr(self.logging.feature_levels, feature, None)
        return None