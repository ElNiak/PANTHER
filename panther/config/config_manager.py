"""Configuration management module for PANTHER framework.

This module provides backward compatibility wrapper around the new unified configuration system.
It maintains the same interface as the legacy ConfigLoader while using the new ConfigurationManager.
"""

import importlib
import logging
import os
import shutil
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml
from omegaconf import DictConfig, ListConfig, OmegaConf, ValidationError

# Import from new unified system
from panther.config.core.manager import ConfigurationManager
from panther.config.core.models import (
    ExperimentConfig,
    GlobalConfig,
    ServiceConfig,
    TestConfig,
)
from panther.config.core.models.observer import (
    ExperimentObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    BaseObserverConfig,
    StorageObserverConfig,
)
from panther.config.core.models.global_config import (
    DockerConfig,
    FastFailConfig,
    FeatureLogLevelsConfig,
    LoggingConfig,
    LoggingLevel,
    PathsConfig,
)

# Keep legacy imports for compatibility
from panther.core.exceptions.experiment_exceptions import PluginValidationError
from panther.core.utils.config_summarizer import ConfigSummarizer
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_config_resolver import PluginConfigResolver
from panther.plugins.plugin_loader_utils import PluginManagerUtils


class ConfigLoader(LoggerMixin):
    """Backward compatibility wrapper around the new ConfigurationManager.

    This class maintains the same interface as the legacy ConfigLoader while
    delegating all operations to the new unified configuration system.
    """

    @staticmethod
    def _get_class_name(plugin_name: str, suffix: str = "Config") -> str:
        """Convert plugin name to class name format. Uses PluginConfigResolver."""
        return PluginConfigResolver.get_class_name(plugin_name, suffix)

    def __init__(
        self,
        experiment_file: str,
        output_dir: Optional[str] = None,
        exec_env_dir: Optional[str] = "",
        net_env_dir: Optional[str] = "",
        iut_dir: Optional[str] = "",
        testers_dir: Optional[str] = "",
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

        # Initialize with config_processing feature
        self.__init_logger__("config_processing")

        # Initialize new ConfigurationManager
        self._config_manager = ConfigurationManager(
            experiment_file,  # Use positional arg matching the ConfigurationManager signature
            output_dir=output_dir,
            exec_env_dir=exec_env_dir,
            net_env_dir=net_env_dir,
            iut_dir=iut_dir,
            testers_dir=testers_dir,
            metrics_collector=metrics_collector,
            debug_override=debug_override,
        )

    def construct_global_config(self, loaded_config: DictConfig) -> GlobalConfig:
        """Delegate to new ConfigurationManager for global config construction.

        Args:
            loaded_config (DictConfig): Loaded configuration dictionary

        Returns:
            GlobalConfig: Constructed global configuration
        """
        # Add plugin directories if needed
        if self.exec_env_dir:
            self.add_plugin_execution_environment()
        if self.net_env_dir:
            self.add_plugin_network_environment()
        if self.iut_dir:
            self.add_plugin_iut_service()
        if self.testers_dir:
            self.add_plugin_tester_service()

        # Use ConfigurationManager to build global config
        self.global_config = self._config_manager.get_global_config()

        # Apply debug override if set
        if self.debug_override:
            self.global_config.logging.level = LoggingLevel.DEBUG

        return self.global_config

    def add_plugin_tester_service(self) -> None:
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
            self.logger.warning(
                "Source directory %s does not exist, skipping copy", source_dir
            )
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

    def validate_plugin_config(
        self, plugin_type: str, plugin_name: str, plugin_config: DictConfig
    ):
        """Delegate to new ConfigurationManager for plugin validation.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :param plugin_config: The plugin configuration to validate.
        :return: Validated plugin configuration.
        :raises ValidationError: If the configuration does not conform to the schema.
        """
        # Convert DictConfig to dict if needed
        config_dict = (
            OmegaConf.to_container(plugin_config)
            if isinstance(plugin_config, DictConfig)
            else plugin_config
        )

        # Use ConfigurationManager to validate plugin config
        return self._config_manager.validate_plugin_config(
            plugin_type, plugin_name, config_dict
        )

    def construct_experiment_config(
        self, loaded_config: DictConfig
    ) -> ExperimentConfig:
        """Delegate to new ConfigurationManager for experiment config construction.

        :param loaded_config: The loaded configuration dictionary (DictConfig or dict).
        :return: An ExperimentConfig object.
        """
        # Use ConfigurationManager to get experiment config
        return self._config_manager.get_experiment_config()

    def validate_plugins_availability(
        self, experiment_config: ExperimentConfig
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all plugins required by the experiment configuration are available.

        :param experiment_config: The experiment configuration to validate
        :return: Tuple of (is_valid, error_messages)
        """
        from panther.plugins.plugin_manager import (  # pylint: disable=import-outside-toplevel
            PluginManager,
        )
        from panther.plugins.plugin_manifest import (  # pylint: disable=import-outside-toplevel
            PluginType,
        )

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
                        required_plugins.add(
                            (plugin_id, exec_env.type, "execution environment")
                        )

            # Check services
            if hasattr(test, "services") and test.services:
                for _, service_config in test.services.items():
                    if hasattr(service_config, "implementation"):
                        impl = service_config.implementation
                        impl_name = impl.name
                        impl_type = impl.type if hasattr(impl, "type") else "iut"

                        # Handle string or enum type
                        impl_type_str = (
                            impl_type if isinstance(impl_type, str) else impl_type.value
                        )
                        if impl_type_str.lower() == "testers":
                            plugin_id = f"{PluginType.TESTER.value}:{impl_name}"
                            required_plugins.add((plugin_id, impl_name, "tester"))
                        else:
                            plugin_id = f"{PluginType.IUT.value}:{impl_name}"
                            required_plugins.add(
                                (plugin_id, impl_name, "IUT implementation")
                            )

        # Validate each required plugin
        for plugin_id, plugin_name, plugin_desc in required_plugins:
            if plugin_id not in plugin_manager.plugin_catalog.catalog:
                errors.append(
                    f"Required {plugin_desc} plugin '{plugin_name}' not found"
                )

        # Resolve dependencies if no errors yet
        if not errors:
            pass  # TODO: Not implemented yet, but could be useful in the future
            plugin_ids = [p[0] for p in required_plugins]
            _, missing_deps = plugin_manager.plugin_catalog.resolve_dependencies(
                plugin_ids
            )
            if missing_deps:
                for dep in missing_deps:
                    errors.append(f"Missing dependency: {dep}")

        return len(errors) == 0, errors

    def load_and_validate_experiment_config(self) -> ExperimentConfig:
        """Delegate to new ConfigurationManager for experiment config loading.

        :return: A validated experiment configuration.
        """
        with (
            self.metrics_collector.timing_context("experiment_config_loading_time")
            if self.metrics_collector
            else nullcontext()
        ):
            try:
                # Use ConfigurationManager to load and validate
                experiment_config = self._config_manager.load_experiment_config(self.experiment_file)

                # Validate plugin availability using existing method
                is_valid, plugin_errors = self.validate_plugins_availability(
                    experiment_config
                )

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
                        self.metrics_collector.set_gauge(
                            "config_services_count", total_services
                        )

                return experiment_config

            except Exception as e:
                if self.metrics_collector:
                    self.metrics_collector.record_error(
                        phase="experiment_config_loading",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        metadata={"config_file": self.experiment_file},
                    )
                raise

    def load_and_validate_global_config(self) -> GlobalConfig:
        """Delegate to new ConfigurationManager for global config loading.

        :return: A validated global configuration.
        """
        if self.metrics_collector:
            self.metrics_collector.increment_counter("config_loads_total")
            config_timer = self.metrics_collector.start_timing(
                "global_config_loading_time"
            )

        try:
            # Use ConfigurationManager to load and get global config
            global_config = self._config_manager.load_global_config()
            self.global_config = global_config

            # Apply debug override if set
            if self.debug_override:
                global_config.logging.level = LoggingLevel.DEBUG

            # Display summary
            global_config_dict = global_config.dict()
            summary = ConfigSummarizer.summarize(global_config_dict)
            print(f"Constructed global config: {summary}")
            print("Experiment configuration successfully validated.")

            if self.metrics_collector:
                self.metrics_collector.increment_counter("config_loads_successful")
                config_timer.stop()

            return global_config

        except Exception as e:
            if self.metrics_collector:
                self.metrics_collector.increment_counter("config_load_errors")
                self.metrics_collector.record_error(
                    phase="config_loading",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    metadata={"config_file": self.experiment_file},
                )
                if "config_timer" in locals():
                    config_timer.stop()
            print(f"Error during configuration loading: {e}")
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
            raise ImportError(
                f"Plugin schema '{plugin_module_path}' not found."
            ) from exc
        except AttributeError as exc:
            raise ImportError(
                f"Plugin schema '{plugin_module_path}' does not define a 'PluginConfig' class."
            ) from exc

    def load_and_validate_protocol_config(
        self, implementation: ServiceConfig
    ) -> Union[ListConfig, DictConfig]:
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
        module_path = (
            f"panther.plugins.protocols.{protocol_type}.{protocol}.config_schema"
        )
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            config_class = getattr(schema_module, f"{protocol.capitalize()}Config")
            self.logger.debug(
                "Protocol: %s - %s - %s",
                protocol,
                implementation["protocol"],
                config_class,
            )
            protocol_instance = config_class(**implementation.protocol)
            return OmegaConf.merge(config_class, protocol_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Failed to load protocol config for '{protocol}': {e}"
            ) from e

    def load_and_validate_implementation_config(
        self, implementation: dict
    ) -> Union[ListConfig, DictConfig]:
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
            module_path = (
                f"panther.plugins.services.iut.{protocol}.{name}.config_schema"
            )
        else:
            module_path = (
                f"panther.plugins.services.{implem_type.lower()}.{name}.config_schema"
            )

        self.logger.debug("Module path: %s", module_path)
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            class_name = self._get_class_name(name)
            config_class = getattr(schema_module, class_name)
            self.logger.debug(
                "Implementation: %s - %s - %s",
                name,
                implementation["implementation"],
                config_class,
            )

            # Load the version configuration
            version_class_name = self._get_class_name(name, "Version")
            version_config_class = getattr(schema_module, version_class_name)
            # TODO cleanup
            if implem_type == "IUT" or implem_type.lower() == "iut":
                version_configs_dir = (
                    str(self._panther_dir).replace("/panther", "")
                    + "/"
                    + module_path.replace(".", "/").replace(
                        "/config_schema", "/version_configs/"
                    )
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
                raise ValueError(
                    f"Version configuration file {version_path} not found."
                )
            raw_version_config = OmegaConf.load(version_path)
            self.logger.debug(
                "Version config: %s - %s", raw_version_config, version_config_class
            )
            protocol_version = OmegaConf.to_object(
                OmegaConf.merge(
                    OmegaConf.structured(version_config_class), raw_version_config
                )
            )

            # Convert type to uppercase for enum compatibility
            impl_config = implementation["implementation"].copy()
            if "type" in impl_config and isinstance(impl_config["type"], str):
                impl_config["type"] = impl_config["type"].upper()

            implementation_instance = config_class(**impl_config)
            implementation_instance.version = protocol_version

            return OmegaConf.merge(config_class, implementation_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Failed to load implementation config for '{name}': {e}"
            ) from e

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
        self.logger.debug(
            "Searching for execution environment classes in %s", exec_env_dir
        )

        try:
            # Use PluginManagerUtils.discover_plugins utility for robust plugin discovery
            plugin_files = PluginManagerUtils.discover_plugins(exec_env_dir)
            for plugin_file in plugin_files:
                plugin_name = plugin_file.stem
                self.logger.debug("Found execution environment class: %s", plugin_name)
                exec_env_classes.append(self._get_class_name(plugin_name, "Config"))
        except Exception as e:
            self.logger.debug(
                "Error discovering execution environment plugins in %s: %s",
                exec_env_dir,
                e,
            )

        self.logger.debug(
            "Total execution environment classes found: %s", len(exec_env_classes)
        )
        return exec_env_classes

    def get_all_net_env_classes(self):
        """
        Get all network environment classes from the plugin directory.

        :return: A list of network environment classes.
        """
        net_env_classes = []
        net_env_dir = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / "environments"
            / "network_environment"
        )
        self.logger.debug(
            "Searching for network environment classes in %s", net_env_dir
        )

        try:
            # Use PluginManagerUtils.discover_plugins utility for robust plugin discovery
            plugin_files = PluginManagerUtils.discover_plugins(net_env_dir)
            for plugin_file in plugin_files:
                plugin_name = plugin_file.stem
                self.logger.debug("Found network environment class: %s", plugin_name)
                net_env_classes.append(self._get_class_name(plugin_name, "Config"))
        except Exception as e:
            self.logger.debug(
                "Error discovering network environment plugins in %s: %s",
                net_env_dir,
                e,
            )

        self.logger.debug(
            "Total network environment classes found: %s", len(net_env_classes)
        )
        return net_env_classes

    def get_all_protocol_classes(self):
        """
        Get all protocol classes from the plugin directory.

        :return: A list of protocol classes.
        """
        protocol_classes = []
        protocol_dir = (
            self._panther_dir / Path(self.global_config.paths.plugin_dir) / "protocols"
        )
        self.logger.debug("Searching for protocol classes in %s", protocol_dir)

        try:
            # Check if directory exists
            if not protocol_dir.exists():
                self.logger.debug("Protocol directory %s does not exist", protocol_dir)
                return protocol_classes

            # Navigate through nested protocol structure (protocol_type/protocol)
            for protocol_type_dir in protocol_dir.iterdir():
                if protocol_type_dir.is_dir():
                    try:
                        # Use PluginManagerUtils.discover_plugins for each protocol type directory
                        protocol_files = PluginManagerUtils.discover_plugins(
                            protocol_type_dir
                        )
                        for protocol_file in protocol_files:
                            protocol_name = protocol_file.stem
                            self.logger.debug("Found protocol class: %s", protocol_name)
                            protocol_classes.append(
                                self._get_class_name(protocol_name, "Config")
                            )
                    except Exception as e:
                        self.logger.debug(
                            "Error discovering protocols in %s: %s",
                            protocol_type_dir,
                            e,
                        )
        except Exception as e:
            self.logger.debug(
                "Error accessing protocol directory %s: %s", protocol_dir, e
            )

        self.logger.debug("Total protocol classes found: %s", len(protocol_classes))
        return protocol_classes

    def get_all_iut_classes(self):
        """
        Get all IUT classes from the plugin directory and return a dictionary with protocols as keys
        and list of implementations as values.

        :return: A dictionary with protocols as keys and list of IUT classes as values.
        """
        iut_classes = {}
        iut_dir = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / "services"
            / "iut"
        )
        self.logger.debug("Searching for IUT classes in %s", iut_dir)

        try:
            # Check if directory exists
            if not iut_dir.exists():
                self.logger.debug("IUT directory %s does not exist", iut_dir)
                return iut_classes

            for protocol_dir in iut_dir.iterdir():
                if protocol_dir.is_dir() and not protocol_dir.name.startswith("__"):
                    protocol_name = protocol_dir.name
                    iut_classes[protocol_name] = []

                    try:
                        # Use PluginManagerUtils.discover_plugins for each protocol directory
                        impl_files = PluginManagerUtils.discover_plugins(protocol_dir)
                        for impl_file in impl_files:
                            impl_name = impl_file.stem
                            self.logger.debug("Found IUT class: %s", impl_name)
                            iut_classes[protocol_name].append(
                                self._get_class_name(impl_name, "Config")
                            )
                    except Exception as e:
                        self.logger.debug(
                            "Error discovering IUT implementations in %s: %s",
                            protocol_dir,
                            e,
                        )
        except Exception as e:
            self.logger.debug("Error accessing IUT directory %s: %s", iut_dir, e)

        self.logger.debug("Total IUT classes found: %s", iut_classes)
        return iut_classes

    def get_all_tester_classes(self):
        """
        Get all tester classes from the plugin directory and return a list of tester classes.

        :return: A list of tester classes.
        """
        tester_classes = []
        tester_dir = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / "services"
            / "testers"
        )
        self.logger.debug("Searching for tester classes in %s", tester_dir)

        try:
            # Use PluginManagerUtils.discover_plugins utility for robust plugin discovery
            plugin_files = PluginManagerUtils.discover_plugins(tester_dir)
            for plugin_file in plugin_files:
                plugin_name = plugin_file.stem
                self.logger.debug("Found tester class: %s", plugin_name)
                tester_classes.append(self._get_class_name(plugin_name, "Config"))
        except Exception as e:
            self.logger.debug(
                "Error discovering tester plugins in %s: %s", tester_dir, e
            )

        self.logger.debug("Total tester classes found: %s", len(tester_classes))
        return tester_classes

    def load_all_plugins(self) -> Dict[str, List[str]]:
        """
        Load all plugins and return them in an ordered dictionary.
        Uses plugin_loader_utils for robust plugin discovery and loading.

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
            plugin_dir = (
                self._panther_dir
                / Path(self.global_config.paths.plugin_dir)
                / plugin_path
            )
            self.logger.debug("Searching for plugins in %s", plugin_dir)
            plugins = []

            try:
                if plugin_type == "iut":
                    # Handle nested IUT structure (protocol/implementation)
                    if plugin_dir.exists():
                        for protocol_dir in plugin_dir.iterdir():
                            if (
                                protocol_dir.is_dir()
                                and not protocol_dir.name.startswith("__")
                            ):
                                try:
                                    impl_files = PluginManagerUtils.discover_plugins(
                                        protocol_dir
                                    )
                                    for impl_file in impl_files:
                                        impl_name = impl_file.stem
                                        plugin_name = f"{protocol_dir.name}/{impl_name}"
                                        plugins.append(plugin_name)
                                        self.logger.debug(
                                            "Found IUT plugin: %s", plugin_name
                                        )

                                        # Attempt to load plugin for validation
                                        try:
                                            PluginManagerUtils.load_plugin_class(
                                                protocol_dir / impl_name, "Manager"
                                            )
                                        except Exception as e:
                                            self.logger.warning(
                                                "Failed to load IUT plugin %s: %s",
                                                plugin_name,
                                                e,
                                            )
                                except Exception as e:
                                    self.logger.debug(
                                        "Error discovering IUT implementations in %s: %s",
                                        protocol_dir,
                                        e,
                                    )
                elif plugin_type == "protocols":
                    # Handle nested protocol structure (protocol_type/protocol)
                    if plugin_dir.exists():
                        for protocol_type_dir in plugin_dir.iterdir():
                            if (
                                protocol_type_dir.is_dir()
                                and not protocol_type_dir.name.startswith("__")
                            ):
                                try:
                                    protocol_files = (
                                        PluginManagerUtils.discover_plugins(
                                            protocol_type_dir
                                        )
                                    )
                                    for protocol_file in protocol_files:
                                        protocol_name = protocol_file.stem
                                        plugin_name = (
                                            f"{protocol_type_dir.name}/{protocol_name}"
                                        )
                                        plugins.append(plugin_name)
                                        self.logger.debug(
                                            "Found protocol plugin: %s", plugin_name
                                        )

                                        # Attempt to load plugin for validation
                                        try:
                                            PluginManagerUtils.load_plugin_class(
                                                protocol_type_dir / protocol_name,
                                                "Config",
                                            )
                                        except Exception as e:
                                            self.logger.warning(
                                                "Failed to load protocol plugin %s: %s",
                                                plugin_name,
                                                e,
                                            )
                                except Exception as e:
                                    self.logger.debug(
                                        "Error discovering protocols in %s: %s",
                                        protocol_type_dir,
                                        e,
                                    )
                else:
                    # Handle flat plugin structure
                    try:
                        plugin_files = PluginManagerUtils.discover_plugins(plugin_dir)
                        for plugin_file in plugin_files:
                            plugin_name = plugin_file.stem
                            plugins.append(plugin_name)
                            self.logger.debug(
                                "Found %s plugin: %s", plugin_type, plugin_name
                            )

                            # Attempt to load plugin for validation
                            try:
                                expected_class = "Manager"
                                if plugin_type.endswith("_environment"):
                                    expected_class = "Config"

                                PluginManagerUtils.load_plugin_class(
                                    plugin_dir / plugin_name, expected_class
                                )
                            except Exception as e:
                                self.logger.warning(
                                    "Failed to load %s plugin %s: %s",
                                    plugin_type,
                                    plugin_name,
                                    e,
                                )
                    except Exception as e:
                        self.logger.debug(
                            "Error discovering %s plugins in %s: %s",
                            plugin_type,
                            plugin_dir,
                            e,
                        )

            except Exception as e:
                self.logger.debug(
                    "Error accessing plugin directory %s: %s", plugin_dir, e
                )
                plugins = []

            all_plugins[plugin_type] = sorted(plugins)

        return all_plugins

    def _auto_detect_plugin_type(
        self, plugin_name: str, protocol: str = None
    ) -> Optional[str]:
        """
        Auto-detect the plugin type by searching through the plugin directories.

        :param plugin_name: The plugin name to search for
        :param protocol: Optional protocol name for IUT/tester plugins
        :return: The detected plugin type or None if not found
        """
        # Get plugin directory path, using default if global_config is not loaded
        base_plugin_dir = (
            "plugins"
            if self.global_config is None
            else self.global_config.paths.plugin_dir
        )

        plugin_types_to_check = [
            ("network_environment", ["environments", "network_environment"]),
            ("execution_environment", ["environments", "execution_environment"]),
            ("iut", ["services", "iut"]),
            ("tester", ["services", "testers"]),
        ]

        for plugin_type, path_components in plugin_types_to_check:
            base_dir = self._panther_dir / Path(base_plugin_dir)
            for component in path_components:
                base_dir = base_dir / component

            if plugin_type in ["iut", "tester"]:
                # For IUT/tester plugins, search through protocol directories
                if base_dir.exists():
                    if protocol:
                        # Check specific protocol directory
                        potential_dir = base_dir / protocol / plugin_name
                        if potential_dir.exists():
                            return plugin_type

                    # Search through all protocol directories
                    for protocol_dir in base_dir.iterdir():
                        if protocol_dir.is_dir() and not protocol_dir.name.startswith(
                            "__"
                        ):
                            potential_dir = protocol_dir / plugin_name
                            if potential_dir.exists():
                                return plugin_type

                    # Check direct path (for plugins not nested under protocol)
                    potential_dir = base_dir / plugin_name
                    if potential_dir.exists():
                        return plugin_type
            else:
                # For environment plugins
                potential_dir = base_dir / plugin_name
                if potential_dir.exists():
                    return plugin_type

        return None

    def list_plugin_parameters(
        self, plugin_name: str, plugin_type: str = None, protocol: str = None
    ):
        """Delegate to new ConfigurationManager for listing plugin parameters.

        :param plugin_type: The plugin type (e.g., "network_environment", "execution_environment", "iut", "tester").
        :param plugin_name: The plugin name (e.g., "shadow_ns", "picoquic").
        :param protocol: Optional protocol name for IUT/tester plugins (e.g., "quic", "http").
        :return: Dictionary of parameters with their types, defaults, and descriptions.
        """
        # Auto-detect plugin type if not provided
        if plugin_type is None:
            plugin_type = self._auto_detect_plugin_type(plugin_name, protocol)
            if plugin_type is None:
                print(
                    f"Could not auto-detect plugin type for '{plugin_name}'. Please specify --plugin-type."
                )
                return {}

        # Use ConfigurationManager to list plugin parameters
        return self._config_manager.list_plugin_parameters(
            plugin_name, plugin_type, protocol
        )

    def construct_observer_config(self, loaded_config: DictConfig) -> BaseObserverConfig:  # noqa: ARG002
        """Delegate to new ConfigurationManager for observer config construction.

        Args:
            loaded_config (DictConfig): The loaded configuration dictionary.

        Returns:
            BaseObserverConfig: The constructed observer configuration.
        """
        # The new ConfigurationManager handles observer config as part of global config
        # This method is kept for backward compatibility but delegates to global config
        if not self.global_config:
            # Load global config if not already loaded
            self.global_config = self._config_manager.get_global_config()

        return self.global_config.observers if self.global_config else BaseObserverConfig()

    def _validate_test_fast_fail_config(self, test_config: TestConfig, test_data: dict):
        """Validate test-level fast-fail configuration."""
        if "fast_fail_enabled" in test_data:
            fast_fail_value = test_data["fast_fail_enabled"]

            # Validate the value is boolean
            if not isinstance(fast_fail_value, bool):
                raise ValueError(
                    f"Test '{test_config.name}': fast_fail_enabled must be a boolean, "
                    f"got {type(fast_fail_value).__name__}: {fast_fail_value}"
                )

            # Check if global config has test_level enabled
            if hasattr(self, "global_config") and self.global_config:
                if not self.global_config.fast_fail.test_level:
                    self.logger.warning(
                        "Test '%s' specifies fast_fail_enabled=%s but global "
                        "fast_fail.test_level is disabled. Test-level setting will be ignored.",
                        test_config.name,
                        fast_fail_value,
                    )

            self.logger.debug(
                "Test '%s' fast-fail configuration validated: enabled=%s",
                test_config.name,
                fast_fail_value,
            )
