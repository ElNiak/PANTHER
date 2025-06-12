import logging
import os
from importlib.metadata import entry_points
from pathlib import Path

from omegaconf import OmegaConf
from panther.core.utils.docker_builder import DockerBuilder
from panther.config.config_global_schema import GlobalConfig


class PluginLoader:
    """
    PluginLoader is responsible for discovering, registering, and building Docker images for protocol, environment, and tester plugins.

    This class supports both file-based (legacy) plugin discovery and entry points-based plugin discovery.

    Attributes:
        logger (logging.Logger): Logger instance for the PluginLoader.
        plugins_base_dir (Path): Base directory for plugins.
        plugins_optional_dir (Optional[Path]): Optional directory for additional plugins.
        docker_builder (DockerBuilder): Instance of DockerBuilder for building Docker images.
        built_images (Dict[str, str]): Dictionary mapping implementation names to Docker image tags.
        protocol_plugins (Dict[str, Path]): Dictionary mapping protocol plugin names to their paths.
        environment_plugins (Dict[str, Path]): Dictionary mapping environment plugin names to their paths.
        tester_plugins (Dict[str, Path]): Dictionary mapping tester plugin names to their paths.
        dockerfiles (Dict[str, Path]): Dictionary mapping implementation names to Dockerfile paths.
    """

    def __init__(
        self,
        plugins_base_dir: str = "plugins",
        plugins_optional_dir: str | None = None,
        global_config: GlobalConfig | None = None,
    ):
        self.logger = logging.getLogger("PluginLoader")

        self.plugins_base_dir = Path(plugins_base_dir)
        # Support for optional plugins
        self.plugins_optional_dir = Path(plugins_optional_dir) if plugins_optional_dir else None
        try:
            self.docker_builder = DockerBuilder()
        except Exception as e:
            self.logger.warning("Failed to initialize DockerBuilder: %s", e)
            self.docker_builder = None

        self.global_config = global_config

        # Event system integration - initialize with default values
        # These will be set by ExperimentManager after creation
        self.event_manager = None
        self.event_emitter = None

        # Initialize logger with class name
        self.logger = logging.getLogger("PluginLoader")

        # Dictionaries to store plugins
        self.built_images = {}
        self.protocol_plugins = {}
        self.environment_plugins = {}
        self.tester_plugins = {}
        self.service_plugins = {}
        self.dockerfiles = {}

    @staticmethod
    def get_class_name(plugin_name, suffix="Config"):
        """
        Generates a class name by capitalizing parts of the plugin name and appending a suffix.

        Args:
            plugin_name (str): The name of the plugin, with parts separated by underscores.
            suffix (str, optional): The suffix to append to the generated class name. Defaults to "Config".

        Returns:
            str: The generated class name.
        """
        class_name_parts = plugin_name.split("_")
        class_name_parts = [part.capitalize() for part in class_name_parts]
        class_name = "".join(class_name_parts) + suffix
        return class_name

    def build_docker_image(self, impl_name: str, versions: str):
        """
        Build a Docker image for the specified implementation and version.
        Args:
            impl_name (str): The name of the implementation for which the Docker image is to be built.
            versions (str): The version information for the implementation. This should include attributes like 'version', 'commit', and 'dependencies'.
        Returns:
            None
        Logs:
            - Debug: When a configuration for the implementation is found.
            - Error: If the Docker image build fails or if the Dockerfile for the implementation is not found.
        Side Effects:
            - Updates the `built_images` dictionary with the new image tag if the build is successful.
            - Exits the program with status code 1 if the Dockerfile is not found.
        """
        if impl_name in self.dockerfiles:
            dockerfile_path = self.dockerfiles[impl_name]
            # Load version-specific configurations from panther.config.yaml
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
                tag_version="latest",  # or use version if desired
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
            raise FileNotFoundError(
                f"Dockerfile not found for implementation '{impl_name}'. Please ensure the Dockerfile exists in the expected path."
            )

    def build_docker_image_from_path(self, path: Path, name: str, version: str | None = None):
        """
        Builds a Docker image from the specified path.
        This method builds a Docker image using the Dockerfile located at the given path.
        It also loads version-specific configurations from `panther.config.yaml` and tags
        the built image with the specified version or "latest" if no version is provided.
        Args:
            path (Path): The path to the Dockerfile.
            name (str): The name of the implementation.
            version (str | None, optional): The version of the implementation. Defaults to None.
        Returns:
            str: The tag of the built Docker image if successful, otherwise None.
        """

        self.logger.info("Building image from path '%s'", path)
        dockerfile_path = path.resolve()
        # Load version-specific configurations from panther.config.yaml
        versions = {
            version: {
                # TODO: define version-specific configurations here
            }
        }
        self.logger.debug("Found configuration for path '%s': %s", path.name, versions)
        for version, version_config in versions.items():
            self.logger.info("Building image for path '%s' version '%s'", path.name, version)
            image_tag = self.docker_builder.build_image(
                impl_name=name,
                version=version,
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent.resolve(),
                config=version_config,
                tag_version="latest",  # TODO or use version if desired
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
                    f"Image build failed for implementation '{path.name}' version '{version}'. Please check the logs for details."
                )
            return image_tag

    def get_implementations_for_protocol(self, protocol: str) -> list[str]:
        """
        Retrieves a list of implementation directories for a given protocol.
        This method searches for directories within the 'services/iut/<protocol>'
        path that represent different implementations of the specified protocol.
        It excludes directories that start with '__' or are named 'templates'.
        Args:
            protocol (str): The name of the protocol for which to find implementations.
        Returns:
            list[str]: A list of directory names representing implementations of the protocol.
        """
        implementations = []
        implementations_dir = Path(os.path.dirname(__file__)) / "services" / "iut" / protocol
        self.logger.debug("Checking for implementations in '%s'", implementations_dir)
        if implementations_dir and implementations_dir.exists():
            for item in implementations_dir.iterdir():
                if item.is_dir() and not item.name.startswith("__") and item.name != "templates":
                    self.logger.debug("Found implementation '%s' at '%s'", item.name, item)
                    implementations.append(item.name)
                    if (item / "Dockerfile").exists():
                        self.dockerfiles[item.name] = item / "Dockerfile"
                        self.logger.debug(
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
        """
        Scans the 'services/testers' directory for subdirectories that represent testers.
        This method iterates through the 'services/testers' directory, checking each item.
        It collects the names of all subdirectories that do not start with '__' and are not named 'templates'.
        The collected names are considered as testers.
        Returns:
            list[str]: A list of tester names found in the 'services/testers' directory.
        """

        implementations = []
        implementations_dir = Path(os.path.dirname(__file__)) / "services" / "testers"
        self.logger.debug("Checking for testers in '%s'", implementations_dir)
        for item in implementations_dir.iterdir():
            self.logger.debug("Checking item '%s'", item)
            if item.is_dir() and not item.name.startswith("__") and item.name != "templates":
                implementations.append(item.name)
                if (item / "Dockerfile").exists():
                    self.dockerfiles[item.name] = item / "Dockerfile"
                    self.logger.debug(
                        "Registered Dockerfile for tester '%s' at '%s'",
                        item.name,
                        item / "Dockerfile",
                    )
        self.logger.debug("Found testers: %s", implementations)
        return implementations

    def discover_entry_point_plugins(self) -> None:
        """
        Discovers plugins registered via entry points.
        This is the modern way to discover plugins and should be preferred over file-based discovery.
        """
        self.logger.info("Discovering plugins via entry points...")

        # Discover protocol plugins
        try:
            protocol_eps = entry_points(group="panther.plugins.protocols")
            for ep in protocol_eps:
                self.logger.info("Found protocol plugin: %s", ep.name)
                try:
                    # We don't load the plugin here, just register its existence
                    plugin_path = Path(ep.value.split(":")[0].replace(".", "/"))
                    self.protocol_plugins[ep.name] = plugin_path
                    self.logger.debug(
                        "Registered protocol plugin '%s' with path '%s'", ep.name, plugin_path
                    )
                    # If the plugin has a Dockerfile, register it
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
                    # If the plugin has a Dockerfile, register it
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
                    # If the plugin has a Dockerfile, register it
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

    def load_plugins(self) -> None:
        """
        Discovers and registers all protocol, environment, and tester plugins.
        Uses both entry points-based discovery (preferred) and file-based discovery (for backward compatibility).
        """
        self.logger.info("Loading plugins...")

        # First try entry points-based discovery (modern approach)
        self.discover_entry_point_plugins()

        # Then fall back to file-based discovery (legacy approach)
        self._legacy_file_based_plugin_discovery()

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
                        self.tester_plugins[testers.name] = item
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
