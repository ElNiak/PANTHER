from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config.config_experiment_schema import NetworkEnvironmentConfig


@dataclass
class DockerComposeConfig(NetworkEnvironmentConfig):
    type: str    = "docker_compose"
    version: str = "3.8"
    network_name: str = "default_network"
    service_prefix: Optional[str] = None  # Optional prefix for service names
    volumes: List[str] = field(default_factory=list)  # List of volume mounts
    environment: Dict[str, str] = field(default_factory=dict)  # Environment variables