"""Configuration management module for PANTHER framework.

This module handles loading, validating, and managing configurations for experiments
and plugins in the PANTHER framework.
"""

import importlib
import logging
import os
import shutil
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, get_type_hints

import yaml
from omegaconf import DictConfig, ListConfig, OmegaConf, ValidationError

from panther.config.config_experiment_schema import (
    ExperimentConfig,
    ServiceConfig,
    TestConfig,
)
from panther.config.config_global_schema import (
    AdditionalPathsConfig,
    DockerConfig,
    FastFailConfig,
    FeatureConfig,
    GlobalConfig,
    LoggingConfig,
    LoggingLevel,
    PathsConfig,
)
from panther.config.config_observer_schema import (
    ExperimentObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    ObserverConfig,
    StorageObserverConfig,
)
from panther.core.exceptions.experiment_exceptions import PluginValidationError
from panther.core.utils.config_summarizer import ConfigSummarizer
from panther.core.utils.feature_logger_mixin import get_feature_logger
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_config_resolver import PluginConfigResolver
from panther.plugins.plugin_loader_utils import PluginManagerUtils


class ConfigLoader(LoggerMixin):
    """Handles loading and validation of PANTHER configurations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize with config_processing feature
        self.__init_logger__("config_processing")

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

    def construct_global_config(self, loaded_config: DictConfig) -> GlobalConfig:
        """_summary_

        Args:
            loaded_config (DictConfig): _description_

        Returns:
            ExperimentConfig: _description_
        """
        # Construct logging configuration with defaults from dataclass
        default_logging = LoggingConfig()  # Get dataclass defaults
        level_str = loaded_config.get("logging", {}).get(
            "level", default_logging.level.name
        )
        # Convert string to LoggingLevel enum
        if isinstance(level_str, str):
            try:
                level = LoggingLevel[level_str.upper()]
            except KeyError:
                self.logger.warning(
                    "Invalid logging level '%s', using DEBUG", level_str
                )
                level = LoggingLevel.DEBUG
        else:
            level = (
                level_str
                if isinstance(level_str, type(LoggingLevel.DEBUG))
                else default_logging.level
            )

        # Extract feature levels from loaded config
        feature_levels_config = None
        if "feature_levels" in loaded_config.get("logging", {}):
            from panther.config.config_global_schema import FeatureLogLevelsConfig
            
            feature_levels_dict = loaded_config.get("logging", {}).get("feature_levels", {})
            feature_levels_kwargs = {}
            
            # Convert string levels to LoggingLevel enum
            for feature_name, level_str in feature_levels_dict.items():
                if isinstance(level_str, str):
                    try:
                        feature_levels_kwargs[feature_name] = LoggingLevel[level_str.upper()]
                    except KeyError:
                        self.logger.warning(
                            "Invalid logging level '%s' for feature '%s', using INFO", 
                            level_str, feature_name
                        )
                        feature_levels_kwargs[feature_name] = LoggingLevel.INFO
                else:
                    feature_levels_kwargs[feature_name] = level_str
            
            # Create FeatureLogLevelsConfig with user's values
            try:
                feature_levels_config = FeatureLogLevelsConfig(**feature_levels_kwargs)
            except TypeError as e:
                # Extract the invalid field name from the error message
                import re
                match = re.search(r"got an unexpected keyword argument '(\w+)'", str(e))
                if match:
                    invalid_field = match.group(1)
                    valid_fields = [f for f in dir(FeatureLogLevelsConfig) if not f.startswith('_')]
                    self.logger.error(
                        "Invalid feature name '%s' in feature_levels configuration. Valid names: %s",
                        invalid_field, ', '.join(sorted(valid_fields))
                    )
                    # Skip the invalid field and retry
                    feature_levels_kwargs.pop(invalid_field, None)
                    feature_levels_config = FeatureLogLevelsConfig(**feature_levels_kwargs)
                else:
                    raise
        
        # Create LoggingConfig with all fields including feature_levels
        logging_config = LoggingConfig(
            level=level,
            format=loaded_config.get("logging", {}).get(
                "format", default_logging.format
            ),
            enable_colors=loaded_config.get("logging", {}).get(
                "enable_colors", default_logging.enable_colors
            ),
            feature_levels=feature_levels_config if feature_levels_config else default_logging.feature_levels,
        )
        OmegaConf.merge(LoggingConfig, logging_config)

        # Construct paths configuration with defaults from dataclass
        default_paths = PathsConfig()  # Get dataclass defaults
        paths_config = PathsConfig(
            output_dir=(
                loaded_config.get("paths", {}).get(
                    "output_dir", default_paths.output_dir
                )
                if not self.output_dir
                else self.output_dir
            ),
            log_dir=loaded_config.get("paths", {}).get(
                "log_dir", default_paths.log_dir
            ),
            config_dir=loaded_config.get("paths", {}).get(
                "config_dir", default_paths.config_dir
            ),
            plugin_dir=loaded_config.get("paths", {}).get(
                "plugin_dir", default_paths.plugin_dir
            ),
            services_dir=loaded_config.get("paths", {}).get(
                "services_dir", default_paths.services_dir
            ),
            iut_dir=loaded_config.get("paths", {}).get(
                "iut_dir", default_paths.iut_dir
            ),
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
            # Check for deprecated fast_fail configuration and warn user
            if "fast_fail" in loaded_config.get("features", {}):
                self.logger.warning(
                    "Configuration 'features.fast_fail' is deprecated. "
                    "Use 'fast_fail.enabled' and 'fast_fail.test_level' instead."
                )

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
            )
        OmegaConf.merge(FeatureConfig, feature_config)

        # Construct observer configuration with defaults
        observer_config = self.construct_observer_config(loaded_config)

        # Construct fast-fail configuration with defaults from dataclass
        default_fast_fail = FastFailConfig()  # Get dataclass defaults
        fast_fail_config = FastFailConfig(
            enabled=loaded_config.get("fast_fail", {}).get(
                "enabled", default_fast_fail.enabled
            ),
            test_level=loaded_config.get("fast_fail", {}).get(
                "test_level", default_fast_fail.test_level
            ),
            docker_build_failures=loaded_config.get("fast_fail", {}).get(
                "docker_build_failures", default_fast_fail.docker_build_failures
            ),
            docker_runtime_failures=loaded_config.get("fast_fail", {}).get(
                "docker_runtime_failures", default_fast_fail.docker_runtime_failures
            ),
            plugin_load_failures=loaded_config.get("fast_fail", {}).get(
                "plugin_load_failures", default_fast_fail.plugin_load_failures
            ),
            service_start_failures=loaded_config.get("fast_fail", {}).get(
                "service_start_failures", default_fast_fail.service_start_failures
            ),
            network_setup_failures=loaded_config.get("fast_fail", {}).get(
                "network_setup_failures", default_fast_fail.network_setup_failures
            ),
            port_conflict_failures=loaded_config.get("fast_fail", {}).get(
                "port_conflict_failures", default_fast_fail.port_conflict_failures
            ),
            ivy_compilation_failures=loaded_config.get("fast_fail", {}).get(
                "ivy_compilation_failures", default_fast_fail.ivy_compilation_failures
            ),
            resource_exhaustion=loaded_config.get("fast_fail", {}).get(
                "resource_exhaustion", default_fast_fail.resource_exhaustion
            ),
            certificate_failures=loaded_config.get("fast_fail", {}).get(
                "certificate_failures", default_fast_fail.certificate_failures
            ),
            configuration_failures=loaded_config.get("fast_fail", {}).get(
                "configuration_failures", default_fast_fail.configuration_failures
            ),
            timeout_cascades=loaded_config.get("fast_fail", {}).get(
                "timeout_cascades", default_fast_fail.timeout_cascades
            ),
            critical_only=loaded_config.get("fast_fail", {}).get(
                "critical_only", default_fast_fail.critical_only
            ),
            max_errors_before_fail=loaded_config.get("fast_fail", {}).get(
                "max_errors_before_fail", default_fast_fail.max_errors_before_fail
            ),
            timeout_cascade_threshold=loaded_config.get("fast_fail", {}).get(
                "timeout_cascade_threshold", default_fast_fail.timeout_cascade_threshold
            ),
            disk_space_threshold_gb=loaded_config.get("fast_fail", {}).get(
                "disk_space_threshold_gb", default_fast_fail.disk_space_threshold_gb
            ),
        )
        OmegaConf.merge(FastFailConfig, fast_fail_config)

        global_config = GlobalConfig(
            logging=logging_config,
            paths=paths_config,
            optional_paths=optional_paths_config,
            docker=docker_config,
            features=feature_config,
            observers=observer_config,
            fast_fail=fast_fail_config,
        )
        OmegaConf.merge(GlobalConfig, global_config)
        if self.debug_override:
            global_config.logging.level = LoggingLevel.DEBUG
        self.global_config = global_config
        return global_config

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
        """
        Validate plugin-specific configuration against its schema.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :param plugin_config: The plugin configuration to validate.
        :return: Validated plugin configuration.
        :raises ValidationError: If the configuration does not conform to the schema.
        """
        # Log plugin validation with smart summarization
        plugin_config_dict = (
            OmegaConf.to_container(plugin_config)
            if isinstance(plugin_config, DictConfig)
            else plugin_config
        )
        self.log_with_context(
            logging.DEBUG,
            f"Validating plugin configuration for {plugin_type}/{plugin_name}",
            plugin_type=plugin_type,
            plugin_name=plugin_name,
            config_summary=(
                ConfigSummarizer.summarize(plugin_config_dict)
                if isinstance(plugin_config_dict, dict)
                else str(plugin_config_dict)
            ),
        )
        plugin_schema_class = self.load_plugin_schema(plugin_type, plugin_name)
        self.logger.debug("Plugin schema class: %s", plugin_schema_class)
        structured_schema = OmegaConf.structured(plugin_schema_class)
        self.logger.debug("Structured schema: %s", structured_schema)

        # Check for unknown parameters
        if hasattr(plugin_schema_class, "__dataclass_fields__"):
            valid_params = set(plugin_schema_class.__dataclass_fields__.keys())
            provided_params = (
                set(plugin_config.keys())
                if isinstance(plugin_config, DictConfig)
                else set()
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

                # Provide helpful information about valid parameters using smart logging
                self.log_with_context(
                    logging.INFO,
                    f"Valid parameters for {plugin_type}/{plugin_name}",
                    parameters=sorted(valid_params),
                    count=len(valid_params),
                )
                self.logger.info(
                    "Use --list-plugin-params %s to see parameter details", plugin_name
                )

        try:
            return OmegaConf.merge(structured_schema, plugin_config)
        except ValidationError as e:
            # Enhanced error message with helpful information
            error_msg = f"Plugin configuration validation failed for {plugin_type}/{plugin_name}: {e}"
            error_msg += f"\n\nTo see valid parameters, run: python -m panther --list-plugin-params {plugin_name}"
            if plugin_type in ["iut", "tester"]:
                error_msg += f" --plugin-type {plugin_type}"
            raise ValidationError(error_msg) from e

    def construct_experiment_config(
        self, loaded_config: DictConfig
    ) -> ExperimentConfig:
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
        tests: List[TestConfig] = []
        for test_data in loaded_config["tests"]:
            # Construct network environment configuration
            network_env = test_data["network_environment"]
            self.logger.debug("Network environment: %s", network_env)
            validated_network_env = self.validate_plugin_config(
                "network_environment", network_env["type"], network_env
            )
            self.logger.debug(
                "Network environment after validation: %s", validated_network_env
            )

            exec_envs = test_data.get("execution_environment", [])
            self.logger.debug("Execution environment: %s", exec_envs)
            for exec_env in exec_envs:
                validated_network_env = self.validate_plugin_config(
                    "execution_environment", exec_env["type"], exec_env
                )
            self.logger.debug(
                "Network environment after validation: %s", validated_network_env
            )

            # Construct services for this test
            services: Dict[str, ServiceConfig] = {}
            for service_name, service_data in test_data["services"].items():
                protocol = self.load_and_validate_protocol_config(
                    service_data
                )  # Resolve protocol subclass
                self.logger.debug("Protocol: %s", protocol)
                implementation = self.load_and_validate_implementation_config(
                    service_data
                )
                self.logger.debug("Implementation: %s", implementation)
                service = ServiceConfig(
                    name=service_data["name"],
                    timeout=service_data.get("timeout", 100),
                    implementation=implementation,
                    protocol=protocol,
                    ports=service_data.get("ports", []),
                    generate_new_certificates=service_data.get(
                        "generate_new_certificates", False
                    ),
                )
                OmegaConf.merge(ServiceConfig, service)
                services[service_name] = service

            # ##########################################################################################################
            # Construct the test configuration:
            # NOTE: We do not validate with merge here, as the schema is not fully compatible with OmegaConf
            # NetworkEnvironmentConfig is a dataclass, and OmegaConf does not support nested dataclasses
            # This can cause ConfigKeyError when trying to access subclass-specific fields
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
                fast_fail_enabled=test_data.get("fast_fail_enabled"),
            )

            # Validate test-level fast-fail configuration
            self._validate_test_fast_fail_config(test, test_data)

            tests.append(test)

        # Construct the ExperimentConfig
        experiment_config = ExperimentConfig(
            tests=tests,
        )
        return experiment_config

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
                    with self.metrics_collector.time_operation(
                        "experiment_yaml_parsing"
                    ):
                        loaded_config = OmegaConf.load(experiment_config_path)
                else:
                    loaded_config = OmegaConf.load(experiment_config_path)

                # Use smart config logging
                self.log_config(
                    OmegaConf.to_container(loaded_config)
                    if isinstance(loaded_config, DictConfig)
                    else loaded_config
                )
                self.logger.debug(
                    OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig))
                )

                # Construct experiment config with timing
                if self.metrics_collector:
                    with self.metrics_collector.time_operation(
                        "experiment_config_construction"
                    ):
                        experiment_config = self.construct_experiment_config(
                            loaded_config
                        )
                else:
                    experiment_config = self.construct_experiment_config(loaded_config)

                self.logger.debug("Experiment config type: %s", type(experiment_config))

                # Only try to serialize if we have a valid dataclass
                if experiment_config and hasattr(
                    experiment_config, "__dataclass_fields__"
                ):
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
                        "Experiment config is not a valid dataclass: %s",
                        experiment_config,
                    )

                # Validate plugin availability
                if self.metrics_collector:
                    with self.metrics_collector.time_operation(
                        "plugin_availability_validation"
                    ):
                        is_valid, plugin_errors = self.validate_plugins_availability(
                            experiment_config
                        )
                else:
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
                self.logger.error(
                    "Unexpected error during configuration loading: %s", e
                )
                raise

    def load_and_validate_global_config(self) -> GlobalConfig:
        """
        Load and validate the global configuration from the experiment configuration file.
        Note no logger is used here.

        :return: A validated global configuration.
        """
        if self.metrics_collector:
            self.metrics_collector.increment_counter("config_loads_total")
            config_timer = self.metrics_collector.start_timing(
                "global_config_loading_time"
            )

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
                    "Loading global configuration with metrics from %s",
                    experiment_config_path,
                )
                with self.metrics_collector.time_operation("yaml_parsing"):
                    loaded_config = OmegaConf.load(experiment_config_path)
            else:
                loaded_config = OmegaConf.load(experiment_config_path)

            # Use smart logging for loaded config display
            loaded_config_dict = (
                OmegaConf.to_container(loaded_config)
                if isinstance(loaded_config, DictConfig)
                else loaded_config
            )
            summary = (
                ConfigSummarizer.summarize(loaded_config_dict)
                if isinstance(loaded_config_dict, dict)
                else str(loaded_config_dict)
            )
            print(f"Loaded experiment config: {summary}")
            # Schema is logged at DEBUG level if needed
            self.logger.debug(
                "ExperimentConfig schema:\n%s",
                OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)),
            )

            # Construct global config with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(
                    "global_config_construction"
                ):
                    global_config = self.construct_global_config(loaded_config)
            else:
                global_config = self.construct_global_config(loaded_config)

            # Convert dataclass to dict for YAML serialization
            global_config_dict = asdict(global_config)
            # Use smart logging for global config display
            global_config_container = (
                OmegaConf.to_container(global_config_dict)
                if isinstance(global_config_dict, DictConfig)
                else global_config_dict
            )
            global_summary = (
                ConfigSummarizer.summarize(global_config_container)
                if isinstance(global_config_container, dict)
                else str(global_config_container)
            )
            print(f"Constructed global config: {global_summary}")
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
        Get all IUT classes from the plugin directory and return a dictionary with protocols as keys and list of implementations as values.

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
        """
        List all configurable parameters for a specified plugin.
        Uses plugin_loader_utils for robust plugin loading.

        :param plugin_type: The plugin type (e.g., "network_environment", "execution_environment", "iut", "tester").
        :param plugin_name: The plugin name (e.g., "shadow_ns", "picoquic").
        :param protocol: Optional protocol name for IUT/tester plugins (e.g., "quic", "http").
        :return: Dictionary of parameters with their types, defaults, and descriptions.
        """
        try:
            # Auto-detect plugin type if not provided
            if plugin_type is None:
                plugin_type = self._auto_detect_plugin_type(plugin_name, protocol)
                if plugin_type is None:
                    print(
                        f"Could not auto-detect plugin type for '{plugin_name}'. Please specify --plugin-type."
                    )
                    return {}

            # Get plugin directory path, using default if global_config is not loaded
            base_plugin_dir = (
                "plugins"
                if self.global_config is None
                else self.global_config.paths.plugin_dir
            )

            # Determine plugin directory path
            if plugin_type in ["iut", "tester"]:
                base_dir = (
                    self._panther_dir / Path(base_plugin_dir) / "services" / plugin_type
                )

                # For IUT/tester plugins, try to find the correct path
                plugin_path = None
                if protocol:
                    # Try with specified protocol first
                    potential_dir = base_dir / protocol / plugin_name
                    if potential_dir.exists():
                        plugin_path = potential_dir

                if not plugin_path:
                    # Search through all protocol directories
                    if base_dir.exists():
                        for protocol_dir in base_dir.iterdir():
                            if (
                                protocol_dir.is_dir()
                                and not protocol_dir.name.startswith("__")
                            ):
                                potential_dir = protocol_dir / plugin_name
                                if potential_dir.exists():
                                    plugin_path = potential_dir
                                    break

                    # Try direct path (for plugins not nested under protocol)
                    if not plugin_path:
                        potential_dir = base_dir / plugin_name
                        if potential_dir.exists():
                            plugin_path = potential_dir

            else:
                # For environment plugins
                plugin_path = (
                    self._panther_dir
                    / Path(base_plugin_dir)
                    / "environments"
                    / plugin_type
                    / plugin_name
                )

            if not plugin_path or not plugin_path.exists():
                error_msg = f"Plugin directory not found for {plugin_name}"
                if protocol:
                    error_msg += f" (protocol: {protocol})"
                raise FileNotFoundError(error_msg)

            # Load the config schema module
            schema_file = plugin_path / "config_schema.py"
            if not schema_file.exists():
                raise FileNotFoundError(f"Config schema file not found: {schema_file}")

            try:
                # Use plugin_loader_utils to load the module
                schema_module = PluginManagerUtils.load_module_from_file(
                    schema_file, f"{plugin_name}_config_schema"
                )

                # Get the config class using the naming convention
                class_name = self._get_class_name(plugin_name, "Config")
                config_class = PluginManagerUtils.get_class_from_module(
                    schema_module, class_name
                )

                self.logger.debug("Found plugin config class: %s", class_name)

            except Exception as e:
                self.logger.error(
                    "Failed to load plugin schema for %s: %s", plugin_name, e
                )
                raise

            # Extract parameters using dataclasses introspection
            parameters = {}

            import dataclasses  # pylint: disable=import-outside-toplevel
            import inspect  # pylint: disable=import-outside-toplevel

            if dataclasses.is_dataclass(config_class):
                fields = dataclasses.fields(config_class)
                type_hints = get_type_hints(config_class)

                for field in fields:
                    param_info = {
                        "type": str(type_hints.get(field.name, "unknown")),
                        "default": (
                            field.default
                            if field.default is not dataclasses.MISSING
                            else None
                        ),
                        "required": field.default is dataclasses.MISSING,
                        "description": inspect.getdoc(field)
                        or "No description available",
                    }
                    parameters[field.name] = param_info
            else:
                self.logger.warning("Config class %s is not a dataclass", class_name)

            return parameters

        except (FileNotFoundError, ImportError) as e:
            print(
                f"Plugin schema for '{plugin_name}' not found. Check if the plugin name is correct."
            )
            print(f"Error details: {e}")

            # Provide helpful guidance for IUT/tester plugins
            if plugin_type in ["iut", "tester"]:
                print(
                    "\nFor IUT/tester plugins, try specifying the protocol if applicable."
                )
                print("Example: quiche is under the 'quic' protocol, so use:")
                print(
                    f"panther --list-plugin-params {plugin_name} --plugin-type {plugin_type} --protocol quic"
                )

            return {}
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Unexpected error while listing parameters for plugin '%s': %s",
                plugin_name,
                e,
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
                    include_event_id=observers_dict["logger"].get(
                        "include_event_id", True
                    ),
                    include_timestamp=observers_dict["logger"].get(
                        "include_timestamp", True
                    ),
                    enable_colors=observers_dict["logger"].get("enable_colors", True),
                    output_file=observers_dict["logger"].get("output_file"),
                    correlation_tracking=observers_dict["logger"].get(
                        "correlation_tracking", True
                    ),
                    structured_output=observers_dict["logger"].get(
                        "structured_output", False
                    ),
                    max_data_length=observers_dict["logger"].get(
                        "max_data_length", 500
                    ),
                )
                observer_config.logger = logger_config

            # Configure metrics observer if present
            if "metrics" in observers_dict:
                metrics_config = MetricsObserverConfig(
                    enabled=observers_dict["metrics"].get("enabled", True),
                    auto_register=observers_dict["metrics"].get("auto_register", True),
                    priority=observers_dict["metrics"].get("priority", 10),
                    log_level=observers_dict["metrics"].get("log_level", "INFO"),
                    publish_metrics=observers_dict["metrics"].get(
                        "publish_metrics", True
                    ),
                    collect_system_metrics=observers_dict["metrics"].get(
                        "collect_system_metrics", True
                    ),
                    publish_interval=observers_dict["metrics"].get(
                        "publish_interval", 30
                    ),
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
                    enable_compression=observers_dict["storage"].get(
                        "enable_compression", True
                    ),
                    max_storage_size=observers_dict["storage"].get(
                        "max_storage_size", 0
                    ),
                    auto_backup=observers_dict["storage"].get("auto_backup", True),
                    backup_interval=observers_dict["storage"].get(
                        "backup_interval", 3600
                    ),
                    retention_days=observers_dict["storage"].get("retention_days", 30),
                    batch_size=observers_dict["storage"].get("batch_size", 100),
                    async_storage=observers_dict["storage"].get("async_storage", False),
                )
                observer_config.storage = storage_config

            # Configure experiment observer if present
            if "experiment" in observers_dict:
                experiment_config = ExperimentObserverConfig(
                    enabled=observers_dict["experiment"].get("enabled", True),
                    auto_register=observers_dict["experiment"].get(
                        "auto_register", True
                    ),
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
