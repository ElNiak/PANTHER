"""Core configuration system for PANTHER.

This module provides the primary configuration management system using
Pydantic models and OmegaConf for advanced configuration handling.
"""

from .base import BaseConfig
from .manager import (
    ConfigurationManager,
    get_config_manager,
    load_experiment,
    validate_service,
    discover_versions,
)

__all__ = [
    'BaseConfig',
    'ConfigurationManager',
    'get_config_manager',
    'load_experiment', 
    'validate_service',
    'discover_versions',
]