from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict

import yaml

from plugins.plugin_interface import IPlugin

class IEnvironmentPlugin(IPlugin):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        environment_settings: Dict[str,Any],
        type: str,
        sub_type: str,
    ):
        super().__init__(type)
        self.templates_dir: str = f"plugins/environments/{type}/{sub_type}/templates"
        self.config_path = config_path
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.plugin_loader = None
        self.environment_settings = environment_settings
        self.config = self.load_config()
        self.validate_config()
    
    @abstractmethod
    def is_network_environment(self):
        """
        Returns True if the plugin is a network environment.
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
