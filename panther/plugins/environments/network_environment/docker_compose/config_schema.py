from typing import Dict, List, Optional

from pydantic import Field

from panther.config.core.models.plugin import NetworkEnvironmentPluginConfig


class DockerComposeConfig(NetworkEnvironmentPluginConfig):
    """Docker Compose network environment configuration.

    Multi-container deployment using Docker Compose for isolated protocol
    testing with per-service containers, configurable networking, and
    background health monitoring.

    Requires Docker Engine (27.03.0+) and Docker Compose (v1.27.0+).
    Ensure your user has proper Docker permissions.

    Inherited from NetworkEnvironmentPluginConfig / BasePluginConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.

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

    # Non-blocking monitoring configuration
    enable_background_monitoring: bool = Field(
        default=True, description="Feature flag for non-blocking monitoring"
    )
    monitoring_interval_seconds: int = Field(
        default=10, description="How often to check service health"
    )
    failure_threshold_count: int = Field(
        default=1, description="Consecutive failures before early termination"
    )
    critical_services: List[str] = Field(
        default_factory=list, description="Services that must stay healthy"
    )
    allow_partial_deployment: bool = Field(
        default=False, description="Continue experiment even if some services fail"
    )
    deploy_timeout: int = Field(
        default=300,
        description="Timeout in seconds for docker compose up/down operations",
    )
    deploy_timeout_debug_multiplier: float = Field(
        default=2.0,
        description="Multiplier applied to deploy_timeout when execution environments (strace, gdb, etc.) are enabled, since debug images are larger and slower to start. Set to 1.0 to disable auto-scaling.",
    )
