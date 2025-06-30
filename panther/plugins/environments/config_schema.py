from dataclasses import dataclass, field
from typing import List

from omegaconf import MISSING


# Network Environment Configuration
@dataclass
class EnvironmentConfig:
    type: str = MISSING

    # Background monitoring configuration for non-blocking service health checks
    enable_background_monitoring: bool = True
    monitoring_interval_seconds: int = 5
    failure_threshold_count: int = 3
    allow_partial_deployment: bool = False
    critical_services: List[str] = field(default_factory=list)
