"""Global configuration models."""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from ..base import BaseConfig
from ..validators import logging_level_validator
from .observer import ObserversConfig


class LoggingLevel(str, Enum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DockerNetworkMode(str, Enum):
    """Docker network mode."""

    BRIDGE = "bridge"
    HOST = "host"
    NONE = "none"
    OVERLAY = "overlay"


class ExportFormat(str, Enum):
    """Metrics/data export format."""

    JSON = "json"
    CSV = "csv"
    PROMETHEUS = "prometheus"


class FeatureLogLevelsConfig(BaseConfig):
    """Feature-specific log level configuration."""

    docker_build: Optional[LoggingLevel] = Field(
        None, description="Docker build operations"
    )
    service_start: Optional[LoggingLevel] = Field(
        None, description="Service startup operations"
    )
    environment_setup: Optional[LoggingLevel] = Field(
        None, description="Environment setup"
    )
    test_execution: Optional[LoggingLevel] = Field(None, description="Test execution")
    metrics_collection: Optional[LoggingLevel] = Field(
        None, description="Metrics collection"
    )
    event_processing: Optional[LoggingLevel] = Field(
        None, description="Event processing"
    )
    plugin_loading: Optional[LoggingLevel] = Field(None, description="Plugin loading")
    configuration: Optional[LoggingLevel] = Field(
        None, description="Configuration operations"
    )
    validation: Optional[LoggingLevel] = Field(
        None, description="Validation operations"
    )
    command_generation: Optional[LoggingLevel] = Field(
        None, description="Command generation"
    )
    output_collection: Optional[LoggingLevel] = Field(
        None, description="Output collection"
    )
    error_handling: Optional[LoggingLevel] = Field(None, description="Error handling")
    fast_fail: Optional[LoggingLevel] = Field(None, description="Fast-fail system")
    observer: Optional[LoggingLevel] = Field(None, description="Observer system")
    state_management: Optional[LoggingLevel] = Field(
        None, description="State management"
    )
    service_managers: Optional[LoggingLevel] = Field(
        None, description="Service manager operations"
    )

    @field_validator("*", mode="before")
    @classmethod
    def validate_log_level(cls, v):
        """Validate and convert log level values to LoggingLevel enum."""
        if v is not None and isinstance(v, str):
            try:
                return LoggingLevel(v.upper())
            except ValueError:
                valid = [e.value for e in LoggingLevel]
                raise ValueError(f"Invalid log level: '{v}'. Valid values are: {valid}")
        return v

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = super().to_dict(**kwargs)
        # Filter out None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}


class LoggingConfig(BaseConfig):
    """Logging configuration."""

    level: LoggingLevel = Field(LoggingLevel.INFO, description="Global log level")
    format: str = Field(
        "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
        description="Log format string",
    )
    enable_colors: bool = Field(True, description="Enable colored output")
    debug_file_logging: bool = Field(
        True,
        description="Enable debug-level logging to files while respecting configured level for console",
    )
    feature_levels: Optional[FeatureLogLevelsConfig] = Field(
        default_factory=FeatureLogLevelsConfig,
        description="Feature-specific log levels",
    )

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v):
        """Convert string to LoggingLevel enum."""
        return logging_level_validator(cls, v)


class PathsConfig(BaseConfig):
    """Paths configuration."""

    output_dir: str = Field("outputs", description="Output directory")
    log_dir: str = Field("outputs/logs", description="Log directory")
    plugin_dir: str = Field("panther/plugins", description="Plugin directory")
    cert_dir: Optional[str] = Field(None, description="Certificate directory")
    temp_dir: Optional[str] = Field("/tmp/panther", description="Temporary directory")


