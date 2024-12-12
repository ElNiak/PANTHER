from enum import Enum
from dataclasses import dataclass, field

from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)
from panther.plugins.environments.network_environment.config_schema import (
    NetworkEnvironmentConfig,
)
from panther.plugins.services.config_schema import ServiceConfig


# Step Configuration
@dataclass
class StepConfig:
    """
    StepConfig class defines the configuration for a step in the experiment.

    Attributes:
        wait (int): The wait time in seconds, with a default value of 60. The valid range is between 1 and 3600 seconds.
        record_pcap (bool | None): An optional flag indicating whether to record PCAP (Packet Capture). Defaults to None.
    """

    wait: int = field(
        default=60, metadata={"min": 1, "max": 3600}
    )  # Range for wait time
    record_pcap: bool | None = None  # Optional flag for PCAP recording


# Assertion Configuration
AssertionType = Enum("AssertionType", ["service_responsive", "data_integrity"])


@dataclass
class AssertionConfig:
    """
    AssertionConfig is a configuration class for defining assertions in the experiment schema.

    Attributes:
        type (AssertionType): Supported assertion types.
        service (str): Service name.
        endpoint (str): Endpoint to assert.
        expected_status (int): Expected status code.
    """

    type: AssertionType  # Supported assertion types
    service: str  # Service name
    endpoint: str  # Endpoint to assert
    expected_status: int  # Expected status code


# Test Configuration
@dataclass
class TestConfig:
    """
    TestConfig class represents the configuration for a test.

    Attributes:
        name (str): The name of the test. Defaults to "Undefined test".
        description (str): A description of the test. Defaults to "Undefined test description".
        network_environment (NetworkEnvironmentConfig): Configuration for the network environment.
        execution_environments (list[ExecutionEnvironmentConfig]): List of execution environment configurations.
        iterations (int): Number of iterations for the test, with a range from 1 to 1000. Defaults to 1.
        services (dict[str, ServiceConfig]): Dictionary of service configurations, keyed by service name.
        steps (StepConfig | None): Configuration for the steps of the test. Defaults to None.
        assertions (list[AssertionConfig] | None): List of assertions for the test. Defaults to None.
    """

    name: str = "Undefined test"  # Test name
    description: str = "Undefined test description"  # Test description
    network_environment: NetworkEnvironmentConfig = field(
        default_factory=NetworkEnvironmentConfig
    )  # Network environment configuration
    execution_environments: list[ExecutionEnvironmentConfig] = field(
        default_factory=lambda: [ExecutionEnvironmentConfig]
    )  # Execution environments
    iterations: int = field(
        default=1, metadata={"min": 1, "max": 1000}
    )  # Range for iterations
    services: dict[str, ServiceConfig] = field(
        default_factory=lambda: {"service_name": ServiceConfig}
    )  # Service configurations
    steps: StepConfig | None = None  # Steps configuration
    assertions: list[AssertionConfig] | None = None  # Assertions


# Experiment Configuration
@dataclass
class ExperimentConfig:
    """
    ExperimentConfig class holds the configuration for an experiment.

    Attributes:
        tests (list[TestConfig]): Required list of tests. Defaults to a list containing a single TestConfig instance.
    """

    tests: list[TestConfig] = field(
        default_factory=lambda: [TestConfig]
    )  # Required list of tests
