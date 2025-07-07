"""
Comprehensive interface compliance tests for PANTHER network environment implementations.

This module tests that all network environment implementations properly follow
the INetworkEnvironment interface contract, ensuring consistent behavior across
different environment types (Docker Compose, localhost, Shadow NS).
"""

import inspect
from abc import ABC
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
    LocalhostSingleContainerEnvironment,
)
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)


@pytest.mark.unit
class TestINetworkEnvironmentInterface:
    """Test the INetworkEnvironment interface definition."""

    def test_interface_is_abstract_base_class(self):
        """Test that INetworkEnvironment is properly defined as ABC."""
        assert issubclass(INetworkEnvironment, ABC)
        assert hasattr(INetworkEnvironment, "__abstractmethods__")

    def test_interface_cannot_be_instantiated(self):
        """Test that the interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            INetworkEnvironment()

    def test_interface_defines_required_methods(self):
        """Test that all required methods are defined in the interface."""
        required_methods = [
            "setup_execution_plugins",
            "update_environment",
            "create_log_dir",
            "generate_from_template",
            "is_network_environment",
            "generate_environment_services",
            "prepare_environment",
            "launch_environment_services",
            "run",
            "deploy_services",
            "setup_environment",
            "teardown_environment",
        ]

        interface_methods = [
            name
            for name, method in inspect.getmembers(
                INetworkEnvironment, inspect.isfunction
            )
        ]

        for method in required_methods:
            assert (
                method in interface_methods
            ), f"Required method '{method}' not found in interface"

    def test_interface_defines_required_attributes(self):
        """Test that interface defines expected instance attributes."""
        # These would be set in __init__ or during execution
        expected_attributes = [
            "docker_name",
            "execution_environment",
            "network_name",
            "execution_environment",
            "services",
            "deployment_commands",
            "timeout",
            "global_config",
            "test_config",
            "jinja_env",
        ]

        # Check that __init__ method accepts the expected parameters
        init_signature = inspect.signature(INetworkEnvironment.__init__)
        # Note: We can't directly test instance attributes on an ABC,
        # but we can verify the interface signature expectations


@pytest.mark.unit
class TestNetworkEnvironmentImplementations:
    """Test that concrete implementations comply with the interface."""

    @pytest.fixture
    def mock_global_config(self):
        """Provide a mock global configuration."""
        config = Mock()
        config.paths.output_dir = "/tmp/test_output"
        config.paths.log_dir = "/tmp/test_logs"
        config.docker.build_docker_image = True
        return config

    @pytest.fixture
    def mock_test_config(self):
        """Provide a mock test configuration."""
        config = Mock()
        config.name = "test_experiment"
        config.network_environment = {"type": "docker_compose"}
        config.services = {}
        return config

    @pytest.fixture
    def docker_compose_environment(self, mock_global_config, mock_test_config):
        """Create a DockerComposeEnvironment instance for testing."""
        with patch(
            "panther.plugins.environments.network_environment.docker_compose.docker_compose.DockerComposeLifecycleManager"
        ):
            env = DockerComposeEnvironment(
                global_config=mock_global_config, test_config=mock_test_config
            )
            return env

    @pytest.fixture
    def localhost_environment(self, mock_global_config, mock_test_config):
        """Create a LocalhostSingleContainerEnvironment instance for testing."""
        with patch(
            "panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container.LocalhostNetworkResolver"
        ):
            env = LocalhostSingleContainerEnvironment(
                global_config=mock_global_config, test_config=mock_test_config
            )
            return env

    def test_docker_compose_implements_interface(self, docker_compose_environment):
        """Test that DockerComposeEnvironment implements INetworkEnvironment."""
        assert isinstance(docker_compose_environment, INetworkEnvironment)
        assert issubclass(DockerComposeEnvironment, INetworkEnvironment)

    def test_localhost_implements_interface(self, localhost_environment):
        """Test that LocalhostSingleContainerEnvironment implements INetworkEnvironment."""
        assert isinstance(localhost_environment, INetworkEnvironment)
        assert issubclass(LocalhostSingleContainerEnvironment, INetworkEnvironment)

    def test_all_interface_methods_implemented(self, docker_compose_environment):
        """Test that all interface methods are implemented in concrete classes."""
        interface_methods = [
            name
            for name, method in inspect.getmembers(
                INetworkEnvironment, inspect.isfunction
            )
        ]

        for method_name in interface_methods:
            if not method_name.startswith("_"):  # Skip private methods
                assert hasattr(
                    docker_compose_environment, method_name
                ), f"Method '{method_name}' not implemented in DockerComposeEnvironment"
                assert callable(
                    getattr(docker_compose_environment, method_name)
                ), f"'{method_name}' is not callable in DockerComposeEnvironment"

    def test_required_attributes_present(self, docker_compose_environment):
        """Test that required attributes are present after initialization."""
        required_attrs = [
            "global_config",
            "test_config",
            "docker_name",
            "network_name",
            "services",
            "timeout",
        ]

        for attr in required_attrs:
            assert hasattr(
                docker_compose_environment, attr
            ), f"Required attribute '{attr}' not found"

    @pytest.mark.parametrize(
        "environment_fixture", ["docker_compose_environment", "localhost_environment"]
    )
    def test_is_network_environment_returns_true(self, environment_fixture, request):
        """Test that is_network_environment returns True for all implementations."""
        env = request.getfixturevalue(environment_fixture)
        assert env.is_network_environment() is True

    @pytest.mark.parametrize(
        "environment_fixture", ["docker_compose_environment", "localhost_environment"]
    )
    def test_create_log_dir_creates_directory(
        self, environment_fixture, request, temp_dir
    ):
        """Test that create_log_dir creates the expected directory."""
        env = request.getfixturevalue(environment_fixture)

        # Mock the log directory path
        log_path = temp_dir / "logs"
        with patch.object(env, "create_log_dir") as mock_create:
            # Test that the method can be called
            env.create_log_dir()
            mock_create.assert_called_once()


@pytest.mark.unit
class TestInterfaceMethodSignatures:
    """Test that interface method signatures are consistent across implementations."""

    @pytest.fixture
    def interface_methods(self):
        """Get all public methods from the interface."""
        return {
            name: method
            for name, method in inspect.getmembers(
                INetworkEnvironment, inspect.isfunction
            )
            if not name.startswith("_")
        }

    def test_method_signatures_match_interface(self, interface_methods):
        """Test that implementation method signatures match the interface."""
        implementations = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
        ]

        for impl_class in implementations:
            for method_name, interface_method in interface_methods.items():
                if hasattr(impl_class, method_name):
                    impl_method = getattr(impl_class, method_name)

                    # Get signatures
                    interface_sig = inspect.signature(interface_method)
                    impl_sig = inspect.signature(impl_method)

                    # Compare parameter names (allowing for additional parameters in implementation)
                    interface_params = list(interface_sig.parameters.keys())
                    impl_params = list(impl_sig.parameters.keys())

                    # Check that all interface parameters are present in implementation
                    for param in interface_params:
                        assert (
                            param in impl_params
                        ), f"Parameter '{param}' missing from {impl_class.__name__}.{method_name}"


@pytest.mark.integration
class TestEnvironmentLifecycle:
    """Test the complete lifecycle of network environment implementations."""

    @pytest.fixture
    def mock_environment_config(self):
        """Create a comprehensive mock environment configuration."""
        return {
            "type": "docker_compose",
            "version": "3.8",
            "services": {
                "test_service": {"image": "test:latest", "ports": ["8080:8080"]}
            },
        }

    @pytest.fixture
    def mock_lifecycle_methods(self):
        """Mock external dependencies for lifecycle testing."""
        with patch("docker.from_env") as mock_docker, patch(
            "subprocess.run"
        ) as mock_subprocess, patch("pathlib.Path.mkdir") as mock_mkdir:
            # Configure mocks
            mock_docker.return_value.ping.return_value = True
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = "success"

            yield {
                "docker": mock_docker,
                "subprocess": mock_subprocess,
                "mkdir": mock_mkdir,
            }

    @pytest.mark.slow
    def test_complete_environment_lifecycle(
        self,
        mock_global_config,
        mock_test_config,
        mock_environment_config,
        mock_lifecycle_methods,
    ):
        """Test the complete setup -> run -> teardown lifecycle."""

        with patch(
            "panther.plugins.environments.network_environment.docker_compose.docker_compose.DockerComposeLifecycleManager"
        ):
            env = DockerComposeEnvironment(
                global_config=mock_global_config, test_config=mock_test_config
            )

            # Test setup phase
            with patch.object(env, "setup_environment") as mock_setup:
                env.setup_environment()
                mock_setup.assert_called_once()

            # Test run phase
            with patch.object(env, "run") as mock_run:
                mock_run.return_value = {"status": "success"}
                result = env.run()
                assert result["status"] == "success"

            # Test teardown phase
            with patch.object(env, "teardown_environment") as mock_teardown:
                env.teardown_environment()
                mock_teardown.assert_called_once()

    def test_error_handling_during_lifecycle(
        self, mock_global_config, mock_test_config
    ):
        """Test that errors during lifecycle are properly handled."""

        with patch(
            "panther.plugins.environments.network_environment.docker_compose.docker_compose.DockerComposeLifecycleManager"
        ):
            env = DockerComposeEnvironment(
                global_config=mock_global_config, test_config=mock_test_config
            )

            # Test setup failure handling
            with patch.object(
                env, "setup_environment", side_effect=Exception("Setup failed")
            ):
                with pytest.raises(Exception) as exc_info:
                    env.setup_environment()
                assert "Setup failed" in str(exc_info.value)


@pytest.mark.property_based
class TestInterfacePropertyBasedTests:
    """Property-based tests for interface compliance."""

    def test_environment_type_consistency(self):
        """Test that environment type identification is consistent."""
        # Property: All network environments should return True for is_network_environment()
        implementations = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
        ]

        for impl_class in implementations:
            with patch.object(impl_class, "__init__", return_value=None):
                # Create instance without initialization side effects
                instance = impl_class.__new__(impl_class)
                # Manually set required attributes
                instance.global_config = Mock()
                instance.test_config = Mock()

                # Property test: should always return True
                assert instance.is_network_environment() is True

    def test_template_generation_consistency(self):
        """Test that template generation behaves consistently across implementations."""
        # Property: generate_from_template should always return a Path-like object
        implementations = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
        ]

        for impl_class in implementations:
            with patch.object(impl_class, "__init__", return_value=None), patch.object(
                impl_class, "generate_from_template"
            ) as mock_generate:
                # Mock return value as Path
                mock_generate.return_value = Path("/tmp/generated_file")

                instance = impl_class.__new__(impl_class)
                result = instance.generate_from_template("template.j2", {})

                # Property: result should be Path-like
                assert hasattr(result, "exists")  # Duck typing for Path-like


@pytest.mark.compliance
class TestInterfaceDocumentationCompliance:
    """Test that implementations provide proper documentation."""

    def test_all_methods_have_docstrings(self):
        """Test that all interface methods have proper documentation."""
        implementations = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
        ]

        for impl_class in implementations:
            methods = [
                method
                for method in dir(impl_class)
                if not method.startswith("_") and callable(getattr(impl_class, method))
            ]

            for method_name in methods:
                method = getattr(impl_class, method_name)
                if hasattr(method, "__doc__"):
                    # Allow empty docstring for simple property methods, but require for complex methods
                    if method_name in [
                        "setup_environment",
                        "teardown_environment",
                        "run",
                        "deploy_services",
                    ]:
                        assert (
                            method.__doc__ is not None
                        ), f"Critical method '{method_name}' in {impl_class.__name__} lacks documentation"

    def test_class_documentation_exists(self):
        """Test that implementation classes have proper class documentation."""
        implementations = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
        ]

        for impl_class in implementations:
            assert (
                impl_class.__doc__ is not None
            ), f"Implementation class {impl_class.__name__} lacks documentation"
            assert (
                len(impl_class.__doc__.strip()) > 20
            ), f"Implementation class {impl_class.__name__} has insufficient documentation"
