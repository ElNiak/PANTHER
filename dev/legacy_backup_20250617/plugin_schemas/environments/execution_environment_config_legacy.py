from dataclasses import dataclass

from omegaconf import MISSING

from panther.config.core.models import EnvironmentConfig


# Execution Environment Configuration
@dataclass
class ExecutionEnvironmentConfig(EnvironmentConfig):
    type: str = MISSING
