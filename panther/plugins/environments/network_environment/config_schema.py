
from dataclasses import dataclass
from omegaconf import MISSING

from panther.plugins.environments.config_schema import EnvironmentConfig

# Network Environment Configuration
@dataclass
class NetworkEnvironmentConfig(EnvironmentConfig):
    type: str = MISSING
