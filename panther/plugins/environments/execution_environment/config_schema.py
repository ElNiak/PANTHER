


from dataclasses import dataclass
from omegaconf import MISSING

from plugins.environments.config_schema import EnvironmentConfig

# Execution Environment Configuration
@dataclass
class ExecutionEnvironmentConfig(EnvironmentConfig):
    type: str = MISSING
