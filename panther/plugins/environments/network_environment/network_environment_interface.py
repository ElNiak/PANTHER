from abc import ABC, abstractmethod
from typing import Any, Dict

from plugins.environments.environment_interface import IEnvironmentPlugin

class INetworkEnvironment(IEnvironmentPlugin):
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
