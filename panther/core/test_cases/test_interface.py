# PANTHER-SCP/panther/core/test_case_interface.py

from abc import ABC, abstractmethod
import logging
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig


class ITestCase(ABC):
    def __init__(self, test_config: TestConfig, global_config: GlobalConfig):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_config: TestConfig = test_config
        self.global_config: GlobalConfig = global_config

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
