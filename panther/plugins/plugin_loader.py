"""
Updated PluginLoader that integrates with the new PluginCatalog system.

This version maintains backward compatibility while adding catalog-based discovery.
"""

import logging
import os
from importlib.metadata import entry_points
from pathlib import Path

from omegaconf import OmegaConf
from panther.core.utils.docker_builder import DockerBuilder
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginType


class PluginLoader:
    """
    Enhanced PluginLoader that uses the new PluginCatalog system while maintaining
    backward compatibility with the existing file-based and entry points discovery.

    This loader now integrates with:
    - PluginCatalog for manifest-based discovery
    - Legacy file-based discovery
    - Entry points discovery
    """

    def __init__(
        self,
        plugins_base_dir: str = "plugins",
        plugins_optional_dir: str | None = None,
        global_config: GlobalConfig | None = None,
    ):
        self.logger = logging.getLogger("PluginLoader")

        self.plugins_base_dir = Path(plugins_base_dir)
        self.plugins_optional_dir = Path(plugins_optional_dir) if plugins_optional_dir else None

        # Initialize plugin catalog with discovery paths
        discovery_paths = [str(self.plugins_base_dir)]
        if self.plugins_optional_dir:
            discovery_paths.append(str(self.plugins_optional_dir))

        self.plugin_catalog = PluginCatalog(discovery_paths)

        # Docker builder for image management
        try:
            self.docker_builder = DockerBuilder(
                build_log_file=global_config.docker.log_docker_image_build
            )
        except Exception as e:
            self.logger.warning("Failed to initialize DockerBuilder: %s", e)
            self.docker_builder = None

        self.global_config = global_config

        # Event system integration
        self.event_manager = None
        self.event_emitter = None

        # Dictionaries to store plugins (backward compatibility)
        self.built_images = {}
        self.protocol_plugins = {}
        self.environment_plugins = {}
        self.tester_plugins = {}
        self.service_plugins = {}
        self.dockerfiles = {}

        # Load plugins on initialization
        self.load_plugins()

    def load_plugins(self) -> None:
        """
        Discovers and registers all plugins using multiple methods:
        1. Catalog-based discovery (preferred)
        2. Entry points-based discovery
        3. File-based discovery (legacy)
        """
        self.logger.info("Loading plugins...")

        # First, use catalog-based discovery
        self._catalog_based_plugin_discovery()

        # Then try entry points-based discovery
        self.discover_entry_point_plugins()

        # Finally, fall back to file-based discovery
        self._legacy_file_based_plugin_discovery()

        self.logger.info(
            "Plugin discovery complete. Found %d plugins in catalog.",
            len(self.plugin_catalog.catalog),
        )

    def _catalog_based_plugin_discovery(self) -> None:
        """
        Discover plugins using the new catalog system with manifest files.
        """
        self.logger.info("Discovering plugins via catalog system...")

        # Scan for plugins with manifests
        plugins = self.plugin_catalog.scan_plugins(use_cache=False)

        for plugin_id, manifest in plugins.items():
            plugin_path = Path(manifest.file_path).parent

            # Map to legacy dictionaries for backward compatibility
            if manifest.type == PluginType.PROTOCOL:
                self.protocol_plugins[manifest.name] = plugin_path
                self.logger.debug(
                    "Registered protocol plugin '%s' from manifest at '%s'",
                    manifest.name,
                    plugin_path,
                )

            elif manifest.type == PluginType.ENVIRONMENT:
                # Determine if it's network or execution environment
                if "network" in str(plugin_path):
                    key = f"network_{manifest.name}"
                else:
                    key = f"execution_{manifest.name}"
                self.environment_plugins[key] = plugin_path
                self.logger.debug(
                    "Registered environment plugin '%s' from manifest at '%s'", key, plugin_path
                )

            elif manifest.type == PluginType.TESTER:
                self.tester_plugins[manifest.name] = plugin_path
                self.logger.debug(
                    "Registered tester plugin '%s' from manifest at '%s'",
                    manifest.name,
                    plugin_path,
                )

            elif manifest.type in [PluginType.SERVICE, PluginType.IUT]:
                self.service_plugins[manifest.name] = plugin_path
                self.logger.debug(
                    "Registered service plugin '%s' from manifest at '%s'",
                    manifest.name,
                    plugin_path,
                )

            # Register Dockerfile if it exists
            dockerfile_path = plugin_path / "Dockerfile"
            if dockerfile_path.exists():
                self.dockerfiles[manifest.name] = dockerfile_path
                self.logger.debug(
                    "Registered Dockerfile for plugin '%s' at '%s'", manifest.name, dockerfile_path
                )

    def get_plugin_manifest(self, plugin_name: str, plugin_type: str | None = None):
        """
        Get the manifest for a specific plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_type: Optional type hint to disambiguate

        Returns:
            PluginManifest if found, None otherwise
        """
        # Try with type hint first
        if plugin_type:
            plugin_id = f"{plugin_type}:{plugin_name}"
            if plugin_id in self.plugin_catalog.catalog:
                return self.plugin_catalog.catalog[plugin_id]

        # Search without type
        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            if manifest.name == plugin_name:
                return manifest

        return None

    def validate_plugin_dependencies(self, plugin_name: str) -> tuple[bool, list[str]]:
        """
        Validate that all dependencies for a plugin are satisfied.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            Tuple of (is_valid, list_of_missing_dependencies)
        """
        manifest = self.get_plugin_manifest(plugin_name)
        if not manifest:
            return False, [f"Plugin '{plugin_name}' not found"]

        # Find the plugin ID
        plugin_id = None
        for pid, m in self.plugin_catalog.catalog.items():
            if m.name == plugin_name:
                plugin_id = pid
                break

        if not plugin_id:
            return False, [f"Plugin ID not found for '{plugin_name}'"]

        # Use catalog's dependency resolution
        _, missing = self.plugin_catalog.resolve_dependencies([plugin_id])

        return len(missing) == 0, missing

    def get_plugin_version(self, plugin_name: str) -> str | None:
        """
        Get the version of a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Version string if found, None otherwise
        """
        manifest = self.get_plugin_manifest(plugin_name)
        return manifest.version if manifest else None

    def list_available_plugins(self) -> dict[str, list[dict[str, str]]]:
        """
        List all available plugins grouped by type.

        Returns:
            Dictionary mapping plugin types to lists of plugin info
        """
        plugins_by_type = {}

        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            plugin_type = manifest.type.value
            if plugin_type not in plugins_by_type:
                plugins_by_type[plugin_type] = []

            plugins_by_type[plugin_type].append(
                {
                    "name": manifest.name,
                    "version": manifest.version,
                    "description": manifest.description,
                    "author": manifest.author,
                }
            )

        return plugins_by_type

    # Keep all existing methods for backward compatibility
    @staticmethod
    def get_class_name(plugin_name, suffix="Config"):
        """Keep for backward compatibility."""
        class_name_parts = plugin_name.split("_")
        class_name_parts = [part.capitalize() for part in class_name_parts]
        class_name = "".join(class_name_parts) + suffix
        return class_name

    def build_docker_image(self, impl_name: str, versions: str):
        """Keep existing docker build logic."""
        self.logger.debug(
            "Looking for Dockerfile for '%s' in dockerfiles: %s",
            impl_name,
            list(self.dockerfiles.keys()),
        )

        # If not found, try to discover it from the protocol implementations
        if impl_name not in self.dockerfiles:
            # Try to find the protocol this implementation belongs to
            for protocol_dir in (Path(os.path.dirname(__file__)) / "services" / "iut").iterdir():
                if protocol_dir.is_dir():
                    impl_dir = protocol_dir / impl_name
                    if impl_dir.exists() and (impl_dir / "Dockerfile").exists():
                        self.dockerfiles[impl_name] = impl_dir / "Dockerfile"
                        self.logger.info(
                            "Discovered Dockerfile for '%s' at '%s'",
                            impl_name,
                            impl_dir / "Dockerfile",
                        )
                        break

        if impl_name in self.dockerfiles:
            dockerfile_path = self.dockerfiles[impl_name]
            self.logger.debug(
                "Found configuration for implementation '%s': %s", impl_name, versions
            )
            image_tag = self.docker_builder.build_image(
                impl_name=impl_name,
                version=("unknown" if not hasattr(versions, "version") else versions.version),
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent,
                config=(
                    {}
                    if not hasattr(versions, "version")
                    else {
                        "commit": versions.commit,
                        "dependencies": OmegaConf.to_container(versions.dependencies),
                    }
                ),
                tag_version="latest",
                build_image_force=(
                    self.global_config.docker.build_docker_image if self.global_config else True
                ),
                remove_dangling=(
                    self.global_config.docker.remove_dangling_images if self.global_config else True
                ),
            )
            if image_tag:
                key = f"{impl_name}_{versions}"
                self.built_images[key] = image_tag
            else:
                self.logger.error(
                    "Image build failed for implementation '%s' version '%s'", impl_name, versions
                )
        else:
            self.logger.error(
                "Dockerfile not found for implementation '%s' in %s. Skipping.",
                impl_name,
                self.dockerfiles,
            )
            raise FileNotFoundError(f"Dockerfile not found for implementation '{impl_name}'.")

    def build_docker_image_from_path(self, path: Path, name: str, version: str | None = None):
        """Keep existing docker build from path logic."""
        self.logger.info("Building image from path '%s'", path)
        dockerfile_path = path.resolve()
        versions = {version: {}}
        self.logger.debug("Found configuration for path '%s': %s", path.name, versions)
        for version, version_config in versions.items():
            self.logger.info("Building image for path '%s' version '%s'", path.name, version)
            image_tag = self.docker_builder.build_image(
                impl_name=name,
                version=version,
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent.resolve(),
                config=version_config,
                tag_version="latest",
                build_image_force=(
                    self.global_config.docker.build_docker_image if self.global_config else True
                ),
                remove_dangling=(
                    self.global_config.docker.remove_dangling_images if self.global_config else True
                ),
            )
            if image_tag:
                key = f"{path.name}_{version}"
                self.built_images[key] = image_tag
            else:
                self.logger.error(
                    "Image build failed for implementation '%s' version '%s'", path.name, version
                )
                raise RuntimeError(
                    f"Image build failed for implementation '{path.name}' version '{version}'."
                )
            return image_tag

    def get_implementations_for_protocol(self, protocol: str) -> list[str]:
        """Enhanced version that uses catalog when possible."""
        self.logger.debug("Getting implementations for protocol: %s", protocol)
        implementations = []

        # First check catalog
        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            if manifest.type == PluginType.IUT and protocol in manifest.supported_protocols:
                implementations.append(manifest.name)

        # If no results from catalog, fall back to file-based discovery
        if not implementations:
            implementations_dir = Path(os.path.dirname(__file__)) / "services" / "iut" / protocol
            self.logger.debug("Checking for implementations in '%s'", implementations_dir)
            if implementations_dir and implementations_dir.exists():
                self.logger.info("Scanning implementations directory: %s", implementations_dir)
                for item in implementations_dir.iterdir():
                    if (
                        item.is_dir()
                        and not item.name.startswith("__")
                        and item.name != "templates"
                    ):
                        self.logger.info("Found implementation '%s' at '%s'", item.name, item)
                        implementations.append(item.name)
                        if (item / "Dockerfile").exists():
                            self.dockerfiles[item.name] = item / "Dockerfile"
                            self.logger.info(
                                "Registered Dockerfile for protocol '%s' implementation '%s' at '%s'",
                                protocol,
                                item.name,
                                item / "Dockerfile",
                            )
                self.logger.debug(
                    "Found implementations for protocol '%s': %s", protocol, implementations
                )
            else:
                self.logger.warning("Protocol plugin '%s' not found or does not exist.", protocol)

        return implementations

    def get_testers(self) -> list[str]:
        """Enhanced version that uses catalog when possible."""
        testers = []

        # First check catalog
        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            if manifest.type == PluginType.TESTER:
                testers.append(manifest.name)

        # If no results from catalog, fall back to file-based discovery
        if not testers:
            implementations_dir = Path(os.path.dirname(__file__)) / "services" / "testers"
            self.logger.debug("Checking for testers in '%s'", implementations_dir)
            for item in implementations_dir.iterdir():
                self.logger.debug("Checking item '%s'", item)
                if item.is_dir() and not item.name.startswith("__") and item.name != "templates":
                    testers.append(item.name)
                    if (item / "Dockerfile").exists():
                        self.dockerfiles[item.name] = item / "Dockerfile"
                        self.logger.debug(
                            "Registered Dockerfile for tester '%s' at '%s'",
                            item.name,
                            item / "Dockerfile",
                        )
            self.logger.debug("Found testers: %s", testers)

        return testers

    def discover_entry_point_plugins(self) -> None:
        """Keep existing entry point discovery."""
        self.logger.info("Discovering plugins via entry points...")

        # Discover protocol plugins
        try:
            protocol_eps = entry_points(group="panther.plugins.protocols")
            for ep in protocol_eps:
                self.logger.info("Found protocol plugin: %s", ep.name)
                try:
                    plugin_path = Path(ep.value.split(":")[0].replace(".", "/"))
                    self.protocol_plugins[ep.name] = plugin_path
                    self.logger.debug(
                        "Registered protocol plugin '%s' with path '%s'", ep.name, plugin_path
                    )
                    dockerfile_path = plugin_path / "Dockerfile"
                    if dockerfile_path.exists():
                        self.dockerfiles[ep.name] = dockerfile_path
                        self.logger.debug(
                            "Registered Dockerfile for protocol plugin '%s' at '%s'",
                            ep.name,
                            dockerfile_path,
                        )
                except Exception as e:
                    self.logger.warning("Failed to register protocol plugin %s: %s", ep.name, e)
        except Exception as e:
            self.logger.warning("Error discovering protocol plugins: %s", e)

        # Discover execution environment plugins
        try:
            exec_env_eps = entry_points(group="panther.plugins.environments.execution")
            for ep in exec_env_eps:
                self.logger.info("Found execution environment plugin: %s", ep.name)
                try:
                    plugin_path = Path(ep.value.split(":")[0].replace(".", "/"))
                    self.environment_plugins[f"execution_{ep.name}"] = plugin_path
                    self.logger.debug(
                        "Registered execution environment plugin '%s' with path '%s'",
                        ep.name,
                        plugin_path,
                    )
                    dockerfile_path = plugin_path / "Dockerfile"
                    if dockerfile_path.exists():
                        self.dockerfiles[f"execution_{ep.name}"] = dockerfile_path
                        self.logger.debug(
                            "Registered Dockerfile for execution environment plugin '%s' at '%s'",
                            ep.name,
                            dockerfile_path,
                        )
                except Exception as e:
                    self.logger.warning(
                        "Failed to register execution environment plugin %s: %s", ep.name, e
                    )
        except Exception as e:
            self.logger.warning("Error discovering execution environment plugins: %s", e)

        # Discover network environment plugins
        try:
            net_env_eps = entry_points(group="panther.plugins.environments.network")
            for ep in net_env_eps:
                self.logger.info("Found network environment plugin: %s", ep.name)
                try:
                    plugin_path = Path(ep.value.split(":")[0].replace(".", "/"))
                    self.environment_plugins[f"network_{ep.name}"] = plugin_path
                    self.logger.debug(
                        "Registered network environment plugin '%s' with path '%s'",
                        ep.name,
                        plugin_path,
                    )
                    dockerfile_path = plugin_path / "Dockerfile"
                    if dockerfile_path.exists():
                        self.dockerfiles[f"network_{ep.name}"] = dockerfile_path
                        self.logger.debug(
                            "Registered Dockerfile for network environment plugin '%s' at '%s'",
                            ep.name,
                            dockerfile_path,
                        )
                except Exception as e:
                    self.logger.warning(
                        "Failed to register network environment plugin %s: %s", ep.name, e
                    )
        except Exception as e:
            self.logger.warning("Error discovering network environment plugins: %s", e)

    def _legacy_file_based_plugin_discovery(self) -> None:
        """Legacy file-based plugin discovery method for backward compatibility."""
        self.logger.debug("Loading plugins from base directory '%s'", self.plugins_base_dir)

        # Discover protocol plugins
        protocols_dir = Path(os.path.dirname(__file__)) / "services" / "iut"
        for protocol in protocols_dir.iterdir():
            self.logger.debug("Checking protocol plugin '%s'", protocol)
            if protocol.is_dir() and not protocol.name.startswith("__"):
                if (protocol / f"{protocol.name}.py").exists():
                    self.protocol_plugins[protocol.name] = protocol
                    self.logger.debug(
                        "Discovered protocol plugin '%s' at '%s'", protocol.name, protocol
                    )

        # Discover environment plugins
        environments_dir = Path(os.path.dirname(__file__)) / "environments"
        if environments_dir.exists() and environments_dir.is_dir():
            self.logger.debug("Checking environments directory '%s'", environments_dir)
            for environment in environments_dir.iterdir():
                if environment.is_dir():
                    self.environment_plugins[environment.name] = {}
                    for item in environment.iterdir():
                        if item.is_dir() and not item.name.startswith("__"):
                            if (item / f"{item.name}.py").exists():
                                self.environment_plugins[environment.name][item.name] = item
                                self.logger.debug(
                                    "Discovered environment plugin '%s' at '%s' under '%s'",
                                    item.name,
                                    item,
                                    environment,
                                )
        else:
            self.logger.warning("Environments directory '%s' does not exist.", environments_dir)

        # Discover testers plugins
        testers_dir = Path(os.path.dirname(__file__)) / "services" / "testers"
        if testers_dir.exists() and testers_dir.is_dir():
            self.logger.debug("Checking testers directory '%s'", testers_dir)
            for testers in testers_dir.iterdir():
                if testers.is_dir() and not testers.name.startswith("__"):
                    if (testers / f"{testers.name}.py").exists():
                        self.tester_plugins[testers.name] = testers
                        self.logger.debug(
                            "Discovered testers plugin '%s' at '%s'", testers.name, testers
                        )
                        if (testers / "Dockerfile").exists():
                            self.dockerfiles[testers.name] = testers / "Dockerfile"
                            self.logger.debug(
                                "Registered Dockerfile for testers plugin '%s' at '%s'",
                                testers.name,
                                testers / "Dockerfile",
                            )
        else:
            self.logger.warning("Testers directory '%s' does not exist.", testers_dir)
