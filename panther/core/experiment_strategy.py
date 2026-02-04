"""Test execution strategies for PANTHER framework.

Implements the Strategy pattern for pluggable test execution approaches,
allowing experiments to choose between different execution models based
on requirements for parallelism, resource constraints, and failure isolation.

**Strategy Pattern Implementation**:
- Abstract base class defines execution contract
- Concrete strategies implement specific execution models
- Strategies are interchangeable at runtime based on configuration

**Available Strategies**:
- SequentialExecutionStrategy: One test at a time, predictable resource usage
- ParallelExecutionStrategy: Concurrent execution, faster but higher resource usage

**Usage Context**:
This module integrates with ExperimentManager to provide execution flexibility.
The choice of strategy affects:
- Resource utilization patterns
- Error isolation boundaries
- Execution timing and throughput
- Debug and logging complexity

**Architecture Integration**:
```mermaid
graph TD
    A[ExperimentManager] --> B[TestExecutionStrategy]
    B --> C[SequentialExecutionStrategy]
    B --> D[ParallelExecutionStrategy]
    C --> E[Test.run()]
    D --> F[ThreadPoolExecutor]
    F --> E
```
"""

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List


class TestExecutionStrategy(ABC):
    """Abstract base class for test execution strategies.

    Defines the contract that all execution strategies must implement.
    Strategies encapsulate the 'how' of test execution while leaving
    the 'what' to the individual test cases.

    **Design Pattern**: Strategy pattern for execution algorithm selection
    **Thread Safety**: Implementations must handle their own thread safety
    **Lifecycle**: Strategies are instantiated per experiment execution
    """

    @abstractmethod
    def execute_tests(self, tests: List[Any]) -> None:
        """Execute a collection of test cases using this strategy's approach.

        Args:
            tests: List of test case objects that implement a run() method

        Raises:
            ExecutionError: When the execution strategy itself fails

        Note:
            Individual test failures should be handled by the test cases
            themselves. This method should only fail if the execution
            strategy infrastructure has problems.
        """
        pass


class SequentialExecutionStrategy(TestExecutionStrategy):
    """Execute tests one at a time in the order provided.

    **Characteristics**:
    - Predictable resource usage (only one test active at a time)
    - Simplified debugging (clear temporal ordering)
    - Lower throughput but better for resource-constrained environments
    - Natural error isolation (failures don't affect other tests)

    **Use Cases**:
    - Development and debugging scenarios
    - Resource-constrained environments
    - Tests that modify shared global state
    - Scenarios requiring deterministic execution order

    **Performance Profile**:
    - Memory: Constant (single test overhead)
    - CPU: Single-threaded utilization
    - Network: No port contention between tests
    - I/O: Sequential file/database access patterns
    """

    def execute_tests(self, tests: List[Any]) -> None:
        """Execute tests sequentially in provided order.

        Implements simple iteration with individual test execution.
        Each test's run() method is called synchronously before
        proceeding to the next test.

        Args:
            tests: Test cases to execute, each must have a run() method

        Note:
            Failures in individual tests do not stop execution of
            remaining tests. Error handling is delegated to test cases.

        Example:
            ```python
            strategy = SequentialExecutionStrategy()
            strategy.execute_tests([test1, test2, test3])
            # Executes: test1.run(), then test2.run(), then test3.run()
            ```
        """
        for test in tests:
            test.run()


class ParallelExecutionStrategy(TestExecutionStrategy):
    """Execute tests concurrently using thread pool.

    **Characteristics**:
    - Higher throughput through parallel execution
    - Increased resource usage (memory, CPU, network)
    - More complex debugging due to concurrent execution
    - Requires thread-safe test implementations

    **Use Cases**:
    - Production testing scenarios with time constraints
    - Independent tests that don't share state
    - Environments with sufficient resources for parallel execution
    - Stress testing network infrastructure

    **Limitations**:
    - Tests must be thread-safe
    - Resource contention may cause flaky failures
    - Debugging concurrent failures is more complex
    - Port conflicts possible with network-based tests

    **Performance Profile**:
    - Memory: Multiplied by concurrent test count
    - CPU: Multi-threaded utilization up to thread pool limit
    - Network: Potential port conflicts between concurrent tests
    - I/O: Concurrent file/database access (may need coordination)
    """

    def execute_tests(self, tests: List[Any]) -> None:
        """Execute tests concurrently using ThreadPoolExecutor.

        Creates a ThreadPoolExecutor and submits all tests for
        concurrent execution. Uses executor.map() to wait for
        all tests to complete before returning.

        Args:
            tests: Test cases to execute concurrently

        Note:
            Uses default ThreadPoolExecutor configuration.
            Number of threads is min(32, (os.cpu_count() or 1) + 4).

            Individual test failures do not affect other running tests.
            All tests will be submitted for execution regardless of
            individual failures.

        Example:
            ```python
            strategy = ParallelExecutionStrategy()
            strategy.execute_tests([test1, test2, test3])
            # Executes: test1.run(), test2.run(), test3.run() concurrently
            ```
        """
        with ThreadPoolExecutor() as executor:
            executor.map(lambda test: test.run(), tests)
