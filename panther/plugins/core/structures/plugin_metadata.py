"""Plugin Metadata Structures.

This module defines the metadata structures used for plugin management,
including PluginMetadata and PluginStatus.
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
    """Lightweight metadata structure for plugin discovery and cataloging.

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
