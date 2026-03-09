"""Environment configuration models."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from omegaconf import OmegaConf
from pydantic import Field

from .base_model import BaseUnifiedModel

T = TypeVar("T", bound="BaseUnifiedModel")


class EnvironmentConfig(BaseUnifiedModel):
    """Base environment configuration."""

    type: str = Field(..., description="Environment type")

    # Background monitoring configuration for non-blocking service health checks
    enable_background_monitoring: bool = Field(
        True, description="Enable background monitoring"
    )
    monitoring_interval_seconds: int = Field(
        5, description="Monitoring interval in seconds"
    )
    failure_threshold_count: int = Field(1, description="Failure threshold count")
    allow_partial_deployment: bool = Field(
        False, description="Allow partial deployment"
    )
    critical_services: List[str] = Field(
        default_factory=list, description="Critical services list"
    )

    # Plugin-specific configuration - exactly like ServiceConfig
    plugin_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Plugin-specific configuration"
    )

    def get_plugin_config(self, config_class: Type[T], validate: bool = True) -> T:
        """Get typed plugin configuration with defaults.

        Merges plugin_config values over config_class defaults using OmegaConf,
        then instantiates the config class with the merged result.

        Args:
            config_class: The plugin configuration class
            validate: Whether to validate (currently unused, kept for API compat)

        Returns:
            Typed plugin configuration instance
        """
        default_instance = config_class()
        default_dict = default_instance.model_dump()

        # OmegaConf deep merge: plugin_config overrides defaults
        merged = OmegaConf.to_container(
            OmegaConf.merge(
                OmegaConf.create(default_dict),
                OmegaConf.create(self.plugin_config or {}),
            ),
            resolve=True,
        )

        return config_class(**merged)


class NetworkEnvironmentConfig(EnvironmentConfig):
    """Base network environment configuration."""

    type: str = Field(..., description="Environment type")

    # Allow extra fields for environment-specific parameters


# Network environment configurations have been moved to plugin directories:
# - DockerComposeConfig -> panther/plugins/environments/network_environment/docker_compose/config_schema.py
# - LocalhostSingleContainerConfig -> panther/plugins/environments/network_environment/localhost_single_container/config_schema.py
# - ShadowNsConfig -> panther/plugins/environments/network_environment/shadow_ns/config_schema.py


class ExecutionEnvironmentConfig(EnvironmentConfig):
    """Base execution environment configuration."""

    type: str = Field(..., description="Environment type")
    enabled: bool = Field(True, description="Whether this environment is enabled")

    # Allow extra fields for environment-specific parameters


# Note: Plugin-specific configurations have been moved to their respective plugin directories
# to support dynamic plugin discovery. Only base classes remain here.
#
# For example:
# - StraceConfig -> panther/plugins/environments/execution_environment/strace/config_schema.py
# - GperfCpuConfig -> panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py
# - etc.
#
# This allows new plugins to be added without modifying core code.
