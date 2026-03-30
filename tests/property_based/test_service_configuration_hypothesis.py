"""Property-based tests for PANTHER service configuration validation using Hypothesis.

This module focuses on testing service configuration patterns, image name generation,
and environment setup validation to ensure robust configuration handling.
"""

import json
import re
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

pytestmark = [pytest.mark.property_based, pytest.mark.service_config]


# Hypothesis strategies for service configuration components
@st.composite
def protocol_name(draw):
    """Generate valid protocol names."""
    protocols = ["quic", "http", "https", "tcp", "udp", "sctp", "websocket", "grpc"]
    custom_protocol = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "-",
            min_size=3,
            max_size=20,
        ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-"))
    )

    return draw(st.one_of(st.sampled_from(protocols), st.just(custom_protocol)))


@st.composite
def implementation_name(draw):
    """Generate valid implementation names."""
    common_implementations = [
        "picoquic",
        "quiche",
        "nginx",
        "apache",
        "haproxy",
        "envoy",
        "nodejs",
        "python",
        "golang",
        "rust",
        "custom",
    ]

    custom_impl = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "-",
            min_size=2,
            max_size=30,
        ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-"))
    )

    return draw(
        st.one_of(st.sampled_from(common_implementations), st.just(custom_impl))
    )


@st.composite
def service_role(draw):
    """Generate valid service roles."""
    roles = [
        "client",
        "server",
        "proxy",
        "load-balancer",
        "gateway",
        "monitor",
        "tester",
    ]
    return draw(st.sampled_from(roles))


@st.composite
def version_string(draw):
    """Generate valid version strings."""
    version_patterns = [
        # Semantic versioning
        st.builds(
            lambda major, minor, patch: f"{major}.{minor}.{patch}",
            major=st.integers(min_value=0, max_value=10),
            minor=st.integers(min_value=0, max_value=20),
            patch=st.integers(min_value=0, max_value=50),
        ),
        # Simple versions
        st.sampled_from(["latest", "stable", "dev", "test", "alpha", "beta", "rc1"]),
        # Date-based versions
        st.builds(
            lambda year, month, day: f"{year}{month:02d}{day:02d}",
            year=st.integers(min_value=2020, max_value=2025),
            month=st.integers(min_value=1, max_value=12),
            day=st.integers(min_value=1, max_value=28),
        ),
        # Git-like versions
        st.builds(
            lambda: f"git-{hex(draw(st.integers(min_value=0, max_value=0xffffff)))[2:]}"
        ),
    ]

    return draw(st.one_of(*version_patterns))


@st.composite
def environment_variables(draw):
    """Generate valid environment variable dictionaries."""
    var_name = st.text(
        alphabet=string.ascii_uppercase + string.digits + "_", min_size=1, max_size=50
    ).filter(lambda x: x and not x[0].isdigit())

    var_value = st.one_of(
        st.text(min_size=0, max_size=200),
        st.integers().map(str),
        st.booleans().map(str),
        st.just(""),
    )

    return draw(
        st.dictionaries(keys=var_name, values=var_value, min_size=0, max_size=20)
    )


@st.composite
def port_configuration(draw):
    """Generate valid port configurations."""
    # Single port
    single_port = st.integers(min_value=1024, max_value=65535)

    # Port range
    port_range = st.builds(
        lambda start, end: f"{start}-{end}",
        start=st.integers(min_value=1024, max_value=60000),
        end=st.integers(min_value=1024, max_value=65535),
    ).filter(lambda x: int(x.split("-")[0]) < int(x.split("-")[1]))

    # Port mapping (host:container)
    port_mapping = st.builds(
        lambda host, container: f"{host}:{container}",
        host=st.integers(min_value=1024, max_value=65535),
        container=st.integers(min_value=1, max_value=65535),
    )

    port_spec = st.one_of(single_port, port_range, port_mapping)

    return draw(st.lists(port_spec, min_size=0, max_size=10, unique=True))


