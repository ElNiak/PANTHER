"""Test execution strategies for PANTHER framework.

This module defines different strategies for executing tests including
sequential and parallel execution approaches.
"""

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor


class TestExecutionStrategy(ABC):
    @abstractmethod
    def execute_tests(self, tests):
        pass


class SequentialExecutionStrategy(TestExecutionStrategy):
    def execute_tests(self, tests):
        for test in tests:
            test.run()


class ParallelExecutionStrategy(TestExecutionStrategy):
    def execute_tests(self, tests):
        with ThreadPoolExecutor() as executor:
            executor.map(lambda test: test.run(), tests)
