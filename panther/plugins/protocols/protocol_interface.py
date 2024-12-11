from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
import yaml

from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.plugin_interface import IPlugin

class IProtocolManager(IPlugin):
    def __init__(
        self,
        service_type: str,
    ):
        super().__init__()
        self.service_config_to_test_path = f"panther/plugins/protocols/{service_type}/"
        self.service_config_to_test = self.load_config()
        self.validate_config()
        
    def validate_config(self):
        """
        Validates the configuration file.
        """
        pass
    
    def load_config(self) -> dict:
        """
        Loads the YAML configuration file.
        """
        config_file = Path(self.service_config_to_test_path)
        if not config_file.exists():
            self.logger.error(
                f"Configuration file '{self.service_config_to_test_path}' does not exist."
            )
        with open(self.service_config_to_test_path, "r") as f:
            return yaml.safe_load(f)
    
    
