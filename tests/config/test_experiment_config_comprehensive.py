#!/usr/bin/env python3
"""
Comprehensive test suite for ExperimentConfig and all related models.

This module tests:
- ExperimentConfig and TestConfig classes
- All network environment configurations
- Service configurations and validation
- Steps, assertions, and metadata handling
- Complete integration scenarios
"""

import json
import sys
from typing import Any, Dict, List

import pytest
import yaml
from omegaconf import OmegaConf
from pydantic import ValidationError

from panther.config.core.models.execution_environment import (
    DockerExecutionConfig,
    ExecutionEnvironmentConfig,
    LocalExecutionConfig,
    StraceExecutionConfig,
)
from panther.config.core.models.experiment import (
    ExperimentConfig,
    ExperimentMetadata,
    StepsConfig,
    TestConfig,
)
from panther.config.core.models.network_environment import (
    DockerComposeNetworkConfig,
    LocalhostNetworkConfig,
    NetworkEnvironmentConfig,
    ShadowNSNetworkConfig,
)
from panther.config.core.models.service import (
    EnvironmentVariable,
    ImplementationConfig,
    PortMapping,
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

        assert config.wait == 30
        assert config.record_pcap is None
        assert config.enable_monitoring is True
        assert config.setup_timeout == 60
        assert config.teardown_timeout == 30

    def test_steps_config_custom_values(self):
        """Test StepsConfig with custom values."""
        config = StepsConfig(
            wait=120,
            record_pcap=True,
            enable_monitoring=False,
            setup_timeout=180,
            teardown_timeout=60,
        )

        assert config.wait == 120
        assert config.record_pcap is True
        assert config.enable_monitoring is False
        assert config.setup_timeout == 180
        assert config.teardown_timeout == 60

    def test_steps_config_validation(self):
        """Test StepsConfig validation rules."""
        # Test negative wait time
        with pytest.raises(ValidationError):
            StepsConfig(wait=-10)

        # Test zero timeout
        with pytest.raises(ValidationError):
            StepsConfig(setup_timeout=0)

        # Test negative teardown timeout
        with pytest.raises(ValidationError):
            StepsConfig(teardown_timeout=-5)


class TestExperimentMetadata:
    """Test ExperimentMetadata functionality."""

    def test_experiment_metadata_defaults(self):
        """Test ExperimentMetadata with defaults."""
        metadata = ExperimentMetadata()

        assert metadata.name == "Unnamed Experiment"
        assert metadata.description == ""
        assert metadata.version == "1.0"
        assert metadata.author is None
        assert metadata.tags == []
        assert metadata.timeout is None

    def test_experiment_metadata_custom(self):
        """Test ExperimentMetadata with custom values."""
        metadata = ExperimentMetadata(
            name="QUIC Performance Test",
            description="Testing QUIC protocol performance",
            version="2.1",
            author="Test Engineer",
            tags=["quic", "performance", "network"],
            timeout=3600,
        )

        assert metadata.name == "QUIC Performance Test"
        assert metadata.description == "Testing QUIC protocol performance"
        assert metadata.version == "2.1"
        assert metadata.author == "Test Engineer"
        assert metadata.tags == ["quic", "performance", "network"]
        assert metadata.timeout == 3600

    def test_experiment_metadata_validation(self):
        """Test ExperimentMetadata validation."""
        # Test negative timeout
        with pytest.raises(ValidationError):
            ExperimentMetadata(timeout=-100)


class TestNetworkEnvironmentConfigs:
    """Test all network environment configurations."""

    def test_docker_compose_network_config_defaults(self):
        """Test DockerComposeNetworkConfig defaults."""
        config = DockerComposeNetworkConfig()

        assert config.type == "docker_compose"
        assert config.version == "3.8"
        assert config.network_name == "panther_network"
        assert config.subnet is None
        assert config.enable_ipv6 is False
        assert config.volumes == []
        assert config.environment == {}

    def test_docker_compose_network_config_custom(self):
        """Test DockerComposeNetworkConfig with custom values."""
        config = DockerComposeNetworkConfig(
            version="3.9",
            network_name="custom_network",
            subnet="192.168.100.0/24",
            enable_ipv6=True,
            volumes=["./data:/app/data"],
            environment={"ENV": "test", "DEBUG": "true"},
        )

        assert config.version == "3.9"
        assert config.network_name == "custom_network"
        assert config.subnet == "192.168.100.0/24"
        assert config.enable_ipv6 is True
        assert config.volumes == ["./data:/app/data"]
        assert config.environment == {"ENV": "test", "DEBUG": "true"}

    def test_localhost_network_config_defaults(self):
        """Test LocalhostNetworkConfig defaults."""
        config = LocalhostNetworkConfig()

        assert config.type == "localhost"
        assert config.interface == "lo"
        assert config.enable_port_forwarding is False
        assert config.port_range_start == 10000
        assert config.port_range_end == 20000

    def test_localhost_network_config_custom(self):
        """Test LocalhostNetworkConfig with custom values."""
        config = LocalhostNetworkConfig(
            interface="eth0",
            enable_port_forwarding=True,
            port_range_start=30000,
            port_range_end=40000,
        )

        assert config.interface == "eth0"
        assert config.enable_port_forwarding is True
        assert config.port_range_start == 30000
        assert config.port_range_end == 40000

    def test_shadow_ns_network_config_defaults(self):
        """Test ShadowNSNetworkConfig defaults."""
        config = ShadowNSNetworkConfig()

        assert config.type == "shadow_ns"
        assert config.namespace_prefix == "panther"
        assert config.bridge_name == "pantherBridge"
        assert config.enable_logging is True
        assert config.cleanup_on_exit is True

    def test_network_environment_config_polymorphism(self):
        """Test NetworkEnvironmentConfig polymorphic behavior."""
        # Test creating different network types
        docker_config = NetworkEnvironmentConfig(type="docker_compose", version="3.8")
        assert isinstance(docker_config, DockerComposeNetworkConfig)
        assert docker_config.version == "3.8"

        localhost_config = NetworkEnvironmentConfig(type="localhost", interface="eth1")
        assert isinstance(localhost_config, LocalhostNetworkConfig)
        assert localhost_config.interface == "eth1"

        shadow_config = NetworkEnvironmentConfig(
            type="shadow_ns", namespace_prefix="test"
        )
        assert isinstance(shadow_config, ShadowNSNetworkConfig)
        assert shadow_config.namespace_prefix == "test"


class TestExecutionEnvironmentConfigs:
    """Test all execution environment configurations."""

    def test_local_execution_config_defaults(self):
        """Test LocalExecutionConfig defaults."""
        config = LocalExecutionConfig()

        assert config.type == "local"
        assert config.timeout == 300
        assert config.working_directory is None
        assert config.environment_variables == {}
        assert config.capture_output is True

    def test_docker_execution_config_defaults(self):
        """Test DockerExecutionConfig defaults."""
        config = DockerExecutionConfig()

        assert config.type == "docker"
        assert config.timeout == 300
        assert config.image == "ubuntu:latest"
        assert config.command is None
        assert config.volumes == []
        assert config.environment_variables == {}
        assert config.network_mode == "bridge"

    def test_strace_execution_config_defaults(self):
        """Test StraceExecutionConfig defaults."""
        config = StraceExecutionConfig()

        assert config.type == "strace"
        assert config.timeout == 300
        assert config.trace_syscalls == []
        assert config.output_file is None
        assert config.follow_forks is True
        assert config.trace_children is True


class TestServiceConfig:
    """Test service configuration classes."""

    def test_port_mapping(self):
        """Test PortMapping configuration."""
        port = PortMapping(host_port=8080, container_port=80, protocol="tcp")

        assert port.host_port == 8080
        assert port.container_port == 80
        assert port.protocol == "tcp"

    def test_environment_variable(self):
        """Test EnvironmentVariable configuration."""
        env_var = EnvironmentVariable(name="API_KEY", value="secret123", secure=True)

        assert env_var.name == "API_KEY"
        assert env_var.value == "secret123"
        assert env_var.secure is True

    def test_implementation_config_defaults(self):
        """Test ImplementationConfig defaults."""
        config = ImplementationConfig(name="picoquic")

        assert config.name == "picoquic"
        assert config.version is None
        assert config.type == "iut"
        assert config.build_args == {}
        assert config.environment_variables == []

    def test_protocol_config_defaults(self):
        """Test ProtocolConfig defaults."""
        config = ProtocolConfig(name="quic")

        assert config.name == "quic"
        assert config.version is None
        assert config.role == "client"
        assert config.parameters == {}

    def test_service_config_complete(self):
        """Test complete ServiceConfig."""
        port_mapping = PortMapping(host_port=8080, container_port=80)
        env_var = EnvironmentVariable(name="MODE", value="test")
        implementation = ImplementationConfig(
            name="nginx", version="1.21", environment_variables=[env_var]
        )
        protocol = ProtocolConfig(name="http", version="1.1", role="server")

        config = ServiceConfig(
            name="web_server",
            implementation=implementation,
            protocol=protocol,
            ports=[port_mapping],
            timeout=120,
            depends_on=["database"],
            environment_variables=[env_var],
        )

        assert config.name == "web_server"
        assert config.implementation.name == "nginx"
        assert config.protocol.name == "http"
        assert len(config.ports) == 1
        assert config.ports[0].host_port == 8080
        assert config.timeout == 120
        assert config.depends_on == ["database"]


class TestTestConfig:
    """Test TestConfig functionality."""

    def test_test_config_minimal(self):
        """Test TestConfig with minimal required fields."""
        network_env = DockerComposeNetworkConfig()
        services = {
            "test_service": ServiceConfig(
                name="test_service",
                implementation=ImplementationConfig(name="test_impl"),
                protocol=ProtocolConfig(name="quic"),
            )
        }

        config = TestConfig(
            name="Basic Test", network_environment=network_env, services=services
        )

        assert config.name == "Basic Test"
        assert config.description == ""
        assert config.iterations == 1
        assert config.parallel_execution is False
        assert isinstance(config.network_environment, DockerComposeNetworkConfig)
        assert len(config.services) == 1
        assert "test_service" in config.services

    def test_test_config_complete(self):
        """Test TestConfig with all features."""
        # Create comprehensive test configuration
        network_env = DockerComposeNetworkConfig(
            version="3.9", network_name="test_network"
        )

        execution_envs = [
            LocalExecutionConfig(timeout=600),
            DockerExecutionConfig(image="test:latest"),
        ]

        services = {
            "client": ServiceConfig(
                name="client",
                implementation=ImplementationConfig(name="picoquic", version="1.0"),
                protocol=ProtocolConfig(name="quic", role="client"),
                timeout=300,
            ),
            "server": ServiceConfig(
                name="server",
                implementation=ImplementationConfig(name="nginx", version="1.21"),
                protocol=ProtocolConfig(name="quic", role="server"),
                timeout=300,
                depends_on=["client"],
            ),
        }

        steps = StepsConfig(wait=60, record_pcap=True)

        metadata = ExperimentMetadata(
            name="QUIC Performance Test",
            description="Comprehensive QUIC testing",
            tags=["quic", "performance"],
        )

        config = TestConfig(
            name="Complete QUIC Test",
            description="Full featured QUIC test configuration",
            network_environment=network_env,
            execution_environments=execution_envs,
            services=services,
            iterations=5,
            parallel_execution=True,
            steps=steps,
            metadata=metadata,
            timeout=1800,
        )

        # Verify all components
        assert config.name == "Complete QUIC Test"
        assert config.description == "Full featured QUIC test configuration"
        assert config.iterations == 5
        assert config.parallel_execution is True
        assert config.timeout == 1800

        assert isinstance(config.network_environment, DockerComposeNetworkConfig)
        assert config.network_environment.version == "3.9"

        assert len(config.execution_environments) == 2
        assert isinstance(config.execution_environments[0], LocalExecutionConfig)
        assert isinstance(config.execution_environments[1], DockerExecutionConfig)

        assert len(config.services) == 2
        assert config.services["client"].protocol.role == "client"
        assert config.services["server"].protocol.role == "server"
        assert config.services["server"].depends_on == ["client"]

        assert config.steps.wait == 60
        assert config.steps.record_pcap is True

        assert config.metadata.name == "QUIC Performance Test"
        assert "performance" in config.metadata.tags

    def test_test_config_validation(self):
        """Test TestConfig validation rules."""
        network_env = LocalhostNetworkConfig()
        services = {
            "service1": ServiceConfig(
                name="service1",
                implementation=ImplementationConfig(name="impl1"),
                protocol=ProtocolConfig(name="proto1"),
            )
        }

        # Test negative iterations
        with pytest.raises(ValidationError):
            TestConfig(
                name="Invalid Test",
                network_environment=network_env,
                services=services,
                iterations=-1,
            )

        # Test zero timeout
        with pytest.raises(ValidationError):
            TestConfig(
                name="Invalid Test",
                network_environment=network_env,
                services=services,
                timeout=0,
            )

    def test_test_config_serialization(self):
        """Test TestConfig serialization/deserialization."""
        network_env = DockerComposeNetworkConfig(version="3.8")
        services = {
            "test_service": ServiceConfig(
                name="test_service",
                implementation=ImplementationConfig(name="test_impl"),
                protocol=ProtocolConfig(name="quic"),
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
        from_yaml = TestConfig(**yaml_dict)

        assert from_yaml.name == original.name
        assert from_yaml.iterations == original.iterations
        assert isinstance(from_yaml.network_environment, DockerComposeNetworkConfig)
        assert from_yaml.network_environment.version == "3.8"

        # Test JSON serialization
        json_str = original.to_json()
        json_dict = json.loads(json_str)
        from_json = TestConfig(**json_dict)

        assert from_json.name == original.name
        assert from_json.iterations == original.iterations


class TestExperimentConfig:
    """Test ExperimentConfig functionality."""

    def test_experiment_config_defaults(self):
        """Test ExperimentConfig with defaults."""
        config = ExperimentConfig()

        assert config.tests == []
        assert isinstance(config.metadata, ExperimentMetadata)
        assert config.metadata.name == "Unnamed Experiment"

    def test_experiment_config_with_tests(self):
        """Test ExperimentConfig with multiple tests."""
        # Create test configurations
        network_env1 = DockerComposeNetworkConfig()
        network_env2 = LocalhostNetworkConfig()

        services1 = {
            "service1": ServiceConfig(
                name="service1",
                implementation=ImplementationConfig(name="impl1"),
                protocol=ProtocolConfig(name="quic"),
            )
        }

        services2 = {
            "service2": ServiceConfig(
                name="service2",
                implementation=ImplementationConfig(name="impl2"),
                protocol=ProtocolConfig(name="http"),
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
        # Create multiple test scenarios
        tests = []

        # QUIC Performance Test
        quic_services = {
            "quic_client": ServiceConfig(
                name="quic_client",
                implementation=ImplementationConfig(name="picoquic", version="1.0"),
                protocol=ProtocolConfig(name="quic", role="client"),
                timeout=300,
            ),
            "quic_server": ServiceConfig(
                name="quic_server",
                implementation=ImplementationConfig(name="nginx", version="1.21"),
                protocol=ProtocolConfig(name="quic", role="server"),
                timeout=300,
            ),
        }

        quic_test = TestConfig(
            name="QUIC Performance Test",
            description="Testing QUIC protocol performance under load",
            network_environment=DockerComposeNetworkConfig(version="3.9"),
            services=quic_services,
            iterations=10,
            steps=StepsConfig(wait=45, record_pcap=True),
            timeout=1800,
        )

        # HTTP/2 Comparison Test
        http2_services = {
            "http2_client": ServiceConfig(
                name="http2_client",
                implementation=ImplementationConfig(name="curl", version="7.80"),
                protocol=ProtocolConfig(name="http2", role="client"),
            ),
            "http2_server": ServiceConfig(
                name="http2_server",
                implementation=ImplementationConfig(name="nginx", version="1.21"),
                protocol=ProtocolConfig(name="http2", role="server"),
            ),
        }

        http2_test = TestConfig(
            name="HTTP/2 Comparison Test",
            description="Comparing HTTP/2 performance against QUIC",
            network_environment=LocalhostNetworkConfig(enable_port_forwarding=True),
            services=http2_services,
            iterations=10,
            steps=StepsConfig(wait=30, record_pcap=True),
            timeout=1200,
        )

        tests = [quic_test, http2_test]

        metadata = ExperimentMetadata(
            name="Protocol Performance Comparison",
            description="Comprehensive comparison of QUIC vs HTTP/2 performance",
            version="1.2",
            author="Performance Team",
            tags=["quic", "http2", "performance", "comparison"],
            timeout=3600,
        )

        config = ExperimentConfig(tests=tests, metadata=metadata)

        # Verify complex configuration
        assert len(config.tests) == 2
        assert config.metadata.name == "Protocol Performance Comparison"
        assert "comparison" in config.metadata.tags

        # Verify QUIC test
        quic_test = config.tests[0]
        assert quic_test.name == "QUIC Performance Test"
        assert quic_test.iterations == 10
        assert quic_test.steps.record_pcap is True
        assert isinstance(quic_test.network_environment, DockerComposeNetworkConfig)
        assert len(quic_test.services) == 2
        assert quic_test.services["quic_client"].protocol.role == "client"

        # Verify HTTP/2 test
        http2_test = config.tests[1]
        assert http2_test.name == "HTTP/2 Comparison Test"
        assert isinstance(http2_test.network_environment, LocalhostNetworkConfig)
        assert http2_test.network_environment.enable_port_forwarding is True

    def test_experiment_config_serialization_roundtrip(self):
        """Test ExperimentConfig complete serialization round-trip."""
        # Create complex configuration
        services = {
            "test_service": ServiceConfig(
                name="test_service",
                implementation=ImplementationConfig(name="picoquic"),
                protocol=ProtocolConfig(name="quic", role="server"),
            )
        }

        test = TestConfig(
            name="Roundtrip Test",
            network_environment=DockerComposeNetworkConfig(version="3.8"),
            services=services,
            iterations=5,
        )

        metadata = ExperimentMetadata(
            name="Roundtrip Experiment", tags=["test", "roundtrip"]
        )

        original = ExperimentConfig(tests=[test], metadata=metadata)

        # YAML round-trip
        yaml_str = original.to_yaml()
        yaml_dict = yaml.safe_load(yaml_str)
        from_yaml = ExperimentConfig(**yaml_dict)

        assert len(from_yaml.tests) == 1
        assert from_yaml.tests[0].name == "Roundtrip Test"
        assert from_yaml.tests[0].iterations == 5
        assert from_yaml.metadata.name == "Roundtrip Experiment"
        assert "roundtrip" in from_yaml.metadata.tags

        # JSON round-trip
        json_str = original.to_json()
        json_dict = json.loads(json_str)
        from_json = ExperimentConfig(**json_dict)

        assert len(from_json.tests) == 1
        assert from_json.tests[0].name == "Roundtrip Test"
        assert from_json.metadata.name == "Roundtrip Experiment"


if __name__ == "__main__":
    print("Running comprehensive ExperimentConfig test suite...")

    try:
        # Test basic components
        test_steps = TestStepsConfig()
        test_steps.test_steps_config_defaults()
        test_steps.test_steps_config_custom_values()
        test_steps.test_steps_config_validation()
        print("✓ StepsConfig tests passed")

        test_metadata = TestExperimentMetadata()
        test_metadata.test_experiment_metadata_defaults()
        test_metadata.test_experiment_metadata_custom()
        print("✓ ExperimentMetadata tests passed")

        # Test network environments
        test_network = TestNetworkEnvironmentConfigs()
        test_network.test_docker_compose_network_config_defaults()
        test_network.test_localhost_network_config_defaults()
        test_network.test_shadow_ns_network_config_defaults()
        test_network.test_network_environment_config_polymorphism()
        print("✓ NetworkEnvironment tests passed")

        # Test execution environments
        test_execution = TestExecutionEnvironmentConfigs()
        test_execution.test_local_execution_config_defaults()
        test_execution.test_docker_execution_config_defaults()
        test_execution.test_strace_execution_config_defaults()
        print("✓ ExecutionEnvironment tests passed")

        # Test service configurations
        test_service = TestServiceConfig()
        test_service.test_port_mapping()
        test_service.test_environment_variable()
        test_service.test_implementation_config_defaults()
        test_service.test_protocol_config_defaults()
        test_service.test_service_config_complete()
        print("✓ ServiceConfig tests passed")

        # Test TestConfig
        test_test_config = TestTestConfig()
        test_test_config.test_test_config_minimal()
        test_test_config.test_test_config_complete()
        test_test_config.test_test_config_serialization()
        print("✓ TestConfig tests passed")

        # Test ExperimentConfig
        test_experiment = TestExperimentConfig()
        test_experiment.test_experiment_config_defaults()
        test_experiment.test_experiment_config_with_tests()
        test_experiment.test_experiment_config_complex_scenario()
        test_experiment.test_experiment_config_serialization_roundtrip()
        print("✓ ExperimentConfig tests passed")

        print("\n🎉 ALL COMPREHENSIVE EXPERIMENT CONFIG TESTS PASSED!")
        print("✅ Tested ExperimentConfig and TestConfig")
        print("✅ Tested all network environment types")
        print("✅ Tested all execution environment types")
        print("✅ Tested service configurations and dependencies")
        print("✅ Tested steps, metadata, and validation")
        print("✅ Tested complex real-world scenarios")
        print("✅ Tested serialization and round-trips")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
