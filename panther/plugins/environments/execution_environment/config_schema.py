from dataclasses import dataclass
from omegaconf import MISSING

from panther.plugins.environments.config_schema import EnvironmentConfig


# Execution Environment Configuration
@dataclass
class ExecutionEnvironmentConfig(EnvironmentConfig):
    type: str = MISSING
