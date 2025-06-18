"""Plugin file management functionality."""

import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class PluginType(Enum):
    """Enum for plugin types."""

    NETWORK_ENVIRONMENT = "network_environment"
    EXECUTION_ENVIRONMENT = "execution_environment"
    IUT = "iut"
    TESTER = "tester"
    PROTOCOL = "protocol"

    @classmethod
    def from_string(cls, value: str) -> Optional["PluginType"]:
        """Convert string to PluginType."""
        try:
            return cls(value.lower())
        except ValueError:
            return None


class PluginFileManager(ErrorHandlerMixin):
    """Handles file system operations for plugins."""

    def __init__(self, panther_dir: Path):
        """Initialize plugin file manager.

        Args:
            panther_dir: Root directory of PANTHER installation
        """
        super().__init__()
        self.panther_dir = panther_dir
        self.plugins_base_dir = panther_dir / "panther" / "plugins"

        # Define plugin directory mappings
        self.plugin_dirs = {
            PluginType.NETWORK_ENVIRONMENT: self.plugins_base_dir
            / "environments"
            / "network_environment",
            PluginType.EXECUTION_ENVIRONMENT: self.plugins_base_dir
            / "environments"
            / "execution_environment",
            PluginType.IUT: self.plugins_base_dir / "services" / "iut",
            PluginType.TESTER: self.plugins_base_dir / "services" / "testers",
            PluginType.PROTOCOL: self.plugins_base_dir / "protocols",
        }

    def add_plugin(
        self,
        plugin_type: PluginType,
        source_dir: Path,
        plugin_name: Optional[str] = None,
    ) -> None:
        """Add a plugin of any type.

        Args:
            plugin_type: Type of plugin to add
            source_dir: Source directory containing plugin files
            plugin_name: Optional name for the plugin (defaults to source dir name)

        Raises:
            ValueError: If plugin type is invalid
            FileNotFoundError: If source directory doesn't exist
            FileExistsError: If plugin already exists
        """
        if plugin_type not in self.plugin_dirs:
            raise ValueError(f"Invalid plugin type: {plugin_type}")

        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        # Determine plugin name
        if not plugin_name:
            plugin_name = source_dir.name

        # Get target directory based on plugin type
        target_base = self.plugin_dirs[plugin_type]

        # Handle nested plugin structures (e.g., services/iut/quic/picoquic)
        if plugin_type in [PluginType.IUT, PluginType.TESTER]:
            # Try to detect protocol from path
            protocol = self._detect_protocol_from_path(source_dir)
            if protocol:
                target_dir = target_base / protocol / plugin_name
            else:
                target_dir = target_base / plugin_name
        else:
            target_dir = target_base / plugin_name

        if target_dir.exists():
            raise FileExistsError(f"Plugin already exists: {target_dir}")

        # Copy plugin files
        self.copy_plugin_files(source_dir, target_dir)
        self.logger.info(f"Added {plugin_type.value} plugin: {plugin_name}")

    def remove_plugin(
        self, plugin_type: PluginType, plugin_name: str, protocol: Optional[str] = None
    ) -> None:
        """Remove a plugin of any type.

        Args:
            plugin_type: Type of plugin to remove
            plugin_name: Name of the plugin to remove
            protocol: Optional protocol for service plugins

        Raises:
            ValueError: If plugin type is invalid
            FileNotFoundError: If plugin doesn't exist
        """
        if plugin_type not in self.plugin_dirs:
            raise ValueError(f"Invalid plugin type: {plugin_type}")

        # Get target directory
        target_base = self.plugin_dirs[plugin_type]

        # Handle nested structures
        if plugin_type in [PluginType.IUT, PluginType.TESTER] and protocol:
            target_dir = target_base / protocol / plugin_name
        else:
            target_dir = target_base / plugin_name

        if not target_dir.exists():
            raise FileNotFoundError(f"Plugin not found: {target_dir}")

        # Remove plugin directory
        shutil.rmtree(target_dir)
        self.logger.info(f"Removed {plugin_type.value} plugin: {plugin_name}")

    def copy_plugin_files(self, source_dir: Path, target_dir: Path) -> None:
        """Copy plugin files with proper error handling.

        Args:
            source_dir: Source directory to copy from
            target_dir: Target directory to copy to

        Raises:
            IOError: If copy operation fails
        """
        try:
            # Create parent directories if needed
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # Copy the entire directory tree
            shutil.copytree(source_dir, target_dir)

            self.logger.debug(f"Copied plugin files from {source_dir} to {target_dir}")

        except Exception as e:
            self.logger.error(f"Failed to copy plugin files: {e}")
            # Clean up partial copy
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise IOError(f"Failed to copy plugin files: {e}")

    def _detect_protocol_from_path(self, source_dir: Path) -> Optional[str]:
        """Detect protocol from plugin path structure.

        Args:
            source_dir: Source directory path

        Returns:
            Protocol name if detected, None otherwise
        """
        # Common protocol names
        protocols = ["quic", "tcp", "udp", "http", "minip"]

        # Check if any protocol name appears in the path
        path_parts = source_dir.parts
        for protocol in protocols:
            if protocol in path_parts:
                return protocol

        # Check parent directory name
        if source_dir.parent.name in protocols:
            return source_dir.parent.name

        return None

    def list_plugins(self, plugin_type: PluginType) -> list[str]:
        """List all plugins of a given type.

        Args:
            plugin_type: Type of plugins to list

        Returns:
            List of plugin names
        """
        if plugin_type not in self.plugin_dirs:
            return []

        plugin_dir = self.plugin_dirs[plugin_type]
        if not plugin_dir.exists():
            return []

        plugins = []

        # Handle nested structures
        if plugin_type in [PluginType.IUT, PluginType.TESTER]:
            # Look for protocol directories first
            for protocol_dir in plugin_dir.iterdir():
                if protocol_dir.is_dir() and not protocol_dir.name.startswith("_"):
                    # Look for plugin directories within protocol
                    for plugin_dir in protocol_dir.iterdir():
                        if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                            plugins.append(f"{protocol_dir.name}/{plugin_dir.name}")
        else:
            # Simple structure
            for plugin_dir in plugin_dir.iterdir():
                if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                    plugins.append(plugin_dir.name)

        return sorted(plugins)

    def plugin_exists(
        self, plugin_type: PluginType, plugin_name: str, protocol: Optional[str] = None
    ) -> bool:
        """Check if a plugin exists.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of the plugin
            protocol: Optional protocol for service plugins

        Returns:
            True if plugin exists, False otherwise
        """
        if plugin_type not in self.plugin_dirs:
            return False

        target_base = self.plugin_dirs[plugin_type]

        if plugin_type in [PluginType.IUT, PluginType.TESTER] and protocol:
            target_dir = target_base / protocol / plugin_name
        else:
            target_dir = target_base / plugin_name

        return target_dir.exists()
