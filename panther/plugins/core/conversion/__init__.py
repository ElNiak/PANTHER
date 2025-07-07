"""
Plugin structure conversion utilities.

This module provides automatic synchronization between PluginManifest
and PluginMetadata structures to prevent field loss during conversions.
"""

from .structure_converter import (
    PluginStructureConverter,
    auto_convert_manifest_to_metadata,
    auto_convert_metadata_to_manifest,
)

__all__ = [
    "PluginStructureConverter",
    "auto_convert_manifest_to_metadata",
    "auto_convert_metadata_to_manifest",
]
