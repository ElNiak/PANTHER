from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict

import yaml

from panther.core.observer.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.plugin_interface import IPlugin

class IEnvironmentPlugin(IPlugin):
    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager
    ):
        super().__init__()
        self.templates_dir: str = f"panther/plugins/environments/{env_type}/{env_sub_type}/templates"
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.plugin_loader = None
        self.env_config_to_test = env_config_to_test
        self.event_manager = event_manager
    
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
    