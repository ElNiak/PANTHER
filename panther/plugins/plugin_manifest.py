"""
Plugin Manifest and Metadata Definitions

This module provides the core data structures for plugin metadata,
versioning, and dependency management in PANTHER.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from packaging import version


class PluginType(Enum):
    """Enumeration of plugin types supported by PANTHER."""

    SERVICE = "service"
    ENVIRONMENT = "environment"
    TESTER = "tester"
    PROTOCOL = "protocol"
    OBSERVER = "observer"
    IUT = "iut"  # Implementation Under Test


@dataclass
class PluginDependency:
    """Represents a dependency requirement for a plugin."""

    name: str
    version_spec: str = "*"  # e.g., ">=1.0.0", "<2.0.0", "==1.2.3"
    plugin_type: PluginType | None = None

    def is_satisfied_by(self, version_str: str) -> bool:
        """Check if a given version satisfies this dependency."""
        if self.version_spec == "*":
            return True

        try:
            # Parse version spec and check
            spec = version.SpecifierSet(self.version_spec)
            return version.Version(version_str) in spec
        except Exception:
            return False


@dataclass
class PluginManifest:
    """
    Complete metadata for a plugin including versioning and dependencies.

    This structure is used for plugin discovery, validation, and loading.
    """

    # Basic metadata
    name: str
    version: str
    type: PluginType

    # Optional metadata
    author: str = ""
    description: str = ""
    license: str = ""
    homepage: str = ""

    # Compatibility
    min_panther_version: str = "1.0.0"
    max_panther_version: str | None = None

    # Dependencies
    dependencies: list[PluginDependency] = field(default_factory=list)

    # Configuration
    config_schema: dict[str, Any] = field(default_factory=dict)
    default_config: dict[str, Any] = field(default_factory=dict)

    # Runtime information
    entry_point: str | None = None  # Module path to main class
    file_path: str | None = None  # Physical file location

    # Feature declarations
    supported_protocols: list[str] = field(default_factory=list)
    supported_events: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)

    # Tags for categorization
    tags: list[str] = field(default_factory=list)

    # New fields for enhanced plugin architecture
    is_category: bool = False  # Distinguishes category plugins
    implementations: list[str] = field(default_factory=list)  # For category plugins
    external_dependencies: list[str] = field(default_factory=list)  # Non-plugin dependencies

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary representation."""
        return {
            "name": self.name,
            "version": self.version,
            "type": self.type.value,
            "author": self.author,
            "description": self.description,
            "license": self.license,
            "homepage": self.homepage,
            "min_panther_version": self.min_panther_version,
            "max_panther_version": self.max_panther_version,
            "dependencies": [
                {
                    "name": dep.name,
                    "version_spec": dep.version_spec,
                    "plugin_type": dep.plugin_type.value if dep.plugin_type else None,
                }
                for dep in self.dependencies
            ],
            "config_schema": self.config_schema,
            "default_config": self.default_config,
            "entry_point": self.entry_point,
            "file_path": self.file_path,
            "supported_protocols": self.supported_protocols,
            "supported_events": self.supported_events,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "is_category": self.is_category,
            "implementations": self.implementations,
            "external_dependencies": self.external_dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginManifest":
        """Create manifest from dictionary representation."""
        # Convert type string to enum
        plugin_type = PluginType(data.get("type", "service"))

        # Convert dependencies
        dependencies = []
        for dep_data in data.get("dependencies", []):
            dep_type = None
            if dep_data.get("plugin_type"):
                dep_type = PluginType(dep_data["plugin_type"])

            dependencies.append(
                PluginDependency(
                    name=dep_data["name"],
                    version_spec=dep_data.get("version_spec", "*"),
                    plugin_type=dep_type,
                )
            )

        return cls(
            name=data["name"],
            version=data["version"],
            type=plugin_type,
            author=data.get("author", ""),
            description=data.get("description", ""),
            license=data.get("license", ""),
            homepage=data.get("homepage", ""),
            min_panther_version=data.get("min_panther_version", "1.0.0"),
            max_panther_version=data.get("max_panther_version"),
            dependencies=dependencies,
            config_schema=data.get("config_schema", {}),
            default_config=data.get("default_config", {}),
            entry_point=data.get("entry_point"),
            file_path=data.get("file_path"),
            supported_protocols=data.get("supported_protocols", []),
            supported_events=data.get("supported_events", []),
            capabilities=data.get("capabilities", []),
            tags=data.get("tags", []),
            is_category=data.get("is_category", False),
            implementations=data.get("implementations", []),
            external_dependencies=data.get("external_dependencies", []),
        )

    def is_compatible_with_panther(self, panther_version: str) -> bool:
        """Check if plugin is compatible with given PANTHER version."""
        try:
            current = version.Version(panther_version)

            # Check minimum version
            if version.Version(self.min_panther_version) > current:
                return False

            # Check maximum version if specified
            if self.max_panther_version:
                if version.Version(self.max_panther_version) < current:
                    return False

            return True
        except Exception:
            return False


@dataclass
class PluginRegistration:
    """Runtime registration information for a loaded plugin."""

    manifest: PluginManifest
    instance: Any | None = None
    loaded: bool = False
    active: bool = False
    load_order: int = -1
    error_message: str | None = None

    @property
    def plugin_id(self) -> str:
        """Generate unique plugin identifier."""
        return f"{self.manifest.type.value}:{self.manifest.name}:{self.manifest.version}"
