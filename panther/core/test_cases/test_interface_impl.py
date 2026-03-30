"""Abstract test case interface defining the test lifecycle."""

# PANTHER-SCP/panther/core/test_case_interface.py

import logging
from abc import ABC, abstractmethod

from panther.config.core.models import GlobalConfig, TestConfig


class ITestCase(ABC):
    """Abstract base class defining the test case lifecycle interface."""

    def __init__(self, test_config: TestConfig, global_config: GlobalConfig):
        """Initialize the test case with test and global configuration."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{test_config.name}")
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
