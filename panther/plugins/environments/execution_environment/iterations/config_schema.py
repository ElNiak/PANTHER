from typing import List

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class IterationsConfig(ExecutionEnvironmentPluginConfig):
    """
    IterationsConfig is a configuration class for setting up and running multiple test iterations.
    """

    # Plugin type
    type: str = Field(default="iterations", description="Execution environment type")

    iterations: int = Field(default=1, description="Number of times to repeat the test")
    parallel: bool = Field(
        default=False, description="Whether to run iterations in parallel"
    )
    vary_parameters: bool = Field(
        default=False, description="Whether to vary parameters between iterations"
    )
    parameter_sets: List[dict] = Field(
        default_factory=list,
        description="Sets of parameters to use for different iterations",
    )
    aggregate_results: bool = Field(
        default=True, description="Whether to aggregate results across iterations"
    )
    delay_between_iterations: int = Field(
        default=0, description="Delay in seconds between iterations"
    )

    # Universal validators for flexible type conversion
    @validator("iterations", pre=True)
    def validate_iterations(cls, v):
        """Convert string/float to integer for iterations."""
        return validate_integer_field(v, "iterations")

    @validator("delay_between_iterations", pre=True)
    def validate_delay(cls, v):
        """Convert string/float to integer for delay."""
        return validate_integer_field(v, "delay_between_iterations")
