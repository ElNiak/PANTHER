"""
Observer Configuration Schema Module

This module provides backward compatibility imports for the legacy observer schema structure
while redirecting to the new unified configuration models.
"""

# Re-export from new unified models
from panther.config.core.models.observer import (
    BaseObserverConfig,
    ExperimentObserverConfig,
    LoggerObserverConfig,
    LogLevel,
    MetricsObserverConfig,
    ObserverConfig,
    StorageObserverConfig,
)

__all__ = [
    "BaseObserverConfig",
    "ExperimentObserverConfig",
    "LoggerObserverConfig",
    "LogLevel",
    "MetricsObserverConfig",
    "ObserverConfig",
    "StorageObserverConfig",
]
