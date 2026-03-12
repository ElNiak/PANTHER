"""Experiment configuration models."""

import functools
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from ..base import BaseConfig
from .environment import ExecutionEnvironmentConfig, NetworkEnvironmentConfig
from .service import ServiceConfig


@functools.lru_cache(maxsize=1)
def _detect_author() -> Optional[str]:
    """Try git user.name, fall back to OS username."""
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    try:
        return os.getlogin()
    except OSError:
        return None


class StepsConfig(BaseConfig):
    """Test steps configuration."""

    pre_commands: List[str] = Field(
        default_factory=list, description="Commands to run before test"
    )
    wait: int = Field(
        60,
        ge=1,
        le=86400,
        description="Wait time between steps in seconds",
        examples=[30, 60, 120, 300],
        json_schema_extra={"unit": "seconds"},
    )
    post_commands: List[str] = Field(
        default_factory=list, description="Commands to run after test"
    )


class ExperimentMetadata(BaseConfig):
    """Experiment metadata."""

    name: Optional[str] = Field("new_experiment", description="Experiment name")
    description: Optional[str] = Field(None, description="Experiment description")
    author: Optional[str] = Field(
        default_factory=_detect_author, description="Experiment author"
    )
    version: Optional[str] = Field("1.0.0", description="Experiment version")
    tags: List[str] = Field(default_factory=list, description="Experiment tags")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )
    modified_at: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last modification timestamp",
    )


class TestConfig(BaseConfig):
    """One test scenario: a set of services deployed together in a network environment.

    The ``services`` dict keys are service names -- used as Docker container names
    AND as the values referenced by ``ProtocolConfig.target``.  Services form a
    directed graph via those ``target`` references (client -> server edges).

    Example YAML::

        tests:
          - name: quic-handshake
            network_environment:
              type: docker_compose
            services:
              server:
                implementation: { name: picoquic, type: iut }
                protocol: { name: quic, version: rfc9000, role: server }
              client:
                implementation: { name: aioquic, type: iut }
                protocol: { name: quic, role: client, target: server }
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Test name",
        examples=["quic-handshake", "http3-transfer"],
    )
    description: Optional[str] = Field(None, description="Test description")
    network_environment: NetworkEnvironmentConfig = Field(
        ..., description="Network environment configuration"
    )
    execution_environment: List[ExecutionEnvironmentConfig] = Field(
        default_factory=list, description="Execution environment configurations"
    )
    services: Dict[str, ServiceConfig] = Field(
        ...,
        description="Service configurations",
        json_schema_extra={"key_generator": "service_name"},
    )
    steps: StepsConfig = Field(default_factory=StepsConfig, description="Test steps")
    iterations: int = Field(
        1,
        ge=1,
        le=1000,
        description="Number of test iterations",
        examples=[1, 5, 10],
    )
    timeout: Optional[int] = Field(
        None,
        ge=1,
        le=86400,
        description="Test timeout in seconds",
        examples=[60, 120, 300],
        json_schema_extra={"unit": "seconds"},
    )
    fast_fail_enabled: Optional[bool] = Field(
        None, description="Override fast-fail for this test"
    )
    continue_on_failure: bool = Field(
        False, description="Continue test on service failures"
    )
    collect_artifacts: bool = Field(True, description="Collect test artifacts")

    @classmethod
    def generate_default_name(cls, test_data: dict) -> str:
        """Generate a descriptive test name from services, protocol, and environment info.

        Follows project naming conventions, e.g.:
        ``"QUIC Client-Server Communication Test"``
        ``"Strace - Shadow QUIC Client-Server Communication Test"``
        """
        services = test_data.get("services", {})
        if not services:
            return ""

        protocols: set = set()
        role_parts: list = []
        for svc_data in services.values():
            svc = svc_data if isinstance(svc_data, dict) else {}
            proto = svc.get("protocol", {})
            proto_name = proto.get("name", "") if isinstance(proto, dict) else ""
            if proto_name:
                protocols.add(proto_name.upper())
            role = (
                proto.get("role", "unknown") if isinstance(proto, dict) else "unknown"
            )
            role_parts.append(role.title())

        proto_str = "-".join(sorted(protocols)) if protocols else "Protocol"
        role_str = "-".join(role_parts) if role_parts else ""

        exec_envs = test_data.get("execution_environment", [])
        exec_prefix = ""
        if isinstance(exec_envs, list) and exec_envs:
            exec_types = [
                e.get("type", "")
                for e in exec_envs
                if isinstance(e, dict) and e.get("type")
            ]
            if exec_types:
                exec_prefix = " ".join(t.title() for t in exec_types) + " - "

        net_env = test_data.get("network_environment", {})
        net_type = net_env.get("type", "") if isinstance(net_env, dict) else ""
        net_prefix = ""
        if net_type and net_type not in ("docker_compose", ""):
            net_prefix = net_type.replace("_", " ").title() + " "

        return f"{exec_prefix}{net_prefix}{proto_str} {role_str} Communication Test".strip()

    @classmethod
    def generate_default_description(cls, test_data: dict) -> str:
        """Generate a test description from services and environment info."""
        services = test_data.get("services", {})
        if not services:
            return ""

        svc_parts: list = []
        for svc_name, svc_data in services.items():
            svc = svc_data if isinstance(svc_data, dict) else {}
            impl = svc.get("implementation", {})
            proto = svc.get("protocol", {})
            impl_name = (
                impl.get("name", svc_name) if isinstance(impl, dict) else svc_name
            )
            role = proto.get("role", "") if isinstance(proto, dict) else ""
            svc_parts.append(f"{impl_name} ({role})" if role else impl_name)

        svc_str = " and ".join(svc_parts)

        net_env = test_data.get("network_environment", {})
        net_type = (
            net_env.get("type", "network") if isinstance(net_env, dict) else "network"
        )

        return (
            f"Verify communication between {svc_str}"
            f" over {net_type.replace('_', ' ')} network."
        )

    @field_validator("services")
    @classmethod
    def validate_services(cls, v):
        """Validate services configuration."""
        if not v:
            raise ValueError("Services dictionary cannot be empty")

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


class ExperimentConfig(BaseConfig):
    """Top-level configuration containing one or more independent tests.

    Each test runs in isolation with its own network environment and services.
    """

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
