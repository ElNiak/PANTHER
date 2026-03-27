"""Integration tests for fast-fail behavior across PANTHER components.

Tests the interaction between:
- ExperimentManager with fast-fail
- DockerBuilder exception handling
- PluginManager error propagation
- Service lifecycle with fast-fail
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import docker
import pytest
from docker.errors import BuildError, DockerException

from panther.config.core.models.experiment import ExperimentConfig
from panther.config.core.models.global_config import FastFailConfig, GlobalConfig
from panther.core.docker_builder.docker_builder import DockerBuilder
from panther.core.exceptions.experiment_exceptions import (
    ConfigurationError,
    ExperimentInitializationError,
    TestCaseInitializationError,
)
from panther.core.exceptions.fast_fail import (
    DockerBuildException,
    ErrorSeverity,
    FastFailHandler,
    PantherException,
    PluginLoadException,
    ServiceStartException,
)
from panther.core.experiment_manager import ExperimentManager
from panther.plugins.plugin_manager import PluginManager

pytestmark = pytest.mark.integration


class TestExperimentManagerFastFail:
    """Test ExperimentManager with fast-fail integration."""

    @pytest.fixture
    def global_config(self):
        """Create a test global configuration."""
        config = GlobalConfig()
        config.fast_fail.enabled = True
        config.fast_fail.docker_build_failures = True
        config.fast_fail.plugin_load_failures = True
        return config

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        with patch("panther.core.experiment_manager.EventManager") as mock:
            instance = MagicMock()
            instance.cleanup_none_observers.return_value = 0
            mock.get_instance.return_value = instance
            yield instance

    @pytest.fixture
    def mock_observer_factory(self):
        """Create a mock observer factory."""
        with patch("panther.core.experiment_manager.get_observer_factory") as mock:
            factory = MagicMock()
            mock.return_value = factory
            yield factory

    def test_experiment_manager_initialization_with_fast_fail(
        self, global_config, mock_event_manager, mock_observer_factory, tmp_path
    ):
        """Test ExperimentManager initializes with fast-fail enabled."""
        # Set output dir to temp path
        global_config.paths.output_dir = str(tmp_path)

        with (
            patch("panther.core.experiment_manager.EmitterRegistry"),
            patch("panther.core.experiment_manager.WorkflowStateTracker"),
        ):
            manager = ExperimentManager(
                global_config=global_config,
                experiment_name="test_experiment",
                fast_fail_enabled=True,
            )

            assert manager.fast_fail_handler is not None
            assert manager.fast_fail_handler.enabled is True
            assert manager.plugin_manager.fast_fail_handler is manager.fast_fail_handler

    def test_experiment_manager_fast_fail_disabled(
        self, global_config, mock_event_manager, mock_observer_factory, tmp_path
    ):
        """Test ExperimentManager with fast-fail disabled."""
        global_config.paths.output_dir = str(tmp_path)
        global_config.fast_fail.enabled = False

        with (
            patch("panther.core.experiment_manager.EmitterRegistry"),
            patch("panther.core.experiment_manager.WorkflowStateTracker"),
        ):
            manager = ExperimentManager(
                global_config=global_config,
                experiment_name="test_experiment",
                fast_fail_enabled=True,  # Will be overridden by global config
            )

            assert manager.fast_fail_handler.enabled is False

    @patch("panther.core.experiment_manager.TestCase")
    def test_experiment_initialization_error_triggers_fast_fail(
        self,
        mock_test_case,
        global_config,
        mock_event_manager,
        mock_observer_factory,
        tmp_path,
    ):
        """Test that experiment initialization errors trigger fast-fail."""
        global_config.paths.output_dir = str(tmp_path)

        with (
            patch("panther.core.experiment_manager.EmitterRegistry"),
            patch("panther.core.experiment_manager.WorkflowStateTracker"),
        ):
            manager = ExperimentManager(
                global_config=global_config, experiment_name="test_experiment"
            )

            # Mock experiment config that will cause initialization error
            experiment_config = MagicMock()
            experiment_config.tests = [MagicMock()]
            manager.experiment_config = experiment_config

            # Make test case initialization fail
            mock_test_case.side_effect = ExperimentInitializationError(
                "Failed to initialize test case", experiment_name="test_experiment"
            )

            with pytest.raises(TestCaseInitializationError) as exc_info:
                manager._initialize_test_cases()

            assert exc_info.value.severity == ErrorSeverity.HIGH
            assert "Failed to initialize test cases" in str(exc_info.value)


class TestDockerBuilderFastFail:
    """Test DockerBuilder with fast-fail exception handling."""

    @pytest.fixture(autouse=True)
    def reset_docker_builder_singleton(self):
        """Reset DockerBuilder singleton before each test for isolation."""
        DockerBuilder.reset_singleton()
        yield
        DockerBuilder.reset_singleton()

    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        with patch("docker.from_env") as mock:
            client = MagicMock()
            mock.return_value = client
            client.ping.return_value = None
            yield client

    def test_docker_connection_failure_enters_cache_only_mode(self):
        """Test Docker connection failure results in None client (cache-only mode)."""
        with patch("docker.from_env") as mock_from_env:
            mock_from_env.side_effect = DockerException("Cannot connect to Docker")
            builder = DockerBuilder.get_instance()
            assert builder.client is None

    def test_docker_build_failure_raises_exception(self, mock_docker_client, tmp_path):
        """Test Docker build failure raises DockerBuildException."""
        builder = DockerBuilder.get_instance()

        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM ubuntu:latest")
        context_path = tmp_path

        build_error = BuildError("Build failed", build_log=[])
        mock_docker_client.images.build.side_effect = build_error

        with pytest.raises(DockerBuildException):
            builder.build_image(
                impl_name="test_impl",
                version="1.0",
                dockerfile_path=dockerfile_path,
                context_path=context_path,
                config={},
            )

    def test_docker_build_unexpected_error(self, mock_docker_client, tmp_path):
        """Test unexpected error during Docker build."""
        builder = DockerBuilder.get_instance()

        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM ubuntu:latest")
        context_path = tmp_path

        mock_docker_client.images.build.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(DockerBuildException):
            builder.build_image(
                impl_name="test_impl",
                version="1.0",
                dockerfile_path=dockerfile_path,
                context_path=context_path,
                config={},
            )

    def test_docker_client_none_raises_exception(self, mock_docker_client, tmp_path):
        """Test Docker operations with None client raises PantherException."""
        builder = DockerBuilder.get_instance()
        builder.client = None

        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM ubuntu:latest")

        with pytest.raises(PantherException) as exc_info:
            builder.build_image(
                impl_name="test_impl",
                version="1.0",
                dockerfile_path=dockerfile_path,
                context_path=tmp_path,
                config={},
            )

        assert "Docker" in str(exc_info.value)


class TestPluginManagerFastFail:
    """Test PluginManager with fast-fail behavior."""

    @pytest.fixture
    def plugin_manager(self):
        """Create a PluginManager instance for testing."""
        with patch("panther.plugins.plugin_manager.DockerBuilder"):
            manager = PluginManager(
                plugin_directories=["test_dir"], fast_fail_handler=Mock()
            )
            yield manager

    def test_service_creation_failure_propagates(self, plugin_manager):
        """Test service creation failure with PluginLoadException."""
        # Mock plugin_factory.create_service_manager to raise PluginLoadException
        plugin_manager.plugin_factory.create_service_manager = Mock(
            side_effect=PluginLoadException(
                message="Failed to load service plugin",
                plugin_name="test_service",
                plugin_type="service",
                severity=ErrorSeverity.HIGH,
            )
        )

        with pytest.raises(PluginLoadException) as exc_info:
            plugin_manager.create_service_manager(
                protocol=Mock(),
                implementation=Mock(),
                implementation_dir=Path("."),
                service_config_to_test=Mock(),
            )

        assert exc_info.value.severity == ErrorSeverity.HIGH
        assert exc_info.value.context["plugin_name"] == "test_service"

    def test_environment_creation_with_fast_fail(self, plugin_manager):
        """Test environment plugin creation with fast-fail."""
        # Mock successful environment creation via plugin_factory
        mock_env = Mock()
        plugin_manager.plugin_factory.create_environment_manager = Mock(
            return_value=mock_env
        )

        result = plugin_manager.create_environment_manager(
            environment="docker_compose",
            test_config=Mock(),
            environment_dir=Path("."),
            output_dir=Path("."),
            event_manager=Mock(),
        )

        assert result == mock_env

        # Now test failure case
        plugin_manager.plugin_factory.create_environment_manager = Mock(
            side_effect=PluginLoadException(
                message="Environment plugin not found",
                plugin_name="unknown_env",
                plugin_type="network_environment",
            )
        )

        with pytest.raises(PluginLoadException):
            plugin_manager.create_environment_manager(
                environment="unknown_env",
                test_config=Mock(),
                environment_dir=Path("."),
                output_dir=Path("."),
                event_manager=Mock(),
            )


class TestFastFailEndToEnd:
    """End-to-end tests for fast-fail scenarios."""

    @pytest.fixture
    def mock_environment(self):
        """Create a complete mock environment."""
        with (
            patch("docker.from_env") as docker_mock,
            patch("panther.core.experiment_manager.EventManager") as event_mock,
            patch(
                "panther.core.experiment_manager.get_observer_factory"
            ) as observer_mock,
            patch("panther.core.experiment_manager.EmitterRegistry"),
            patch("panther.core.experiment_manager.WorkflowStateTracker"),
        ):
            # Setup Docker mock
            docker_client = MagicMock()
            docker_mock.return_value = docker_client
            docker_client.ping.return_value = None

            # Setup event manager
            event_instance = MagicMock()
            event_instance.cleanup_none_observers.return_value = 0
            event_mock.get_instance.return_value = event_instance

            # Setup observer factory
            factory = MagicMock()
            observer_mock.return_value = factory

            yield {
                "docker_client": docker_client,
                "event_manager": event_instance,
                "observer_factory": factory,
            }

    def test_docker_build_failure_stops_experiment(self, mock_environment, tmp_path):
        """Test that Docker build failure stops the entire experiment via fast-fail handler."""
        global_config = GlobalConfig()
        global_config.paths.output_dir = str(tmp_path)
        global_config.fast_fail.enabled = True
        global_config.fast_fail.docker_build_failures = True

        manager = ExperimentManager(
            global_config=global_config, experiment_name="test_experiment"
        )

        docker_error = DockerBuildException(
            message="Build failed",
            image_name="test_service",
            dockerfile="Dockerfile",
        )

        with pytest.raises(DockerBuildException):
            manager.fast_fail_handler.handle_error(docker_error, raise_on_critical=True)

        assert manager.fast_fail_handler.critical_error is not None
        assert isinstance(
            manager.fast_fail_handler.critical_error, DockerBuildException
        )

        with pytest.raises(DockerBuildException):
            manager.fast_fail_handler.check_critical()

    def test_plugin_load_failure_cascade(self, mock_environment, tmp_path):
        """Test cascading plugin load failures."""
        global_config = GlobalConfig()
        global_config.paths.output_dir = str(tmp_path)
        global_config.fast_fail.enabled = True
        global_config.fast_fail.plugin_load_failures = True

        manager = ExperimentManager(
            global_config=global_config, experiment_name="test_experiment"
        )

        # Simulate multiple plugin failures
        errors = []

        # First plugin fails with HIGH severity
        error1 = PluginLoadException(
            message="Core plugin failed",
            plugin_name="core_plugin",
            plugin_type="service",
            severity=ErrorSeverity.HIGH,
        )

        should_continue = manager.fast_fail_handler.handle_error(
            error1, raise_on_critical=False
        )
        errors.append(error1)
        assert should_continue is False  # HIGH severity stops execution

        # Optional plugin fails with MEDIUM severity
        error2 = PluginLoadException(
            message="Optional plugin failed",
            plugin_name="optional_plugin",
            plugin_type="tester",
            severity=ErrorSeverity.MEDIUM,
        )

        should_continue = manager.fast_fail_handler.handle_error(
            error2, raise_on_critical=False
        )
        errors.append(error2)
        assert should_continue is True  # MEDIUM severity continues

        # Verify error count
        assert manager.fast_fail_handler.error_count == 2

        # Critical plugin fails
        error3 = PluginLoadException(
            message="Critical plugin failed",
            plugin_name="critical_plugin",
            plugin_type="network_environment",
            severity=ErrorSeverity.CRITICAL,
        )

        with pytest.raises(PluginLoadException):
            manager.fast_fail_handler.handle_error(error3, raise_on_critical=True)

        assert manager.fast_fail_handler.critical_error == error3

    def test_configuration_based_fast_fail_behavior(self, mock_environment, tmp_path):
        """Test different fast-fail configurations."""
        base_config = GlobalConfig()
        base_config.paths.output_dir = str(tmp_path)

        # Test 1: Fast-fail completely disabled
        config1 = base_config
        config1.fast_fail.enabled = False

        manager1 = ExperimentManager(global_config=config1, experiment_name="test1")

        # Even critical errors should not stop execution
        error = DockerBuildException(
            message="Build failed", image_name="test", dockerfile="Dockerfile"
        )

        result = manager1.fast_fail_handler.handle_error(error, raise_on_critical=True)
        assert result is True  # Continues when disabled

        # Test 2: Fast-fail enabled — HIGH severity stops execution
        config2 = GlobalConfig()
        config2.paths.output_dir = str(tmp_path)
        config2.fast_fail.enabled = True

        manager2 = ExperimentManager(global_config=config2, experiment_name="test2")

        high_error = PluginLoadException(
            message="Plugin failed",
            plugin_name="test",
            plugin_type="service",
            severity=ErrorSeverity.HIGH,
        )

        result = manager2.fast_fail_handler.handle_error(
            high_error, raise_on_critical=False
        )
        assert result is False  # HIGH severity stops when enabled
        assert manager2.fast_fail_handler.error_count == 1


class TestServiceLifecycleFastFail:
    """Test service lifecycle with fast-fail."""

    def test_service_start_exception_handling(self):
        """Test ServiceStartException in service lifecycle."""
        handler = FastFailHandler(enabled=True)

        # Simulate service startup failure
        error = ServiceStartException(
            message="Service failed to start", service_name="test_service"
        )

        result = handler.handle_error(error, raise_on_critical=False)

        assert result is False  # HIGH severity should not continue
        assert handler.error_count == 1

    def test_multiple_service_failures(self):
        """Test handling multiple service failures."""
        handler = FastFailHandler(enabled=True)

        services = ["service1", "service2", "service3"]
        failed_services = []

        for service in services:
            try:
                # Simulate service start attempt
                if service in ["service1", "service2"]:
                    error = ServiceStartException(
                        message=f"{service} failed to start", service_name=service
                    )

                    should_continue = handler.handle_error(
                        error, raise_on_critical=False
                    )

                    if not should_continue:
                        failed_services.append(service)
                        # In real scenario, would skip remaining services
                        break
            except Exception:
                failed_services.append(service)

        assert len(failed_services) == 1  # Stopped after first HIGH severity error
        assert handler.error_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
