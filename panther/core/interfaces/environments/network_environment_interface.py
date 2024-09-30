from abc import ABC, abstractmethod
from typing import Any, Dict

from core.interfaces.environments.environment_interface import IEnvironmentPlugin

class INetworkEnvironment(IEnvironmentPlugin):
    @abstractmethod
    def configure_network(self, services: Dict[str, Dict[str, Any]]):
        """
        Configures the network environment.
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
