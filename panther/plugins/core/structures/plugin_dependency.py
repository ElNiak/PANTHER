from dataclasses import dataclass
from typing import Optional

from packaging import version

from panther.plugins.core.structures.plugin_type import PluginType


@dataclass
class PluginDependency:
    """Represents a dependency requirement for a plugin."""

    name: str
    version_spec: str = "*"  # e.g., ">=1.0.0", "<2.0.0", "==1.2.3"
    plugin_type: Optional[PluginType] = None

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
