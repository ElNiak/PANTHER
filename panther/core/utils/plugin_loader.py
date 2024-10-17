# PANTHER-SCP/panther/utils/plugin_loader.py

import logging
from pathlib import Path
from typing import Dict, Any, List

import yaml
from utils.docker_builder import DockerBuilder


class PluginLoader:
    def __init__(self, plugins_base_dir: str = "plugins"):
        self.logger = logging.getLogger("PluginLoader")
        self.plugins_base_dir = Path(plugins_base_dir)
        self.docker_builder = DockerBuilder()
        self.built_images: Dict[str, str] = {}  # Maps implementation names to image tags
        self.protocol_plugins: Dict[str, Path] = {}
        self.environment_plugins: Dict[str, Path] = {}
        self.load_plugins()
        
    def build_all_docker_images(self):
        """
        Finds and builds all Docker images from Dockerfiles using DockerBuilder.
        Updates the built_images dictionary with successful builds.
        """
        # TODO: should depend of the network environment, if shadow, we need a single container with all implems,
        # TODO: if docker compose, we need a container per implementation
        dockerfiles = self.docker_builder.find_dockerfiles(self.plugins_base_dir)
        for impl_name, dockerfile_path in dockerfiles.items():
            # Load version-specific configurations from config.yaml
            config_path = dockerfile_path.parent / "config.yaml"
            if not config_path.exists():
                self.logger.error(f"Configuration file '{config_path}' does not exist for implementation '{impl_name}'. Skipping.")
                continue

            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)

            impl_config = full_config.get(impl_name, {})
            versions = impl_config.get('versions', {})
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

    def get_implementations_for_protocol(self, protocol: str) -> List[str]:
        """
        Retrieves a list of implementations under a given protocol.

        :param protocol: Name of the protocol.
        :return: List of implementation names.
        """
        implementations = []
        protocol_dir = self.protocol_plugins.get(protocol)
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
    
    def load_plugins(self):
        """
        Discovers and registers all protocol and environment plugins.
        """
        self.logger.debug(f"Loading plugins from base directory '{self.plugins_base_dir}'")

        # Discover protocol plugins
        protocols_dir = self.plugins_base_dir
        for protocol in protocols_dir.iterdir():
            if protocol.is_dir() and not protocol.name.startswith('__') and protocol.name not in ['environments']:
                if (protocol / "quic_plugin.py").exists() or (protocol / "protocol_plugin.py").exists():
                    self.protocol_plugins[protocol.name] = protocol
                    self.logger.debug(f"Discovered protocol plugin '{protocol.name}' at '{protocol}'")

        # Discover environment plugins
        environments_dir = self.plugins_base_dir / "environments"
        if environments_dir.exists() and environments_dir.is_dir():
            for environment in environments_dir.iterdir():
                if environment.is_dir() and not environment.name.startswith('__'):
                    if (environment / "environment_plugin.py").exists():
                        self.environment_plugins[environment.name] = environment
                        self.logger.debug(f"Discovered environment plugin '{environment.name}' at '{environment}'")
        else:
            self.logger.warning(f"Environments directory '{environments_dir}' does not exist.")