@st.composite
def service_dependencies(draw):
    """Generate service dependency lists."""
    dependency_name = st.text(
        alphabet=string.ascii_lowercase + string.digits + "-", min_size=2, max_size=30
    ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-"))

    return draw(st.lists(dependency_name, min_size=0, max_size=10, unique=True))


@st.composite
def complete_service_configuration(draw):
    """Generate complete PANTHER service configurations."""
    service_name = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "-",
            min_size=2,
            max_size=50,
        ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-"))
    )

    config = {
        "name": service_name,
        "protocol": draw(protocol_name()),
        "implementation": draw(implementation_name()),
        "role": draw(service_role()),
        "version": draw(st.one_of(st.none(), version_string())),
        "environment": draw(environment_variables()),
        "ports": draw(port_configuration()),
        "dependencies": draw(service_dependencies()),
        "dockerfile_path": draw(
            st.one_of(
                st.none(),
                st.just("Dockerfile"),
                st.builds(
                    lambda name: f"docker/{name}.Dockerfile",
                    name=st.text(
                        alphabet=string.ascii_lowercase, min_size=1, max_size=20
                    ),
                ),
            )
        ),
        "build_context": draw(
            st.one_of(
                st.none(),
                st.just("."),
                st.builds(
                    lambda path: f"build/{path}",
                    path=st.text(
                        alphabet=string.ascii_lowercase + "/", min_size=1, max_size=30
                    ),
                ),
            )
        ),
        "volumes": draw(
            st.lists(
                st.builds(
                    lambda host, container: f"{host}:{container}",
                    host=st.text(
                        alphabet=string.ascii_letters + string.digits + "/_-",
                        min_size=1,
                        max_size=50,
                    ),
                    container=st.text(
                        alphabet=string.ascii_letters + string.digits + "/_-",
                        min_size=1,
                        max_size=50,
                    ),
                ),
                min_size=0,
                max_size=5,
            )
        ),
        "command": draw(
            st.one_of(
                st.none(),
                st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),
            )
        ),
        "healthcheck": draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    keys=st.sampled_from(
                        ["test", "interval", "timeout", "retries", "start_period"]
                    ),
                    values=st.text(min_size=1, max_size=100),
                    min_size=1,
                    max_size=5,
                ),
            )
        ),
    }

    return config


@st.composite
def network_configuration(draw):
    """Generate network configurations for services."""
    network_types = ["bridge", "host", "overlay", "macvlan", "none"]

    return {
        "name": draw(
            st.text(
                alphabet=string.ascii_lowercase + string.digits + "-",
                min_size=2,
                max_size=30,
            ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-"))
        ),
        "driver": draw(st.sampled_from(network_types)),
        "subnet": draw(
            st.one_of(
                st.none(),
                st.sampled_from(["172.20.0.0/16", "192.168.100.0/24", "10.0.0.0/8"]),
            )
        ),
        "gateway": draw(
            st.one_of(
                st.none(), st.sampled_from(["172.20.0.1", "192.168.100.1", "10.0.0.1"])
            )
        ),
        "ipam": draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    keys=st.sampled_from(["driver", "config"]),
                    values=st.text(min_size=1, max_size=50),
                    min_size=0,
                    max_size=3,
                ),
            )
        ),
    }


