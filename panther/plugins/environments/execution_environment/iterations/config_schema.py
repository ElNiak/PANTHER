from dataclasses import dataclass, field

from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class IterationsConfig(ExecutionEnvironmentConfig):
    """
    IterationsConfig is a configuration class for setting up and running multiple test iterations.

    Attributes:
        iterations (int): Number of times to repeat the test. Default is 1.
        parallel (bool): Whether to run iterations in parallel. Default is False.
        vary_parameters (bool): Whether to vary parameters between iterations. Default is False.
        parameter_sets (list): Sets of parameters to use for different iterations. Default is empty list.
        aggregate_results (bool): Whether to aggregate results across iterations. Default is True.
        delay_between_iterations (int): Delay in seconds between iterations. Default is 0.
    """

    iterations: int = 1  # Number of times to repeat the test
    parallel: bool = False  # Whether to run iterations in parallel
    vary_parameters: bool = False  # Whether to vary parameters between iterations
    parameter_sets: list[dict] = field(
        default_factory=list
    )  # Sets of parameters for different iterations
    aggregate_results: bool = True  # Whether to aggregate results across iterations
    delay_between_iterations: int = 0  # Delay in seconds between iterations
