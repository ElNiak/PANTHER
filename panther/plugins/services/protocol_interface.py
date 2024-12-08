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

class IProtocolManager(IPlugin):
    def __init__(
        self,
        type: str,
    ):
        super().__init__()
        self.config_path = f"plugins/services/{type}/"
        

        self.config = self.load_config()
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
        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.error(
                f"Configuration file '{self.config_path}' does not exist."
            )
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)
    
    
