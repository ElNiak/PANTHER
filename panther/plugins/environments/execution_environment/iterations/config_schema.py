from typing import List

from pydantic import Field

from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class IterationsConfig(ExecutionEnvironmentPluginConfig):
    """
    IterationsConfig is a configuration class for setting up and running multiple test iterations.
    """

    # Plugin type
    type: str = Field(
        default="iterations",
        description="Execution environment type"
    )
    
    iterations: int = Field(
        default=1,
        description="Number of times to repeat the test"
    )
    parallel: bool = Field(
        default=False,
        description="Whether to run iterations in parallel"
    )
    vary_parameters: bool = Field(
        default=False,
        description="Whether to vary parameters between iterations"
    )
    parameter_sets: List[dict] = Field(
        default_factory=list,
        description="Sets of parameters to use for different iterations"
    )
    aggregate_results: bool = Field(
        default=True,
        description="Whether to aggregate results across iterations"
    )
    delay_between_iterations: int = Field(
        default=0,
        description="Delay in seconds between iterations"
    )
