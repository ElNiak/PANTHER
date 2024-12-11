from dataclasses import dataclass, field
from typing import Dict, List, Optional

from panther.config.config_experiment_schema import NetworkEnvironmentConfig


@dataclass
class LocalhostSingleContainerConfig(NetworkEnvironmentConfig):
    type: str    = "localhost_single_container"
    version: str = "3.8"
    network_name: str = "default_network"
    service_prefix: Optional[str] = None  # Optional prefix for service names
    environment: Dict[str, str] = field(default_factory=dict)  # Environment variables