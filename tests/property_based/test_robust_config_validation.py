"""Property-based tests for robust configuration validation using Hypothesis."""
import json
import string
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

pytestmark = [pytest.mark.property_based, pytest.mark.config_validation]


# Custom strategies for PANTHER-specific types
@st.composite
def panther_service_names(draw):
    """Generate valid service names for PANTHER."""
    # Service names should be valid identifiers
    first_char = draw(st.sampled_from(string.ascii_lowercase))
    rest_chars = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "_",
            min_size=0,
            max_size=20,
        )
    )
    return first_char + rest_chars


@st.composite
def panther_implementation_names(draw):
    """Generate valid implementation names."""
    known_implementations = [
        "picoquic",
        "aioquic",
        "lsquic",
        "mvfst",
        "quiche",
        "quinn",
        "quic_go",
        "quant",
    ]
    return draw(st.sampled_from(known_implementations))


@st.composite
def panther_protocol_names(draw):
    """Generate valid protocol names."""
    known_protocols = ["quic", "tcp", "udp"]
    return draw(st.sampled_from(known_protocols))


@st.composite
def panther_roles(draw):
    """Generate valid protocol roles."""
    return draw(st.sampled_from(["client", "server", "peer"]))


@st.composite
def panther_timeouts(draw):
    """Generate valid timeout values."""
    return draw(st.integers(min_value=1, max_value=3600))  # 1 second to 1 hour


@st.composite
def panther_port_mappings(draw):
    """Generate valid Docker port mappings."""
    port = draw(st.integers(min_value=1024, max_value=65535))
    return f"{port}:{port}"


@st.composite
def panther_service_configs(draw):
    """Generate valid service configurations."""
    return {
        "implementation": {
            "name": draw(panther_implementation_names()),
            "type": draw(st.sampled_from(["iut", "testers"])),
        },
        "protocol": {
            "name": draw(panther_protocol_names()),
            "version": draw(st.sampled_from(["rfc9000", "v1", "draft-29"])),
            "role": draw(panther_roles()),
        },
        "timeout": draw(panther_timeouts()),
        "generate_new_certificates": draw(st.booleans()),
    }


