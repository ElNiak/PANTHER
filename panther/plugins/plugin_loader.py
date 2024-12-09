# PANTHER-SCP/panther/utils/plugin_loader.py

import importlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from omegaconf import DictConfig, OmegaConf, ValidationError
import yaml
from core.utils.docker_builder import DockerBuilder
from config.config_schema import ImplementationConfig


class PluginLoader:
    def __init__(self, plugins_base_dir: str = "plugins"):
        self.logger = logging.getLogger("PluginLoader")
        self.plugins_base_dir = Path(plugins_base_dir)
        self.docker_builder = DockerBuilder()
        self.built_images: Dict[str, str] = {}  # Maps implementation names to image tags
        self.protocol_plugins: Dict[str, Path] = {}
        self.environment_plugins: Dict[str, Path] = {}
        self.tester_plugins: Dict[str, Path] = {}
        self.dockerfiles = self.docker_builder.find_dockerfiles(self.plugins_base_dir)
        self.logger.info(f"Found Dockerfiles: {self.dockerfiles}")
        
    @staticmethod
    def load_plugin_schema(plugin_type: str, plugin_name: str):
        """
        Dynamically load a plugin schema based on its type and name.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :return: The plugin's schema module.
        :raises ImportError: If the schema module cannot be found.
        """
        plugin_module_path = f"plugins.environments.{plugin_type}.{plugin_name}.config_schema"
        try:
            class_name_parts = plugin_name.split("_")
            class_name_parts = [part.capitalize() for part in class_name_parts]
            class_name = "".join(class_name_parts) + "Config"
            plugin_module = importlib.import_module(plugin_module_path)
            config_class = getattr(plugin_module, class_name)
            return config_class  # Assume PluginConfig is the schema class
        except ImportError:
            raise ImportError(f"Plugin schema '{plugin_module_path}' not found.")
        except AttributeError:
            raise ImportError(f"Plugin schema '{plugin_module_path}' does not define a 'PluginConfig' class.")

    @staticmethod
    def load_implementation_config(implementation: dict) -> ImplementationConfig:
        """
        Dynamically loads the appropriate implementation configuration class.
        
        :param implementation: A dictionary containing `name` and other fields.
        :return: An instance of the dynamically loaded configuration class.
        """
        name = implementation["implementation"]["name"]
        type = implementation["implementation"]["type"]
        protocol = implementation["protocol"]["name"]
        if type == "iut":
            module_path = f"plugins.services.{type}.{protocol}.{name}.config_schema"  # Assuming schema files are in plugins
        else:
            module_path = f"plugins.services.{type}.{name}.config_schema"
        print(f"Module path: {module_path}")
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            class_name_parts = name.split("_")
            class_name_parts = [part.capitalize() for part in class_name_parts]
            class_name = "".join(class_name_parts) + "Config"
            config_class = getattr(schema_module, class_name)
            print(f"Implementation: {name} - {implementation['implementation']} - {config_class}")
            return config_class(**implementation["implementation"])
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load implementation config for '{name}': {e}")
    
    @staticmethod
    def load_protocol_config(implementation: dict) -> ImplementationConfig:
        """
        Dynamically loads the appropriate implementation configuration class.
        
        :param implementation: A dictionary containing `name` and other fields.
        :return: An instance of the dynamically loaded configuration class.
        """
        protocol = implementation["protocol"]["name"]
        module_path = f"plugins.services.iut.{protocol}.config_schema"  # Assuming schema files are in plugins
        try:
            # Import the module and dynamically get the class
            schema_module = importlib.import_module(module_path)
            config_class = getattr(schema_module, f"{protocol.capitalize()}Config")
            print(f"Protocol: {protocol} - {implementation['protocol']} - {config_class}")
            return config_class(**implementation["protocol"])
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to load protocol config for '{protocol}': {e}")
        
    @staticmethod
    def validate_plugin_config(plugin_type: str, plugin_name: str, plugin_config: DictConfig):
        """
        Validate plugin-specific configuration against its schema.

        :param plugin_type: The plugin type (e.g., "network_environment").
        :param plugin_name: The plugin name (e.g., "shadow_ns").
        :param plugin_config: The plugin configuration to validate.
        :return: Validated plugin configuration.
        :raises ValidationError: If the configuration does not conform to the schema.
        """
        print(f"Validating plugin configuration for {plugin_type}/{plugin_name} with {plugin_config}")
        plugin_schema_class = PluginLoader.load_plugin_schema(plugin_type, plugin_name)
        print(f"Plugin schema class: {plugin_schema_class}")
        structured_schema   = OmegaConf.structured(plugin_schema_class)
        try:
            return OmegaConf.merge(structured_schema, plugin_config)
        except ValidationError as e:
            raise ValidationError(
                f"Plugin configuration validation failed for {plugin_type}/{plugin_name}: {e}"
            )
            
    def build_docker_image(self, impl_name: str, version: Optional[str] = None):
        """
        Builds a Docker image for a given implementation and version.

        :param impl_name: Name of the implementation.
        :param version: Version of the implementation.
        """
        if impl_name in self.dockerfiles:
            dockerfile_path = self.dockerfiles[impl_name]
            # Load version-specific configurations from config.yaml
            config_path = dockerfile_path.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)

                impl_config = full_config.get(impl_name, {})
                if not version:
                    if "ivy" in impl_name:
                        versions = impl_config.get("quic",{}).get('versions', {})
                    else:
                        versions = impl_config.get('versions', {})
                else:
                    versions = {version: impl_config.get(version, {})}
                    
                self.logger.debug(f"Found configuration for implementation '{impl_name}': {versions}")
                for version, version_config in versions.items():
                    self.logger.info(f"Building image for implementation '{impl_name}' version '{version}'")
                    image_tag = self.docker_builder.build_image(
                        impl_name=impl_name,
                        version=version,
                        dockerfile_path=dockerfile_path,
                        context_path=dockerfile_path.parent,
                        config=version_config,
                        tag_version="latest"  # or use version if desired
                    )
                    if image_tag:
                        key = f"{impl_name}_{version}"
                        self.built_images[key] = image_tag
                    else:
                        self.logger.error(f"Image build failed for implementation '{impl_name}' version '{version}'")
            else:
                self.logger.error(f"Configuration file '{config_path}' does not exist for implementation '{impl_name}'. Skipping.")
                exit(1)
        else:
            self.logger.error(f"Dockerfile not found for implementation '{impl_name}' in {self.dockerfiles}. Skipping.")
            exit(1)
        
    def build_docker_image_from_path(self, path: Path, name: str, version: Optional[str] = None):
        """
        Builds a Docker image for a given implementation and version.

        :param impl_name: Name of the implementation.
        :param version: Version of the implementation.
        """
        self.logger.info(f"Building image from path '{path.name}'")
        dockerfile_path = path
        # Load version-specific configurations from config.yaml
        config_path = dockerfile_path.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)

            impl_config = full_config.get(path.name, {})
            if not version:
                if "ivy" in path.name:
                    versions = impl_config.get("quic",{}).get('versions', {})
                else:
                    versions = impl_config.get('versions', {})
            else:
                versions = {version: impl_config.get(version, {})}
                
            self.logger.debug(f"Found configuration for path '{path.name}': {versions}")
            for version, version_config in versions.items():
                self.logger.info(f"Building image for path '{path.name}' version '{version}'")
                image_tag = self.docker_builder.build_image(
                    impl_name=name,
                    version=version,
                    dockerfile_path=dockerfile_path,
                    context_path=dockerfile_path.parent,
                    config=version_config,
                    tag_version="latest"  # TODO or use version if desired
                )
                if image_tag:
                    key = f"{path.name}_{version}"
                    self.built_images[key] = image_tag
                else:
                    self.logger.error(f"Image build failed for implementation '{path.name}' version '{version}'")
                return image_tag
        else:
            self.logger.error(f"Configuration file '{config_path}' does not exist for implementation '{path.name}'. Skipping.")
            exit(1)
        
    
    def build_all_docker_images(self):
        """
        Finds and builds all Docker images from Dockerfiles using DockerBuilder.
        Updates the built_images dictionary with successful builds.
        """
        # TODO: should depend of the network environment, if shadow, we need a single container with all implems,
        # TODO: if docker compose, we need a container per implementation
        for impl_name, dockerfile_path in self.dockerfiles.items():
            # Load version-specific configurations from config.yaml
            config_path = dockerfile_path.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)

                impl_config = full_config.get(impl_name, {})
                if "ivy" in impl_name:
                    versions = impl_config.get("quic",{}).get('versions', {}) # TODO: multiple prototocol
                else:
                    versions = impl_config.get('versions', {})
                    
                self.logger.debug(f"Found configuration for implementation '{impl_name}': {versions}")
                for version, version_config in versions.items():
                    self.logger.info(f"Building image for implementation '{impl_name}' version '{version}'")
                    image_tag = self.docker_builder.build_image(
                        impl_name=impl_name,
                        version=version,
                        dockerfile_path=dockerfile_path,
                        context_path=dockerfile_path.parent,
                        config=version_config,
                        tag_version="latest"  # or use version if desired
                    )
                    if image_tag:
                        key = f"{impl_name}_{version}"
                        self.built_images[key] = image_tag
                    else:
                        self.logger.error(f"Image build failed for implementation '{impl_name}' version '{version}'")
            else:
                self.logger.error(f"Configuration file '{config_path}' does not exist for implementation '{impl_name}'. Skipping.")

            

    def get_implementations_for_protocol(self, protocol: str) -> List[str]:
        """
        Retrieves a list of implementations under a given protocol.

        :param protocol: Name of the protocol.
        :return: List of implementation names.
        """
        implementations = []
        implementations_dir = self.plugins_base_dir  / "services" / "iut" / protocol
        self.logger.debug(f"Checking for implementations in '{implementations_dir}'")
        if implementations_dir and implementations_dir.exists():
            for item in implementations_dir.iterdir():
                if item.is_dir() and not item.name.startswith('__') and item.name != "templates":
                    implementations.append(item.name)
            self.logger.debug(f"Found implementations for protocol '{protocol}': {implementations}")
        else:
            self.logger.warning(f"Protocol plugin '{protocol}' not found or does not exist.")
        return implementations
    
    def get_testers(self) -> List[str]:
        """
        Retrieves a list of implementations under a given protocol.

        :param protocol: Name of the protocol.
        :return: List of implementation names.
        """
        implementations = []
        implementations_dir = self.plugins_base_dir  / "services" / "testers" 
        self.logger.debug(f"Checking for testers in '{implementations_dir}'")
        for item in implementations_dir.iterdir():
            self.logger.debug(f"Checking item '{item}'")
            if item.is_dir() and not item.name.startswith('__') and item.name != "templates":
                implementations.append(item.name)
        self.logger.debug(f"Found testers: {implementations}")
        return implementations
    
    def load_plugins(self):
        """
        Discovers and registers all protocol and environment plugins.
        """
        self.logger.debug(f"Loading plugins from base directory '{self.plugins_base_dir}'")

        # Discover protocol plugins
        protocols_dir = self.plugins_base_dir / "services" / "iut"
        for protocol in protocols_dir.iterdir():
            self.logger.debug(f"Checking protocol plugin '{protocol}'")
            if protocol.is_dir() and not protocol.name.startswith('__'):
                if (protocol / f"{protocol.name}_plugin.py").exists():
                    self.protocol_plugins[protocol.name] = protocol
                    self.logger.debug(f"Discovered protocol plugin '{protocol.name}' at '{protocol}'")

        # Discover environment plugins
        environments_dir = self.plugins_base_dir / "environments"
        if environments_dir.exists() and environments_dir.is_dir():
            self.logger.debug(f"Checking environments directory '{environments_dir}'")
            for environment in environments_dir.iterdir():
                if environment.is_dir():
                    self.environment_plugins[environment.name] = {}
                    for item in environment.iterdir():
                        if item.is_dir() and not item.name.startswith('__'):
                            if (item / f"{item.name}_plugin.py").exists():
                                self.environment_plugins[environment.name][item.name] = item
                                self.logger.debug(f"Discovered environment plugin '{item.name}' at '{item}' under '{environment}'")
        else:
            self.logger.warning(f"Environments directory '{environments_dir}' does not exist.")
            
        # Discover testers plugins
        testers_dir = self.plugins_base_dir / "services" / "testers"
        if testers_dir.exists() and testers_dir.is_dir():
            self.logger.debug(f"Checking testers directory '{testers_dir}'")
            for testers in testers_dir.iterdir():
                if testers.is_dir() and not testers.name.startswith('__'):
                    if (testers / f"{testers.name}_plugin.py").exists():
                        self.tester_plugins[testers.name] = item
                        self.logger.debug(f"Discovered testers plugin '{testers.name}' at '{testers}'")
        else:
            self.logger.warning(f"Testers directory '{testers_dir}' does not exist.")
        
