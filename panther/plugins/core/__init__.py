"""
Plugin Core Components Module

This module provides core plugin components for the PANTHER framework,
including metadata management, factory patterns, and other utilities
used by the unified plugin manager.
"""

from .plugin_discovery import PluginDiscovery
from .plugin_factory import PluginFactory
from .structures.plugin_manifest import PluginManifest
from .structures.plugin_metadata import (
    PluginMetadata,
    PluginMetadataLoader,
    PluginStatus,
)

__all__ = [
    "PluginMetadata",
    "PluginMetadataLoader",
    "PluginStatus",
    "PluginManifest",
    "PluginFactory",
    "PluginDiscovery",
]
