from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
import yaml

from plugins.plugin_loader import PluginLoader
from plugins.plugin_interface import IPlugin

class IServiceManager(IPlugin):
    def __init__(
        self,
        type: str,
        protocol: str,
        implementation_name: str,
    ):
        super().__init__()
        
        self.available_types = ["testers", "implementations"]
        self.type = type
        assert self.type in self.available_types, f"Invalid service type: {self.type}"
        
        if self.type == "testers":
            self.config_path = f"plugins/services/{type}/{implementation_name}/config.yaml"
            self.templates_dir = f"plugins/services/{type}/{implementation_name}/templates/"
        else:
            self.config_path = f"plugins/services/{type}/{protocol}/{implementation_name}/config.yaml"
            self.templates_dir = f"plugins/services/{type}/{protocol}/{implementation_name}/templates/"
        
        
        if not os.path.isdir(self.templates_dir):
            self.logger.error(
                f"Templates directory '{self.templates_dir}' does not exist."
            )
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug(
                f"Available templates in '{self.templates_dir}': {templates}"
            )
        
        self.plugin_loader = None
        
        self.config = self.load_config()
        self.validate_config()
        
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters['realpath'] = lambda x: os.path.abspath(x)
        self.jinja_env.filters['is_dict']  = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks   = True
        self.jinja_env.lstrip_blocks = True
        
        # Service-specific attributes
        # Some attributes are set by the plugin loader, others are set by the plugin itself and the experiment manager
        self.service_name     = None
        self.service_protocol = protocol
        self.service_targets  = []
        self.service_version  = None
        self.working_dir      = None
        self.process          = None
        self.available_roles  = []
        self.role = None
        self.environments = {}
        
        self.pre_run_cmds  = []
        self.compile_cmds  = []
        self.run_cmd       = {
            "command_binary": "",
            "command_args":   "",
            "timeout": 60
        }
        self.post_run_cmds = []
    
    
    def is_tester(self):
        """
        Returns True if the plugin is a network service.
        """
        return self.type == "testers"
    
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
    
