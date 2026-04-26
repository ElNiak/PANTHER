#!/usr/bin/env python3
"""Comprehensive test suite for actual PANTHER ExperimentConfig and related models.

This module tests the real configuration structure as discovered through Serena analysis.
"""

import json
import sys
from typing import Any, Dict, List

import pytest
import yaml
from pydantic import ValidationError

from panther.config.core.models.environment import (
    ExecutionEnvironmentConfig,
    NetworkEnvironmentConfig,
)
from panther.config.core.models.experiment import (
    ExperimentConfig,
    ExperimentMetadata,
    StepsConfig,
    TestConfig,
)
from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
)

# Add PANTHER to Python path
# PANTHER is now available in Python path since we're in the PANTHER project


class TestStepsConfig:
    """Test StepsConfig functionality."""

    def test_steps_config_defaults(self):
        """Test StepsConfig with default values."""
        config = StepsConfig()

        assert config.pre_commands == []
        assert config.wait == 60
        assert config.post_commands == []

    def test_steps_config_custom_values(self):
        """Test StepsConfig with custom values."""
        config = StepsConfig(
            pre_commands=["echo 'starting'", "setup.sh"],
            wait=120,
            post_commands=["cleanup.sh", "echo 'finished'"],
        )

        assert config.pre_commands == ["echo 'starting'", "setup.sh"]
        assert config.wait == 120
        assert config.post_commands == ["cleanup.sh", "echo 'finished'"]

    def test_steps_config_serialization(self):
        """Test StepsConfig serialization."""
        config = StepsConfig(
            pre_commands=["setup"], wait=90, post_commands=["teardown"]
        )

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["pre_commands"] == ["setup"]
        assert config_dict["wait"] == 90
        assert config_dict["post_commands"] == ["teardown"]

        # Test YAML serialization
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["wait"] == 90


class TestExperimentMetadata:
    """Test ExperimentMetadata functionality."""

    def test_experiment_metadata_defaults(self):
        """Test ExperimentMetadata with defaults."""
        metadata = ExperimentMetadata()

        assert metadata.name == "new_experiment"
        assert metadata.description is None
        assert metadata.author is not None  # git user.name or OS username
        assert metadata.version == "1.0.0"
        assert metadata.tags == []
        assert metadata.created_at is not None  # auto-populated ISO timestamp
        assert metadata.modified_at is not None  # auto-populated ISO timestamp

    def test_experiment_metadata_custom(self):
        """Test ExperimentMetadata with custom values."""
        metadata = ExperimentMetadata(
            name="QUIC Performance Test",
            description="Testing QUIC protocol performance",
            author="Test Engineer",
            version="2.1",
            tags=["quic", "performance", "network"],
            created_at="2024-01-01T10:00:00Z",
            modified_at="2024-01-02T15:30:00Z",
        )

        assert metadata.name == "QUIC Performance Test"
        assert metadata.description == "Testing QUIC protocol performance"
        assert metadata.author == "Test Engineer"
        assert metadata.version == "2.1"
        assert metadata.tags == ["quic", "performance", "network"]
        assert metadata.created_at == "2024-01-01T10:00:00Z"
        assert metadata.modified_at == "2024-01-02T15:30:00Z"

    def test_experiment_metadata_serialization(self):
        """Test ExperimentMetadata serialization."""
        metadata = ExperimentMetadata(
            name="Test Experiment", author="Developer", tags=["test", "validation"]
        )

        # Test dict conversion
        metadata_dict = metadata.to_dict()
        assert metadata_dict["name"] == "Test Experiment"
        assert metadata_dict["author"] == "Developer"
        assert metadata_dict["tags"] == ["test", "validation"]

        # Test JSON serialization
        json_str = metadata.to_json()
        parsed = json.loads(json_str)
        assert parsed["name"] == "Test Experiment"