class DockerUserMappingConfig(BaseConfig):
    """Docker user mapping configuration."""

    run_as_host_user: bool = Field(False, description="Run containers as host user")
    custom_uid: Optional[int] = Field(
        None,
        ge=0,
        le=65534,
        description="Custom user ID",
        examples=[1000, 0],
        json_schema_extra={"category": "docker"},
    )
    custom_gid: Optional[int] = Field(
        None,
        ge=0,
        le=65534,
        description="Custom group ID",
        examples=[1000, 0],
        json_schema_extra={"category": "docker"},
    )
    user_name: str = Field("panther", description="Container user name")
    fallback_to_root: bool = Field(
        True, description="Fallback to root if user creation fails"
    )


class ServiceDockerOverrideConfig(BaseConfig):
    """Per-service Docker build overrides. None = inherit from global DockerConfig."""

    force_build_docker_image: Optional[bool] = Field(
        None, description="Override global force_build for this service"
    )
    no_docker_cache: Optional[bool] = Field(
        None, description="Override global no_docker_cache for this service"
    )
    use_buildx: Optional[bool] = Field(
        None, description="Override global use_buildx for this service"
    )
    target_platform: Optional[str] = Field(
        None, description="Override global target_platform for this service"
    )
    build_args: Optional[Dict[str, str]] = Field(
        None, description="Additional build args (merged over global build_args)"
    )


class DockerConfig(BaseConfig):
    """Docker configuration."""

    force_build_docker_image: bool = Field(True, description="Build Docker images")
    log_docker_image_build: bool = Field(
        True, description="Log Docker image build process"
    )
    user_mapping: DockerUserMappingConfig = Field(
        default_factory=DockerUserMappingConfig,
        description="User mapping configuration",
    )
    registry: Optional[str] = Field(None, description="Docker registry URL")
    build_args: Dict[str, str] = Field(
        default_factory=dict, description="Build arguments"
    )
    cache_from: Optional[str] = Field(None, description="Cache source for builds")
    network_mode: DockerNetworkMode = Field(
        DockerNetworkMode.BRIDGE,
        description="Docker network mode",
        examples=["bridge", "host", "none"],
        json_schema_extra={"category": "docker"},
    )

    @field_validator("network_mode", mode="before")
    @classmethod
    def validate_network_mode(cls, v):
        """Convert string to DockerNetworkMode enum."""
        if isinstance(v, str):
            try:
                return DockerNetworkMode(v.lower())
            except ValueError:
                valid = [e.value for e in DockerNetworkMode]
                raise ValueError(f"Invalid network mode '{v}'. Valid: {valid}")
        return v

    # Docker Buildx configuration fields
    use_buildx: bool = Field(
        True, description="Enable Docker Buildx for cross-platform builds"
    )
    target_platform: Optional[str] = Field(
        None,
        description="Override target platform (e.g., linux/amd64, linux/arm64). If None, auto-detects based on host architecture",
    )
    buildx_builder: str = Field("default", description="Buildx builder instance name")
    multi_platform: bool = Field(
        False, description="Enable multi-platform image building"
    )
    no_docker_cache: bool = Field(
        False,
        description="Skip Docker build layer cache entirely (passes --no-cache to builds). "
        "When True, also implies force_build_docker_image=True (image-level cache is skipped). "
        "Only passed as --no-cache on the first build of each tag per session.",
    )


_resolve_logger = logging.getLogger(__name__)


