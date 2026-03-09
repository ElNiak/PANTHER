"""Localhost single-container network environment configuration schema."""

from typing import Dict, Optional

from pydantic import Field

from panther.config.core.models.environment import NetworkEnvironmentConfig


class LocalhostSingleContainerConfig(NetworkEnvironmentConfig):
    """Localhost single-container network environment configuration.

    Lightweight testing environment where all services run in a single
    Docker container on localhost. Ideal for simple protocol testing with
    minimal network complexity, offering quick setup for development and
    initial verification before moving to multi-container environments.

    Services communicate directly via localhost networking within a
    single container. Uses ``EnvironmentManagerDockerMixin`` for
    consistent Docker operations.

    Inherited from NetworkEnvironmentConfig / BasePluginConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.

    Example YAML::

        network_environment:
          type: localhost_single_container
          environment:
            DEBUG: "1"
    """

    type: str = Field(
        default="localhost_single_container", description="Network environment type"
    )
    version: str = Field(default="3.8", description="Docker version compatibility")
    service_prefix: Optional[str] = Field(
        default=None, description="Optional prefix for service names"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
