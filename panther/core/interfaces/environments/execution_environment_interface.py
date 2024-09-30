from abc import ABC, abstractmethod

from core.interfaces.environments.environment_interface import IEnvironmentPlugin

class IExecutionEnvironment(IEnvironmentPlugin):
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
