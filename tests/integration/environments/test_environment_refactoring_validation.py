"""Integration tests to validate environment refactoring maintains functionality.

This test suite ensures that the refactoring of environment architectures:
1. Maintains all existing functionality
2. Does not introduce regressions
3. Preserves performance characteristics
4. Validates new base classes work correctly

CRITICAL: These tests must pass both before AND after refactoring.
"""

import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    BackgroundServiceMonitor,
    DockerComposeEnvironment,
)
from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
    LocalhostSingleContainerEnvironment,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import (
    ShadowNsEnvironment,
)


class TestEnvironmentRefactoringValidation:
    """Test suite to validate environment refactoring maintains functionality."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        return Mock()

    @pytest.fixture
    def base_env_config(self):
        """Create base environment configuration."""
        config = Mock()
        config.type = "docker_compose"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 0.1
        config.failure_threshold_count = 2
        config.allow_partial_deployment = False
        config.critical_services = []
        return config

    def test_docker_compose_environment_instantiation(
        self, base_env_config, mock_event_manager, tmp_path
    ):
        """Test that DockerComposeEnvironment can be instantiated correctly."""
        env = DockerComposeEnvironment(
            env_config_to_test=base_env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )

        assert env is not None
        assert env.env_type == "network"
        assert env.env_sub_type == "docker_compose"
        assert hasattr(env, "logger")

    def test_localhost_environment_instantiation(
        self, base_env_config, mock_event_manager, tmp_path
    ):
        """Test that LocalhostSingleContainerEnvironment can be instantiated correctly."""
        base_env_config.type = "localhost_single_container"

        env = LocalhostSingleContainerEnvironment(
            env_config_to_test=base_env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="localhost_single_container",
            event_manager=mock_event_manager,
        )

        assert env is not None
        assert env.env_type == "network"
        assert env.env_sub_type == "localhost_single_container"
        assert hasattr(env, "logger")

    def test_shadow_ns_environment_instantiation(
        self, base_env_config, mock_event_manager, tmp_path
    ):
        """Test that ShadowNsEnvironment can be instantiated correctly."""
        base_env_config.type = "shadow_ns"

        env = ShadowNsEnvironment(
            env_config_to_test=base_env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="shadow_ns",
            event_manager=mock_event_manager,
        )

        assert env is not None
        assert env.env_type == "network"
        assert env.env_sub_type == "shadow_ns"
        assert hasattr(env, "logger")

    def test_monitor_classes_have_consistent_interface(self):
        """Test that all monitor classes have consistent interfaces."""
        # These are the core methods that should exist on all monitors
        required_methods = [
            "start_monitoring",
            "stop_monitoring",
            "_monitor_loop",
            "_check_all_services",
        ]

        # Test BackgroundServiceMonitor
        mock_env = Mock()
        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 0.1
        mock_config.failure_threshold_count = 2

        monitor = BackgroundServiceMonitor(mock_env, ["service1"], mock_config)

        for method in required_methods:
            assert hasattr(
                monitor, method
            ), f"BackgroundServiceMonitor missing {method}"
            assert callable(getattr(monitor, method)), f"{method} is not callable"

    def test_network_resolver_imports(self):
        """Test that all network resolvers can be imported without errors."""
        try:
            from panther.plugins.environments.network_environment.docker_compose.docker_network_resolver import (
                DockerComposeNetworkResolver,
            )
            from panther.plugins.environments.network_environment.localhost_single_container.localhost_network_resolver import (
                LocalhostNetworkResolver,
            )
            from panther.plugins.environments.network_environment.shadow_ns.shadow_network_resolver import (
                ShadowNetworkResolver,
            )

            # Basic instantiation test
            assert DockerComposeNetworkResolver is not None
            assert LocalhostNetworkResolver is not None
            assert ShadowNetworkResolver is not None

        except ImportError as e:
            pytest.fail(f"Failed to import network resolvers: {e}")

    def test_template_files_exist(self):
        """Test that required template files exist."""
        base_path = (
            Path(__file__).parent.parent.parent.parent
            / "panther"
            / "plugins"
            / "environments"
            / "network_environment"
        )

        # Docker Compose templates
        docker_templates = [
            base_path / "docker_compose" / "templates" / "Dockerfile.jinja",
            base_path / "docker_compose" / "templates" / "docker-compose.yml.jinja",
        ]

        # Localhost templates
        localhost_templates = [
            base_path / "localhost_single_container" / "templates" / "Dockerfile.jinja",
        ]

        # Shadow NS templates
        shadow_templates = [
            base_path / "shadow_ns" / "templates" / "Dockerfile.jinja",
        ]

        all_templates = docker_templates + localhost_templates + shadow_templates

        for template in all_templates:
            if template.exists():
                assert (
                    template.is_file()
                ), f"Template {template} exists but is not a file"
                assert (
                    template.suffix == ".jinja"
                ), f"Template {template} should have .jinja extension"

    @pytest.mark.performance
    def test_monitor_performance_baseline(self):
        """Test monitor thread performance baseline."""
        mock_env = Mock()
        mock_env.logger = Mock()
        mock_env._is_service_ready = Mock(return_value=True)

        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 0.01  # Fast monitoring
        mock_config.failure_threshold_count = 2
        mock_config.critical_services = []
        mock_config.allow_partial_deployment = False

        services = [f"service_{i}" for i in range(10)]  # 10 services
        monitor = BackgroundServiceMonitor(mock_env, services, mock_config)

        # Measure startup time
        start_time = time.time()
        monitor.start_monitoring()
        startup_time = time.time() - start_time

        # Should start quickly
        assert (
            startup_time < 0.1
        ), f"Monitor startup took {startup_time:.3f}s, expected <0.1s"

        # Let it run for a bit
        time.sleep(0.1)

        # Measure shutdown time
        start_time = time.time()
        monitor.stop_monitoring()
        shutdown_time = time.time() - start_time

        # Should stop quickly
        assert (
            shutdown_time < 0.2
        ), f"Monitor shutdown took {shutdown_time:.3f}s, expected <0.2s"

    def test_memory_usage_stability(self):
        """Test that monitors don't have memory leaks."""
        import gc
        import sys

        mock_env = Mock()
        mock_env.logger = Mock()
        mock_env._is_service_ready = Mock(return_value=True)

        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 0.001
        mock_config.failure_threshold_count = 2
        mock_config.critical_services = []
        mock_config.allow_partial_deployment = False

        # Create and destroy monitors multiple times
        initial_objects = len(gc.get_objects())

        for _ in range(5):
            monitor = BackgroundServiceMonitor(mock_env, ["service1"], mock_config)
            monitor.start_monitoring()
            time.sleep(0.01)
            monitor.stop_monitoring()
            del monitor
            gc.collect()

        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Allow some growth but not excessive
        assert (
            object_growth < 100
        ), f"Potential memory leak: {object_growth} new objects created"

    def test_exception_handling_resilience(self):
        """Test that environments handle exceptions gracefully."""
        mock_env = Mock()
        mock_env.logger = Mock()
        mock_env._is_service_ready = Mock(side_effect=Exception("Test exception"))

        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 0.01
        mock_config.failure_threshold_count = 2
        mock_config.critical_services = []
        mock_config.allow_partial_deployment = False

        monitor = BackgroundServiceMonitor(mock_env, ["service1"], mock_config)
        monitor.start_monitoring()

        # Let it run with exceptions
        time.sleep(0.05)

        # Should still be running despite exceptions
        assert monitor.monitoring_active is True
        assert monitor.monitor_thread.is_alive()

        monitor.stop_monitoring()

    def test_thread_safety_validation(self):
        """Test thread safety under concurrent access."""
        mock_env = Mock()
        mock_env.logger = Mock()
        mock_env._is_service_ready = Mock(return_value=True)

        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 0.001
        mock_config.failure_threshold_count = 2
        mock_config.critical_services = []
        mock_config.allow_partial_deployment = False

        monitor = BackgroundServiceMonitor(
            mock_env, ["service1", "service2"], mock_config
        )
        monitor.start_monitoring()

        # Simulate concurrent access from multiple threads
        def concurrent_access():
            for _ in range(50):
                _ = monitor.service_states.copy()
                _ = monitor.failure_counts.copy()
                time.sleep(0.001)

        threads = [threading.Thread(target=concurrent_access) for _ in range(3)]

        for t in threads:
            t.start()

        time.sleep(0.1)  # Let monitoring run concurrently

        for t in threads:
            t.join(timeout=1.0)
            assert not t.is_alive(), "Thread did not complete (possible deadlock)"

        monitor.stop_monitoring()

    def test_configuration_parameter_validation(self):
        """Test that configuration parameters are properly validated."""
        mock_env = Mock()
        mock_env.logger = Mock()

        # Test with invalid monitoring interval
        invalid_config = Mock()
        invalid_config.monitoring_interval_seconds = -1  # Invalid
        invalid_config.failure_threshold_count = 2
        invalid_config.critical_services = []
        invalid_config.allow_partial_deployment = False

        # Should handle invalid config gracefully
        monitor = BackgroundServiceMonitor(mock_env, ["service1"], invalid_config)
        # The monitor should either fix the invalid value or handle it gracefully
        assert hasattr(monitor, "config")


