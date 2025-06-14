from dataclasses import dataclass, field

from panther.config.config_experiment_schema import NetworkEnvironmentConfig


@dataclass
class DockerComposeConfig(NetworkEnvironmentConfig):
    type: str = "docker_compose"
    version: str = "3.8"
    network_name: str = "default_network"
    service_prefix: str | None = None  # Optional prefix for service names
    volumes: list[str] = field(default_factory=list)  # List of volume mounts
    environment: dict[str, str] = field(default_factory=dict)  # Environment variables

    # Non-blocking monitoring configuration
    enable_background_monitoring: bool = (
        True  # Feature flag for non-blocking monitoring
    )
    monitoring_interval_seconds: int = 10  # How often to check service health
    failure_threshold_count: int = 3  # Consecutive failures before early termination
    critical_services: list[str] = field(
        default_factory=list
    )  # Services that must stay healthy
    allow_partial_deployment: bool = (
        False  # Continue experiment even if some services fail
    )
