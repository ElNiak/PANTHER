"""Configuration management module for PANTHER framework.

This module handles loading, validating, and managing configurations for experiments
and plugins in the PANTHER framework.
"""

import importlib
import logging
import os
from pathlib import Path
import shutil
from contextlib import nullcontext
from dataclasses import asdict
from omegaconf import DictConfig, OmegaConf, ValidationError, ListConfig
import yaml
from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.exceptions.experiment_exceptions import PluginValidationError
from panther.config.config_global_schema import (
    AdditionalPathsConfig,
    DockerConfig,
    FeatureConfig,
    GlobalConfig,
    LoggingConfig,
    LoggingLevel,
    PathsConfig,
)
from panther.config.config_experiment_schema import (
    ExperimentConfig,
    ServiceConfig,
    TestConfig,
)
from panther.config.config_observer_schema import (
    ObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    StorageObserverConfig,
    ExperimentObserverConfig,
)
from importlib_resources import files


class ConfigLoader(LoggerMixin):
    """Handles loading and validation of PANTHER configurations."""

    @staticmethod
    def _get_class_name(plugin_name: str, suffix: str = "Config") -> str:
        """Convert plugin name to class name format."""
        class_name_parts = plugin_name.split("_")
        class_name_parts = [part.capitalize() for part in class_name_parts]
        class_name = "".join(class_name_parts) + suffix
        return class_name

    def __init__(
        self,
        experiment_file: str,
        output_dir: str | None = None,
        exec_env_dir: str | None = "",
        net_env_dir: str | None = "",
        iut_dir: str | None = "",
        testers_dir: str | None = "",
        metrics_collector=None,
        debug_override: bool = False,
    ):
        super().__init__()
        self.experiment_file = experiment_file
        self.output_dir = output_dir
        self.metrics_collector = metrics_collector

        self.exec_env_dir = exec_env_dir
        self.net_env_dir = net_env_dir
        self.iut_dir = iut_dir
        self.testers_dir = testers_dir
        self.global_config: GlobalConfig = None

        self._panther_dir = Path(os.path.dirname(__file__)).parent

        self.debug_override = debug_override

    def construct_global_config(self, loaded_config: DictConfig) -> GlobalConfig:
        """_summary_

        Args:
            loaded_config (DictConfig): _description_

        Returns:
            ExperimentConfig: _description_
        """
        # Construct logging configuration with defaults from dataclass
        default_logging = LoggingConfig()  # Get dataclass defaults
        level_str = loaded_config.get("logging", {}).get("level", default_logging.level.name)
        # Convert string to LoggingLevel enum
        if isinstance(level_str, str):
            try:
                level = LoggingLevel[level_str.upper()]
            except KeyError:
                self.logger.warning("Invalid logging level '%s', using DEBUG", level_str)
                level = LoggingLevel.DEBUG
        else:
            level = (
                level_str
                if isinstance(level_str, type(LoggingLevel.DEBUG))
                else default_logging.level
            )

        logging_config = LoggingConfig(
            level=level,
            format=loaded_config.get("logging", {}).get("format", default_logging.format),
        )
        OmegaConf.merge(LoggingConfig, logging_config)

        # Construct paths configuration with defaults from dataclass
        default_paths = PathsConfig()  # Get dataclass defaults
        paths_config = PathsConfig(
            output_dir=(
                loaded_config.get("paths", {}).get("output_dir", default_paths.output_dir)
                if not self.output_dir
                else self.output_dir
            ),
            log_dir=loaded_config.get("paths", {}).get("log_dir", default_paths.log_dir),
            config_dir=loaded_config.get("paths", {}).get("config_dir", default_paths.config_dir),
            plugin_dir=loaded_config.get("paths", {}).get("plugin_dir", default_paths.plugin_dir),
            services_dir=loaded_config.get("paths", {}).get(
                "services_dir", default_paths.services_dir
            ),
            iut_dir=loaded_config.get("paths", {}).get("iut_dir", default_paths.iut_dir),
            testers_dir=loaded_config.get("paths", {}).get(
                "testers_dir", default_paths.testers_dir
            ),
        )
        OmegaConf.merge(PathsConfig, paths_config)

        # Construct optional paths configuration
        optional_paths_config = AdditionalPathsConfig(
            exec_env_dir=self.exec_env_dir or "",
            net_env_dir=self.net_env_dir or "",
            iut_dir=self.iut_dir or "",
            testers_dir=self.testers_dir or "",
        )

        self.add_plugin_execution_environment()

        self.add_plugin_network_environment()

        self.add_plugin_iut_service()

        self.add_plugin_tester_service()

        # Construct Docker configuration with defaults from dataclass
        default_docker = DockerConfig()  # Get dataclass defaults
        docker_config = DockerConfig(
            build_docker_image=loaded_config.get("docker", {}).get(
                "build_docker_image", default_docker.build_docker_image
            ),
            log_docker_image_build=loaded_config.get("docker", {}).get(
                "log_docker_image_build", default_docker.log_docker_image_build
            ),
            remove_docker_image=loaded_config.get("docker", {}).get(
                "remove_docker_image", default_docker.remove_docker_image
            ),
            remove_docker_container=loaded_config.get("docker", {}).get(
                "remove_docker_container", default_docker.remove_docker_container
            ),
            remove_docker_network=loaded_config.get("docker", {}).get(
                "remove_docker_network", default_docker.remove_docker_network
            ),
            remove_docker_volume=loaded_config.get("docker", {}).get(
                "remove_docker_volume", default_docker.remove_docker_volume
            ),
            remove_dangling_images=loaded_config.get("docker", {}).get(
                "remove_dangling_images", default_docker.remove_dangling_images
            ),
        )
        OmegaConf.merge(DockerConfig, docker_config)

        # Construct feature configuration with defaults from dataclass
        default_features = FeatureConfig()  # Get dataclass defaults
        if "features" not in loaded_config:
            feature_config = default_features
        else:
            feature_config = FeatureConfig(
                logger_observer=(
                    loaded_config["features"]["logger_observer"]
                    if "logger_observer" in loaded_config["features"]
                    else default_features.logger_observer
                ),
                storage_handler=(
                    loaded_config["features"]["storage_handler"]
                    if "storage_handler" in loaded_config["features"]
                    else default_features.storage_handler
                ),
                fast_fail=(
                    loaded_config["features"]["fast_fail"]
                    if "fast_fail" in loaded_config["features"]
                    else default_features.fast_fail
                ),
            )
        OmegaConf.merge(FeatureConfig, feature_config)

        # Construct observer configuration with defaults
        observer_config = self.construct_observer_config(loaded_config)

        global_config = GlobalConfig(
            logging=logging_config,
            paths=paths_config,
            optional_paths=optional_paths_config,
            docker=docker_config,
            features=feature_config,
            observers=observer_config,
        )
        OmegaConf.merge(GlobalConfig, global_config)
        if self.debug_override:
            global_config.logging.level = LoggingLevel.DEBUG
        self.global_config = global_config
        return global_config

    def add_plugin_tester_service(self):
        """
        Adds a plugin tester service by copying tester files from the specified directory.

        This method checks if the `testers_dir` attribute is set and not empty. If so, it converts
        `testers_dir` to a `Path` object and constructs the target directory path for the testers.
        It then calls the `copy_plugin_files` method to copy the tester files to the target directory.

        Raises:
            Exception: If the `testers_dir` attribute is not set or is empty.
        """
        if self.testers_dir and self.testers_dir != "":
            print(f"Copying testers from {self.testers_dir}")
            self.testers_dir = Path(self.testers_dir)
            testers_target_dir = os.path.join(
                self._panther_dir,
                "plugins",
                "services",
                "testers",
                self.testers_dir.name,
            )
            self.copy_plugin_files(self.testers_dir, testers_target_dir)

    def copy_plugin_files(self, source_dir, target_dir):
        """
        Copies plugin files from the source directory to the target directory.

        This method checks if the target directory exists, and if not, it creates it.
        It then iterates through all items in the source directory,
        and copies each item to the target directory. If an item is a directory, it
        recursively copies the entire directory. If an item is a file, it copies the file.

        Parameters:
        source_dir (str): The path to the source directory containing plugin files
        target_dir (str): The path to the target directory where plugin files
                      should be copied.

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        # Check if source directory exists before attempting to copy
        if not os.path.exists(source_dir):
            self.logger.warning("Source directory %s does not exist, skipping copy", source_dir)
            return

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        for item in os.listdir(source_dir):
            print(f"Copying {item} from {source_dir} to {target_dir}")
            s = os.path.join(source_dir, item)
            d = os.path.join(target_dir, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

    def remove_plugin_tester_service(self):
        """
        Removes the plugin tester service directory if it exists.

        This method checks if the `testers_dir` attribute is set and not empty.
        If so, it constructs the path to the target directory within the
        "panther/plugins/services/testers" directory. If the target directory
        exists, it removes the directory and all its contents.

        Attributes:
            testers_dir (str): The directory path of the testers to be removed.

        Side Effects:
            Deletes the directory specified by `testers_dir` and all its contents.

        Prints:
            A message indicating the removal of the testers directory.
        """
        if self.testers_dir and self.testers_dir != "":
            testers_target_dir = os.path.join(
                self._panther_dir,
                "plugins",
                "services",
                "testers",
                Path(self.testers_dir).name,
            )
            if os.path.exists(testers_target_dir):
                print(f"Removing testers from {testers_target_dir}")
                shutil.rmtree(testers_target_dir)

    def add_plugin_iut_service(self):
        """
        Add the plugin IUTs service directory defined by "iut_dir" inside the application
        at panther/plugins/services/iut/{iut_dir}

        Parameters:
        testers_iut_dir (str): The path to the target directory where plugin files
                      should be copied.

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if self.iut_dir and self.iut_dir != "":
            print(f"Copying IUT from {self.iut_dir}")
            self.iut_dir = Path(self.iut_dir)
            iut_target_dir = os.path.join(
                self._panther_dir, "plugins", "services", "iut", self.iut_dir.name
            )
            self.copy_plugin_files(self.iut_dir, iut_target_dir)

    def remove_plugin_iut_service(self):
        """
        Remove the plugin IUTs service directory defined by "iut_dir" inside the application
        at panther/plugins/services/iut/{iut_dir}

        Attributes:
            iut_dir (str): The directory path of the testers to be removed.

        Side Effects:
            Deletes the directory specified by `iut_dir` and all its contents.

        Prints:
            A message indicating the removal of the testers director
        """
        if self.iut_dir and self.iut_dir != "":
            iut_target_dir = os.path.join(
                self._panther_dir, "plugins", "services", "iut", Path(self.iut_dir).name
            )
            if os.path.exists(iut_target_dir):
                print(f"Removing IUT from {iut_target_dir}")
                shutil.rmtree(iut_target_dir)

    def add_plugin_network_environment(self):
        """
        Add the plugin network environment directory defined by "net_env_dir" inside the application
        at panther/plugins/environments/network_environment/{net_env_dir}

        Parameters:
        net_env_dir (str): The path to the target directory where plugin files
                      should be copied.

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if self.net_env_dir and self.net_env_dir != "":
            # TODO improve this
            print(f"Copying network environment from {self.net_env_dir}")
            self.net_env_dir = Path(self.net_env_dir)
            net_env_target_dir = os.path.join(
                self._panther_dir,
                "plugins",
                "environments",
                "network_environment",
                self.net_env_dir.name,
            )
            self.copy_plugin_files(self.net_env_dir, net_env_target_dir)

    def remove_plugin_network_environment(self):
        """
        Remove the plugin IUTs service directory defined by "iut_dir" inside the application
        at panther/plugins/services/iut/{iut_dir}

        Attributes:
            iut_dir (str): The directory path of the testers to be removed.

        Side Effects:
            Deletes the directory specified by `iut_dir` and all its contents.

        Prints:
            A message indicating the removal of the testers director
        """
        if self.net_env_dir and self.net_env_dir != "":
            net_env_target_dir = os.path.join(
                self._panther_dir,
                "plugins",
                "environments",
                "network_environment",
                Path(self.net_env_dir).name,
            )
            if os.path.exists(net_env_target_dir):
                print(f"Removing network environment from {net_env_target_dir}")
                shutil.rmtree(net_env_target_dir)

    def add_plugin_execution_environment(self):
        if self.exec_env_dir and self.exec_env_dir != "":
            # TODO improve this
            print(f"Copying execution environment from {self.exec_env_dir}")
            self.exec_env_dir = Path(self.exec_env_dir)
            exec_env_target_dir = os.path.join(
                self._panther_dir,
                "plugins",
                "environments",
                "execution_environment",
                self.exec_env_dir.name,
            )
            self.copy_plugin_files(self.exec_env_dir, exec_env_target_dir)

    def remove_plugin_execution_environment(self):
        if self.exec_env_dir and self.exec_env_dir != "":
            exec_env_target_dir = os.path.join(
                self._panther_dir,
                "plugins",
                "environments",
                "execution_environment",
                Path(self.exec_env_dir).name,
            )
            if os.path.exists(exec_env_target_dir):
                print(f"Removing execution environment from {exec_env_target_dir}")
                shutil.rmtree(exec_env_target_dir)

    def cleanup(self):
        self.remove_plugin_execution_environment()
        self.remove_plugin_network_environment()
        self.remove_plugin_iut_service()
        self.remove_plugin_tester_service()

    def validate_plugin_config(self, plugin_type: str, plugin_name: str, plugin_config: DictConfig):
        """
        Validate plugin-specific configuration against its schema.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :param plugin_config: The plugin configuration to validate.
        :return: Validated plugin configuration.
        :raises ValidationError: If the configuration does not conform to the schema.
        """
        self.logger.debug(
            "Validating plugin configuration for %s/%s with %s",
            plugin_type,
            plugin_name,
            plugin_config,
        )
        plugin_schema_class = self.load_plugin_schema(plugin_type, plugin_name)
        self.logger.debug("Plugin schema class: %s", plugin_schema_class)
        structured_schema = OmegaConf.structured(plugin_schema_class)
        self.logger.debug("Structured schema: %s", structured_schema)

        # Check for unknown parameters
        if hasattr(plugin_schema_class, "__dataclass_fields__"):
            valid_params = set(plugin_schema_class.__dataclass_fields__.keys())
            provided_params = (
                set(plugin_config.keys()) if isinstance(plugin_config, DictConfig) else set()
            )

            # Always include 'type' as a valid parameter
            valid_params.add("type")

            unknown_params = provided_params - valid_params
            if unknown_params:
                self.logger.warning(
                    "Unknown parameters for %s/%s: %s. These will be ignored.",
                    plugin_type,
                    plugin_name,
                    unknown_params,
                )

                # Provide helpful information about valid parameters
                self.logger.info(
                    "Valid parameters for %s/%s: %s", plugin_type, plugin_name, sorted(valid_params)
                )
                self.logger.info(
                    "Use --list-plugin-params %s to see parameter details", plugin_name
                )

        try:
            return OmegaConf.merge(structured_schema, plugin_config)
        except ValidationError as e:
            # Enhanced error message with helpful information
            error_msg = (
                f"Plugin configuration validation failed for {plugin_type}/{plugin_name}: {e}"
            )
            error_msg += f"\n\nTo see valid parameters, run: python -m panther --list-plugin-params {plugin_name}"
            if plugin_type in ["iut", "tester"]:
                error_msg += f" --plugin-type {plugin_type}"
            raise ValidationError(error_msg) from e

    def construct_experiment_config(self, loaded_config: DictConfig) -> ExperimentConfig:
        """
        Manually construct an ExperimentConfig object from a loaded configuration.

        :param loaded_config: The loaded configuration dictionary (DictConfig or dict).
        :return: An ExperimentConfig object.
        """
        self.logger.info(
            "Constructing experiment configuration with global configuration - %s",
            self.global_config,
        )
        # Construct tests
        tests: list[TestConfig] = []
        for test_data in loaded_config["tests"]:
            # Construct network environment configuration
            network_env = test_data["network_environment"]
            self.logger.debug("Network environment: %s", network_env)
            validated_network_env = self.validate_plugin_config(
                "network_environment", network_env["type"], network_env
            )
            self.logger.debug("Network environment after validation: %s", validated_network_env)

            exec_envs = test_data.get("execution_environment", [])
            self.logger.debug("Execution environment: %s", exec_envs)
            for exec_env in exec_envs:
                validated_network_env = self.validate_plugin_config(
                    "execution_environment", exec_env["type"], exec_env
                )
            self.logger.debug("Network environment after validation: %s", validated_network_env)

            # Construct services for this test
            services: dict[str, ServiceConfig] = {}
            for service_name, service_data in test_data["services"].items():
                protocol = self.load_and_validate_protocol_config(
                    service_data
                )  # Resolve protocol subclass
                self.logger.debug("Protocol: %s", protocol)
                implementation = self.load_and_validate_implementation_config(service_data)
                self.logger.debug("Implementation: %s", implementation)
                service = ServiceConfig(
                    name=service_data["name"],
                    timeout=service_data.get("timeout", 100),
                    implementation=implementation,
                    protocol=protocol,
                    ports=service_data.get("ports", []),
                    generate_new_certificates=service_data.get("generate_new_certificates", False),
                )
                OmegaConf.merge(ServiceConfig, service)
                services[service_name] = service

            # ##########################################################################################################
            # Construct the test configuration:
            # NOTE: We do not validate with merge here, as the schema is not fully compatible with OmegaConf
            # It is because NetworkEnvironmentConfig is a dataclass, and OmegaConf does not support nested dataclasses
            # For example, let
            # class NetworkEnvironmentConfig:
            #     type: str
            # And:
            # class DockerComposeConfig(NetworkEnvironmentConfig):
            #     type: str    = "docker_compose"
            #     version: str = "3.8"#omegaconf.errors.ConfigKeyError: Key 'version' not in 'NetworkEnvironmentConfig'
            #     network_name: str = "default_network"
            #     service_prefix: Optional[str] = None  # Optional prefix for service names
            #     volumes: List[str] = field(default_factory=list)  # List of volume mounts
            #     environment: Dict[str, str] = field(default_factory=dict)  # Environment variables
            # Thus we prelinarily validate the network environment configuration,
            # It will thus ignore non defined fields in the schema -> not ideal for validation
            # We will need to find a way to validate nested dataclasses with OmegaConf
            # TODO if tests name is undefined, use the service name + other parameters
            # TODO if we use the validated version -> bugs (but it should be enough to validate format)
            # ##########################################################################################################

            test = TestConfig(
                name=test_data["name"],
                description=test_data["description"],
                network_environment=network_env,
                execution_environments=test_data.get("execution_environment", []),
                iterations=test_data["iterations"],
                services=services,
                steps=test_data.get("steps"),
                assertions=test_data.get("assertions"),
            )
            tests.append(test)

        # Construct the ExperimentConfig
        experiment_config = ExperimentConfig(
            tests=tests,
        )
        return experiment_config

    def validate_plugins_availability(
        self, experiment_config: ExperimentConfig
    ) -> tuple[bool, list[str]]:
        """
        Validate that all plugins required by the experiment configuration are available.

        :param experiment_config: The experiment configuration to validate
        :return: Tuple of (is_valid, error_messages)
        """
        from panther.plugins.plugin_manager import (
            PluginManager,
        )  # pylint: disable=import-outside-toplevel
        from panther.plugins.plugin_manifest import (
            PluginType,
        )  # pylint: disable=import-outside-toplevel

        errors = []
        required_plugins = set()

        # Create a unified plugin manager for validation using correct plugin directory paths
        plugin_directories = [
            str(self._panther_dir / "plugins" / "services"),
            str(self._panther_dir / "plugins" / "environments"),
            str(self._panther_dir / "plugins" / "protocols"),
        ]
        plugin_manager = PluginManager(
            plugin_directories=plugin_directories,
            event_manager=None,  # Event manager not needed for validation
        )

        # Extract required plugins from experiment config
        for test in experiment_config.tests:
            # Check network environment
            if hasattr(test, "network_environment") and test.network_environment:
                env_type = test.network_environment.type
                if env_type:
                    plugin_id = f"{PluginType.ENVIRONMENT.value}:{env_type}"
                    required_plugins.add((plugin_id, env_type, "network environment"))

            # Check execution environments
            if hasattr(test, "execution_environment") and test.execution_environment:
                for exec_env in test.execution_environment:
                    if hasattr(exec_env, "type") and exec_env.type:
                        plugin_id = f"{PluginType.ENVIRONMENT.value}:{exec_env.type}"
                        required_plugins.add((plugin_id, exec_env.type, "execution environment"))

            # Check services
            if hasattr(test, "services") and test.services:
                for _, service_config in test.services.items():
                    if hasattr(service_config, "implementation"):
                        impl = service_config.implementation
                        impl_name = impl.name
                        impl_type = impl.type if hasattr(impl, "type") else "iut"

                        # Handle string or enum type
                        impl_type_str = impl_type if isinstance(impl_type, str) else impl_type.value
                        if impl_type_str.lower() == "testers":
                            plugin_id = f"{PluginType.TESTER.value}:{impl_name}"
                            required_plugins.add((plugin_id, impl_name, "tester"))
                        else:
                            plugin_id = f"{PluginType.IUT.value}:{impl_name}"
                            required_plugins.add((plugin_id, impl_name, "IUT implementation"))

        # Validate each required plugin
        for plugin_id, plugin_name, plugin_desc in required_plugins:
            if plugin_id not in plugin_manager.plugin_catalog.catalog:
                errors.append(f"Required {plugin_desc} plugin '{plugin_name}' not found")

        # Resolve dependencies if no errors yet
        if not errors:
            pass  # TODO: Not implemented yet, but could be useful in the future
            plugin_ids = [p[0] for p in required_plugins]
            _, missing_deps = plugin_manager.plugin_catalog.resolve_dependencies(plugin_ids)
            if missing_deps:
                for dep in missing_deps:
                    errors.append(f"Missing dependency: {dep}")

        return len(errors) == 0, errors

    def load_and_validate_experiment_config(self) -> ExperimentConfig:
        """
        Load and validate the entire experiment configuration, including plugin-specific validation.

        :return: A validated experiment configuration.
        """
        with (
            self.metrics_collector.timing_context("experiment_config_loading_time")
            if self.metrics_collector
            else nullcontext()
        ):

            try:
                experiment_config_path = self.experiment_file
                if not os.path.exists(experiment_config_path):
                    raise FileNotFoundError(
                        f"Experiment configuration file '{experiment_config_path}' not found."
                    )

                # Load the YAML configuration
                if self.metrics_collector:
                    with self.metrics_collector.time_operation("experiment_yaml_parsing"):
                        loaded_config = OmegaConf.load(experiment_config_path)
                else:
                    loaded_config = OmegaConf.load(experiment_config_path)

                self.logger.debug("Loaded experiment config: %s", loaded_config)
                self.logger.debug(OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)))

                # Construct experiment config with timing
                if self.metrics_collector:
                    with self.metrics_collector.time_operation("experiment_config_construction"):
                        experiment_config = self.construct_experiment_config(loaded_config)
                else:
                    experiment_config = self.construct_experiment_config(loaded_config)

                self.logger.debug("Experiment config type: %s", type(experiment_config))

                # Only try to serialize if we have a valid dataclass
                if experiment_config and hasattr(experiment_config, "__dataclass_fields__"):
                    try:
                        self.logger.debug(
                            "Constructed experiment config: %s",
                            OmegaConf.to_yaml(asdict(experiment_config)),
                        )
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        self.logger.warning(
                            "Could not serialize experiment config for debug: %s", e
                        )
                else:
                    self.logger.warning(
                        "Experiment config is not a valid dataclass: %s", experiment_config
                    )

                # Validate plugin availability
                if self.metrics_collector:
                    with self.metrics_collector.time_operation("plugin_availability_validation"):
                        is_valid, plugin_errors = self.validate_plugins_availability(
                            experiment_config
                        )
                else:
                    is_valid, plugin_errors = self.validate_plugins_availability(experiment_config)

                if not is_valid:
                    error_msg = "Plugin validation failed:\n" + "\n".join(
                        f"  - {err}" for err in plugin_errors
                    )
                    if self.metrics_collector:
                        self.metrics_collector.record_error(
                            phase="plugin_availability_validation",
                            error_type="PluginValidationError",
                            error_message=error_msg,
                            component="config_manager",
                            metadata={"errors": plugin_errors},
                        )
                    raise PluginValidationError(error_msg)

                self.logger.info("Experiment configuration successfully validated.")

                if self.metrics_collector:
                    # Record config metrics
                    if hasattr(experiment_config, "tests"):
                        self.metrics_collector.set_gauge(
                            "config_tests_count", len(experiment_config.tests)
                        )

                        # Count services across all tests
                        total_services = 0
                        for test in experiment_config.tests:
                            if hasattr(test, "services") and test.services:
                                total_services += len(test.services)
                        self.metrics_collector.set_gauge("config_services_count", total_services)

                return experiment_config

            except ValidationError as e:
                if self.metrics_collector:
                    self.metrics_collector.record_error(
                        phase="experiment_config_validation",
                        error_type="ValidationError",
                        error_message=str(e),
                        component="config_manager",
                        metadata={"config_file": str(experiment_config_path)},
                    )
                self.logger.error("Configuration validation failed: %s", e)
                raise
            except yaml.parser.ParserError as e:
                if self.metrics_collector:
                    self.metrics_collector.record_error(
                        phase="experiment_config_loading",
                        error_type="YAMLParserError",
                        error_message=str(e),
                        component="config_manager",
                        metadata={"config_file": str(experiment_config_path)},
                    )
                self.logger.error("YAML parsing error: %s", e)
                raise
            except Exception as e:  # pylint: disable=broad-exception-caught
                if self.metrics_collector:
                    self.metrics_collector.record_error(
                        phase="experiment_config_loading",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        metadata={"config_file": experiment_config_path},
                    )
                self.logger.error("Unexpected error during configuration loading: %s", e)
                raise

    def load_and_validate_global_config(self) -> GlobalConfig:
        """
        Load and validate the global configuration from the experiment configuration file.
        Note no logger is used here.

        :return: A validated global configuration.
        """
        if self.metrics_collector:
            self.metrics_collector.increment_counter("config_loads_total")
            config_timer = self.metrics_collector.start_timing("global_config_loading_time")

        try:
            # Check if experiment config file exists (contains global config)
            experiment_config_path = self.experiment_file
            if not os.path.exists(experiment_config_path):
                raise FileNotFoundError(
                    f"Global configuration file '{experiment_config_path}' not found."
                )

            # Load the YAML configuration
            if self.metrics_collector:
                logging.debug(
                    "Loading global configuration with metrics from %s", experiment_config_path
                )
                with self.metrics_collector.time_operation("yaml_parsing"):
                    loaded_config = OmegaConf.load(experiment_config_path)
            else:
                loaded_config = OmegaConf.load(experiment_config_path)

            print(f"Loaded experiment config: {loaded_config}")
            print(OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)))

            # Construct global config with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation("global_config_construction"):
                    global_config = self.construct_global_config(loaded_config)
            else:
                global_config = self.construct_global_config(loaded_config)

            # Convert dataclass to dict for YAML serialization
            global_config_dict = asdict(global_config)
            print(f"Constructed global config: {OmegaConf.to_yaml(global_config_dict)}")
            print("Experiment configuration successfully validated.")

            if self.metrics_collector:
                self.metrics_collector.increment_counter("config_loads_successful")
                config_timer.stop()

            return global_config

        except ValidationError as e:
            if self.metrics_collector:
                self.metrics_collector.increment_counter("config_validation_errors")
                self.metrics_collector.record_error(
                    phase="config_validation",
                    error_type="ValidationError",
                    error_message=str(e),
                    metadata={"config_file": experiment_config_path},
                )
                if "config_timer" in locals():
                    config_timer.stop()
            print(f"Configuration validation failed: {e}")
            raise
        except yaml.parser.ParserError as e:
            if self.metrics_collector:
                self.metrics_collector.increment_counter("config_parsing_errors")
                self.metrics_collector.record_error(
                    phase="config_loading",
                    error_type="YAMLParserError",
                    error_message=str(e),
                    metadata={"config_file": experiment_config_path},
                )
                if "config_timer" in locals():
                    config_timer.stop()
            print(f"YAML parsing error: {e}")
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            if self.metrics_collector:
                self.metrics_collector.increment_counter("config_load_errors")
                self.metrics_collector.record_error(
                    phase="config_loading",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    metadata={"config_file": experiment_config_path},
                )
                if "config_timer" in locals():
                    config_timer.stop()
            print(f"Unexpected error during configuration loading: {e}")
            raise

    @staticmethod
    def load_plugin_schema(plugin_type: str, plugin_name: str):
        """
        Dynamically load a plugin schema based on its type and name.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :return: The plugin's schema module.
        :raises ImportError: If the schema module cannot be found.
        """

        plugin_module_path = (
            f"panther.plugins.environments.{plugin_type}.{plugin_name}.config_schema"
        )
        try:
            class_name = ConfigLoader._get_class_name(plugin_name)
            plugin_module = importlib.import_module(plugin_module_path)
            config_class = getattr(plugin_module, class_name)
            return config_class  # Assume PluginConfig is the schema class
        except ImportError as exc:
            raise ImportError(f"Plugin schema '{plugin_module_path}' not found.") from exc
        except AttributeError as exc:
            raise ImportError(
                f"Plugin schema '{plugin_module_path}' does not define a 'PluginConfig' class."
            ) from exc

    def load_and_validate_protocol_config(
        self, implementation: ServiceConfig
    ) -> ListConfig | DictConfig:
        """
        Dynamically loads the appropriate implementation configuration class.

        :param implementation: A dictionary containing `name` and other fields.
        :return: An instance of the dynamically loaded configuration class.
        """
        self.logger.debug("Service: %s", implementation)
        protocol = implementation.protocol.name
        if hasattr(implementation.protocol, "protocol_type"):
            protocol_type = implementation.protocol.protocol_type
        else:
            protocol_type = "client_server"  # TODO: Default to client-server for now
            # Assuming schema files are in plugins
        module_path = f"panther.plugins.protocols.{protocol_type}.{protocol}.config_schema"
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            config_class = getattr(schema_module, f"{protocol.capitalize()}Config")
            self.logger.debug(
                "Protocol: %s - %s - %s", protocol, implementation["protocol"], config_class
            )
            protocol_instance = config_class(**implementation.protocol)
            return OmegaConf.merge(config_class, protocol_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load protocol config for '{protocol}': {e}") from e

    def load_and_validate_implementation_config(
        self, implementation: dict
    ) -> ListConfig | DictConfig:
        """
        Dynamically loads the appropriate implementation configuration class.
        """

        self.logger.debug("Implementation: %s", implementation)
        name = implementation["implementation"]["name"]
        implem_type = implementation["implementation"]["type"]
        protocol = implementation["protocol"]["name"]
        protocol_version = implementation["protocol"]["version"]
        if implem_type == "IUT" or implem_type.lower() == "iut":
            # Assuming schema files are in plugins
            module_path = f"panther.plugins.services.iut.{protocol}.{name}.config_schema"
        else:
            module_path = f"panther.plugins.services.{implem_type.lower()}.{name}.config_schema"

        self.logger.debug("Module path: %s", module_path)
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            class_name = self._get_class_name(name)
            config_class = getattr(schema_module, class_name)
            self.logger.debug(
                "Implementation: %s - %s - %s", name, implementation["implementation"], config_class
            )

            # Load the version configuration
            version_class_name = self._get_class_name(name, "Version")
            version_config_class = getattr(schema_module, version_class_name)
            # TODO cleanup
            if implem_type == "IUT" or implem_type.lower() == "iut":
                version_configs_dir = (
                    str(self._panther_dir).replace("/panther", "")
                    + "/"
                    + module_path.replace(".", "/").replace("/config_schema", "/version_configs/")
                )
            else:
                version_configs_dir = (
                    str(self._panther_dir).replace("/panther", "")
                    + "/"
                    + module_path.replace(".", "/").replace(
                        "/config_schema", f"/version_configs/{protocol}/"
                    )
                )

            version_path = os.path.join(version_configs_dir, f"{protocol_version}.yaml")
            if not os.path.exists(version_path):
                raise ValueError(f"Version configuration file {version_path} not found.")
            raw_version_config = OmegaConf.load(version_path)
            self.logger.debug("Version config: %s - %s", raw_version_config, version_config_class)
            protocol_version = OmegaConf.to_object(
                OmegaConf.merge(OmegaConf.structured(version_config_class), raw_version_config)
            )

            # Convert type to uppercase for enum compatibility
            impl_config = implementation["implementation"].copy()
            if "type" in impl_config and isinstance(impl_config["type"], str):
                impl_config["type"] = impl_config["type"].upper()

            implementation_instance = config_class(**impl_config)
            implementation_instance.version = protocol_version

            return OmegaConf.merge(config_class, implementation_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load implementation config for '{name}': {e}") from e

    def get_all_exec_env_classes(self):
        """
        Get all execution environment classes from the plugin directory.

        :return: A list of execution environment classes.
        """

        exec_env_classes = []
        exec_env_dir = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / "environments"
            / "execution_environment"
        )
        self.logger.debug("Searching for execution environment classes in %s", exec_env_dir)

        # Check if directory exists
        if not exec_env_dir.exists():
            self.logger.debug("Execution environment directory %s does not exist", exec_env_dir)
            return exec_env_classes

        try:
            for plugin_dir in exec_env_dir.iterdir():
                if plugin_dir.is_dir():
                    plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                    if plugin_file.exists():
                        self.logger.debug("Found execution environment class: %s", plugin_dir.name)
                        exec_env_classes.append(self._get_class_name(plugin_dir.name, "Config"))
                    else:
                        self.logger.debug("No execution environment class found in %s", plugin_dir)
        except (FileNotFoundError, OSError) as e:
            self.logger.debug(
                "Error accessing execution environment directory %s: %s", exec_env_dir, e
            )

        self.logger.debug("Total execution environment classes found: %s", len(exec_env_classes))
        return exec_env_classes

    def get_all_net_env_classes(self):
        """
        Get all network environment classes from the plugin directory.

        :return: A list of network environment classes.
        """

        exec_env_classes = []
        exec_env_dir = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / "environments"
            / "network_environment"
        )
        self.logger.debug("Searching for network environment classes in %s", exec_env_dir)

        # Check if directory exists
        if not exec_env_dir.exists():
            self.logger.debug("Network environment directory %s does not exist", exec_env_dir)
            return exec_env_classes

        try:
            for plugin_dir in exec_env_dir.iterdir():
                if plugin_dir.is_dir():
                    plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                    if plugin_file.exists():
                        self.logger.debug("Found network environment class: %s", plugin_dir.name)
                        exec_env_classes.append(self._get_class_name(plugin_dir.name, "Config"))
                    else:
                        self.logger.debug("No network environment class found in %s", plugin_dir)
        except (FileNotFoundError, OSError) as e:
            self.logger.debug(
                "Error accessing network environment directory %s: %s", exec_env_dir, e
            )

        self.logger.debug("Total network environment classes found: %s", len(exec_env_classes))
        return exec_env_classes

    def get_all_protocol_classes(self):
        """
        Get all protocol classes from the plugin directory.

        :return: A list of protocol classes.
        """

        protocol_classes = []
        protocol_dir = self._panther_dir / Path(self.global_config.paths.plugin_dir) / "protocols"
        self.logger.debug("Searching for protocol classes in %s", protocol_dir)

        # Check if directory exists
        if not protocol_dir.exists():
            self.logger.debug("Protocol directory %s does not exist", protocol_dir)
            return protocol_classes

        try:
            for protocol_type_dir in protocol_dir.iterdir():
                if protocol_type_dir.is_dir():
                    for protocol_dir in protocol_type_dir.iterdir():
                        if protocol_dir.is_dir():
                            protocol_file = protocol_dir / f"{protocol_dir.name}.py"
                            if protocol_file.exists():
                                self.logger.debug("Found protocol class: %s", protocol_dir.name)
                                protocol_classes.append(
                                    self._get_class_name(protocol_dir.name, "Config")
                                )
                            else:
                                self.logger.debug("No protocol class found in %s", protocol_dir)
        except (FileNotFoundError, OSError) as e:
            self.logger.debug("Error accessing protocol directory %s: %s", protocol_dir, e)

        self.logger.debug("Total protocol classes found: %s", len(protocol_classes))
        return protocol_classes

    def get_all_iut_classes(self):
        """
        Get all IUT classes from the plugin directory and return a dictionary with protocols as keys and list of implementations as values.

        :return: A dictionary with protocols as keys and list of IUT classes as values.
        """

        iut_classes = {}
        iut_dir = self._panther_dir / Path(self.global_config.paths.plugin_dir) / "services" / "iut"
        self.logger.debug("Searching for IUT classes in %s", iut_dir)
        for protocol_dir in iut_dir.iterdir():
            if protocol_dir.is_dir():
                protocol_name = protocol_dir.name
                iut_classes[protocol_name] = []
                for plugin_dir in protocol_dir.iterdir():
                    if plugin_dir.is_dir() and not plugin_dir.name.startswith("__"):
                        plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                        if plugin_file.exists():
                            self.logger.debug("Found IUT class: %s", plugin_dir.name)
                            iut_classes[protocol_name].append(
                                self._get_class_name(plugin_dir.name, "Config")
                            )
                        else:
                            self.logger.debug("No IUT class found in %s", plugin_dir)
        self.logger.debug("Total IUT classes found: %s", iut_classes)
        return iut_classes

    def get_all_tester_classes(self):
        """
        Get all tester classes from the plugin directory and return a list of tester classes.

        :return: A list of tester classes.
        """

        tester_classes = []
        # tester_dir =  self.panther_dir / Path(self.global_config.paths.plugin_dir) / "services" / "testers"
        tester_dir = files(
            f"{self.global_config.paths.plugin_dir}.services.testers"
        )  # .joinpath('resource1.txt')
        self.logger.debug("Searching for tester classes in %s", tester_dir)
        for plugin_dir in tester_dir.iterdir():
            if plugin_dir.is_dir():
                plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                if plugin_file.exists():  # type: ignore
                    self.logger.debug("Found tester class: %s", plugin_dir.name)
                    tester_classes.append(self._get_class_name(plugin_dir.name, "Config"))
                else:
                    self.logger.debug("No tester class found in %s", plugin_dir)
        self.logger.debug("Total tester classes found: %s", len(tester_classes))
        return tester_classes

    def load_all_plugins(self) -> dict[str, list[str]]:
        """
        Load all plugins and return them in an ordered dictionary.

        :return: An ordered dictionary with plugin types as keys and list of plugin names as values.
        """
        plugin_types = {
            "execution_environment": "environments/execution_environment",
            "network_environment": "environments/network_environment",
            "protocols": "protocols",
            "iut": "services/iut",
            "testers": "services/testers",
        }
        all_plugins = {}

        for plugin_type, plugin_path in plugin_types.items():
            plugin_dir = self._panther_dir / Path(self.global_config.paths.plugin_dir) / plugin_path
            self.logger.debug("Searching for plugins in %s", plugin_dir)
            plugins = []

            # Check if plugin directory exists
            if not plugin_dir.exists():
                self.logger.debug("Plugin directory %s does not exist", plugin_dir)
                all_plugins[plugin_type] = []
                continue

            try:
                if plugin_type == "iut":
                    for protocol_dir in plugin_dir.iterdir():
                        if protocol_dir.is_dir() and not protocol_dir.name.startswith("__"):
                            for sub_dir in protocol_dir.iterdir():
                                if sub_dir.is_dir() and not sub_dir.name.startswith("__"):
                                    plugin_file = sub_dir / f"{sub_dir.name}.py"
                                    if plugin_file.exists():
                                        self.logger.debug("Found plugin: %s", sub_dir.name)
                                        plugins.append(f"{protocol_dir.name}/{sub_dir.name}")
                                        try:
                                            importlib.import_module(
                                                f"panther.plugins.{plugin_path.replace('/', '.')}.{protocol_dir.name}.{sub_dir.name}"
                                            )
                                        except ImportError as e:
                                            self.logger.error(
                                                "Failed to load plugin %s: %s", sub_dir.name, e
                                            )
                else:
                    for sub_dir in plugin_dir.iterdir():
                        if sub_dir.is_dir() and not sub_dir.name.startswith("__"):
                            plugin_file = sub_dir / f"{sub_dir.name}.py"
                            if plugin_file.exists():
                                self.logger.debug("Found plugin: %s", sub_dir.name)
                                plugins.append(sub_dir.name)
                                try:
                                    importlib.import_module(
                                        f"panther.plugins.{plugin_path.replace('/', '.')}.{sub_dir.name}"
                                    )
                                except ImportError as e:
                                    self.logger.error(
                                        "Failed to load plugin %s: %s", sub_dir.name, e
                                    )
            except (FileNotFoundError, OSError) as e:
                self.logger.debug("Error accessing plugin directory %s: %s", plugin_dir, e)
                plugins = []

            all_plugins[plugin_type] = sorted(plugins)

        return all_plugins

    def list_plugin_parameters(self, plugin_type: str, plugin_name: str, protocol: str = None):
        """
        List all configurable parameters for a specified plugin.

        :param plugin_type: The plugin type (e.g., "network_environment", "execution_environment", "iut", "tester").
        :param plugin_name: The plugin name (e.g., "shadow_ns", "picoquic").
        :param protocol: Optional protocol name for IUT/tester plugins (e.g., "quic", "http").
        :return: Dictionary of parameters with their types, defaults, and descriptions.
        """

        try:
            # Determine the correct module path based on plugin type
            if plugin_type in ["iut", "tester"]:
                # For IUT and tester plugins, they're in the services directory
                # For IUT plugins, they might be nested under a protocol directory
                # Try first the direct path (for simpler plugins)
                try:
                    module_path = (
                        f"panther.plugins.services.{plugin_type}.{plugin_name}.config_schema"
                    )
                    plugin_module = importlib.import_module(module_path)
                except ImportError:
                    # If not found, it might be under a protocol subdirectory
                    # Look for it in different protocol directories
                    found = False

                    # If protocol is provided, try that first
                    if protocol:
                        try:
                            module_path = f"panther.plugins.services.{plugin_type}.{protocol}.{plugin_name}.config_schema"
                            plugin_module = importlib.import_module(module_path)
                            found = True
                        except ImportError:
                            pass

                    # If not found with provided protocol or no protocol provided, search through known protocols
                    if not found:
                        last_exc = None
                        for protocol_dir in ["quic", "http", "minip"]:
                            try:
                                module_path = f"panther.plugins.services.{plugin_type}.{protocol_dir}.{plugin_name}.config_schema"
                                plugin_module = importlib.import_module(module_path)
                                found = True
                                break
                            except ImportError as exc:
                                last_exc = exc
                                continue

                    if not found:
                        error_msg = f"Could not find plugin schema for {plugin_name}"
                        if protocol:
                            error_msg += f" (protocol: {protocol})"
                        raise ImportError(error_msg) from last_exc
            else:
                # For environment plugins
                module_path = (
                    f"panther.plugins.environments.{plugin_type}.{plugin_name}.config_schema"
                )
                plugin_module = importlib.import_module(module_path)

            self.logger.debug("Found plugin schema at %s", module_path)

            # Get the class name using the plugin loader helper
            class_name = ConfigLoader._get_class_name(plugin_name)
            config_class = getattr(plugin_module, class_name)

            # Format and return the parameters
            parameters = {}

            # Use dataclasses introspection to get fields
            import dataclasses  # pylint: disable=import-outside-toplevel
            import inspect  # pylint: disable=import-outside-toplevel
            from typing import get_type_hints  # pylint: disable=import-outside-toplevel

            if dataclasses.is_dataclass(config_class):
                fields = dataclasses.fields(config_class)
                type_hints = get_type_hints(config_class)

                for field in fields:
                    param_info = {
                        "type": str(type_hints.get(field.name, "unknown")),
                        "default": (
                            field.default if field.default is not dataclasses.MISSING else None
                        ),
                        "required": field.default is dataclasses.MISSING,
                        "description": inspect.getdoc(field) or "No description available",
                    }
                    parameters[field.name] = param_info

            return parameters

        except ImportError as e:
            print(
                f"Plugin schema for '{plugin_name}' not found. Check if the plugin name is correct."
            )
            print(f"Error details: {e}")

            # Let's provide more helpful guidance for IUT/tester plugins
            if plugin_type in ["iut", "tester"]:
                print("\nFor IUT/tester plugins, try specifying the protocol if applicable.")
                print("Example: quiche is under the 'quic' protocol, so use:")
                print(
                    f"panther --list-plugin-params {plugin_name} --plugin-type {plugin_type} --protocol quic"
                )

            return {}
        except AttributeError as e:
            logging.error("Error retrieving parameters for plugin '%s': %s", plugin_name, e)
            return {}
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error(
                "Unexpected error while listing parameters for plugin '%s': %s", plugin_name, e
            )
            return {}

    def construct_observer_config(self, loaded_config: DictConfig) -> ObserverConfig:
        """
        Construct the ObserverConfig from the loaded configuration.

        Args:
            loaded_config (DictConfig): The loaded configuration dictionary.

        Returns:
            ObserverConfig: The constructed observer configuration.
        """
        self.logger.debug("Constructing observer configuration")
        observer_config = ObserverConfig()

        if "observers" in loaded_config:
            observers_dict = loaded_config.get("observers", {})

            # Configure logger observer if present
            if "logger" in observers_dict:
                logger_config = LoggerObserverConfig(
                    enabled=observers_dict["logger"].get("enabled", True),
                    auto_register=observers_dict["logger"].get("auto_register", True),
                    priority=observers_dict["logger"].get("priority", 0),
                    log_level=observers_dict["logger"].get("log_level", "INFO"),
                    include_data=observers_dict["logger"].get("include_data", True),
                    include_event_id=observers_dict["logger"].get("include_event_id", True),
                    include_timestamp=observers_dict["logger"].get("include_timestamp", True),
                    enable_colors=observers_dict["logger"].get("enable_colors", True),
                    output_file=observers_dict["logger"].get("output_file"),
                    correlation_tracking=observers_dict["logger"].get("correlation_tracking", True),
                    structured_output=observers_dict["logger"].get("structured_output", False),
                    max_data_length=observers_dict["logger"].get("max_data_length", 500),
                )
                observer_config.logger = logger_config

            # Configure metrics observer if present
            if "metrics" in observers_dict:
                metrics_config = MetricsObserverConfig(
                    enabled=observers_dict["metrics"].get("enabled", True),
                    auto_register=observers_dict["metrics"].get("auto_register", True),
                    priority=observers_dict["metrics"].get("priority", 10),
                    log_level=observers_dict["metrics"].get("log_level", "INFO"),
                    publish_metrics=observers_dict["metrics"].get("publish_metrics", True),
                    collect_system_metrics=observers_dict["metrics"].get(
                        "collect_system_metrics", True
                    ),
                    publish_interval=observers_dict["metrics"].get("publish_interval", 30),
                    enable_real_time_monitoring=observers_dict["metrics"].get(
                        "enable_real_time_monitoring", False
                    ),
                    resource_collection_interval=observers_dict["metrics"].get(
                        "resource_collection_interval", 10
                    ),
                    metric_collection_interval=observers_dict["metrics"].get(
                        "metric_collection_interval", 10
                    ),
                )
                observer_config.metrics = metrics_config

            # Configure storage observer if present
            if "storage" in observers_dict:
                storage_config = StorageObserverConfig(
                    enabled=observers_dict["storage"].get("enabled", True),
                    auto_register=observers_dict["storage"].get("auto_register", True),
                    priority=observers_dict["storage"].get("priority", 20),
                    log_level=observers_dict["storage"].get("log_level", "INFO"),
                    storage_path=observers_dict["storage"].get("storage_path"),
                    enable_compression=observers_dict["storage"].get("enable_compression", True),
                    max_storage_size=observers_dict["storage"].get("max_storage_size", 0),
                    auto_backup=observers_dict["storage"].get("auto_backup", True),
                    backup_interval=observers_dict["storage"].get("backup_interval", 3600),
                    retention_days=observers_dict["storage"].get("retention_days", 30),
                    batch_size=observers_dict["storage"].get("batch_size", 100),
                    async_storage=observers_dict["storage"].get("async_storage", False),
                )
                observer_config.storage = storage_config

            # Configure experiment observer if present
            if "experiment" in observers_dict:
                experiment_config = ExperimentObserverConfig(
                    enabled=observers_dict["experiment"].get("enabled", True),
                    auto_register=observers_dict["experiment"].get("auto_register", True),
                    priority=observers_dict["experiment"].get("priority", 5),
                    log_level=observers_dict["experiment"].get("log_level", "INFO"),
                    output_dir=observers_dict["experiment"].get("output_dir"),
                    test_name=observers_dict["experiment"].get("test_name"),
                    track_timing=observers_dict["experiment"].get("track_timing", True),
                    track_steps=observers_dict["experiment"].get("track_steps", True),
                )
                observer_config.experiment = experiment_config

        self.logger.debug("Observer configuration constructed successfully")
        return observer_config
