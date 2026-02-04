from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.plugins.core.structures.plugin_dependency import PluginDependency
from panther.plugins.core.structures.plugin_type import PluginType

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.plugins.core.docker_metadata import DockerRequirements

"""
Plugin Manifest and Metadata Definitions

This module provides the core data structures for plugin metadata,
versioning, and dependency management in PANTHER.
"""

from dataclasses import dataclass, field

from packaging import version


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
    max_panther_version: Optional[str] = None

    # Dependencies
    dependencies: List[PluginDependency] = field(default_factory=list)

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # Runtime information
    entry_point: Optional[str] = None  # Module path to main class
    file_path: Optional[str] = None  # Physical file location
    runtime_mode: Optional[
        str
    ] = None  # Required runtime mode (minimal, debug, profile)

    # Feature declarations
    supported_protocols: List[str] = field(default_factory=list)
    supported_events: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)

    # Tags for categorization
    tags: List[str] = field(default_factory=list)

    # New fields for enhanced plugin architecture
    is_category: bool = False  # Distinguishes category plugins
    implementations: List[str] = field(default_factory=list)  # For category plugins
    external_dependencies: List[str] = field(
        default_factory=list
    )  # Non-plugin dependencies

    def to_dict(self) -> Dict[str, Any]:
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
            "runtime_mode": self.runtime_mode,
            "supported_protocols": self.supported_protocols,
            "supported_events": self.supported_events,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "is_category": self.is_category,
            "implementations": self.implementations,
            "external_dependencies": self.external_dependencies,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
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
            runtime_mode=data.get("runtime_mode"),
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
