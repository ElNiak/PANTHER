# PANTHER-SCP/panther/config/config.py

from dataclasses import fields, is_dataclass
import importlib
import logging
import os
from typing import Any, List, Optional, Dict, get_args, get_origin
from omegaconf import DictConfig, OmegaConf, ValidationError
import yaml

from config.config_schema import DockerConfig, ExperimentConfig, ImplementationConfig, LoggingConfig, PathsConfig, ProtocolConfig, ServiceConfig, TestConfig
from plugins.plugin_loader import PluginLoader


class ConfigLoader:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        # TODO setup logger and config in the ExperimentManager
        self.logger = logging.getLogger("ConfigLoader")
        self.experiment_config: Optional[DictConfig] = None

    def parse_service(self, service_config: dict) -> ServiceConfig:
        """
        Parse and validate a single service configuration dynamically.

        :param service_config: The dictionary representation of the service configuration.
        :return: A validated ServiceConfig instance.
        """
        print(f"Parsing service: {service_config}")
        # Dynamically load the implementation configuration
        implementation_instance = PluginLoader.load_implementation_config(service_config)
        print(f"Parsed implementation: {implementation_instance}")

        # Parse and validate protocol configuration
        protocol_instance = PluginLoader.load_protocol_config(service_config) 
        
        print(f"Parsed protocol: {protocol_instance}")

        # Create and validate the ServiceConfig
        service_instance = ServiceConfig(
            name=service_config["name"],
            implementation=implementation_instance,
            protocol=protocol_instance,
            ports=service_config.get("ports", [])
        )
        print(f"Parsed service: {service_instance}")
        return service_instance

    # def validate_test_config(self, test_config: dict):
    #     """
    #     Validate a single test configuration, including services and plugins.

    #     :param test_config: A dictionary representing the test configuration.
    #     """
    #     print(f"Validating test: {test_config['name']}")

    #     # Parse services
    #     for service_name, service in test_config["services"].items():
    #         self.parse_service(service)

    #     # TODO automatise with folder name
    #     # Validate network environment plugin
    #     if "network_environment" in test_config:
    #         network_env = test_config["network_environment"]
    #         validated_network_env = PluginLoader.validate_plugin_config(
    #             "network_environment", network_env["type"], network_env.get("settings", {})
    #         )
    #         network_env["settings"] = validated_network_env

    #     # Validate execution environment plugins
    #     if "execution_environment" in test_config:
    #         for exec_env in test_config["execution_environment"]:
    #             PluginLoader.validate_plugin_config(
    #                 "execution_environment", exec_env["type"], exec_env.get("settings", {})
    #             )
    
    # def validate_nested_dataclasses(self, schema: Any, config: Any) -> Any:
    #     """
    #     Recursively validates nested dataclasses within an OmegaConf DictConfig,
    #     resolving polymorphic fields dynamically.

    #     :param schema: The structured dataclass schema to validate against.
    #     :param config: The DictConfig object to validate.
    #     :return: The fully validated dataclass instance.
    #     """
    #     if not is_dataclass(schema):
    #         raise TypeError(f"Schema must be a dataclass, got {type(schema).__name__}")

    #     resolved_config = config.copy()

    #     for field in fields(schema):
    #         field_name = field.name
    #         field_type = field.type

    #         if field_name in config:
    #             value = config[field_name]

    #             print(f"Validating field: {field_name} with value: {value}")

    #             # Resolve origin and argument types
    #             origin_type = get_origin(field_type)
    #             args = get_args(field_type)

    #             # Handle lists of dataclasses or polymorphic types
    #             if origin_type is list and args:
    #                 item_type = args[0]
    #                 if is_dataclass(item_type):
    #                     # Validate each item in the list
    #                     resolved_list = [
    #                         self.validate_nested_dataclasses(item_type, item) if isinstance(item, dict) else item
    #                         for item in value
    #                     ]
    #                     resolved_config[field_name] = resolved_list
    #                     print(f"Resolved list for field: {field_name} -> {resolved_list}")
    #                 elif issubclass(item_type, ProtocolConfig):
    #                     # Handle polymorphic ProtocolConfig list
    #                     resolved_list = [
    #                         PluginLoader.load_protocol_config(item) for item in value
    #                     ]
    #                     resolved_config[field_name] = resolved_list
    #                     print(f"Resolved ProtocolConfig list for field: {field_name} -> {resolved_list}")

    #             # Handle polymorphic fields
    #             elif isinstance(value, dict) and issubclass(field_type, ProtocolConfig):
    #                 resolved_protocol = PluginLoader.load_protocol_config(value)
    #                 resolved_config[field_name] = resolved_protocol
    #                 print(f"Resolved ProtocolConfig for field: {field_name} -> {resolved_protocol}")

    #             # Recursively validate nested dataclasses
    #             elif is_dataclass(field_type) and isinstance(value, dict):
    #                 resolved_config[field_name] = self.validate_nested_dataclasses(field_type, value)
    #                 print(f"Resolved nested dataclass for field: {field_name} -> {resolved_config[field_name]}")

    #     # Merge resolved configuration with the structured schema
    #     final_config = OmegaConf.merge(OmegaConf.structured(schema), resolved_config)
    #     print(f"Final resolved configuration: {final_config}")
    #     return final_config


    def construct_experiment_config(self, loaded_config: DictConfig) -> ExperimentConfig:
        """
        Manually construct an ExperimentConfig object from a loaded configuration.

        :param loaded_config: The loaded configuration dictionary (DictConfig or dict).
        :return: An ExperimentConfig object.
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

        # Construct tests
        tests: List[TestConfig] = []
        for test_data in loaded_config["tests"]:
            # Construct network environment configuration
            network_env = test_data["network_environment"]
            print(f"Network environment: {network_env}")
            validated_network_env = PluginLoader.validate_plugin_config(
                "network_environment", network_env["type"], network_env
            )
            print(f"Network environment after validation: {validated_network_env}")
            
            # Construct services for this test
            services: Dict[str, ServiceConfig] = {}
            for service_name, service_data in test_data["services"].items():
                implementation = PluginLoader.load_implementation_config(service_data) 
                OmegaConf.merge(ImplementationConfig, implementation)
                protocol = PluginLoader.load_protocol_config(service_data)   # Resolve protocol subclass
                OmegaConf.merge(ProtocolConfig, protocol)
                service = ServiceConfig(
                    name=service_data["name"],
                    implementation=implementation,
                    protocol=protocol,
                    ports=service_data.get("ports", []),
                    generate_new_certificates=service_data.get("generate_new_certificates", False)
                )
                OmegaConf.merge(ServiceConfig, service)
                services[service_name] = service

            # Construct the test configuration
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
            # Thus we prelinarily validate the network environment configuration
            
            test = TestConfig(
                name=test_data["name"],
                description=test_data["description"],
                network_environment=network_env,
                execution_environment=test_data.get("execution_environment", []),
                iterations=test_data["iterations"],
                services=services,
                steps=test_data.get("steps"),
                assertions=test_data.get("assertions"),
            )
            # OmegaConf.merge(TestConfig, test)
            tests.append(test)

        # Construct the ExperimentConfig
        experiment_config = ExperimentConfig(
            logging=logging_config,
            paths=paths_config,
            docker=docker_config,
            tests=tests,
        )
        return experiment_config


    def load_experiment_config(self) -> DictConfig:
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

            # # Parse and validate each test
            # for test in loaded_config["tests"]:
            #     self.validate_test_config(test)

            print(f"Loaded experiment config: {loaded_config}")
            print(OmegaConf.to_yaml(OmegaConf.structured(ExperimentConfig)))
            # Validate against the base structured schema
            # experiment_config = self.validate_nested_dataclasses(ExperimentConfig, loaded_config)
            # TODO error with nested dataclasses
            # experiment_config = OmegaConf.merge(OmegaConf.structured(ExperimentConfig), loaded_config)
            
            experiment_config = self.construct_experiment_config(loaded_config)
            print(f"Constructed experiment config: {OmegaConf.to_yaml(experiment_config)}")
            self.logger.info("Experiment configuration successfully validated.")
            # exit()
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

    def load_plugin_schema(self, plugin_type: str, plugin_name: str):
        """
        Dynamically load a plugin schema based on its type and name.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :return: The plugin's schema module.
        """
        plugin_module_path = f"panther.plugins.environments.{plugin_type}.{plugin_name}.config_schema"
        try:
            plugin_module = importlib.import_module(plugin_module_path)
            return plugin_module
        except ImportError as e:
            self.logger.error(f"Plugin schema '{plugin_module_path}' not found: {e}")
            raise

    def get_config(self, config_name: str) -> DictConfig:
        """
        Load a specific configuration file by name.

        :param config_name: Name of the configuration file (without .yaml extension).
        :return: A DictConfig object representing the specified configuration.
        """
        config_path = os.path.join(self.config_dir, f"{config_name}.yaml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
        return OmegaConf.load(config_path)
