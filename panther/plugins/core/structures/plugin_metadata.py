"""
Plugin Metadata Structures

This module defines the metadata structures used for plugin management,
including PluginMetadata, PluginMetadataLoader, and PluginStatus.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .plugin_type import PluginType


class PluginStatus(Enum):
    """Plugin lifecycle status."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    FAILED = "failed"
    UNLOADED = "unloaded"


@dataclass
class PluginMetadata:
    """
    Lightweight metadata structure for plugin discovery and cataloging.

    This is a simplified version of PluginManifest used during the discovery phase.
    """

    name: str
    type: str  # String representation of plugin type
    path: Optional[Path] = None
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    supported_protocols: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: PluginStatus = PluginStatus.DISCOVERED

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginMetadata":
        """Create PluginMetadata from dictionary."""
        path = data.get("path")
        if path and not isinstance(path, Path):
            path = Path(path)

        return cls(
            name=data.get("name", ""),
            type=data.get("type", "service"),
            path=path,
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            supported_protocols=data.get("supported_protocols", []),
            dependencies=data.get("dependencies", []),
            capabilities=data.get("capabilities", []),
            tags=data.get("tags", []),
            status=PluginStatus(data.get("status", "discovered")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.type,
            "path": str(self.path) if self.path else None,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "supported_protocols": self.supported_protocols,
            "dependencies": self.dependencies,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "status": self.status.value,
        }

    def has_capability(self, capability: str) -> bool:
        """Check if plugin has a specific capability."""
        return capability in self.capabilities

    def is_compatible_with(self, protocol: str = None, version: str = None) -> bool:
        """Check if plugin is compatible with a protocol/version."""
        if protocol and self.supported_protocols:
            return protocol in self.supported_protocols
        return True


class PluginMetadataLoader:
    """Utility class for loading plugin metadata from various sources."""

    @staticmethod
    def from_module(module) -> Optional[PluginMetadata]:
        """Extract metadata from a Python module."""
        try:
            # Look for metadata attributes in the module
            name = getattr(module, "__plugin_name__", module.__name__.split(".")[-1])
            plugin_type = getattr(module, "__plugin_type__", "service")
            version = getattr(module, "__version__", "1.0.0")
            description = getattr(module, "__description__", "")
            author = getattr(module, "__author__", "")
            supported_protocols = getattr(module, "__supported_protocols__", [])
            dependencies = getattr(module, "__dependencies__", [])
            capabilities = getattr(module, "__capabilities__", [])

            return PluginMetadata(
                name=name,
                type=plugin_type,
                version=version,
                description=description,
                author=author,
                supported_protocols=supported_protocols,
                dependencies=dependencies,
                capabilities=capabilities,
            )
        except Exception:
            return None

    @staticmethod
    def from_decorator_metadata(metadata: dict) -> Optional[PluginMetadata]:
        """Create PluginMetadata from decorator registration data."""
        try:
            return PluginMetadata(
                name=metadata.get("name", ""),
                type=metadata.get("plugin_type", "service"),
                version=metadata.get("version", "1.0.0"),
                description=metadata.get("description", ""),
                author=metadata.get("author", ""),
                supported_protocols=metadata.get("supported_protocols", []),
                dependencies=metadata.get("dependencies", []),
                capabilities=metadata.get("capabilities", []),
            )
        except Exception:
            return None

    @staticmethod
    def load_from_directory(
        directory: Path, plugin_type: str
    ) -> Optional[PluginMetadata]:
        """Load plugin metadata from a directory."""
        import json

        import yaml

        try:
            # Try to find a plugin.yaml or plugin.json
            yaml_file = directory / "plugin.yaml"
            json_file = directory / "plugin.json"

            metadata_dict = None

            if yaml_file.exists():
                with open(yaml_file, "r") as f:
                    metadata_dict = yaml.safe_load(f)
            elif json_file.exists():
                with open(json_file, "r") as f:
                    metadata_dict = json.load(f)
            else:
                # Create basic metadata from directory name
                metadata_dict = {
                    "name": directory.name,
                    "type": plugin_type,
                    "version": "1.0.0",
                    "description": f"{directory.name} plugin",
                    "path": str(directory),
                }

            if metadata_dict:
                metadata_dict["path"] = directory
                metadata_dict["type"] = plugin_type
                return PluginMetadata.from_dict(metadata_dict)

        except Exception:
            # Fallback to basic metadata
            return PluginMetadata(
                name=directory.name,
                type=plugin_type,
                path=directory,
                version="1.0.0",
                description=f"{directory.name} plugin",
            )

        return None