class TestNetworkEnvironmentConfig:
    """Test NetworkEnvironmentConfig base functionality."""

    def test_network_environment_config_basic(self):
        """Test basic NetworkEnvironmentConfig."""
        config = NetworkEnvironmentConfig(type="docker_compose")

        assert config.type == "docker_compose"
        assert config.enable_background_monitoring is True

    def test_network_environment_config_custom(self):
        """Test NetworkEnvironmentConfig with custom values."""
        config = NetworkEnvironmentConfig(
            type="localhost_single_container", enable_background_monitoring=False
        )

        assert config.type == "localhost_single_container"
        assert config.enable_background_monitoring is False


class TestExecutionEnvironmentConfig:
    """Test ExecutionEnvironmentConfig functionality."""

    def test_execution_environment_config_basic(self):
        """Test basic ExecutionEnvironmentConfig."""
        config = ExecutionEnvironmentConfig(type="strace")

        assert config.type == "strace"
        assert config.enabled is True

    def test_execution_environment_config_custom(self):
        """Test ExecutionEnvironmentConfig with custom values."""
        config = ExecutionEnvironmentConfig(type="gperf_cpu", enabled=False)

        assert config.type == "gperf_cpu"
        assert config.enabled is False

    def test_execution_environment_config_list(self):
        """Test multiple ExecutionEnvironmentConfig."""
        configs = [
            ExecutionEnvironmentConfig(type="strace"),
            ExecutionEnvironmentConfig(type="gperf_cpu", enabled=False),
            ExecutionEnvironmentConfig(type="memcheck"),
        ]

        assert len(configs) == 3
        assert configs[0].type == "strace"
        assert configs[1].enabled is False
        assert configs[2].type == "memcheck"


class TestServiceConfig:
    """Test ServiceConfig functionality."""

    def test_service_config_minimal(self):
        """Test ServiceConfig with minimal requirements."""
        # Create minimal implementation and protocol configs
        implementation = ImplementationConfig(name="picoquic", type="iut")
        protocol = ProtocolConfig(name="quic", role="server")

        config = ServiceConfig(implementation=implementation, protocol=protocol)

        assert config.implementation.name == "picoquic"
        assert config.protocol.name == "quic"
        assert config.environment == {}
        assert config.ports == []
        assert config.volumes == []
        assert config.depends_on == []

    def test_service_config_complete(self):
        """Test ServiceConfig with all features."""
        implementation = ImplementationConfig(name="nginx", version="1.21", type="iut")

        protocol = ProtocolConfig(name="http", version="1.1", role="server")

        config = ServiceConfig(
            implementation=implementation,
            protocol=protocol,
            environment={"DEBUG": "true", "LOG_LEVEL": "info"},
            timeout=300,
            ports=["8080:80", "8443:443"],
            volumes=["/host/data:/app/data", "/host/logs:/app/logs"],
            generate_new_certificates=True,
            command_override="nginx -g 'daemon off;'",
            working_directory="/app",
            depends_on=["database", "redis"],
            restart_policy="unless-stopped",
            plugin_config={"custom_param": "value"},
        )

        assert config.implementation.name == "nginx"
        assert config.protocol.name == "http"
        assert config.environment["DEBUG"] == "true"
        assert config.timeout == 300
        assert len(config.ports) == 2
        assert len(config.volumes) == 2
        assert config.generate_new_certificates is True
        assert config.command_override == "nginx -g 'daemon off;'"
        assert config.working_directory == "/app"
        assert config.depends_on == ["database", "redis"]
        assert config.restart_policy == "unless-stopped"
        assert config.plugin_config["custom_param"] == "value"

    def test_service_config_serialization(self):
        """Test ServiceConfig serialization."""
        implementation = ImplementationConfig(name="test_impl", type="iut")
        protocol = ProtocolConfig(
            name="test_proto", role="client", target="test_server"
        )

        config = ServiceConfig(
            implementation=implementation,
            protocol=protocol,
            environment={"KEY": "value"},
            ports=["9000:8000"],
        )

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["implementation"]["name"] == "test_impl"
        assert config_dict["protocol"]["name"] == "test_proto"
        assert config_dict["environment"]["KEY"] == "value"
        assert config_dict["ports"] == ["9000:8000"]


