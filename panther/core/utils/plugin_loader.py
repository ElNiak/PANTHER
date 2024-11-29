# PANTHER-SCP/panther/utils/plugin_loader.py

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from core.utils.docker_builder import DockerBuilder


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
            self.logger.error(f"Configuration file '{config_path}' does not exist for implementation '{impl_name}'. Skipping.")
            exit(1)
        
    def build_docker_image_from_path(self, path: Path, version: Optional[str] = None):
        """
        Builds a Docker image for a given implementation and version.

        :param impl_name: Name of the implementation.
        :param version: Version of the implementation.
        """
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
                
            self.logger.debug(f"Found configuration for implementation '{path.name}': {versions}")
            for version, version_config in versions.items():
                self.logger.info(f"Building image for implementation '{path.name}' version '{version}'")
                image_tag = self.docker_builder.build_image(
                    impl_name=path.name,
                    version=version,
                    dockerfile_path=dockerfile_path,
                    context_path=dockerfile_path.parent,
                    config=version_config,
                    tag_version="latest"  # or use version if desired
                )
                if image_tag:
                    key = f"{path.name}_{version}"
                    self.built_images[key] = image_tag
                else:
                    self.logger.error(f"Image build failed for implementation '{path.name}' version '{version}'")
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
        implementations_dir = self.plugins_base_dir  / "implementations" / protocol
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
        implementations_dir = self.plugins_base_dir  / "testers" 
        self.logger.debug(f"Checking for testers in '{implementations_dir}'")
        for item in implementations_dir.iterdir():
                if item.is_dir() and not item.name.startswith('__') and item.name != "templates":
                    implementations.append(item.name)
        return implementations
    
    def load_plugins(self):
        """
        Discovers and registers all protocol and environment plugins.
        """
        self.logger.debug(f"Loading plugins from base directory '{self.plugins_base_dir}'")

        # Discover protocol plugins
        protocols_dir = self.plugins_base_dir / "implementations"
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
            
        # Discover tester plugins
        testers_dir = self.plugins_base_dir / "testers"
        if testers_dir.exists() and testers_dir.is_dir():
            self.logger.debug(f"Checking testers directory '{testers_dir}'")
            for tester in testers_dir.iterdir():
                if tester.is_dir() and not tester.name.startswith('__'):
                    if (tester / f"{tester.name}_plugin.py").exists():
                        self.tester_plugins[tester.name] = item
                        self.logger.debug(f"Discovered tester plugin '{tester.name}' at '{tester}'")
        else:
            self.logger.warning(f"Testers directory '{testers_dir}' does not exist.")
        