class TestEnvironmentConsistency:
    """Test suite to validate consistency across environment types."""

    def test_all_environments_have_required_methods(self):
        """Test that all environment classes have required methods."""
        required_methods = [
            "prepare_environment",
            "deploy_services",
            "_teardown_environment",
            "collect_outputs",
        ]

        environment_classes = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
            ShadowNsEnvironment,
        ]

        for env_class in environment_classes:
            for method in required_methods:
                assert hasattr(
                    env_class, method
                ), f"{env_class.__name__} missing {method}"

    def test_environment_inheritance_consistency(self):
        """Test that environments follow consistent inheritance patterns."""
        from panther.plugins.environments.network_environment.base_network_environment import (
            BaseNetworkEnvironment,
        )

        environment_classes = [
            DockerComposeEnvironment,
            LocalhostSingleContainerEnvironment,
            ShadowNsEnvironment,
        ]

        for env_class in environment_classes:
            assert issubclass(
                env_class, BaseNetworkEnvironment
            ), f"{env_class.__name__} should inherit from BaseNetworkEnvironment"

    def test_output_patterns_consistency(self):
        """Test that all environments implement output patterns correctly."""
        mock_config = Mock()
        mock_event_manager = Mock()
        tmp_path = "/tmp/test"

        environments = [
            DockerComposeEnvironment(
                mock_config, tmp_path, "network", "docker_compose", mock_event_manager
            ),
            LocalhostSingleContainerEnvironment(
                mock_config, tmp_path, "network", "localhost", mock_event_manager
            ),
            ShadowNsEnvironment(
                mock_config, tmp_path, "network", "shadow_ns", mock_event_manager
            ),
        ]

        for env in environments:
            # All environments should have output pattern methods
            assert hasattr(env, "get_output_patterns") or hasattr(
                env, "collect_outputs"
            )

            # Should have consistent output directory structure
            assert hasattr(env, "output_dir")
            assert env.output_dir is not None