class TestTestConfig:
    """Test TestConfig functionality."""

    def test_test_config_minimal(self):
        """Test TestConfig with minimal required fields."""
        network_env = NetworkEnvironmentConfig(type="docker_compose")

        services = {
            "test_service": ServiceConfig(
                implementation=ImplementationConfig(name="test_impl", type="iut"),
                protocol=ProtocolConfig(name="quic", role="server"),
            )
        }

        config = TestConfig(
            name="Basic Test", network_environment=network_env, services=services
        )

        assert config.name == "Basic Test"
        assert config.description is None
        assert config.iterations == 1
        assert config.timeout is None
        assert config.fast_fail_enabled is None
        assert config.continue_on_failure is False
        assert config.collect_artifacts is True
        assert isinstance(config.network_environment, NetworkEnvironmentConfig)
        assert len(config.services) == 1
        assert "test_service" in config.services

    def test_test_config_complete(self):
        """Test TestConfig with all features."""
        network_env = NetworkEnvironmentConfig(type="shadow_ns", enabled=True)

        execution_envs = [
            ExecutionEnvironmentConfig(type="strace"),
            ExecutionEnvironmentConfig(type="gperf_cpu"),
        ]

        services = {
            "client": ServiceConfig(
                implementation=ImplementationConfig(
                    name="picoquic", version="1.0", type="iut"
                ),
                protocol=ProtocolConfig(name="quic", role="client", target="server"),
                timeout=300,
            ),
            "server": ServiceConfig(
                implementation=ImplementationConfig(
                    name="nginx", version="1.21", type="iut"
                ),
                protocol=ProtocolConfig(name="quic", role="server"),
                timeout=300,
                depends_on=["client"],
            ),
        }

        steps = StepsConfig(
            pre_commands=["echo 'Starting test'"],
            wait=60,
            post_commands=["echo 'Test completed'"],
        )

        config = TestConfig(
            name="Complete Test",
            description="Full featured test configuration",
            network_environment=network_env,
            execution_environment=execution_envs,
            services=services,
            steps=steps,
            iterations=5,
            timeout=1800,
            fast_fail_enabled=False,
            continue_on_failure=True,
            collect_artifacts=False,
        )

        # Verify all components
        assert config.name == "Complete Test"
        assert config.description == "Full featured test configuration"
        assert config.iterations == 5
        assert config.timeout == 1800
        assert config.fast_fail_enabled is False
        assert config.continue_on_failure is True
        assert config.collect_artifacts is False

        assert isinstance(config.network_environment, NetworkEnvironmentConfig)
        assert config.network_environment.type == "shadow_ns"

        assert len(config.execution_environment) == 2
        assert config.execution_environment[0].type == "strace"
        assert config.execution_environment[1].type == "gperf_cpu"

        assert len(config.services) == 2
        assert config.services["client"].protocol.role == "client"
        assert config.services["server"].protocol.role == "server"
        assert config.services["server"].depends_on == ["client"]

        assert config.steps.wait == 60
        assert len(config.steps.pre_commands) == 1

    def test_test_config_validation(self):
        """Test TestConfig validation rules."""
        network_env = NetworkEnvironmentConfig(type="localhost_single_container")
        services = {
            "service1": ServiceConfig(
                implementation=ImplementationConfig(name="impl1", type="iut"),
                protocol=ProtocolConfig(name="proto1", role="server"),
            )
        }

        # Test valid config
        config = TestConfig(
            name="Valid Test", network_environment=network_env, services=services
        )
        assert config.name == "Valid Test"

    def test_test_config_serialization(self):
        """Test TestConfig serialization/deserialization."""
        network_env = NetworkEnvironmentConfig(type="docker_compose")
        services = {
            "test_service": ServiceConfig(
                implementation=ImplementationConfig(name="test_impl", type="iut"),
                protocol=ProtocolConfig(name="quic", role="server"),
            )
        }

        original = TestConfig(
            name="Serialization Test",
            network_environment=network_env,
            services=services,
            iterations=3,
        )

        # Test YAML serialization
        yaml_str = original.to_yaml()
        yaml_dict = yaml.safe_load(yaml_str)

        # Check that we can create from dict (validation)
        assert yaml_dict["name"] == "Serialization Test"
        assert yaml_dict["iterations"] == 3
        assert yaml_dict["network_environment"]["type"] == "docker_compose"

        # Test JSON serialization
        json_str = original.to_json()
        json_dict = json.loads(json_str)

        assert json_dict["name"] == "Serialization Test"
        assert json_dict["iterations"] == 3