def resolve_docker_build_config(
    global_docker: DockerConfig,
    service_docker: Optional[ServiceDockerOverrideConfig] = None,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Resolve per-service Docker overrides over global defaults.

    Returns a flat dict with resolved values for use in build_image().
    For build_args: service values are merged OVER global values (service wins on key collision).
    For all other fields: service value used if not None, else global value.
    """
    _log = logger or _resolve_logger
    resolved = {
        "force_build_docker_image": global_docker.force_build_docker_image,
        "no_docker_cache": global_docker.no_docker_cache,
        "use_buildx": global_docker.use_buildx,
        "target_platform": global_docker.target_platform,
        "build_args": dict(global_docker.build_args),
    }

    if service_docker is None:
        return resolved

    for field in (
        "force_build_docker_image",
        "no_docker_cache",
        "use_buildx",
        "target_platform",
    ):
        val = getattr(service_docker, field)
        if val is not None:
            old_val = resolved[field]
            if old_val != val:
                _log.debug("Service override: %s = %s (was %s)", field, val, old_val)
            resolved[field] = val

    if service_docker.build_args is not None:
        overridden = set(service_docker.build_args) & set(resolved["build_args"])
        for key in overridden:
            _log.debug(
                "Service build_args override: %s = %s (was %s)",
                key,
                service_docker.build_args[key],
                resolved["build_args"][key],
            )
        resolved["build_args"].update(service_docker.build_args)

    return resolved


class ProgressConfig(BaseConfig):
    """Progress display configuration."""

    enable_progress_bar: bool = Field(True, description="Enable progress bars")
    redirect_logging: bool = Field(True, description="Redirect logs to files")
    show_spinner: bool = Field(True, description="Show activity spinner")
    show_test_status: bool = Field(True, description="Show test status information")
    use_emojis: bool = Field(True, description="Use emojis in progress display")
    update_interval: float = Field(
        0.1,
        ge=0.01,
        le=10.0,
        description="Progress update interval (seconds)",
        examples=[0.1, 0.5, 1.0],
        json_schema_extra={"unit": "seconds"},
    )


class FastFailConfig(BaseConfig):
    """Fast-fail configuration."""

    enabled: bool = Field(True, description="Enable fast-fail system")
    test_level: bool = Field(False, description="Enable per-test configuration")
    docker_build_failures: bool = Field(True, description="Fail on Docker build errors")
    service_start_failures: bool = Field(
        True, description="Fail on service start errors"
    )
    ivy_compilation_failures: bool = Field(
        True, description="Fail on Ivy compilation errors"
    )
    timeout_cascade_threshold: int = Field(
        1,
        ge=1,
        le=100,
        description="Consecutive timeouts before failing",
        examples=[1, 3, 5],
    )
    critical_only: bool = Field(False, description="Only fail on critical errors")


class MetricsConfig(BaseConfig):
    """Metrics collection configuration."""

    enabled: bool = Field(True, description="Enable metrics collection")
    collect_system_metrics: bool = Field(True, description="Collect system metrics")
    publish_interval: int = Field(
        30,
        ge=1,
        le=3600,
        description="Metrics publish interval (seconds)",
        examples=[10, 30, 60],
        json_schema_extra={"unit": "seconds"},
    )
    export_format: ExportFormat = Field(
        ExportFormat.JSON,
        description="Export format for metrics data",
        examples=["json", "csv", "prometheus"],
        json_schema_extra={"category": "output"},
    )
    retention_days: int = Field(
        30,
        ge=1,
        le=365,
        description="Metrics retention period (days)",
        examples=[7, 30, 90],
        json_schema_extra={"unit": "days"},
    )

    @field_validator("export_format", mode="before")
    @classmethod
    def validate_export_format(cls, v):
        """Convert string to ExportFormat enum."""
        if isinstance(v, str):
            try:
                return ExportFormat(v.lower())
            except ValueError:
                valid = [e.value for e in ExportFormat]
                raise ValueError(f"Invalid export format '{v}'. Valid: {valid}")
        return v


class GlobalConfig(BaseConfig):
    """Shared settings applied across ALL tests in an experiment (logging, Docker, paths, progress, fast-fail, metrics, observers)."""

    version: str = Field("1.0", description="Configuration version")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    paths: PathsConfig = Field(
        default_factory=PathsConfig, description="Paths configuration"
    )
    docker: DockerConfig = Field(
        default_factory=DockerConfig, description="Docker configuration"
    )
    progress: ProgressConfig = Field(
        default_factory=ProgressConfig, description="Progress configuration"
    )
    fast_fail: FastFailConfig = Field(
        default_factory=FastFailConfig, description="Fast-fail configuration"
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig, description="Metrics configuration"
    )
    observers: ObserversConfig = Field(
        default_factory=ObserversConfig, description="Observer configurations"
    )

    def apply_overrides(self, overrides: Dict[str, Any]) -> "GlobalConfig":
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
