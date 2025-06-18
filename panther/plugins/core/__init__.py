"""
Plugin Core Components Module

This module provides core plugin components for the PANTHER framework,
including metadata management, factory patterns, and other utilities
used by the unified plugin manager.
"""

from .plugin_metadata import PluginMetadata, PluginManifest
from .plugin_factory import PluginFactory

__all__ = [
    "PluginMetadata", 
    "PluginManifest",
    "PluginFactory"
]