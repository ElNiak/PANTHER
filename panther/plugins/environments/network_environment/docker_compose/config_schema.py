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
