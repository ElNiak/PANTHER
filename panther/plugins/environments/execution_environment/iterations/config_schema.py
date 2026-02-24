from typing import List

from pydantic import Field, validator

from panther.config.core.components.universal_validators import validate_integer_field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig


class IterationsConfig(ExecutionEnvironmentPluginConfig):
    """Iteration runner configuration for repeated test execution.

    Runs a test scenario multiple times to collect statistical data, detect
    flaky behavior, or exercise parameter sweeps. Each iteration executes the
    same test configuration (optionally with varied parameters) and results
    can be aggregated for statistical analysis.

    Unlike the other execution environments (Memcheck, Helgrind, GDB, strace,
    GPerf), this environment does not wrap the service with an analysis tool.
    Instead, it controls *how many times* the test is run and whether
    iterations run sequentially or in parallel. It can be combined with other
    execution environments in the same test configuration.

    Use cases:
        - Reproducibility testing: run a test N times to confirm consistent
          results.
        - Flaky test detection: repeat tests to surface intermittent failures.
        - Parameter sweeps: vary configuration across iterations for
          sensitivity analysis.
        - Statistical profiling: collect enough data points for meaningful
          performance metrics.

    Inherited fields from ``ExecutionEnvironmentPluginConfig``:
        - ``enabled``: Whether the plugin is enabled (default: True).
        - ``collect_metrics``: Whether to collect metrics (default: True).

    Example YAML::

        execution_environments:
          - type: iterations
            iterations: 10
            parallel: false
            aggregate_results: true
            delay_between_iterations: 2

        # With parameter variation:
        execution_environments:
          - type: iterations
            iterations: 3
            vary_parameters: true
            parameter_sets:
              - {initial_window: 10}
              - {initial_window: 20}
              - {initial_window: 40}
    """

    # Plugin type identifier -- do not change.
    type: str = Field(default="iterations", description="Execution environment type")

    # -- Iteration control --

    iterations: int = Field(
        default=1,
        description=(
            "Number of times to repeat the test. Must be >= 1. "
            "Default: 1 (single run, no repetition)."
        ),
    )
    parallel: bool = Field(
        default=False,
        description=(
            "Run iterations in parallel rather than sequentially. "
            "Faster but may cause resource contention if iterations "
            "share Docker networks or ports. Default: False."
        ),
    )
    vary_parameters: bool = Field(
        default=False,
        description=(
            "Vary configuration parameters between iterations using "
            "the parameter_sets list. When True, each iteration uses "
            "the corresponding entry from parameter_sets. "
            "Default: False."
        ),
    )
    parameter_sets: List[dict] = Field(
        default_factory=list,
        description=(
            "List of parameter dictionaries, one per iteration. Each "
            "dict is merged into the test configuration for that "
            "iteration. Only used when vary_parameters is True. "
            "Example: [{'timeout': 10}, {'timeout': 20}]. "
            "Default: [] (empty)."
        ),
    )

    # -- Result handling --

    aggregate_results: bool = Field(
        default=True,
        description=(
            "Aggregate results across all iterations into a combined "
            "report with summary statistics (mean, stddev, etc.). "
            "When False, each iteration's results are kept separate. "
            "Default: True."
        ),
    )

    # -- Timing --

    delay_between_iterations: int = Field(
        default=0,
        description=(
            "Delay in seconds between consecutive iterations. Use to "
            "allow resource cleanup or avoid rate limiting between "
            "runs. Only applies when parallel is False. "
            "Default: 0 (no delay)."
        ),
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
