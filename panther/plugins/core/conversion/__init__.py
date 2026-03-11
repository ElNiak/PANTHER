"""Plugin structure conversion utilities.

This module provides automatic synchronization between PluginManifest
and PluginMetadata structures to prevent field loss during conversions.
"""

from .structure_converter import (
    PluginStructureConverter,
    auto_convert_manifest_to_metadata,
)

__all__ = [
    "PluginStructureConverter",
    "auto_convert_manifest_to_metadata",
]
