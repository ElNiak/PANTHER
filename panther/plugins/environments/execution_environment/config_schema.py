


from dataclasses import dataclass
from omegaconf import MISSING

# Execution Environment Configuration
@dataclass
class ExecutionEnvironmentConfig:
    type: str = MISSING
