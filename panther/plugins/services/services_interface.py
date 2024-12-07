from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict, Optional

import yaml

from plugins.plugin_loader import PluginLoader
from plugins.plugin_interface import IPlugin

class IServiceManager(IPlugin):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        type: str,
        sub_type: str,
    ):
        super().__init__(type)
        self.templates_dir: str = f"plugins/services/{type}/{sub_type}/templates"
        self.config_path = config_path
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.plugin_loader = None
        self.config = self.load_config()
        self.validate_config()
    
    
    @abstractmethod
    def is_tester(self):
        """
        Returns True if the plugin is a network service.
        """
        pass
    
    # @abstractmethod
    # def setup_environment(self):
    #     """
    #     Sets up the required service before running experiments.
    #     """
    #     pass

    # @abstractmethod
    # def teardown_environment(self):
    #     """
    #     Tears down the service after experiments are completed.
    #     """
    #     pass
    
    def load_config(self) -> dict:
        """
        Loads the YAML configuration file.
        """
        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.error(
                f"Configuration file '{self.config_path}' does not exist."
            )
            return {}
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from '{self.config_path}'")
            return config
        except Exception as e:
            self.logger.error(
                f"Failed to load configuration: {e}\n{traceback.format_exc()}"
            )
            return {}
        
    def validate_config(self):
        """
        Validates the configuration.
        To be implemented by the plugin.
        """
        pass
    
    @abstractmethod
    def get_base_url(self, service_name: str) -> str:
        """
        Returns the base URL for the given service.
        """
        raise NotImplementedError("Method 'get_base_url' must be implemented in subclasses.")
    
    @abstractmethod
    def get_implementation_name(self) -> str:
        """
        Returns the name of the implementation.

        :return: Implementation name as a string.
        """
        pass
    
    @abstractmethod
    def prepare(self, plugin_loader: Optional[PluginLoader] = None):
        """
        Builds the Docker image for the implementation based on the environment.
        
        :param environment: The name of the environment (e.g., 'docker_compose', 'shadow_ns').
        """
        pass 
    
    @abstractmethod
    def generate_deployment_commands(self, service_params: Dict[str, Any], environment:str) -> Dict[str, str]:
        """
        Generates deployment commands based on service parameters.

        :param service_params: Parameters specific to the service.
        :return: A dictionary mapping service names to their respective command strings.
        """
        pass
    
    @abstractmethod
    def start_service(self, service_name: str, command: str):
        """
        Starts the service using the provided command.

        :param service_name: Name of the service.
        :param command: Command string to start the service.
        """
        pass

    @abstractmethod
    def stop_service(self, service_name: str):
        """
        Stops the service gracefully.

        :param service_name: Name of the service.
        """
        pass