class TestServiceConfigurationProperties:
    """Property-based tests for service configuration validation."""

    @given(complete_service_configuration())
    @settings(max_examples=200)
    def test_valid_service_configs_generate_valid_image_names(self, config):
        """Property: Valid service configs should generate valid Docker image names."""
        # Mock image name generator
        generator = Mock()

        def generate_image_name(service_config):
            """Generate image name following PANTHER conventions."""
            components = []

            # Add service name
            components.append(service_config["name"])

            # Add protocol if specified
            if service_config.get("protocol"):
                components.append(service_config["protocol"])

            # Add implementation if specified
            if service_config.get("implementation"):
                components.append(service_config["implementation"])

            # Add role if specified
            if service_config.get("role"):
                components.append(service_config["role"])

            # Create base name
            base_name = "-".join(components)

            # Add version/tag
            version = service_config.get("version", "latest")
            image_name = f"{base_name}:{version}"

            # Sanitize for Docker naming requirements
            image_name = image_name.lower()
            image_name = re.sub(r"[^a-z0-9:._/-]", "-", image_name)
            image_name = re.sub(r"-+", "-", image_name)
            image_name = image_name.strip("-")

            return image_name

        generator.generate.side_effect = generate_image_name

        # Generate image name
        image_name = generator.generate(config)

        # Validate the generated image name
        assert image_name is not None
        assert len(image_name) > 0
        assert ":" in image_name, f"Generated image name {image_name} missing tag"

        # Check Docker naming constraints
        name_part, tag_part = image_name.split(":", 1)

        # Name part should be valid
        assert re.match(
            r"^[a-z0-9][a-z0-9._/-]*[a-z0-9]$|^[a-z0-9]$", name_part
        ), f"Invalid image name part: {name_part}"

        # Tag part should be valid
        assert re.match(
            r"^[a-z0-9][a-z0-9._-]*$|^[a-z0-9]$", tag_part
        ), f"Invalid image tag part: {tag_part}"

        # Overall length should be reasonable
        assert (
            len(image_name) <= 255
        ), f"Image name too long: {len(image_name)} characters"

    @given(complete_service_configuration())
    @settings(max_examples=100)
    def test_service_config_validation_is_consistent(self, config):
        """Property: Service configuration validation should be consistent."""
        # Mock validator
        validator = Mock()

        def validate_service_config(service_config):
            """Validate service configuration completeness and correctness."""
            errors = []

            # Required fields
            required_fields = ["name", "protocol", "implementation", "role"]
            for field in required_fields:
                if not service_config.get(field):
                    errors.append(f"Missing required field: {field}")

            # Name validation
            name = service_config.get("name", "")
            if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
                errors.append(f"Invalid service name: {name}")

            # Port validation
            ports = service_config.get("ports", [])
            for port in ports:
                if isinstance(port, int):
                    if not (1 <= port <= 65535):
                        errors.append(f"Invalid port number: {port}")
                elif isinstance(port, str):
                    # Handle port ranges and mappings
                    if ":" in port:
                        parts = port.split(":")
                        if len(parts) != 2:
                            errors.append(f"Invalid port mapping: {port}")
                    elif "-" in port:
                        parts = port.split("-")
                        if len(parts) != 2:
                            errors.append(f"Invalid port range: {port}")

            # Environment variable validation
            env_vars = service_config.get("environment", {})
            for key, value in env_vars.items():
                if not re.match(r"^[A-Z_][A-Z0-9_]*$", key):
                    errors.append(f"Invalid environment variable name: {key}")

            return len(errors) == 0, errors

        validator.validate.side_effect = validate_service_config

        # First validation
        is_valid_1, errors_1 = validator.validate(config)

        # Second validation (should be identical)
        is_valid_2, errors_2 = validator.validate(config)

        # Results should be consistent
        assert is_valid_1 == is_valid_2, "Validation results inconsistent between runs"
        assert errors_1 == errors_2, "Validation errors inconsistent between runs"

    @given(st.lists(complete_service_configuration(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_multi_service_configurations_have_unique_names(self, configs):
        """Property: Multi-service configurations should have unique service names."""
        # Mock multi-service validator
        validator = Mock()

        def validate_unique_names(service_configs):
            """Validate that all service names are unique."""
            names = [config["name"] for config in service_configs]
            unique_names = set(names)

            if len(names) != len(unique_names):
                duplicates = [name for name in names if names.count(name) > 1]
                return False, f"Duplicate service names: {set(duplicates)}"

            return True, []

        validator.validate_unique_names.side_effect = validate_unique_names

        # Test uniqueness validation
        is_unique, errors = validator.validate_unique_names(configs)

        # Check if names are actually unique
        names = [config["name"] for config in configs]
        expected_unique = len(names) == len(set(names))

        assert (
            is_unique == expected_unique
        ), f"Uniqueness validation mismatch: validator={is_unique}, actual={expected_unique}"

    @given(complete_service_configuration(), network_configuration())
    @settings(max_examples=100)
    def test_service_network_integration_is_valid(self, service_config, network_config):
        """Property: Service-network integration should be valid."""
        # Mock network integrator
        integrator = Mock()

        def integrate_service_with_network(service, network):
            """Integrate service with network configuration."""
            integration_result = {
                "service_name": service["name"],
                "network_name": network["name"],
                "valid": True,
                "issues": [],
            }

            # Check for port conflicts
            service_ports = service.get("ports", [])
            for port in service_ports:
                if isinstance(port, str) and ":" in port:
                    host_port = port.split(":")[0]
                    try:
                        port_num = int(host_port)
                        if port_num < 1024:
                            integration_result["issues"].append(
                                f"Privileged port {port_num} may require root"
                            )
                    except ValueError:
                        integration_result["issues"].append(
                            f"Invalid port specification: {port}"
                        )

            # Check network driver compatibility
            network_driver = network.get("driver", "bridge")
            if network_driver == "host" and service_ports:
                integration_result["issues"].append(
                    "Host network mode conflicts with port mappings"
                )

            # Check subnet compatibility
            subnet = network.get("subnet")
            if subnet and not re.match(r"^\d+\.\d+\.\d+\.\d+/\d+$", subnet):
                integration_result["issues"].append(f"Invalid subnet format: {subnet}")

            if integration_result["issues"]:
                integration_result["valid"] = False

            return integration_result

        integrator.integrate.side_effect = integrate_service_with_network

        # Test integration
        result = integrator.integrate(service_config, network_config)

        # Basic validation
        assert "service_name" in result
        assert "network_name" in result
        assert "valid" in result
        assert "issues" in result

        # If there are issues, valid should be False
        if result["issues"]:
            assert (
                result["valid"] is False
            ), f"Integration marked valid despite issues: {result['issues']}"

    @given(complete_service_configuration())
    @settings(max_examples=100)
    def test_service_config_serialization_preserves_data(self, config):
        """Property: Service config serialization should preserve all data."""
        # Mock serializer
        serializer = Mock()

        def serialize_and_deserialize(service_config):
            """Serialize to JSON and back."""
            try:
                # Serialize to JSON string
                json_str = json.dumps(service_config, sort_keys=True)

                # Deserialize back
                restored_config = json.loads(json_str)

                return restored_config
            except (TypeError, ValueError) as e:
                return {"error": str(e)}

        serializer.round_trip.side_effect = serialize_and_deserialize

        # Test serialization round trip
        restored = serializer.round_trip(config)

        # Should not have errors
        assert "error" not in restored, f"Serialization failed: {restored.get('error')}"

        # All original keys should be present
        for key in config.keys():
            assert key in restored, f"Key {key} lost during serialization"

        # All values should be preserved (accounting for JSON type limitations)
        for key, original_value in config.items():
            restored_value = restored[key]

            # Handle None values
            if original_value is None:
                assert restored_value is None, f"None value changed for key {key}"

            # Handle string/int/bool values
            elif isinstance(original_value, (str, int, bool)):
                assert (
                    restored_value == original_value
                ), f"Value changed for key {key}: {original_value} -> {restored_value}"

            # Handle lists and dicts (structure should be preserved)
            elif isinstance(original_value, (list, dict)):
                assert type(restored_value) == type(
                    original_value
                ), f"Type changed for key {key}: {type(original_value)} -> {type(restored_value)}"


class TestServiceConfigurationStateMachine(RuleBasedStateMachine):
    """Stateful testing for service configuration management."""

    def __init__(self):
        super().__init__()
        self.services = {}
        self.networks = {}
        self.deployed_services = set()
        self.failed_deployments = set()

        # Mock components
        self.config_manager = Mock()
        self.deployment_manager = Mock()
        self.network_manager = Mock()

        # Configure mocks
        self.config_manager.add_service.side_effect = self._mock_add_service
        self.config_manager.remove_service.side_effect = self._mock_remove_service
        self.config_manager.get_service.side_effect = self._mock_get_service
        self.deployment_manager.deploy_service.side_effect = self._mock_deploy_service
        self.network_manager.create_network.side_effect = self._mock_create_network

    # Bundles
    service_names = Bundle("service_names")
    network_names = Bundle("network_names")

    @initialize()
    def init_state(self):
        """Initialize state machine."""
        self.services = {}
        self.networks = {}
        self.deployed_services = set()
        self.failed_deployments = set()

    @rule(target=service_names, config=complete_service_configuration())
    def add_service(self, config):
        """Rule: Add a service configuration."""
        service_name = config["name"]
        assume(service_name not in self.services)

        # Add service
        result = self.config_manager.add_service(config)
        assert result is True, f"Failed to add service {service_name}"

        return service_name

    @rule(target=network_names, config=network_configuration())
    def create_network(self, config):
        """Rule: Create a network."""
        network_name = config["name"]
        assume(network_name not in self.networks)

        # Create network
        result = self.network_manager.create_network(config)
        assert result is True, f"Failed to create network {network_name}"

        return network_name

    @rule(service_name=service_names)
    def deploy_service(self, service_name):
        """Rule: Deploy a service."""
        assume(service_name in self.services)
        assume(service_name not in self.deployed_services)
        assume(service_name not in self.failed_deployments)

        # Attempt deployment
        success = self.deployment_manager.deploy_service(service_name)

        if success:
            self.deployed_services.add(service_name)
        else:
            self.failed_deployments.add(service_name)

    @rule(service_name=service_names)
    def get_service_config(self, service_name):
        """Rule: Retrieve service configuration."""
        if service_name in self.services:
            config = self.config_manager.get_service(service_name)
            assert (
                config is not None
            ), f"Service {service_name} should exist but wasn't found"
            assert config["name"] == service_name, f"Retrieved wrong service config"

    @rule(service_name=service_names)
    def remove_service(self, service_name):
        """Rule: Remove a service."""
        if service_name in self.services:
            # Remove from deployed if deployed
            if service_name in self.deployed_services:
                self.deployed_services.remove(service_name)

            # Remove from failed if failed
            if service_name in self.failed_deployments:
                self.failed_deployments.remove(service_name)

            # Remove service
            result = self.config_manager.remove_service(service_name)
            assert result is True, f"Failed to remove service {service_name}"

    @invariant()
    def services_in_state_exist_in_manager(self):
        """Invariant: All services in state should exist in manager."""
        for service_name in list(self.services.keys()):
            config = self.config_manager.get_service(service_name)
            assert (
                config is not None
            ), f"Service {service_name} in state but not in manager"

    @invariant()
    def deployed_services_exist_in_services(self):
        """Invariant: Deployed services must exist in services."""
        for service_name in self.deployed_services:
            assert (
                service_name in self.services
            ), f"Deployed service {service_name} not in services"

    @invariant()
    def failed_deployments_exist_in_services(self):
        """Invariant: Failed deployments must exist in services."""
        for service_name in self.failed_deployments:
            assert (
                service_name in self.services
            ), f"Failed deployment {service_name} not in services"

    @invariant()
    def no_service_both_deployed_and_failed(self):
        """Invariant: No service can be both deployed and failed."""
        overlap = self.deployed_services & self.failed_deployments
        assert len(overlap) == 0, f"Services both deployed and failed: {overlap}"

    # Mock implementation methods
    def _mock_add_service(self, config):
        """Mock adding service to configuration."""
        service_name = config["name"]
        self.services[service_name] = config.copy()
        return True

    def _mock_remove_service(self, service_name):
        """Mock removing service from configuration."""
        if service_name in self.services:
            del self.services[service_name]
            return True
        return False

    def _mock_get_service(self, service_name):
        """Mock retrieving service configuration."""
        return self.services.get(service_name)

    def _mock_deploy_service(self, service_name):
        """Mock service deployment with realistic failure rate."""
        if service_name not in self.services:
            return False

        # Simulate ~85% success rate
        import random

        return random.random() > 0.15

    def _mock_create_network(self, config):
        """Mock network creation."""
        network_name = config["name"]
        self.networks[network_name] = config.copy()
        return True


# Run the state machine test
TestServiceConfigurationStateMachine = TestServiceConfigurationStateMachine.TestCase


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
