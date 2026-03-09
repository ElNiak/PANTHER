"""Experiment configuration models."""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base_model import BaseUnifiedModel
from .environment import ExecutionEnvironmentConfig, NetworkEnvironmentConfig
from .service import ServiceConfig


class StepsConfig(BaseUnifiedModel):
    """Test steps configuration."""

    pre_commands: List[str] = Field(
        default_factory=list, description="Commands to run before test"
    )
    wait: int = Field(60, description="Wait time in seconds")
    post_commands: List[str] = Field(
        default_factory=list, description="Commands to run after test"
    )

    @field_validator("wait")
    @classmethod
    def validate_wait(cls, v):
        """Validate wait time is positive."""
        if v <= 0:
            raise ValueError("Wait time must be positive")
        return v


class ExperimentMetadata(BaseUnifiedModel):
    """Experiment metadata."""

    name: Optional[str] = Field(None, description="Experiment name")
    description: Optional[str] = Field(None, description="Experiment description")
    author: Optional[str] = Field(None, description="Experiment author")
    version: Optional[str] = Field(None, description="Experiment version")
    tags: List[str] = Field(default_factory=list, description="Experiment tags")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    modified_at: Optional[str] = Field(None, description="Last modification timestamp")


class TestConfig(BaseUnifiedModel):
    """Individual test configuration."""

    name: str = Field(..., description="Test name")
    description: Optional[str] = Field(None, description="Test description")
    network_environment: NetworkEnvironmentConfig = Field(
        ..., description="Network environment configuration"
    )
    execution_environment: List[ExecutionEnvironmentConfig] = Field(
        default_factory=list, description="Execution environment configurations"
    )
    services: Dict[str, ServiceConfig] = Field(
        ..., description="Service configurations"
    )
    steps: StepsConfig = Field(default_factory=StepsConfig, description="Test steps")
    iterations: int = Field(1, description="Number of iterations")
    timeout: Optional[int] = Field(None, description="Test timeout in seconds")
    fast_fail_enabled: Optional[bool] = Field(
        None, description="Override fast-fail for this test"
    )
    continue_on_failure: bool = Field(
        False, description="Continue test on service failures"
    )
    collect_artifacts: bool = Field(True, description="Collect test artifacts")

    @field_validator("iterations")
    @classmethod
    def validate_iterations(cls, v):
        """Validate iterations is positive."""
        if v <= 0:
            raise ValueError("Iterations must be positive")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout is positive if set."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("services")
    @classmethod
    def validate_services(cls, v):
        """Validate services configuration."""
        if not v:
            raise ValueError("At least one service must be defined")

        # Check for service targets
        for service_name, service in v.items():
            if hasattr(service.protocol, "target") and service.protocol.target:
                if service.protocol.target not in v:
                    raise ValueError(
                        f"Service '{service_name}' targets unknown service '{service.protocol.target}'"
                    )

        return v

    def get_service_dependencies(self) -> Dict[str, List[str]]:
        """Get service dependency graph.

        Returns:
            Dictionary mapping service names to their dependencies
        """
        dependencies = {}

        for service_name, service in self.services.items():
            deps = []
            if hasattr(service.protocol, "target") and service.protocol.target:
                deps.append(service.protocol.target)
            dependencies[service_name] = deps

        return dependencies

    def get_execution_order(self) -> List[str]:
        """Get service execution order based on dependencies.

        Returns:
            List of service names in execution order
        """
        # Simple topological sort
        dependencies = self.get_service_dependencies()
        ordered = []
        visited = set()

        def visit(service: str):
            if service in visited:
                return
            visited.add(service)

            for dep in dependencies.get(service, []):
                visit(dep)

            ordered.append(service)

        for service in self.services:
            visit(service)

        return ordered


class ExperimentConfig(BaseUnifiedModel):
    """Main experiment configuration."""

    tests: List[TestConfig] = Field(..., description="List of test configurations")
    metadata: Optional[ExperimentMetadata] = Field(
        None, description="Experiment metadata"
    )

    @field_validator("tests")
    @classmethod
    def validate_tests(cls, v):
        """Validate tests list."""
        if not v:
            raise ValueError("At least one test must be defined")

        # Check for unique test names
        names = [test.name for test in v]
        if len(names) != len(set(names)):
            raise ValueError("Test names must be unique")

        return v

    def get_test_by_name(self, name: str) -> Optional[TestConfig]:
        """Get test configuration by name.

        Args:
            name: Test name

        Returns:
            Test configuration or None
        """
        for test in self.tests:
            if test.name == name:
                return test
        return None

    def get_all_services(self) -> Dict[str, ServiceConfig]:
        """Get all unique services across all tests.

        Returns:
            Dictionary of service configurations
        """
        all_services = {}

        for test in self.tests:
            for service_name, service in test.services.items():
                key = f"{test.name}/{service_name}"
                all_services[key] = service

        return all_services

    def validate_cross_test_references(self) -> List[str]:
        """Validate references across tests.

        Returns:
            List of validation errors
        """
        errors = []

        # For now, tests are independent
        # Future: could validate shared resources, ports, etc.

        return errors

    def apply_defaults(self, defaults: Dict[str, Any]) -> "ExperimentConfig":
        """Apply default values to configuration.

        Args:
            defaults: Default values to apply

        Returns:
            New ExperimentConfig with defaults applied
        """
        return self.merge(defaults)
