"""Configuration schemas for network environment plugins."""

from dataclasses import dataclass, field
from typing import List

from omegaconf import MISSING


# Network Environment Configuration
@dataclass
class EnvironmentConfig:
    """Base configuration for all network environments.

    Defines common settings shared by all environment plugins
    (Docker Compose, Shadow NS, Localhost). Concrete environment
    plugins extend this with type-specific parameters.

    Background monitoring runs in a non-blocking thread to detect
    unhealthy services during experiment execution without blocking
    the main test flow.

    Attributes:
        type: Environment type identifier (set by each plugin).
        enable_background_monitoring: Run health checks in background thread.
        monitoring_interval_seconds: Seconds between health check polls.
        failure_threshold_count: Consecutive failures before termination.
        allow_partial_deployment: Continue if some services fail to start.
        critical_services: Services that must stay healthy for the experiment.
    """

    type: str = MISSING

    # Background monitoring configuration for non-blocking service health checks
    enable_background_monitoring: bool = True
    monitoring_interval_seconds: int = 5
    failure_threshold_count: int = 3
    allow_partial_deployment: bool = False
    critical_services: List[str] = field(default_factory=list)
