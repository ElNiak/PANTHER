"""Data structures for runtime plugin registration information."""

from dataclasses import dataclass
from typing import Any, Optional

from panther.plugins.core.structures.plugin_manifest import PluginManifest


@dataclass
class PluginRegistration:
    """Runtime registration information for a loaded plugin."""

    manifest: PluginManifest
    instance: Optional[Any] = None
    loaded: bool = False
    active: bool = False
    load_order: int = -1
    error_message: Optional[str] = None

    @property
    def plugin_id(self) -> str:
        """Generate unique plugin identifier."""
        return (
            f"{self.manifest.type.value}:{self.manifest.name}:{self.manifest.version}"
        )