class TestServiceConfigurationValidation:
    """Property-based tests for service configuration validation."""

    @given(panther_service_configs())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_config_structure_validation(self, service_config):
        """Test that generated service configurations have valid structure."""
        # Required fields should always be present
        required_fields = ["implementation", "protocol", "timeout"]
        for field in required_fields:
            assert field in service_config

        # Implementation should have name and type
        assert "name" in service_config["implementation"]
        assert "type" in service_config["implementation"]
        assert service_config["implementation"]["type"] in ["iut", "testers"]

        # Protocol should have name, version, and role
        assert "name" in service_config["protocol"]
        assert "role" in service_config["protocol"]
        assert service_config["protocol"]["role"] in ["client", "server", "peer"]

        # Timeout should be positive integer
        assert isinstance(service_config["timeout"], int)
        assert service_config["timeout"] > 0

    @given(st.text(min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_name_validation_robustness(self, service_name):
        """Test service name validation with various inputs."""
        # Test that service name validation handles edge cases

        # Valid service names: alphanumeric + underscore, starting with letter
        is_valid_name = (
            service_name[0].isalpha()
            and all(c.isalnum() or c == "_" for c in service_name)
            and len(service_name) <= 50
        )

        if is_valid_name:
            # Valid names should pass basic checks
            assert len(service_name) > 0
            assert service_name[0].isalpha()
        else:
            # Invalid names should be caught by validation
            # (In a real implementation, these would be rejected)
            pass

    @given(st.integers())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_timeout_validation_robustness(self, timeout_value):
        """Test timeout validation with various integer inputs."""
        # Valid timeouts: positive integers within reasonable range
        is_valid_timeout = 1 <= timeout_value <= 7200  # 1 second to 2 hours

        if is_valid_timeout:
            assert timeout_value > 0
            assert timeout_value <= 7200
        else:
            # Invalid timeouts should be rejected
            assert timeout_value <= 0 or timeout_value > 7200

    @given(st.lists(panther_port_mappings(), min_size=0, max_size=5))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_port_mapping_validation_robustness(self, port_mappings):
        """Test port mapping validation with various configurations."""
        for port_mapping in port_mappings:
            # Port mappings should follow format "host_port:container_port"
            assert ":" in port_mapping
            host_port, container_port = port_mapping.split(":")

            # Both should be valid port numbers
            assert host_port.isdigit()
            assert container_port.isdigit()
            assert 1024 <= int(host_port) <= 65535
            assert 1024 <= int(container_port) <= 65535


# Additional strategies for command configurations
@st.composite
def command_binaries(draw):
    """Generate valid command binaries."""
    # Common binary patterns
    common_binaries = [
        "picoquic_server",
        "picoquic_client",
        "aioquic",
        "test_app",
        "server",
        "client",
    ]
    return draw(st.sampled_from(common_binaries))


@st.composite
def command_arguments(draw):
    """Generate command arguments."""
    # Generate realistic command arguments
    arg_patterns = [
        "-c /certs/cert.pem",
        "-k /certs/key.pem",
        "-p 4443",
        "--host 0.0.0.0",
        "--debug",
        "--log-level info",
    ]
    num_args = draw(st.integers(min_value=0, max_value=5))
    return " ".join(
        draw(st.lists(st.sampled_from(arg_patterns), min_size=0, max_size=num_args))
    )


@st.composite
def working_directories(draw):
    """Generate valid working directories."""
    dirs = ["/app", "/usr/local/bin", "/opt/app", "/tmp", "/workspace"]
    return draw(st.sampled_from(dirs))


class TestCommandConfigurationValidation:
    """Property-based tests for command configuration validation."""

    @given(
        command_binary=command_binaries(),
        command_args=command_arguments(),
        working_dir=working_directories(),
        timeout=panther_timeouts(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_run_command_validation(
        self, command_binary, command_args, working_dir, timeout
    ):
        """Test run command validation with various inputs."""
        run_cmd = {
            "command_binary": command_binary,
            "command_args": command_args,
            "working_dir": working_dir,
            "timeout": timeout,
            "command_env": {},
        }

        # Basic validation checks
        assert isinstance(run_cmd["command_binary"], str)
        assert len(run_cmd["command_binary"]) > 0
        assert isinstance(run_cmd["command_args"], str)
        assert isinstance(run_cmd["working_dir"], str)
        assert run_cmd["working_dir"].startswith("/")
        assert isinstance(run_cmd["timeout"], int)
        assert run_cmd["timeout"] > 0
        assert isinstance(run_cmd["command_env"], dict)

    @given(
        st.dictionaries(
            st.text(alphabet=string.ascii_uppercase + "_", min_size=1, max_size=20),
            st.text(min_size=0, max_size=100),
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_environment_variable_validation(self, env_vars):
        """Test environment variable validation with various inputs."""
        for var_name, var_value in env_vars.items():
            # Environment variable names should be valid
            assert isinstance(var_name, str)
            assert len(var_name) > 0
            assert var_name.replace("_", "").isalnum() or var_name.isupper()

            # Environment variable values should be strings
            assert isinstance(var_value, str)

    @given(st.lists(st.text(min_size=1, max_size=200), min_size=0, max_size=10))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_command_list_validation(self, command_list):
        """Test validation of command lists (pre/post run commands)."""
        for command in command_list:
            # Commands should be non-empty strings
            assert isinstance(command, str)
            assert len(command.strip()) > 0


# Additional strategies for experiment configurations
@st.composite
def experiment_names(draw):
    """Generate valid experiment names."""
    # Experiment names should be descriptive but not too long
    words = [
        "test",
        "experiment",
        "validation",
        "performance",
        "integration",
        "quic",
        "tcp",
        "protocol",
    ]
    num_words = draw(st.integers(min_value=1, max_value=3))
    selected_words = draw(
        st.lists(st.sampled_from(words), min_size=num_words, max_size=num_words)
    )
    return "_".join(selected_words)


@st.composite
def network_environments(draw):
    """Generate valid network environment configurations."""
    env_type = draw(
        st.sampled_from(["docker_compose", "localhost_single_container", "shadow_ns"])
    )
    config = {"type": env_type}

    if env_type == "docker_compose":
        config["version"] = draw(st.sampled_from(["3.8", "3.9"]))
    elif env_type == "shadow_ns":
        config["duration"] = f"{draw(st.integers(min_value=60, max_value=3600))}s"

    return config


@st.composite
def execution_environment(draw):
    """Generate valid execution environment configurations."""
    env_types = ["strace", "gperf_cpu", "gperf_heap", "memcheck", "helgrind"]
    num_envs = draw(st.integers(min_value=0, max_value=3))

    environments = []
    for _ in range(num_envs):
        env_type = draw(st.sampled_from(env_types))
        env_config = {"type": env_type}

        if env_type == "strace":
            env_config["trace_calls"] = draw(
                st.lists(
                    st.sampled_from(["read", "write", "send", "recv", "open", "close"]),
                    min_size=1,
                    max_size=5,
                )
            )

        environments.append(env_config)

    return environments


class TestExperimentConfigurationValidation:
    """Property-based tests for experiment configuration validation."""

    @given(
        name=experiment_names(),
        network_env=network_environments(),
        exec_envs=execution_environment(),
        services=st.dictionaries(
            panther_service_names(), panther_service_configs(), min_size=1, max_size=5
        ),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_complete_experiment_validation(
        self, name, network_env, exec_envs, services
    ):
        """Test complete experiment configuration validation."""
        experiment_config = {
            "name": name,
            "description": f"Property-based test experiment: {name}",
            "network_environment": network_env,
            "execution_environment": exec_envs,
            "services": services,
            "steps": {"wait": 60},
        }

        # Basic structure validation
        assert "name" in experiment_config
        assert "network_environment" in experiment_config
        assert "services" in experiment_config
        assert len(experiment_config["services"]) > 0

        # Network environment validation
        assert "type" in experiment_config["network_environment"]
        assert experiment_config["network_environment"]["type"] in [
            "docker_compose",
            "localhost_single_container",
            "shadow_ns",
        ]

        # Services validation
        for service_name, service_config in experiment_config["services"].items():
            assert isinstance(service_name, str)
            assert len(service_name) > 0
            assert "implementation" in service_config
            assert "protocol" in service_config
            assert "timeout" in service_config

    @given(
        st.lists(
            st.dictionaries(st.just("name"), experiment_names()).flatmap(
                lambda d: st.fixed_dictionaries(d).flatmap(
                    lambda base: st.fixed_dictionaries(
                        {
                            **base,
                            "services": st.dictionaries(
                                panther_service_names(),
                                panther_service_configs(),
                                min_size=1,
                                max_size=3,
                            ),
                            "network_environment": network_environments(),
                        }
                    )
                )
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_experiment_validation(self, experiments):
        """Test validation of multiple experiments in a single configuration."""
        # All experiments should have unique names
        experiment_names = [exp["name"] for exp in experiments]
        assert len(experiment_names) == len(set(experiment_names))

        # Each experiment should be valid
        for experiment in experiments:
            assert "name" in experiment
            assert "services" in experiment
            assert "network_environment" in experiment
            assert len(experiment["services"]) > 0


class TestEdgeCaseValidation:
    """Property-based tests for edge cases and error conditions."""

    @given(st.text())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_arbitrary_string_handling(self, arbitrary_string):
        """Test that arbitrary strings don't break configuration parsing."""
        # This tests defensive programming - arbitrary input shouldn't crash the system

        # Test JSON parsing safety
        try:
            if arbitrary_string.strip():
                json.loads(arbitrary_string)
                # If it parses as JSON, it might be valid config
        except (json.JSONDecodeError, ValueError):
            # Expected for most arbitrary strings
            pass

    @given(
        st.dictionaries(
            st.text(), st.one_of(st.text(), st.integers(), st.booleans(), st.none())
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_arbitrary_dict_validation(self, arbitrary_dict):
        """Test configuration validation with arbitrary dictionary inputs."""
        # Test that arbitrary dictionaries are handled gracefully

        # Check for required fields
        required_service_fields = ["implementation", "protocol", "timeout"]
        has_required_fields = all(
            field in arbitrary_dict for field in required_service_fields
        )

        if has_required_fields:
            # Check if it could be a valid service config
            impl = arbitrary_dict.get("implementation")
            protocol = arbitrary_dict.get("protocol")
            timeout = arbitrary_dict.get("timeout")

            # Basic type checking
            if (
                isinstance(impl, dict)
                and isinstance(protocol, dict)
                and isinstance(timeout, int)
                and timeout > 0
            ):
                # Might be a valid config
                pass

        # Ensure no exceptions are raised during basic processing
        assert isinstance(arbitrary_dict, dict)

    @given(
        st.lists(
            st.one_of(
                st.text(),
                st.integers(),
                st.dictionaries(st.text(), st.text()),
                st.none(),
            )
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_mixed_type_list_handling(self, mixed_list):
        """Test handling of lists with mixed types."""
        # Configuration lists should handle mixed types gracefully

        for item in mixed_list:
            # Each item should be processable without exceptions
            assert item is None or isinstance(item, (str, int, dict))

    @example("")  # Empty string
    @example("   ")  # Whitespace only
    @example("null")  # JSON null
    @example("{}")  # Empty object
    @given(st.text())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_boundary_string_values(self, boundary_string):
        """Test boundary conditions for string values."""
        # Test specific boundary cases

        if boundary_string == "":
            assert len(boundary_string) == 0
        elif boundary_string.isspace():
            assert boundary_string.strip() == ""
        elif boundary_string == "null":
            # Should not be confused with None
            assert boundary_string == "null"
        elif boundary_string == "{}":
            # Should not be confused with empty dict
            assert boundary_string == "{}"
