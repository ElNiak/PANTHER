from abc import ABC, abstractmethod
from typing import Any, Dict

from core.observer.event_manager import EventManager
from plugins.environments.environment_interface import IEnvironmentPlugin

class IExecutionEnvironment(IEnvironmentPlugin):
    
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
    
    def is_network_environment(self):
        """
        Returns True if the plugin is an network environment.
        """
        return False
    
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
