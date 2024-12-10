
from dataclasses import dataclass
from omegaconf import MISSING

# Network Environment Configuration
@dataclass
class EnvironmentConfig:
    type: str = MISSING
