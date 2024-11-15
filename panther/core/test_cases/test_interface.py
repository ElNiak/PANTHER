# PANTHER-SCP/panther/core/test_case_interface.py

from abc import ABC, abstractmethod
import logging
from omegaconf import DictConfig

class ITestCase(ABC):
    def __init__(self, test_config: DictConfig, logger: logging.Logger):
        self.logger = logger
        self.test_config = test_config

    @abstractmethod
    def run(self):
        """Runs the test case."""
        raise NotImplementedError

    @abstractmethod
    def deploy_services(self):
        """Starts the services defined in the test configuration."""
        raise NotImplementedError

    @abstractmethod
    def execute_steps(self):
        """Executes steps defined in the test configuration."""
        raise NotImplementedError

    @abstractmethod
    def validate_assertions(self):
        """Validates assertions defined in the test configuration."""
        raise NotImplementedError
