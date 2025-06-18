"""Experiment configuration schema for PANTHER framework.

This module provides backward compatibility imports for the legacy schema structure
while redirecting to the new unified configuration models.
"""

# Re-export from new unified models
from panther.config.core.models.experiment import (
    ExperimentConfig,
    ExperimentMetadata,
    StepsConfig,
    TestConfig,
)
from panther.config.core.models.service import ServiceConfig

# Re-export environment configs
from panther.config.core.models.environment import (
    ExecutionEnvironmentConfig,
    NetworkEnvironmentConfig,
)

__all__ = [
    "ExperimentConfig",
    "ExperimentMetadata",
    "StepsConfig",
    "TestConfig",
    "ServiceConfig",
    "ExecutionEnvironmentConfig",
    "NetworkEnvironmentConfig",
]
