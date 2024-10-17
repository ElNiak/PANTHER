# PANTHER-SCP/panther/core/factories/environment_manager.py

from typing import Dict, Any
from plugins.environments.environment_interface import IEnvironmentPlugin

class EnvironmentManager:
    def __init__(self, environment_plugins: Dict[str, IEnvironmentPlugin]):
        self.environment_plugins = environment_plugins
        
    def parse_gml(self, gml_file: str):
        """
        Parses the GML file and returns the graph.
        """
        raise NotImplementedError

    def setup_environment(self, environment_name: str, services: Dict[str, Dict[str, Any]]):
        """
        Sets up the specified environment using the corresponding plugin.
        """
        plugin = self.environment_plugins.get(environment_name)
        if not plugin:
            raise ValueError(f"Environment plugin '{environment_name}' not found.")
        plugin.setup_environment(services)

    def teardown_environment(self, environment_name: str):
        """
        Tears down the specified environment using the corresponding plugin.
        """
        plugin = self.environment_plugins.get(environment_name)
        if not plugin:
            raise ValueError(f"Environment plugin '{environment_name}' not found.")
        plugin.teardown_environment()
