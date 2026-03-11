"""Version Configuration Loader.

This module provides automatic version configuration loading for plugins
based on protocol-defined versions. It discovers and loads YAML configuration
files from version_configs/ directories.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from panther.plugins.core.plugin_decorators import (
    get_protocol_versions,
    register_version_config,
)


class VersionLoader:
    """Handles automatic discovery and loading of version configurations.

    This class:
    - Discovers version configuration files in plugin directories
    - Validates versions against protocol-defined versions
    - Loads and caches version configurations
    - Registers configurations with the plugin decorator system
    """

    def __init__(self):  # noqa: D107
        self.logger = logging.getLogger("VersionLoader")
        self._cache: Dict[str, Dict[str, Any]] = {}

    def discover_and_load_versions(
        self, plugin_name: str, plugin_path: Path, protocol_name: str
    ) -> Dict[str, Any]:
        """Discover and load version configurations for a plugin.

        Args:
            plugin_name: Name of the plugin (e.g., "picoquic")
            plugin_path: Path to the plugin directory
            protocol_name: Name of the protocol (e.g., "quic")

        Returns:
            Dictionary mapping version names to configurations
        """
        # Check cache first
        cache_key = f"{plugin_name}:{protocol_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get protocol-defined versions
        protocol_versions = get_protocol_versions(protocol_name)
        if not protocol_versions:
            self.logger.warning(
                f"No protocol versions found for {protocol_name}. "
                f"Make sure the protocol plugin is registered."
            )
            # Fall back to discovering versions from files
            protocol_versions = None

        # Look for version_configs directory
        version_configs_dir = plugin_path / "version_configs"
        if not version_configs_dir.exists():
            self.logger.debug(
                f"No version_configs directory found for {plugin_name} at {version_configs_dir}"
            )
            return {}

        # Load version configurations
        loaded_versions = {}

        # First, try loading from the root version_configs directory
        for config_file in version_configs_dir.glob("*.yaml"):
            version_name = config_file.stem

            # Validate against protocol versions if available
            if protocol_versions and version_name not in protocol_versions:
                self.logger.warning(
                    f"Version {version_name} found for {plugin_name} but not defined "
                    f"in protocol {protocol_name}. Available versions: {protocol_versions}"
                )
                # Still load it but warn

            try:
                config = self._load_version_file(config_file)
                if config:
                    loaded_versions[version_name] = config
                    # Register with decorator system
                    register_version_config(plugin_name, version_name, config)
                    self.logger.debug(
                        f"Loaded version {version_name} for {plugin_name} from {config_file}"
                    )
            except Exception as e:
                self.logger.error(f"Failed to load version config {config_file}: {e}")

        # Also check for .yml files
        for config_file in version_configs_dir.glob("*.yml"):
            version_name = config_file.stem
            if version_name not in loaded_versions:  # Don't reload if .yaml exists
                if protocol_versions and version_name not in protocol_versions:
                    self.logger.warning(
                        f"Version {version_name} found for {plugin_name} but not defined "
                        f"in protocol {protocol_name}"
                    )

                try:
                    config = self._load_version_file(config_file)
                    if config:
                        loaded_versions[version_name] = config
                        register_version_config(plugin_name, version_name, config)
                        self.logger.debug(
                            f"Loaded version {version_name} for {plugin_name} from {config_file}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to load version config {config_file}: {e}"
                    )

        # Check for protocol-specific subdirectories (e.g., version_configs/quic/)
        if protocol_name:
            protocol_dir = version_configs_dir / protocol_name
            if protocol_dir.exists() and protocol_dir.is_dir():
                self.logger.debug(
                    f"Found protocol-specific version directory: {protocol_dir}"
                )

                # Load YAML files from protocol subdirectory
                for config_file in protocol_dir.glob("*.yaml"):
                    version_name = config_file.stem

                    if (
                        version_name not in loaded_versions
                    ):  # Don't override root configs
                        if protocol_versions and version_name not in protocol_versions:
                            self.logger.warning(
                                f"Version {version_name} found for {plugin_name} but not defined "
                                f"in protocol {protocol_name}. Available versions: {protocol_versions}"
                            )

                        try:
                            config = self._load_version_file(config_file)
                            if config:
                                loaded_versions[version_name] = config
                                register_version_config(
                                    plugin_name, version_name, config
                                )
                                self.logger.debug(
                                    f"Loaded version {version_name} for {plugin_name} from {config_file}"
                                )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to load version config {config_file}: {e}"
                            )

                # Also check for .yml files
                for config_file in protocol_dir.glob("*.yml"):
                    version_name = config_file.stem
                    if version_name not in loaded_versions:
                        if protocol_versions and version_name not in protocol_versions:
                            self.logger.warning(
                                f"Version {version_name} found for {plugin_name} but not defined "
                                f"in protocol {protocol_name}"
                            )

                        try:
                            config = self._load_version_file(config_file)
                            if config:
                                loaded_versions[version_name] = config
                                register_version_config(
                                    plugin_name, version_name, config
                                )
                                self.logger.debug(
                                    f"Loaded version {version_name} for {plugin_name} from {config_file}"
                                )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to load version config {config_file}: {e}"
                            )

        # Log summary
        if loaded_versions:
            self.logger.info(
                f"Loaded {len(loaded_versions)} version configurations for {plugin_name}: "
                f"{list(loaded_versions.keys())}"
            )
        else:
            self.logger.warning(
                f"No version configurations found for {plugin_name} in {version_configs_dir}"
            )

        # Cache the results
        self._cache[cache_key] = loaded_versions

        return loaded_versions

    def _load_version_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load a version configuration file.

        Args:
            file_path: Path to the YAML configuration file

        Returns:
            Loaded configuration dictionary or None if failed
        """
        try:
            with open(file_path, "r") as f:
                config = yaml.safe_load(f)

            # Validate basic structure
            if not isinstance(config, dict):
                self.logger.error(
                    f"Invalid version config format in {file_path}: expected dictionary"
                )
                return None

            # Ensure version field matches filename
            file_version = file_path.stem
            if "version" in config and config["version"] != file_version:
                self.logger.warning(
                    f"Version mismatch in {file_path}: "
                    f"file name '{file_version}' vs config '{config['version']}'"
                )
                # Use filename as authoritative
                config["version"] = file_version

            return config

        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return None

    def get_available_versions(self, plugin_name: str, protocol_name: str) -> List[str]:
        """Get list of available versions for a plugin.

        This combines protocol-defined versions with discovered versions.

        Args:
            plugin_name: Name of the plugin
            protocol_name: Name of the protocol

        Returns:
            List of available version names
        """
        # Get protocol versions
        protocol_versions = set(get_protocol_versions(protocol_name))

        # Get cached loaded versions
        cache_key = f"{plugin_name}:{protocol_name}"
        if cache_key in self._cache:
            loaded_versions = set(self._cache[cache_key].keys())
        else:
            loaded_versions = set()

        # Combine both sources
        all_versions = protocol_versions | loaded_versions

        return sorted(list(all_versions))

    def clear_cache(self):
        """Clear the version configuration cache."""
        self._cache.clear()
        self.logger.debug("Cleared version configuration cache")


# Global instance for convenience
_version_loader = VersionLoader()


def discover_plugin_versions(
    plugin_name: str, plugin_path: Path, protocol_name: str
) -> Dict[str, Any]:
    """Convenience function to discover and load plugin versions.

    Args:
        plugin_name: Name of the plugin
        plugin_path: Path to the plugin directory
        protocol_name: Name of the protocol

    Returns:
        Dictionary mapping version names to configurations
    """
    return _version_loader.discover_and_load_versions(
        plugin_name, plugin_path, protocol_name
    )