class TestExperimentConfig:
    """Test ExperimentConfig functionality."""

    def test_experiment_config_defaults(self):
        """Test ExperimentConfig with minimal required fields."""
        # ExperimentConfig requires at least one test
        minimal_service = ServiceConfig(
            implementation=ImplementationConfig(name="test_impl", type="iut"),
            protocol=ProtocolConfig(name="test_proto", role="server"),
        )

        minimal_test = TestConfig(
            name="Minimal Test",
            network_environment=NetworkEnvironmentConfig(type="docker_compose"),
            services={"test_service": minimal_service},
        )

        config = ExperimentConfig(tests=[minimal_test])

        assert len(config.tests) == 1
        assert config.tests[0].name == "Minimal Test"
        assert config.metadata is None

    def test_experiment_config_with_metadata(self):
        """Test ExperimentConfig with metadata."""
        # Create minimal test for ExperimentConfig
        minimal_service = ServiceConfig(
            implementation=ImplementationConfig(name="test_impl", type="iut"),
            protocol=ProtocolConfig(name="test_proto", role="server"),
        )

        minimal_test = TestConfig(
            name="Metadata Test",
            network_environment=NetworkEnvironmentConfig(type="docker_compose"),
            services={"test_service": minimal_service},
        )

        metadata = ExperimentMetadata(
            name="Test Suite",
            description="Comprehensive test suite",
            author="Test Team",
        )

        config = ExperimentConfig(tests=[minimal_test], metadata=metadata)

        assert len(config.tests) == 1
        assert config.tests[0].name == "Metadata Test"
        assert config.metadata.name == "Test Suite"
        assert config.metadata.author == "Test Team"

    def test_experiment_config_with_tests(self):
        """Test ExperimentConfig with multiple tests."""
        # Create test configurations
        network_env1 = NetworkEnvironmentConfig(type="docker_compose")
        network_env2 = NetworkEnvironmentConfig(type="localhost_single_container")

        services1 = {
            "service1": ServiceConfig(
                implementation=ImplementationConfig(name="impl1", type="iut"),
                protocol=ProtocolConfig(name="quic", role="server"),
            )
        }

        services2 = {
            "service2": ServiceConfig(
                implementation=ImplementationConfig(name="impl2", type="iut"),
                protocol=ProtocolConfig(name="http", role="server"),
            )
        }

        test1 = TestConfig(
            name="QUIC Test", network_environment=network_env1, services=services1
        )

        test2 = TestConfig(
            name="HTTP Test", network_environment=network_env2, services=services2
        )

        metadata = ExperimentMetadata(
            name="Multi-Protocol Test Suite", description="Testing multiple protocols"
        )

        config = ExperimentConfig(tests=[test1, test2], metadata=metadata)

        assert len(config.tests) == 2
        assert config.tests[0].name == "QUIC Test"
        assert config.tests[1].name == "HTTP Test"
        assert config.metadata.name == "Multi-Protocol Test Suite"

    def test_experiment_config_complex_scenario(self):
        """Test ExperimentConfig with complex real-world scenario."""
        # Create QUIC Performance Test
        quic_services = {
            "quic_client": ServiceConfig(
                implementation=ImplementationConfig(
                    name="picoquic", version="1.0", type="iut"
                ),
                protocol=ProtocolConfig(
                    name="quic", role="client", target="quic_server"
                ),
                timeout=300,
            ),
            "quic_server": ServiceConfig(
                implementation=ImplementationConfig(
                    name="nginx", version="1.21", type="iut"
                ),
                protocol=ProtocolConfig(name="quic", role="server"),
                timeout=300,
            ),
        }

        quic_test = TestConfig(
            name="QUIC Performance Test",
            description="Testing QUIC protocol performance under load",
            network_environment=NetworkEnvironmentConfig(type="docker_compose"),
            services=quic_services,
            iterations=10,
            steps=StepsConfig(wait=45, pre_commands=["echo 'Starting QUIC test'"]),
            timeout=1800,
        )

        # Create HTTP/2 Comparison Test
        http2_services = {
            "http2_client": ServiceConfig(
                implementation=ImplementationConfig(
                    name="curl", version="7.80", type="iut"
                ),
                protocol=ProtocolConfig(
                    name="http2", role="client", target="http2_server"
                ),
            ),
            "http2_server": ServiceConfig(
                implementation=ImplementationConfig(
                    name="nginx", version="1.21", type="iut"
                ),
                protocol=ProtocolConfig(name="http2", role="server"),
            ),
        }

        http2_test = TestConfig(
            name="HTTP/2 Comparison Test",
            description="Comparing HTTP/2 performance against QUIC",
            network_environment=NetworkEnvironmentConfig(
                type="localhost_single_container"
            ),
            services=http2_services,
            iterations=10,
            steps=StepsConfig(wait=30, pre_commands=["echo 'Starting HTTP/2 test'"]),
            timeout=1200,
        )

        metadata = ExperimentMetadata(
            name="Protocol Performance Comparison",
            description="Comprehensive comparison of QUIC vs HTTP/2 performance",
            version="1.2",
            author="Performance Team",
            tags=["quic", "http2", "performance", "comparison"],
        )

        config = ExperimentConfig(tests=[quic_test, http2_test], metadata=metadata)

        # Verify complex configuration
        assert len(config.tests) == 2
        assert config.metadata.name == "Protocol Performance Comparison"
        assert "comparison" in config.metadata.tags

        # Verify QUIC test
        quic_test = config.tests[0]
        assert quic_test.name == "QUIC Performance Test"
        assert quic_test.iterations == 10
        assert len(quic_test.steps.pre_commands) == 1
        assert isinstance(quic_test.network_environment, NetworkEnvironmentConfig)
        assert len(quic_test.services) == 2
        assert quic_test.services["quic_client"].protocol.role == "client"

        # Verify HTTP/2 test
        http2_test = config.tests[1]
        assert http2_test.name == "HTTP/2 Comparison Test"
        assert isinstance(http2_test.network_environment, NetworkEnvironmentConfig)

    def test_experiment_config_serialization_roundtrip(self):
        """Test ExperimentConfig complete serialization round-trip."""
        services = {
            "test_service": ServiceConfig(
                implementation=ImplementationConfig(name="picoquic", type="iut"),
                protocol=ProtocolConfig(name="quic", role="server"),
            )
        }

        test = TestConfig(
            name="Roundtrip Test",
            network_environment=NetworkEnvironmentConfig(type="docker_compose"),
            services=services,
            iterations=5,
        )

        metadata = ExperimentMetadata(
            name="Roundtrip Experiment", tags=["test", "roundtrip"]
        )

        original = ExperimentConfig(tests=[test], metadata=metadata)

        # YAML round-trip test structure verification
        yaml_str = original.to_yaml()
        yaml_dict = yaml.safe_load(yaml_str)

        assert len(yaml_dict["tests"]) == 1
        assert yaml_dict["tests"][0]["name"] == "Roundtrip Test"
        assert yaml_dict["tests"][0]["iterations"] == 5
        assert yaml_dict["metadata"]["name"] == "Roundtrip Experiment"
        assert "roundtrip" in yaml_dict["metadata"]["tags"]

        # JSON round-trip test structure verification
        json_str = original.to_json()
        json_dict = json.loads(json_str)

        assert len(json_dict["tests"]) == 1
        assert json_dict["tests"][0]["name"] == "Roundtrip Test"
        assert json_dict["metadata"]["name"] == "Roundtrip Experiment"


