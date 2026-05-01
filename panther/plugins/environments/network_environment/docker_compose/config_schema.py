"""Docker Compose network environment configuration schema."""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from panther.config.core.models.environment import NetworkEnvironmentConfig


class AuxiliaryNetworkConfig(BaseModel):
    """Auxiliary Docker network for services that declare secondary endpoints.

    Used when at least one service in the experiment declares
    secondary_endpoints, providing a second IP per such container so the
    Ivy tester can present multiple speakers (e.g., RFC 4271 Sec 6.8 BGP
    collision detection).

    Path α design constraint: each service may declare at most ONE secondary
    endpoint; only the first entry is materialized as ipv4_address on the
    auxiliary bridge. Multi-endpoint support is pending. The docker_compose
    plugin enforces this via a runtime guard in
    `_auxiliary_network_render_context`.
    """

    name: str = Field(
        default="panther_aux_network",
        description="Docker network name for the auxiliary bridge",
    )
    subnet: str = Field(
        default="10.0.0.0/24",
        description="IPv4 subnet (CIDR) for the auxiliary bridge",
    )

    model_config = ConfigDict(extra="forbid")


class DockerComposeConfig(NetworkEnvironmentConfig):
    """Docker Compose network environment configuration.

    Multi-container deployment using Docker Compose for isolated protocol
    testing with per-service containers, configurable networking, and
    background health monitoring.

    Requires Docker Engine (27.03.0+) and Docker Compose (v1.27.0+).
    Ensure your user has proper Docker permissions.

    Inherited from NetworkEnvironmentConfig / EnvironmentConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.
        network_name, subnet, enable_ipv6 — network settings.
        enable_background_monitoring, monitoring_interval_seconds,
        failure_threshold_count, allow_partial_deployment, critical_services —
        monitoring settings.

    Example YAML::

        network_environment:
          type: docker_compose
          version: "3.8"
          enable_background_monitoring: true
          monitoring_interval_seconds: 10
          deploy_timeout: 300

    Troubleshooting:
        - **Network conflicts**: ensure unique network names or use ``service_prefix``
        - **Permission issues**: run with appropriate Docker permissions
        - **Container communication failures**: check Docker network settings
        - **Startup timeouts**: increase ``deploy_timeout`` value
        - **Debug tip**: set ``logging.level: DEBUG`` and use
          ``docker compose logs`` to view container logs
    """

    type: str = Field(default="docker_compose", description="Network environment type")
    version: str = Field(default="3.8", description="Docker Compose file version")
    service_prefix: Optional[str] = Field(
        default=None, description="Optional prefix for service names"
    )
    volumes: List[str] = Field(
        default_factory=list, description="List of volume mounts"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )

    # Override base default (5) with docker-compose-specific default (10)
    monitoring_interval_seconds: int = Field(
        default=10, description="How often to check service health"
    )

    deploy_timeout: int = Field(
        default=300,
        description="Timeout in seconds for docker compose up/down operations",
    )
    deploy_timeout_debug_multiplier: float = Field(
        default=2.0,
        description="Multiplier applied to deploy_timeout when execution environments are enabled",
    )

    auxiliary_network: Optional[AuxiliaryNetworkConfig] = Field(
        default=None,
        description=(
            "Auxiliary Docker network for services declaring secondary_endpoints. "
            "Generated only when at least one service in the experiment uses it."
        ),
    )
