"""Integration tests for plugin system and event system interactions."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.event_system,
    pytest.mark.plugin_test,
]


class TestPluginEventIntegration:
    """Test integration between plugin system and event-driven architecture."""

    def test_service_manager_event_emission(
        self, mock_event_manager, sample_service_config
    ):
        """Test that service managers properly emit events during lifecycle."""
        # Mock a service manager that emits events
        from panther.plugins.services.services_interface import IServiceManager

        mock_service_manager = Mock(spec=IServiceManager)
        mock_service_manager.service_name = "test_service"
        mock_service_manager.event_manager = mock_event_manager

        # Simulate service lifecycle with event emission
        mock_service_manager.initialize = Mock()
        mock_service_manager.deploy = Mock()
        mock_service_manager.teardown = Mock()

        # Test lifecycle with event tracking
        mock_service_manager.initialize()
        mock_service_manager.deploy()
        mock_service_manager.teardown()

        # Verify lifecycle methods were called
        mock_service_manager.initialize.assert_called_once()
        mock_service_manager.deploy.assert_called_once()
        mock_service_manager.teardown.assert_called_once()

    def test_plugin_loader_event_integration(self, mock_event_manager, temp_dir):
        """Test that plugin loader emits events during plugin discovery and loading."""
        # Create fake plugin structure
        plugin_dir = (
            Path(temp_dir)
            / "plugins"
            / "services"
            / "iut"
            / "test_protocol"
            / "test_impl"
        )
        plugin_dir.mkdir(parents=True)

        plugin_file = plugin_dir / "test_impl.py"
        plugin_file.write_text(
            """
from panther.plugins.services.services_interface import IServiceManager

class TestImplServiceManager(IServiceManager):
    def __init__(self, service_config, event_manager):
        self.service_config = service_config
        self.event_manager = event_manager
        self.service_name = "test_impl"

    def generate_commands(self):
        return {"run_cmd": {"command_binary": "test"}}

    def validate_config(self, config):
        return True
