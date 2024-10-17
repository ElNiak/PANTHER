# PANTHER-SCP/panther/core/test_case_interface.py

from abc import ABC, abstractmethod
import logging

class ITestCase(ABC):
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @abstractmethod
    def run(self):
        """Runs the test case."""
        pass

    @abstractmethod
    def run_services(self):
        """Starts the services defined in the test configuration."""
        pass

    @abstractmethod
    def execute_steps(self):
        """Executes steps defined in the test configuration."""
        pass

    @abstractmethod
    def validate_assertions(self):
        """Validates assertions defined in the test configuration."""
        pass