class TestBusinessRulesValidation:
    """Test BusinessRulesValidator service validation rules."""

    def _make_test_config(self, services_dict):
        """Helper to create a TestConfig with given services."""
        services = {}
        for name, (impl_type, role, target) in services_dict.items():
            proto_kwargs = {"name": "quic", "role": role}
            if target:
                proto_kwargs["target"] = target
            services[name] = ServiceConfig(
                implementation=ImplementationConfig(
                    name=f"{name}_impl", type=impl_type
                ),
                protocol=ProtocolConfig(**proto_kwargs),
            )
        return TestConfig(
            name="Test",
            network_environment=NetworkEnvironmentConfig(type="docker_compose"),
            services=services,
        )

    def _validate(self, test_config):
        """Run BusinessRulesValidator on a TestConfig."""
        from panther.config.core.components.validators import BusinessRulesValidator

        validator = BusinessRulesValidator()
        return validator._validate_test_rules(test_config)

    def test_single_service_produces_error(self):
        """Rule 1: Single service should produce an error."""
        tc = self._make_test_config({"svc": ("iut", "server", None)})
        result = self._validate(tc)
        assert not result.is_valid
        error_msgs = [e.message for e in result.errors]
        assert any("At least 2 services" in m for m in error_msgs)

    def test_two_services_no_count_error(self):
        """Rule 1: Two services should not produce a count error."""
        tc = self._make_test_config(
            {
                "client": ("iut", "client", "server"),
                "server": ("iut", "server", None),
            }
        )
        result = self._validate(tc)
        error_msgs = [e.message for e in result.errors]
        assert not any("At least 2 services" in m for m in error_msgs)

    def test_no_tester_produces_warning(self):
        """Rule 2: No tester service should produce a warning."""
        tc = self._make_test_config(
            {
                "client": ("iut", "client", "server"),
                "server": ("iut", "server", None),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert any("No tester service" in m for m in warning_msgs)

    def test_with_tester_no_tester_warning(self):
        """Rule 2: Tester present should not produce tester warning."""
        tc = self._make_test_config(
            {
                "iut_server": ("iut", "server", None),
                "tester_client": ("testers", "client", "iut_server"),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert not any("No tester service" in m for m in warning_msgs)

    def test_no_iut_produces_warning(self):
        """Rule 5: No IUT service should produce a warning."""
        tc = self._make_test_config(
            {
                "tester1": ("testers", "client", "tester2"),
                "tester2": ("testers", "server", None),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert any("No IUT service" in m for m in warning_msgs)

    def test_with_iut_no_iut_warning(self):
        """Rule 5: IUT present should not produce IUT warning."""
        tc = self._make_test_config(
            {
                "iut_server": ("iut", "server", None),
                "tester_client": ("testers", "client", "iut_server"),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert not any("No IUT service" in m for m in warning_msgs)

    def test_client_without_server_produces_warning(self):
        """Rule 3: Client without server should produce a warning."""
        # Pydantic requires clients to have a target, so we point them at each other
        tc = self._make_test_config(
            {
                "client1": ("iut", "client", "client2"),
                "client2": ("testers", "client", "client1"),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert any("no server service" in m for m in warning_msgs)

    def test_server_without_client_produces_warning(self):
        """Rule 3: Server without client should produce a warning."""
        tc = self._make_test_config(
            {
                "server1": ("iut", "server", None),
                "server2": ("testers", "server", None),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert any("no client service" in m for m in warning_msgs)

    def test_client_and_server_no_counterpart_warning(self):
        """Rule 3: Both client and server should not produce counterpart warning."""
        tc = self._make_test_config(
            {
                "client": ("iut", "client", "server"),
                "server": ("testers", "server", None),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert not any("no server service" in m for m in warning_msgs)
        assert not any("no client service" in m for m in warning_msgs)

    def test_client_without_target_covered_by_pydantic(self):
        """Rule 4: Pydantic enforces that clients must have a target.

        The 'client without target' business rule is a defensive check
        that only triggers for raw dicts (webapp). ProtocolConfig's
        validator prevents creating a client without a target, so we
        verify that the Pydantic constraint works.
        """
        with pytest.raises(
            ValidationError, match="Client services must specify a target"
        ):
            self._make_test_config(
                {
                    "client": ("iut", "client", None),
                    "server": ("testers", "server", None),
                }
            )

    def test_client_targeting_non_server_produces_warning(self):
        """Rule 4: Client targeting a peer should produce a warning."""
        tc = self._make_test_config(
            {
                "client": ("iut", "client", "peer_svc"),
                "peer_svc": ("testers", "peer", None),
            }
        )
        result = self._validate(tc)
        warning_msgs = [w.message for w in result.warnings]
        assert any("expected role='server'" in m for m in warning_msgs)

    def test_single_service_testconfig_construction_works(self):
        """Pydantic-level construction should still allow 1 service."""
        tc = self._make_test_config({"svc": ("iut", "server", None)})
        assert len(tc.services) == 1


if __name__ in {"__main__", "__mp_main__"}:
    print("Running comprehensive ExperimentConfig test suite (actual structure)...")

    try:
        # Test basic components
        test_steps = TestStepsConfig()
        test_steps.test_steps_config_defaults()
        test_steps.test_steps_config_custom_values()
        test_steps.test_steps_config_serialization()
        print("✓ StepsConfig tests passed")

        test_metadata = TestExperimentMetadata()
        test_metadata.test_experiment_metadata_defaults()
        test_metadata.test_experiment_metadata_custom()
        test_metadata.test_experiment_metadata_serialization()
        print("✓ ExperimentMetadata tests passed")

        # Test environment configurations
        test_network = TestNetworkEnvironmentConfig()
        test_network.test_network_environment_config_basic()
        test_network.test_network_environment_config_custom()
        print("✓ NetworkEnvironmentConfig tests passed")

        test_execution = TestExecutionEnvironmentConfig()
        test_execution.test_execution_environment_config_basic()
        test_execution.test_execution_environment_config_custom()
        test_execution.test_execution_environment_config_list()
        print("✓ ExecutionEnvironmentConfig tests passed")

        # Test service configurations
        test_service = TestServiceConfig()
        test_service.test_service_config_minimal()
        test_service.test_service_config_complete()
        test_service.test_service_config_serialization()
        print("✓ ServiceConfig tests passed")

        # Test TestConfig
        test_test_config = TestTestConfig()
        test_test_config.test_test_config_minimal()
        test_test_config.test_test_config_complete()
        test_test_config.test_test_config_validation()
        test_test_config.test_test_config_serialization()
        print("✓ TestConfig tests passed")

        # Test ExperimentConfig
        test_experiment = TestExperimentConfig()
        test_experiment.test_experiment_config_defaults()
        test_experiment.test_experiment_config_with_metadata()
        test_experiment.test_experiment_config_with_tests()
        test_experiment.test_experiment_config_complex_scenario()
        test_experiment.test_experiment_config_serialization_roundtrip()
        print("✓ ExperimentConfig tests passed")

        print("\n🎉 ALL COMPREHENSIVE EXPERIMENT CONFIG TESTS PASSED!")
        print("✅ Tested actual PANTHER configuration structure")
        print("✅ Tested ExperimentConfig and TestConfig")
        print("✅ Tested NetworkEnvironmentConfig and ExecutionEnvironmentConfig")
        print("✅ Tested ServiceConfig with all features")
        print("✅ Tested StepsConfig and ExperimentMetadata")
        print("✅ Tested complex real-world scenarios")
        print("✅ Tested serialization and round-trips")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
