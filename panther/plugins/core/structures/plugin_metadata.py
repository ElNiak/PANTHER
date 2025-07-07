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
    Now supports dynamic fields from decorator registration.
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
    runtime_mode: Optional[str] = None

    # Dynamic fields from decorator registration
    external_dependencies: List[str] = field(default_factory=list)
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginMetadata":
        """Create PluginMetadata from dictionary."""
        path = data.get("path")
        if path and not isinstance(path, Path):
            path = Path(path)

        # Extract known fields
        known_fields = {
            "name",
            "type",
            "path",
            "version",
            "description",
            "author",
            "supported_protocols",
            "dependencies",
            "capabilities",
            "tags",
            "status",
            "runtime_mode",
            "external_dependencies",
            "extra_fields",
        }

        # Collect any extra fields not in the known set
        extra_fields = {k: v for k, v in data.items() if k not in known_fields}

        # Merge with any extra_fields already in data
        if "extra_fields" in data and isinstance(data["extra_fields"], dict):
            extra_fields.update(data["extra_fields"])

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
            runtime_mode=data.get("runtime_mode"),
            external_dependencies=data.get("external_dependencies", []),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
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
            "runtime_mode": self.runtime_mode,
        }

        # Add dynamic fields if they have values
        if self.runtime_mode:
            result["runtime_mode"] = self.runtime_mode
        if self.external_dependencies:
            result["external_dependencies"] = self.external_dependencies

        # Add any extra fields
        result.update(self.extra_fields)

        return result

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
            # Known core fields that map directly
            core_mapping = {
                "plugin_type": "type",
                "external_dependencies": "external_dependencies",
            }

            # Build data dict for from_dict method
            data = {}

            # Map known fields
            for meta_key, meta_value in metadata.items():
                if meta_key in core_mapping:
                    data[core_mapping[meta_key]] = meta_value
                elif meta_key in {
                    "name",
                    "version",
                    "description",
                    "author",
                    "supported_protocols",
                    "dependencies",
                    "capabilities",
                    "runtime_mode",
                }:
                    data[meta_key] = meta_value
                else:
                    # Unknown fields go to extra_fields
                    if "extra_fields" not in data:
                        data["extra_fields"] = {}
                    data["extra_fields"][meta_key] = meta_value

            # Use from_dict to handle all the dynamic field logic
            return PluginMetadata.from_dict(data)
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
