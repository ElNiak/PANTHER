from abc import ABC, abstractmethod
import os
from pathlib import Path
import socket
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from core.observer.event_manager import EventManager
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.environments.environment_interface import IEnvironmentPlugin

class INetworkEnvironment(IEnvironmentPlugin):
    
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        environment_settings: Dict[str,Any],
        type: str,
        sub_type: str,
        event_manager: EventManager
    ):
        super().__init__(config_path, output_dir, environment_settings, type, sub_type, event_manager)
        self.network_name = f"{sub_type}_network"
        self.execution_environments = []
        
        self.services = {}
        self.deployment_commands = {}
        self.timeout = 60
        
        self.logger.debug(f"Environment settings: {self.environment_settings} in {self.templates_dir}")
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters['realpath'] = lambda x: os.path.abspath(x)
        self.jinja_env.filters['is_dict']  = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks   = True
        self.jinja_env.lstrip_blocks = True
    
    def resolve_environment_variables(self, env_vars):
        """
        Resolves environment variables incrementally, ensuring no duplication
        and preserving unresolved tokens. Processes variables in dependency order.

        :param env_vars: dict, environment variables with potential references.
        :return: dict, resolved environment variables.
        """
        resolved_env = {}

        self.logger.debug("Initial environment variables:")
        for k, v in env_vars.items():
            self.logger.debug(f"{k}: {v}")

        for key, value in env_vars.items():
            if isinstance(value, str):
                resolved_value = value
                self.logger.debug(f"Resolving variable: {key} - Original value: {value}")
                for var_name, var_value in resolved_env.items():  # Use already resolved variables
                    if f"${{{var_name}}}" in resolved_value or f"${var_name}" in resolved_value:
                        resolved_value = resolved_value.replace(f"${{{var_name}}}", var_value)
                        resolved_value = resolved_value.replace(f"${var_name}", var_value)
                        self.logger.debug(f"Replaced ${var_name} in {key} with {var_value}")
                resolved_value = resolved_value.replace('$', '$$')
                resolved_env[key] = resolved_value

        self.logger.debug("Final resolved environment variables without duplication:")
        for k, v in resolved_env.items():
            self.logger.debug(f"{k}: {v}")

        return resolved_env
    
    def is_network_environment(self):
        """
        Returns True if the plugin is a network environment.
        """
        return True
    
    @abstractmethod
    def generate_environment_services(self, paths: Dict[str, str], timestamp: str):
        """
        Generates the services required for the network environment.
        
        :param services: A dictionary containing the services to be generated.
        :return: A list of generated services.
        """
        pass
    
    @abstractmethod
    def prepare_environment(self):
        """
        Prepares the environment for running experiments.
        """
        pass
    
    @abstractmethod
    def launch_environment_services(self):
        """
        Launches the services in the network environment.
        """
        pass
    
    @abstractmethod
    def deploy_services(self):
        """
        Deploys the specified services in the network environment.
        """
        pass
    
    @abstractmethod
    def setup_environment(self):
        """
        Sets up the required environment before running experiments.
        """
        pass

    @abstractmethod
    def teardown_environment(self):
        """
        Tears down the environment after experiments are completed.
        """
        pass