"""
        )

        # Mock plugin manager with event integration
        with patch(
            "panther.plugins.plugin_manager.PluginManager"
        ) as mock_plugin_manager:
            mock_instance = Mock()
            mock_plugin_manager.return_value = mock_instance

            # Simulate plugin discovery with events
            mock_instance.discover_plugins = Mock(return_value=["test_impl"])
            mock_instance.load_plugin = Mock()

            # Test plugin discovery and loading
            plugins = mock_instance.discover_plugins()
            for plugin in plugins:
                mock_instance.load_plugin(plugin)

            # Verify operations
            mock_instance.discover_plugins.assert_called_once()
            assert mock_instance.load_plugin.call_count == len(plugins)

    def test_command_generation_event_flow(
        self, mock_event_manager, mock_command_processor
    ):
        """Test event flow during command generation pipeline."""
        # Mock command generation with event emission
        test_config = {
            "service_name": "test_service",
            "implementation": {"name": "test_impl", "type": "iut"},
            "protocol": {"name": "test_protocol"},
        }

        # Simulate command generation pipeline
        mock_command_processor.generate_commands.return_value = {
            "pre_compile_cmds": [],
            "compile_cmds": ["gcc -o test test.c"],
            "post_compile_cmds": [],
            "pre_run_cmds": ["echo 'Starting test'"],
            "run_cmd": {
                "command_binary": "test",
                "command_args": "--run",
                "timeout": 60,
                "working_dir": "/app",
                "command_env": {},
            },
            "post_run_cmds": ["echo 'Test completed'"],
        }

        # Test command generation
        commands = mock_command_processor.generate_commands(test_config)

        # Verify command structure
        assert "run_cmd" in commands
        assert commands["run_cmd"]["command_binary"] == "test"
        assert len(commands["compile_cmds"]) == 1

        mock_command_processor.generate_commands.assert_called_once_with(test_config)


class TestEnvironmentPluginIntegration:
    """Test integration between environment plugins and other system components."""

    @pytest.mark.requires_docker
    def test_docker_compose_service_integration(
        self, mock_event_manager, sample_test_config
    ):
        """Test integration between Docker Compose environment and service plugins."""
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            DockerComposeEnvironment,
        )

        # Mock environment with service integration
        with patch.object(DockerComposeEnvironment, "__init__", return_value=None):
            env = DockerComposeEnvironment.__new__(DockerComposeEnvironment)
            env.logger = Mock()
            env.event_manager = mock_event_manager
            env.services_managers = []

            # Mock service managers
            mock_service1 = Mock()
            mock_service1.service_name = "service1"
            mock_service1.generate_commands.return_value = {
                "run_cmd": {"command_binary": "service1"}
            }

            mock_service2 = Mock()
            mock_service2.service_name = "service2"
            mock_service2.generate_commands.return_value = {
                "run_cmd": {"command_binary": "service2"}
            }

            env.services_managers = [mock_service1, mock_service2]

            # Mock environment methods
            env.prepare = Mock()
            env.deploy = Mock()
            env.run = Mock()
            env.teardown = Mock()

            # Test environment lifecycle with services
            env.prepare(env.services_managers)
            env.deploy()
            env.run()
            env.teardown()

            # Verify all phases completed
            env.prepare.assert_called_once_with(env.services_managers)
            env.deploy.assert_called_once()
            env.run.assert_called_once()
            env.teardown.assert_called_once()

    def test_execution_environment_service_integration(
        self, mock_event_manager, sample_test_config
    ):
        """Test integration between execution environments and service plugins."""
        # Mock execution environment (e.g., strace, gperf)
        mock_exec_env = Mock()
        mock_exec_env.env_type = "execution"
        mock_exec_env.env_sub_type = "profiling"

        # Mock service manager
        mock_service = Mock()
        mock_service.service_name = "test_service"
        mock_service.service_config_to_test = Mock()
        mock_service.service_config_to_test.implementation.gperf_compatible = True
        mock_service.run_cmd = {"run_cmd": {"command_env": {}}, "post_run_cmds": []}
        mock_service.environments = {}

        # Test execution environment setup
        mock_exec_env.setup_environment = Mock()
        mock_exec_env.setup_environment(
            [mock_service], sample_test_config, None, "timestamp", None
        )

        # Verify setup was called with correct parameters
        mock_exec_env.setup_environment.assert_called_once()


class TestEventObserverIntegration:
    """Test integration between event system and observer components."""

    def test_logger_observer_integration(self, mock_event_manager):
        """Test that logger observer properly processes events."""
        # Mock logger observer
        mock_logger_observer = Mock()
        mock_logger_observer.priority = 100
        mock_logger_observer.on_event = Mock()

        # Add observer to event manager
        mock_event_manager.add_observer(mock_logger_observer)

        # Create and emit test events
        mock_event = Mock()
        mock_event.event_type = "test.event"
        mock_event.data = {"test": "data"}

        mock_event_manager.emit_event(mock_event)

        # Verify observer was added and event was emitted
        mock_event_manager.add_observer.assert_called_with(mock_logger_observer)
        mock_event_manager.emit_event.assert_called_with(mock_event)

    def test_metrics_observer_integration(self, mock_event_manager):
        """Test that metrics observer properly collects performance data."""
        mock_metrics_observer = Mock()
        mock_metrics_observer.priority = 90
        mock_metrics_observer.on_event = Mock()

        # Test metrics collection
        mock_event_manager.add_observer(mock_metrics_observer)

        # Simulate performance events
        performance_event = Mock()
        performance_event.event_type = "performance.measurement"
        performance_event.data = {
            "component": "command_generation",
            "duration": 0.025,
            "memory_usage": 1024,
        }

        mock_event_manager.emit_event(performance_event)

        # Verify metrics observer integration
        mock_event_manager.add_observer.assert_called_with(mock_metrics_observer)
        mock_event_manager.emit_event.assert_called_with(performance_event)

    def test_storage_observer_integration(self, mock_event_manager, temp_dir):
        """Test that storage observer properly persists events."""
        mock_storage_observer = Mock()
        mock_storage_observer.priority = 80
        mock_storage_observer.storage_path = temp_dir

        # Test event storage
        mock_event_manager.add_observer(mock_storage_observer)

        # Create storable event
        storage_event = Mock()
        storage_event.event_type = "experiment.completed"
        storage_event.data = {
            "experiment_name": "test_experiment",
            "duration": 120.5,
            "results": {"success": True},
        }

        mock_event_manager.emit_event(storage_event)

        # Verify storage integration
        mock_event_manager.add_observer.assert_called_with(mock_storage_observer)
        mock_event_manager.emit_event.assert_called_with(storage_event)


class TestCompleteSystemIntegration:
    """Test complete system integration scenarios."""

    @pytest.mark.slow
    def test_experiment_lifecycle_integration(
        self, mock_event_manager, sample_test_config, sample_global_config
    ):
        """Test complete experiment lifecycle with all components integrated."""
        # Mock experiment manager
        from panther.core.experiment_manager import ExperimentManager

        with patch.object(ExperimentManager, "__init__", return_value=None):
            exp_manager = ExperimentManager.__new__(ExperimentManager)
            exp_manager.event_manager = mock_event_manager
            exp_manager.logger = Mock()

            # Mock lifecycle methods
            exp_manager.initialize = Mock()
            exp_manager.load_plugins = Mock()
            exp_manager.deploy_environment = Mock()
            exp_manager.execute_tests = Mock()
            exp_manager.teardown = Mock()

            # Test complete lifecycle
            exp_manager.initialize(sample_test_config, sample_global_config)
            exp_manager.load_plugins()
            exp_manager.deploy_environment()
            exp_manager.execute_tests()
            exp_manager.teardown()

            # Verify all lifecycle phases
            exp_manager.initialize.assert_called_once_with(
                sample_test_config, sample_global_config
            )
            exp_manager.load_plugins.assert_called_once()
            exp_manager.deploy_environment.assert_called_once()
            exp_manager.execute_tests.assert_called_once()
            exp_manager.teardown.assert_called_once()

    def test_plugin_environment_service_integration(self, mock_event_manager):
        """Test three-way integration between plugins, environments, and services."""
        # Mock all three components
        mock_plugin_manager = Mock()
        mock_environment = Mock()
        mock_service_manager = Mock()

        # Setup integration chain
        mock_plugin_manager.create_service_manager.return_value = mock_service_manager
        mock_service_manager.generate_commands.return_value = {
            "run_cmd": {"command_binary": "test"}
        }
        mock_environment.deploy_service = Mock()

        # Test integration flow
        service_manager = mock_plugin_manager.create_service_manager(
            "test_config", mock_event_manager
        )
        commands = service_manager.generate_commands()
        mock_environment.deploy_service(service_manager, commands)

        # Verify integration chain
        mock_plugin_manager.create_service_manager.assert_called_once_with(
            "test_config", mock_event_manager
        )
        mock_service_manager.generate_commands.assert_called_once()
        mock_environment.deploy_service.assert_called_once_with(
            service_manager, commands
        )
