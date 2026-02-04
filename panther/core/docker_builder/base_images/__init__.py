"""
Base Images Management System for PANTHER

This module implements a modular base image management system following SOLID and DRY principles.
Provides intelligent base image selection, caching, and plugin-aware Docker image composition.

Architecture:
- BaseImageStrategy: Abstract interface for base image selection strategies
- TieredBaseImageStrategy: Implements 4-tier hierarchy (runtime->dev->build->builder)
- BaseImageManager: Coordinates base image operations and caching
- BaseImageRegistry: Plugin-aware base image discovery and metadata management
"""

from .docker_builder_integration import BaseImageManagerMixin
from .interfaces import (
    BaseImageMetadata,
    BaseImageStrategy,
    PluginRequirementsExtractor,
)
from .plugin_extractor import PantherPluginRequirementsExtractor
from .strategies import (
    PlatformAwareStrategy,
    PluginAwareStrategy,
    TieredBaseImageStrategy,
)

__all__ = [
    "BaseImageStrategy",
    "BaseImageMetadata",
    "PluginRequirementsExtractor",
    "TieredBaseImageStrategy",
    "PlatformAwareStrategy",
    "PluginAwareStrategy",
    "PantherPluginRequirementsExtractor",
    "BaseImageManagerMixin",
]
