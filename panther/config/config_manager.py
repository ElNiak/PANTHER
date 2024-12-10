# PANTHER-SCP/panther/config/config.py

from dataclasses import fields, is_dataclass
import importlib
import logging
import os
from typing import Any, List, Optional, Dict, get_args, get_origin
from omegaconf import DictConfig, OmegaConf, ValidationError
import yaml

from config.config_global_schema import DockerConfig, GlobalConfig, LoggingConfig, PathsConfig
from config.config_experiment_schema import ExperimentConfig, ServiceConfig, TestConfig
from plugins.protocols.config_schema import ProtocolConfig
from plugins.services.iut.config_schema import ImplementationConfig
from plugins.plugin_loader import PluginLoader

class ConfigLoader:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        # TODO setup logger and config in the ExperimentManager
        self.logger = logging.getLogger("ConfigLoader")
        self.global_config = None

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
            output_dir=loaded_config["paths"]["output_dir"],
            log_dir=loaded_config["paths"]["log_dir"],
            config_dir=loaded_config["paths"]["config_dir"],
            plugin_dir=loaded_config["paths"]["plugin_dir"],
        )
        OmegaConf.merge(PathsConfig, paths_config)

        # Construct Docker configuration
        docker_config = DockerConfig(
            build_docker_image=loaded_config["docker"]["build_docker_image"]
        )
        OmegaConf.merge(DockerConfig, docker_config)
        
        global_config = GlobalConfig(
            logging=logging_config,
            paths=paths_config,
            docker=docker_config,
        )
        OmegaConf.merge(GlobalConfig, global_config)
        self.global_config = global_config
        return global_config
    
    def validate_plugin_config(self, plugin_type: str, plugin_name: str, plugin_config: DictConfig):
        """
        Validate plugin-specific configuration against its schema.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :param plugin_config: The plugin configuration to validate.
        :return: Validated plugin configuration.
        :raises ValidationError: If the configuration does not conform to the schema.
        """
        self.logger.debug(f"Validating plugin configuration for {plugin_type}/{plugin_name} with {plugin_config}")
        plugin_schema_class = self.load_plugin_schema(plugin_type, plugin_name)
        self.logger.debug(f"Plugin schema class: {plugin_schema_class}")
        structured_schema   = OmegaConf.structured(plugin_schema_class)
        self.logger.debug(f"Structured schema: {structured_schema}")
        try:
            return OmegaConf.merge(structured_schema, plugin_config)
        except ValidationError as e:
            raise ValidationError(
                f"Plugin configuration validation failed for {plugin_type}/{plugin_name}: {e}"
            )
    
    def construct_experiment_config(self, loaded_config: DictConfig) -> ExperimentConfig:
        """
        Manually construct an ExperimentConfig object from a loaded configuration.

        :param loaded_config: The loaded configuration dictionary (DictConfig or dict).
        :return: An ExperimentConfig object.
        """
        self.logger.info(f"Constructing experiment configuration with global configuration - {self.global_config}")
        # Construct tests
        tests: List[TestConfig] = []
        for test_data in loaded_config["tests"]:
            # Construct network environment configuration
            network_env = test_data["network_environment"]
            self.logger.debug(f"Network environment: {network_env}")
            validated_network_env = self.validate_plugin_config("network_environment", network_env["type"], network_env)
            self.logger.debug(f"Network environment after validation: {validated_network_env}")
            
            exec_envs = test_data.get("execution_environment", [])
            self.logger.debug(f"Execution environment: {exec_envs}")
            for exec_env in exec_envs:
                validated_network_env = self.validate_plugin_config("execution_environment", exec_env["type"], exec_env)
            self.logger.debug(f"Network environment after validation: {validated_network_env}")
            
            # Construct services for this test
            services: Dict[str, ServiceConfig] = {}
            for service_name, service_data in test_data["services"].items():
                protocol = self.load_and_validate_protocol_config(service_data)   # Resolve protocol subclass
                self.logger.debug(f"Protocol: {protocol}")
                implementation = self.load_and_validate_implementation_config(service_data, protocol) 
                self.logger.debug(f"Implementation: {implementation}")
                service = ServiceConfig(
                    name=service_data["name"],
                    timeout=service_data.get("timeout", 100),
                    implementation=implementation,
                    protocol=protocol,
                    ports=service_data.get("ports", []),
                    generate_new_certificates=service_data.get("generate_new_certificates", False)
                )
                OmegaConf.merge(ServiceConfig, service)
                services[service_name] = service
            # Construct the test configuration:
            # NOTE: We do not validate with merge here, as the schema is not fully compatible with OmegaConf
            # It is because NetworkEnvironmentConfig is a dataclass, and OmegaConf does not support nested dataclasses
            # For example, let
            # class NetworkEnvironmentConfig:
            #     type: str
            # And:
            # class DockerComposeConfig(NetworkEnvironmentConfig):
            #     type: str    = "docker_compose"
            #     version: str = "3.8" # omegaconf.errors.ConfigKeyError: Key 'version' not in 'NetworkEnvironmentConfig'
            #     network_name: str = "default_network"
            #     service_prefix: Optional[str] = None  # Optional prefix for service names
            #     volumes: List[str] = field(default_factory=list)  # List of volume mounts
            #     environment: Dict[str, str] = field(default_factory=dict)  # Environment variables
            
            # Thus we prelinarily validate the network environment configuration,
            # It will thus ignore non defined fields in the schema -> not ideal for validation
            # We will need to find a way to validate nested dataclasses with OmegaConf
            # TODO if tests name is undefined, use the service name + other parameters
            # TODO if we use the validated version -> bugs (but it should be enough to validate format)
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


    def load_and_validate_experiment_config(self) -> DictConfig:
        """
        Load and validate the entire experiment configuration, including plugin-specific validation.

        :return: A validated experiment configuration.
        """
        experiment_config_path = os.path.join(self.config_dir, "experiment_config.yaml")
        if not os.path.exists(experiment_config_path):
            raise FileNotFoundError(f"Experiment configuration file '{experiment_config_path}' not found.")

        try:
            # Load the YAML configuration
            loaded_config = OmegaConf.load(experiment_config_path)
            self.logger.debug(f"Loaded experiment config: {loaded_config}")
            self.logger.debug(OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)))
            experiment_config = self.construct_experiment_config(loaded_config)
            self.logger.debug(f"Constructed experiment config: {OmegaConf.to_yaml(experiment_config)}")
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
    
    def load_and_validate_global_config(self) -> DictConfig:
        """
        Load and validate the entire experiment configuration, including plugin-specific validation.
        Note no logger is used here.

        :return: A validated experiment configuration.
        """
        experiment_config_path = os.path.join(self.config_dir, "experiment_config.yaml")
        if not os.path.exists(experiment_config_path):
            raise FileNotFoundError(f"Experiment configuration file '{experiment_config_path}' not found.")

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
        
    def load_plugin_schema(self, plugin_type: str, plugin_name: str):
        """
        Dynamically load a plugin schema based on its type and name.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :return: The plugin's schema module.
        :raises ImportError: If the schema module cannot be found.
        """
        plugin_module_path = f"plugins.environments.{plugin_type}.{plugin_name}.config_schema"
        try:
            class_name = PluginLoader.get_class_name(plugin_name)
            plugin_module = importlib.import_module(plugin_module_path)
            config_class = getattr(plugin_module, class_name)
            return config_class  # Assume PluginConfig is the schema class
        except ImportError:
            raise ImportError(f"Plugin schema '{plugin_module_path}' not found.")
        except AttributeError:
            raise ImportError(f"Plugin schema '{plugin_module_path}' does not define a 'PluginConfig' class.")

    
    def load_and_validate_protocol_config(self, implementation: ServiceConfig) -> ProtocolConfig:
        """
        Dynamically loads the appropriate implementation configuration class.
        
        :param implementation: A dictionary containing `name` and other fields.
        :return: An instance of the dynamically loaded configuration class.
        """
        self.logger.debug(f"Service: {implementation}")
        protocol      = implementation.protocol.name
        if hasattr(implementation.protocol, "protocol_type"):
            protocol_type = implementation.protocol.protocol_type
        else:
            protocol_type = "client_server" # TODO: Default to client-server for now
        module_path = f"plugins.protocols.{protocol_type}.{protocol}.config_schema"  # Assuming schema files are in plugins
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            config_class = getattr(schema_module, f"{protocol.capitalize()}Config")
            self.logger.debug(f"Protocol: {protocol} - {implementation['protocol']} - {config_class}")
            protocol_instance = config_class(**implementation.protocol)
            return OmegaConf.merge(config_class, protocol_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load protocol config for '{protocol}': {e}")
    
    def load_and_validate_implementation_config(self, implementation: dict, protocol_conf: ProtocolConfig) -> ImplementationConfig:
        """
        Dynamically loads the appropriate implementation configuration class.
        
        :param implementation: A dictionary containing `name` and other fields.
        :return: An instance of the dynamically loaded configuration class.
        """
        self.logger.debug(f"Implementation: {implementation} - {protocol_conf}")
        name = implementation["implementation"]["name"]
        type = implementation["implementation"]["type"]
        protocol = implementation["protocol"]["name"]
        protocol_version = implementation["protocol"]["version"]
        if type == "iut":
            module_path = f"plugins.services.{type}.{protocol}.{name}.config_schema"  # Assuming schema files are in plugins
        else:
            module_path = f"plugins.services.{type}.{name}.config_schema"
        
        self.logger.debug(f"Module path: {module_path}")
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            class_name = PluginLoader.get_class_name(name)
            config_class = getattr(schema_module, class_name)
            self.logger.debug(f"Implementation: {name} - {implementation['implementation']} - {config_class}")
            
            # Load the version configuration
            version_class_name = PluginLoader.get_class_name(name, "Version")
            version_config_class = getattr(schema_module, version_class_name)
            if type == "iut":
                version_configs_dir = module_path.replace(".","/").replace("/config_schema","/version_configs/")
            else:
                version_configs_dir = module_path.replace(".","/").replace("/config_schema",f"/version_configs/{protocol}/")
                
            version_path = os.path.join(version_configs_dir, f"{protocol_version}.yaml")
            if not os.path.exists(version_path):
                raise ValueError(f"Version configuration file {version_path} not found.")
            raw_version_config = OmegaConf.load(version_path)
            self.logger.debug(f"Version config: {raw_version_config} - {version_config_class}")
            protocol_version = OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(version_config_class), raw_version_config))
        
            implementation_instance = config_class(**implementation["implementation"])
            implementation_instance.version = protocol_version
    
            return OmegaConf.merge(config_class, implementation_instance)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load implementation config for '{name}': {e}")
    

