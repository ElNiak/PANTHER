import importlib
import logging
import os
from pathlib import Path
import shutil
from omegaconf import DictConfig, OmegaConf, ValidationError, ListConfig
import yaml
from panther.config.config_global_schema import (
    DockerConfig,
    FeatureConfig,
    GlobalConfig,
    LoggingConfig,
    PathsConfig,
)
from panther.config.config_experiment_schema import (
    ExperimentConfig,
    ServiceConfig,
    TestConfig,
)
from panther.plugins.plugin_loader import PluginLoader
from importlib_resources import files

class ConfigLoader:
    def __init__(
        self,
        experiment_file: str,
        output_dir: str | None = None,
        exec_env_dir: str | None = "",
        net_env_dir: str | None = "",
        iut_dir: str | None = "",
        testers_dir: str | None = "",
    ):

        self.experiment_file = experiment_file
        self.output_dir = output_dir

        self.exec_env_dir = exec_env_dir
        self.net_env_dir = net_env_dir
        self.iut_dir = iut_dir
        self.testers_dir = testers_dir

        self.logger = logging.getLogger("ConfigLoader")
        self.global_config = None
        
        self._panther_dir = Path(os.path.dirname(__file__)).parent

    def construct_global_config(self, loaded_config: DictConfig) -> GlobalConfig:
        """_summary_

        Args:
            loaded_config (DictConfig): _description_

        Returns:
            ExperimentConfig: _description_
        """
        # Construct logging configuration
        logging_config = LoggingConfig(
            level=loaded_config["logging"]["level"],
            format=loaded_config["logging"]["format"],
        )
        OmegaConf.merge(LoggingConfig, logging_config)

        # Construct paths configuration
        paths_config = PathsConfig(
            output_dir=(
                loaded_config["paths"]["output_dir"]
                if not self.output_dir
                else self.output_dir
            ),
            log_dir=loaded_config["paths"]["log_dir"],
            config_dir=loaded_config["paths"]["config_dir"],
            plugin_dir=loaded_config["paths"]["plugin_dir"],
        )
        OmegaConf.merge(PathsConfig, paths_config)

        # TODO: Not used for now
        # optional_paths_config = AdditionalPathsConfig(
        #     exec_env_dir=self.exec_env_dir,
        #     net_env_dir=self.net_env_dir,
        #     iut_dir=self.iut_dir,
        #     testers_dir=self.testers_dir,
        # )

        self.add_plugin_execution_environment()

        self.add_plugin_network_environment()

        self.add_plugin_iut_service()

        self.add_plugin_tester_service()

        # Construct Docker configuration
        docker_config = DockerConfig(
            build_docker_image=loaded_config["docker"]["build_docker_image"]
        )
        OmegaConf.merge(DockerConfig, docker_config)
        
        if "features" not in loaded_config:
            feature_config = FeatureConfig()
        else:
            feature_config = FeatureConfig(
                logger_observer=loaded_config["features"]["logger_observer"] if "logger_observer" in loaded_config["features"] else True,
                storage_handler=loaded_config["features"]["storage_handler"] if "storage_handler" in loaded_config["features"] else True,
                fast_fail=loaded_config["features"]["fast_fail"] if "fast_fail" in loaded_config["features"] else True
            )
        OmegaConf.merge(FeatureConfig, feature_config)

        global_config = GlobalConfig(
            logging=logging_config,
            paths=paths_config,
            # optional_paths=optional_paths_config,
            docker=docker_config,
            features=feature_config
        )
        OmegaConf.merge(GlobalConfig, global_config)
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
                self._panther_dir , "plugins", "services", "testers", self.testers_dir.name
            )
            self.copy_plugin_files(testers_target_dir)

    def copy_plugin_files(self, testers_target_dir):
        """
        Copies plugin files from the source directory to the target directory.

        This method checks if the target directory exists, and if not, it creates it.
        It then iterates through all items in the source directory (self.testers_dir),
        and copies each item to the target directory. If an item is a directory, it
        recursively copies the entire directory. If an item is a file, it copies the file.

        Parameters:
        testers_target_dir (str): The path to the target directory where plugin files
                      should be copied.

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if not os.path.exists(os.path.join(self._panther_dir,testers_target_dir)):
            os.makedirs(testers_target_dir)
        for item in os.listdir(self.testers_dir):
            print(f"Copying {item} from {self.testers_dir} to {testers_target_dir}")
            s = os.path.join(self.testers_dir, item)
            d = os.path.join(testers_target_dir, item)
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
                 self._panther_dir, "plugins", "services", "testers", Path(self.testers_dir).name
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
            self.copy_plugin_files(iut_target_dir)

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
                 self._panther_dir , "plugins", "services", "iut", Path(self.iut_dir).name
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
            self.copy_plugin_files(net_env_target_dir)

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
            self.copy_plugin_files(exec_env_target_dir)

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
        self.logger.debug(
            f"Validating plugin configuration for {plugin_type}/{plugin_name} with {plugin_config}"
        )
        plugin_schema_class = self.load_plugin_schema(plugin_type, plugin_name)
        self.logger.debug(f"Plugin schema class: {plugin_schema_class}")
        structured_schema = OmegaConf.structured(plugin_schema_class)
        self.logger.debug(f"Structured schema: {structured_schema}")
        try:
            return OmegaConf.merge(structured_schema, plugin_config)
        except ValidationError as e:
            raise ValidationError(
                f"Plugin configuration validation failed for {plugin_type}/{plugin_name}: {e}"
            )

    def construct_experiment_config(
        self, loaded_config: DictConfig
    ) -> ExperimentConfig:
        """
        Manually construct an ExperimentConfig object from a loaded configuration.

        :param loaded_config: The loaded configuration dictionary (DictConfig or dict).
        :return: An ExperimentConfig object.
        """
        self.logger.info(
            f"Constructing experiment configuration with global configuration - {self.global_config}"
        )
        # Construct tests
        tests: list[TestConfig] = []
        for test_data in loaded_config["tests"]:
            # Construct network environment configuration
            network_env = test_data["network_environment"]
            self.logger.debug(f"Network environment: {network_env}")
            validated_network_env = self.validate_plugin_config(
                "network_environment", network_env["type"], network_env
            )
            self.logger.debug(
                f"Network environment after validation: {validated_network_env}"
            )

            exec_envs = test_data.get("execution_environment", [])
            self.logger.debug(f"Execution environment: {exec_envs}")
            for exec_env in exec_envs:
                validated_network_env = self.validate_plugin_config(
                    "execution_environment", exec_env["type"], exec_env
                )
            self.logger.debug(
                f"Network environment after validation: {validated_network_env}"
            )

            # Construct services for this test
            services: dict[str, ServiceConfig] = {}
            for service_name, service_data in test_data["services"].items():
                protocol = self.load_and_validate_protocol_config(
                    service_data
                )  # Resolve protocol subclass
                self.logger.debug(f"Protocol: {protocol}")
                implementation = self.load_and_validate_implementation_config(
                    service_data
                )
                self.logger.debug(f"Implementation: {implementation}")
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

    def load_and_validate_experiment_config(self) -> ExperimentConfig:
        """
        Load and validate the entire experiment configuration, including plugin-specific validation.

        :return: A validated experiment configuration.
        """
        experiment_config_path = self.experiment_file
        if not os.path.exists(experiment_config_path):
            raise FileNotFoundError(
                f"Experiment configuration file '{experiment_config_path}' not found."
            )

        try:
            # Load the YAML configuration
            loaded_config = OmegaConf.load(experiment_config_path)
            self.logger.debug(f"Loaded experiment config: {loaded_config}")
            self.logger.debug(OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)))
            experiment_config = self.construct_experiment_config(loaded_config)
            self.logger.debug(
                f"Constructed experiment config: {OmegaConf.to_yaml(experiment_config)}"
            )
            self.logger.info("Experiment configuration successfully validated.")
            return experiment_config
        except ValidationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
        except yaml.parser.ParserError as e:
            self.logger.error(f"YAML parsing error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during configuration loading: {e}")
            raise

    def load_and_validate_global_config(self) -> GlobalConfig:
        """
        Load and validate the entire experiment configuration, including plugin-specific validation.
        Note no logger is used here.

        :return: A validated experiment configuration.
        """
        experiment_config_path = self.experiment_file
        if not os.path.exists(experiment_config_path):
            raise FileNotFoundError(
                f"Experiment configuration file '{experiment_config_path}' not found."
            )

        try:
            # Load the YAML configuration
            loaded_config = OmegaConf.load(experiment_config_path)
            print(f"Loaded experiment config: {loaded_config}")
            print(OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)))
            global_config = self.construct_global_config(loaded_config)
            print(f"Constructed global config: {OmegaConf.to_yaml(global_config)}")
            print("Experiment configuration successfully validated.")
            return global_config
        except ValidationError as e:
            print(f"Configuration validation failed: {e}")
            raise
        except yaml.parser.ParserError as e:
            print(f"YAML parsing error: {e}")
            raise
        except Exception as e:
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
            class_name = PluginLoader.get_class_name(plugin_name)
            plugin_module = importlib.import_module(plugin_module_path)
            config_class = getattr(plugin_module, class_name)
            return config_class  # Assume PluginConfig is the schema class
        except ImportError:
            raise ImportError(f"Plugin schema '{plugin_module_path}' not found.")
        except AttributeError:
            raise ImportError(
                f"Plugin schema '{plugin_module_path}' does not define a 'PluginConfig' class."
            )

    def load_and_validate_protocol_config(
        self, implementation: ServiceConfig
    ) -> ListConfig | DictConfig:
        """
        Dynamically loads the appropriate implementation configuration class.

        :param implementation: A dictionary containing `name` and other fields.
        :return: An instance of the dynamically loaded configuration class.
        """
        self.logger.debug(f"Service: {implementation}")
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
                f"Protocol: {protocol} - {implementation['protocol']} - {config_class}"
            )
            protocol_instance = config_class(**implementation.protocol)
            return OmegaConf.merge(config_class, protocol_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load protocol config for '{protocol}': {e}")

    def load_and_validate_implementation_config(
        self, implementation: dict
    ) -> ListConfig | DictConfig:
        """
        Dynamically loads the appropriate implementation configuration class.
        """
        self.logger.debug(f"Implementation: {implementation}")
        name = implementation["implementation"]["name"]
        implem_type = implementation["implementation"]["type"]
        protocol = implementation["protocol"]["name"]
        protocol_version = implementation["protocol"]["version"]
        if implem_type == "iut":
            # Assuming schema files are in plugins
            module_path = f"panther.plugins.services.{implem_type}.{protocol}.{name}.config_schema"
        else:
            module_path = f"panther.plugins.services.{implem_type}.{name}.config_schema"

        self.logger.debug(f"Module path: {module_path}")
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            class_name = PluginLoader.get_class_name(name)
            config_class = getattr(schema_module, class_name)
            self.logger.debug(
                f"Implementation: {name} - {implementation['implementation']} - {config_class}"
            )

            # Load the version configuration
            version_class_name = PluginLoader.get_class_name(name, "Version")
            version_config_class = getattr(schema_module, version_class_name)
            # TODO cleanup  
            if implem_type == "iut":
                version_configs_dir = str(self._panther_dir).replace("/panther","") \
                    + "/" + \
                    module_path.replace(".", "/").replace(
                    "/config_schema", "/version_configs/"
                )
            else:
                version_configs_dir = str(self._panther_dir).replace("/panther","") \
                    + "/" + \
                    module_path.replace(".", "/").replace(
                    "/config_schema", f"/version_configs/{protocol}/"
                )

            version_path = os.path.join(version_configs_dir, f"{protocol_version}.yaml")
            if not os.path.exists(version_path):
                raise ValueError(
                    f"Version configuration file {version_path} not found."
                )
            raw_version_config = OmegaConf.load(version_path)
            self.logger.debug(
                f"Version config: {raw_version_config} - {version_config_class}"
            )
            protocol_version = OmegaConf.to_object(
                OmegaConf.merge(
                    OmegaConf.structured(version_config_class), raw_version_config
                )
            )

            implementation_instance = config_class(**implementation["implementation"])
            implementation_instance.version = protocol_version

            return OmegaConf.merge(config_class, implementation_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load implementation config for '{name}': {e}")

    def get_all_exec_env_classes(self):
        """
        Get all execution environment classes from the plugin directory.

        :return: A list of execution environment classes.
        """
        exec_env_classes = []
        exec_env_dir = (
            self._panther_dir /
            Path(self.global_config.paths.plugin_dir) /
            "environments" /
            "execution_environment"
        )
        self.logger.debug(
            f"Searching for execution environment classes in {exec_env_dir}"
        )
        for plugin_dir in exec_env_dir.iterdir():
            if plugin_dir.is_dir():
                plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                if plugin_file.exists():
                    self.logger.debug(
                        f"Found execution environment class: {plugin_dir.name}"
                    )
                    exec_env_classes.append(
                        PluginLoader.get_class_name(plugin_dir.name, "Config")
                    )
                else:
                    self.logger.debug(
                        f"No execution environment class found in {plugin_dir}"
                    )
        self.logger.debug(
            f"Total execution environment classes found: {len(exec_env_classes)}"
        )
        return exec_env_classes

    def get_all_net_env_classes(self):
        """
        Get all network environment classes from the plugin directory.

        :return: A list of network environment classes.
        """
        exec_env_classes = []
        exec_env_dir = (
            self._panther_dir /
            Path(self.global_config.paths.plugin_dir) /
            "environments" /
            "network_environment"
        )
        self.logger.debug(
            f"Searching for network environment classes in {exec_env_dir}"
        )
        for plugin_dir in exec_env_dir.iterdir():
            if plugin_dir.is_dir():
                plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                if plugin_file.exists():
                    self.logger.debug(
                        f"Found network environment class: {plugin_dir.name}"
                    )
                    exec_env_classes.append(
                        PluginLoader.get_class_name(plugin_dir.name, "Config")
                    )
                else:
                    self.logger.debug(
                        f"No network environment class found in {plugin_dir}"
                    )
        self.logger.debug(
            f"Total network environment classes found: {len(exec_env_classes)}"
        )
        return exec_env_classes

    def get_all_protocol_classes(self):
        """
        Get all protocol classes from the plugin directory.

        :return: A list of protocol classes.
        """
        protocol_classes = []
        protocol_dir =  self._panther_dir / Path(self.global_config.paths.plugin_dir) / "protocols"
        self.logger.debug(f"Searching for protocol classes in {protocol_dir}")
        for protocol_type_dir in protocol_dir.iterdir():
            if protocol_type_dir.is_dir():
                for protocol_dir in protocol_type_dir.iterdir():
                    if protocol_dir.is_dir():
                        protocol_file = protocol_dir / f"{protocol_dir.name}.py"
                        if protocol_file.exists():
                            self.logger.debug(
                                f"Found protocol class: {protocol_dir.name}"
                            )
                            protocol_classes.append(
                                PluginLoader.get_class_name(protocol_dir.name, "Config")
                            )
                        else:
                            self.logger.debug(
                                f"No protocol class found in {protocol_dir}"
                            )
        self.logger.debug(f"Total protocol classes found: {len(protocol_classes)}")
        return protocol_classes

    def get_all_iut_classes(self):
        """
        Get all IUT classes from the plugin directory and return a dictionary with protocols as keys and list of implementations as values.

        :return: A dictionary with protocols as keys and list of IUT classes as values.
        """
        iut_classes = {}
        iut_dir =  self._panther_dir / Path(self.global_config.paths.plugin_dir) / "services" / "iut"
        self.logger.debug(f"Searching for IUT classes in {iut_dir}")
        for protocol_dir in iut_dir.iterdir():
            if protocol_dir.is_dir():
                protocol_name = protocol_dir.name
                iut_classes[protocol_name] = []
                for plugin_dir in protocol_dir.iterdir():
                    if plugin_dir.is_dir() and not plugin_dir.name.startswith("__"):
                        plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                        if plugin_file.exists():
                            self.logger.debug(f"Found IUT class: {plugin_dir.name}")
                            iut_classes[protocol_name].append(
                                PluginLoader.get_class_name(plugin_dir.name, "Config")
                            )
                        else:
                            self.logger.debug(f"No IUT class found in {plugin_dir}")
        self.logger.debug(f"Total IUT classes found: {iut_classes}")
        return iut_classes

    def get_all_tester_classes(self):
        """
        Get all tester classes from the plugin directory and return a list of tester classes.

        :return: A list of tester classes.
        """
        tester_classes = []
        #tester_dir =  self.panther_dir / Path(self.global_config.paths.plugin_dir) / "services" / "testers"
        tester_dir = files(f'{self.global_config.paths.plugin_dir}.services.testers') # .joinpath('resource1.txt')
        self.logger.debug(f"Searching for tester classes in {tester_dir}")
        for plugin_dir in tester_dir.iterdir():
            if plugin_dir.is_dir():
                plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                if plugin_file.exists():
                    self.logger.debug(f"Found tester class: {plugin_dir.name}")
                    tester_classes.append(
                        PluginLoader.get_class_name(plugin_dir.name, "Config")
                    )
                else:
                    self.logger.debug(f"No tester class found in {plugin_dir}")
        self.logger.debug(f"Total tester classes found: {len(tester_classes)}")
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
            
            plugin_dir =  self._panther_dir / Path(self.global_config.paths.plugin_dir) / plugin_path
            self.logger.debug(f"Searching for plugins in {plugin_dir}")
            plugins = []
            if plugin_type == "iut":
                for protocol_dir in plugin_dir.iterdir():
                    if protocol_dir.is_dir() and not protocol_dir.name.startswith("__"):
                        for sub_dir in protocol_dir.iterdir():
                            if sub_dir.is_dir() and not sub_dir.name.startswith("__"):
                                plugin_file = sub_dir / f"{sub_dir.name}.py"
                                if plugin_file.exists():
                                    self.logger.debug(f"Found plugin: {sub_dir.name}")
                                    plugins.append(
                                        f"{protocol_dir.name}/{sub_dir.name}"
                                    )
                                    try:
                                        importlib.import_module(
                                            f"panther.plugins.{plugin_path.replace('/', '.')}.{protocol_dir.name}.{sub_dir.name}"
                                        )
                                    except ImportError as e:
                                        self.logger.error(
                                            f"Failed to load plugin {sub_dir.name}: {e}"
                                        )
            else:
                for sub_dir in plugin_dir.iterdir():
                    if sub_dir.is_dir() and not sub_dir.name.startswith("__"):
                        plugin_file = sub_dir / f"{sub_dir.name}.py"
                        if plugin_file.exists():
                            self.logger.debug(f"Found plugin: {sub_dir.name}")
                            plugins.append(sub_dir.name)
                            try:
                                importlib.import_module(
                                    f"panther.plugins.{plugin_path.replace('/', '.')}.{sub_dir.name}"
                                )
                            except ImportError as e:
                                self.logger.error(
                                    f"Failed to load plugin {sub_dir.name}: {e}"
                                )
            all_plugins[plugin_type] = sorted(plugins)

        return all_plugins