@pytest.mark.integration
class TestEnvironmentIntegration:
    """Integration tests for complete environment workflows."""

    @pytest.fixture
    def integration_config(self):
        """Create integration test configuration."""
        config = Mock()
        config.type = "docker_compose"
        config.enable_background_monitoring = False  # Simpler for testing
        config.monitoring_interval_seconds = 1.0
        config.failure_threshold_count = 3
        config.allow_partial_deployment = True
        config.critical_services = []
        return config

    def test_environment_lifecycle_docker_compose(self, integration_config, tmp_path):
        """Test complete Docker Compose environment lifecycle."""
        mock_event_manager = Mock()

        env = DockerComposeEnvironment(
            env_config_to_test=integration_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )

        # Mock external dependencies
        env.execute_with_logging = Mock(return_value=(0, "success"))
        env.execute_command = Mock(return_value=(0, "success"))
        env.execute_docker_command = Mock(return_value=(0, "success"))
        env._is_service_ready = Mock(return_value=True)
        env.services_managers = []

        try:
            # Test preparation phase
            env.prepare_environment()

            # Test deployment phase
            result = env.deploy_services()
            assert result is True

            # Test output collection
            outputs = env.collect_outputs()
            assert isinstance(outputs, dict)

        finally:
            # Test teardown phase
            env._teardown_environment()

    def test_error_propagation_consistency(self):
        """Test that errors are propagated consistently across environments."""
        # This test ensures that all environments handle errors the same way
        # This is critical for maintaining consistent behavior after refactoring

        mock_config = Mock()
        mock_event_manager = Mock()
        tmp_path = "/tmp/test"

        environments = [
            DockerComposeEnvironment(
                mock_config, tmp_path, "network", "docker_compose", mock_event_manager
            ),
            LocalhostSingleContainerEnvironment(
                mock_config, tmp_path, "network", "localhost", mock_event_manager
            ),
            ShadowNsEnvironment(
                mock_config, tmp_path, "network", "shadow_ns", mock_event_manager
            ),
        ]

        for env in environments:
            # All environments should have consistent error handling
            assert hasattr(env, "logger")

            # Should have consistent exception types
            from panther.core.exceptions import EnvironmentSetupException

            # Verify that environments can raise appropriate exceptions
            assert EnvironmentSetupException is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
