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
    wait: int = field(
        default=60, metadata={"min": 1, "max": 3600}
    )  # Range for wait time
    record_pcap: bool | None = None  # Optional flag for PCAP recording


# Assertion Configuration
AssertionType = Enum("AssertionType", ["service_responsive", "data_integrity"])


@dataclass
class AssertionConfig:
    type: AssertionType  # Supported assertion types
    service: str  # Service name
    endpoint: str  # Endpoint to assert
    expected_status: int  # Expected status code


# Test Configuration
@dataclass
class TestConfig:
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
    tests: list[TestConfig] = field(
        default_factory=lambda: [TestConfig]
    )  # Required list of tests

    def __name__(self):
        return "ExperimentConfig"
