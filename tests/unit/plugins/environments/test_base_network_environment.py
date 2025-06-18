"""Unit tests for BaseNetworkEnvironment and mixins."""

import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)
from panther.plugins.environments.network_environment.mixins import (
    ConfigurationProcessorMixin,
    ErrorHandlerMixin,
    ServiceHealthCheck,
    ServiceStatus,
    StatusMonitorMixin,
    SubprocessExecutorMixin,
)


class ConcreteNetworkEnvironment(BaseNetworkEnvironment):
    """Concrete implementation for testing."""
    
    def _do_setup_environment(self):
        pass
    
    def _do_teardown_environment(self):
        pass
    
    def _do_deploy_services(self, services):
        pass
    
    def _get_service_log_directory(self, service):
        return "/tmp/logs"
    
    def _teardown_environment(self):
        pass
    
    def deploy_services(self, services):
        pass
    
    def generate_environment_services(self):
        return []
    
    def handle_event(self, event):
        pass
    
    def initialize(self):
        pass
    
    def launch_environment_services(self):
        pass
    
    def prepare_environment(self):
        pass


class TestBaseNetworkEnvironment:
    """Test BaseNetworkEnvironment functionality."""

    def test_initialization(self, tmp_path):
        """Test base environment initialization."""
        # Create test config
        env_config = Mock()
        event_manager = Mock()

        # Create instance using concrete implementation
        env = ConcreteNetworkEnvironment(
            env_config_to_test=env_config,
            output_dir=str(tmp_path),
            env_type="test_env",
            env_sub_type="test_sub",
            event_manager=event_manager,
        )

        # Verify initialization
        assert env.output_dir == tmp_path
        assert env.env_type == "test_env"
        assert env.env_sub_type == "test_sub"
        assert env.deployed is False
        assert env.setup_complete is False
        assert env.teardown_complete is False

        # Verify directories were created
        assert (tmp_path / "logs").exists()

    def test_setup_environment_workflow(self, tmp_path):
        """Test the setup environment workflow."""
        # Setup
        env_config = Mock()
        event_manager = Mock()
        event_manager.emit = Mock()

        class TestEnv(BaseNetworkEnvironment):
            def prepare_environment(self):
                return True

            def generate_environment_services(self, paths, timestamp):
                # Create a dummy file to verify
                (self.output_dir / "test_generated.yml").touch()

            def launch_environment_services(self):
                pass

            def deploy_services(self):
                return True

            def _teardown_environment(self):
                pass
            
            def _do_setup_environment(self):
                pass
            
            def _do_deploy_services(self):
                pass
            
            def _do_teardown_environment(self):
                pass
            
            def _get_service_log_directory(self, service_name: str) -> str:
                return str(self.output_dir / "logs" / service_name)
            
            def handle_event(self, event):
                pass
            
            def initialize(self):
                pass

        env = TestEnv(
            env_config_to_test=env_config,
            output_dir=str(tmp_path),
            env_type="test",
            env_sub_type="test",
            event_manager=event_manager,
        )
        
        # Set up event emitter for event emission
        env.event_emitter = Mock()
        env.event_emitter.emit_environment_setup_completed = Mock()
        env.event_emitter.emit_environment_created = Mock()
        env.event_emitter.emit_environment_setup_failed = Mock()

        # Mock required attributes using dict-like objects that OmegaConf can handle
        from omegaconf import DictConfig
        
        env.test_config = DictConfig({"name": "test_config", "steps": {"wait": 60}})
        env.services_managers = []
        env.log_dirs = str(tmp_path / "logs")

        # Run setup
        test_config = DictConfig({"name": "test", "steps": {"wait": 60}})
        global_config = DictConfig({"logging": {"level": "INFO"}})
        
        result = env.setup_environment(
            services_managers=[],
            test_config=test_config,
            global_config=global_config,
            timestamp="20240101_120000",
            plugin_manager=None,
            execution_environment=[],
        )

        # Verify
        assert result is True
        assert env.setup_complete is True
        assert env.setup_start_time is not None
        assert env.setup_end_time is not None

        # Verify events were emitted
        assert env.event_emitter.emit_environment_setup_completed.called

    def test_teardown_environment(self, tmp_path):
        """Test environment teardown."""
        # Setup
        env_config = Mock()
        event_manager = Mock()

        class TestEnv(BaseNetworkEnvironment):
            def _teardown_environment(self):
                self.teardown_called = True

            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self):
                pass
            
            def _do_setup_environment(self):
                pass
            
            def _do_deploy_services(self):
                pass
            
            def _do_teardown_environment(self):
                pass
            
            def _get_service_log_directory(self, service_name: str) -> str:
                return str(self.output_dir / "logs" / service_name)
            
            def handle_event(self, event):
                pass
            
            def initialize(self):
                pass

        env = TestEnv(
            env_config_to_test=env_config,
            output_dir=str(tmp_path),
            env_type="test",
            env_sub_type="test",
            event_manager=event_manager,
        )

        env.test_config = Mock(name="test")

        # Add a mock process
        mock_process = Mock()
        mock_process.poll.return_value = None
        env.processes = [mock_process]

        # Run teardown
        env.teardown_environment()

        # Verify
        assert env.teardown_complete is True
        assert env.teardown_called is True
        assert mock_process.terminate.called
        assert len(env.processes) == 0


class TestSubprocessExecutorMixin:
    """Test SubprocessExecutorMixin functionality."""

    def test_execute_command_success(self):
        """Test successful command execution."""

        class TestExecutor(SubprocessExecutorMixin):
            def __init__(self):
                self.logger = Mock()

        executor = TestExecutor()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="success",
                stderr="",
            )

            result = executor.execute_command(["echo", "test"])

            assert result.returncode == 0
            assert result.stdout == "success"
            assert result.stderr == ""
            assert result.command == ["echo", "test"]
            assert result.duration > 0

    def test_execute_command_failure(self):
        """Test command execution failure."""

        class TestExecutor(SubprocessExecutorMixin):
            def __init__(self):
                self.logger = Mock()

        executor = TestExecutor()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="error",
            )

            with pytest.raises(subprocess.CalledProcessError):
                executor.execute_command(["false"], check=True)

    def test_execute_with_retry(self):
        """Test command execution with retry."""

        class TestExecutor(SubprocessExecutorMixin):
            def __init__(self):
                self.logger = Mock()
                self.call_count = 0

            def execute_command(self, command, **kwargs):
                self.call_count += 1
                if self.call_count < 3:
                    raise subprocess.CalledProcessError(1, command)
                return Mock(returncode=0)

        executor = TestExecutor()

        with patch("time.sleep"):  # Skip sleep in tests
            result = executor.execute_with_retry(["test"], max_retries=3, retry_delay=0)

        assert executor.call_count == 3
        assert result.returncode == 0

    def test_execute_docker_command(self):
        """Test Docker command execution."""

        class TestExecutor(SubprocessExecutorMixin):
            def __init__(self):
                self.logger = Mock()
                self.execute_command = Mock(return_value=Mock())

        executor = TestExecutor()

        result = executor.execute_docker_command(["ps", "-a"])

        executor.execute_command.assert_called_once()
        call_args = executor.execute_command.call_args[0][0]
        assert call_args == ["docker", "ps", "-a"]


class TestErrorHandlerMixin:
    """Test ErrorHandlerMixin functionality."""

    def test_handle_deployment_error(self):
        """Test deployment error handling."""

        class TestHandler(ErrorHandlerMixin):
            def __init__(self):
                self.logger = Mock()

        handler = TestHandler()

        # Test with CalledProcessError
        error = subprocess.CalledProcessError(
            1, ["test", "command"], stderr="test error"
        )

        cleanup_called = False

        def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        handler.handle_deployment_error(error, cleanup_func=cleanup)

        # Verify logging
        assert handler.logger.error.called
        assert cleanup_called

    def test_safe_cleanup(self):
        """Test safe cleanup execution."""

        class TestHandler(ErrorHandlerMixin):
            def __init__(self):
                self.logger = Mock()

        handler = TestHandler()

        # Track cleanup calls
        cleanup_calls = []

        def cleanup1():
            cleanup_calls.append(1)

        def cleanup2():
            cleanup_calls.append(2)
            raise Exception("Cleanup 2 failed")

        def cleanup3():
            cleanup_calls.append(3)

        # Run safe cleanup
        handler.safe_cleanup(cleanup1, cleanup2, cleanup3)

        # All cleanups should be attempted
        assert cleanup_calls == [1, 2, 3]

    def test_safe_docker_cleanup(self):
        """Test Docker cleanup."""

        class TestHandler(ErrorHandlerMixin):
            def __init__(self):
                self.logger = Mock()
                self.execute_command = Mock()

        handler = TestHandler()

        handler.safe_docker_cleanup("test_container")

        # Verify cleanup commands
        assert handler.execute_command.call_count == 3
        calls = handler.execute_command.call_args_list
        assert calls[0][0][0] == ["docker", "stop", "test_container"]
        assert calls[1][0][0] == ["docker", "rm", "--force", "test_container"]
        assert calls[2][0][0] == ["docker", "rmi", "--force", "test_container:latest"]


class TestConfigurationProcessorMixin:
    """Test ConfigurationProcessorMixin functionality."""

    def test_process_service_config(self):
        """Test service configuration processing."""

        class TestProcessor(ConfigurationProcessorMixin):
            def __init__(self):
                self.logger = Mock()

        processor = TestProcessor()

        # Test valid config
        config = {
            "implementation": {"name": "test", "type": "iut"},
            "protocol": {"name": "quic", "role": "server"},
            "timeout": 60,
            "ports": ["4443:4443"],
        }

        result = processor.process_service_config(config)

        assert result["implementation"] == config["implementation"]
        assert result["protocol"] == config["protocol"]
        assert result["timeout"] == 60
        assert result["ports"] == ["4443:4443"]

    def test_process_service_config_missing_required(self):
        """Test service config with missing required fields."""

        class TestProcessor(ConfigurationProcessorMixin):
            def __init__(self):
                self.logger = Mock()

        processor = TestProcessor()

        # Missing implementation
        config = {
            "protocol": {"name": "quic", "role": "server"},
        }

        with pytest.raises(ValueError, match="Missing required field 'implementation'"):
            processor.process_service_config(config)

    def test_process_environment_variables(self):
        """Test environment variable processing."""

        class TestProcessor(ConfigurationProcessorMixin):
            pass

        processor = TestProcessor()

        env_vars = {
            "BASE_DIR": "/app",
            "LOG_DIR": "${BASE_DIR}/logs",
            "DATA_DIR": "${BASE_DIR}/data",
        }

        result = processor._process_environment_variables(env_vars)

        assert result["BASE_DIR"] == "/app"
        assert result["LOG_DIR"] == "/app/logs"
        assert result["DATA_DIR"] == "/app/data"

    def test_validate_network_config(self):
        """Test network configuration validation."""

        class TestProcessor(ConfigurationProcessorMixin):
            pass

        processor = TestProcessor()

        # Valid config
        config = {"type": "docker_compose"}
        assert processor.validate_network_config(config) is True

        # Invalid type
        config = {"type": "invalid_type"}
        with pytest.raises(ValueError, match="Invalid network type"):
            processor.validate_network_config(config)


class TestStatusMonitorMixin:
    """Test StatusMonitorMixin functionality."""

    def test_monitor_service_status_success(self):
        """Test successful service monitoring."""

        class TestMonitor(StatusMonitorMixin):
            def __init__(self):
                self.logger = Mock()
                self.ready_count = 0

            def _check_service_health(self, service_name, custom_check):
                self.ready_count += 1
                if self.ready_count >= 2:
                    return Mock(
                        status=ServiceStatus.READY,
                        is_healthy=True,
                        message="Service ready",
                        check_time=0.1,
                    )
                return Mock(
                    status=ServiceStatus.STARTING,
                    is_healthy=False,
                    message="Service starting",
                    check_time=0.1,
                )

        monitor = TestMonitor()

        with patch("time.sleep"):  # Skip sleep in tests
            result = monitor.monitor_service_status(
                "test_service",
                check_interval=0,
                timeout=10,
            )

        assert result.status == ServiceStatus.READY
        assert result.is_healthy is True

    def test_monitor_service_status_timeout(self):
        """Test service monitoring timeout."""

        class TestMonitor(StatusMonitorMixin):
            def __init__(self):
                self.logger = Mock()

            def _check_service_health(self, service_name, custom_check):
                return Mock(
                    status=ServiceStatus.STARTING,
                    is_healthy=False,
                    message="Service starting",
                    check_time=0.1,
                )

        monitor = TestMonitor()

        with patch("time.sleep"):  # Skip sleep in tests
            # Use itertools.cycle to provide infinite values
            import itertools
            time_values = itertools.cycle([0, 0.1, 0.2, 0.3, 0.4, 0.5, 100])
            with patch("time.time", side_effect=lambda: next(time_values)):
                result = monitor.monitor_service_status(
                    "test_service",
                    check_interval=0,
                    timeout=1,
                )

        assert result.status == ServiceStatus.FAILED
        assert result.is_healthy is False
        assert "did not become ready" in result.message

    def test_wait_for_port(self):
        """Test port availability checking."""

        class TestMonitor(StatusMonitorMixin):
            def __init__(self):
                self.logger = Mock()

        monitor = TestMonitor()

        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_socket

            result = monitor.wait_for_port("localhost", 8080, timeout=1)

            assert result is True
            mock_socket.connect_ex.assert_called_with(("localhost", 8080))

    def test_create_status_report(self):
        """Test status report creation."""

        class TestMonitor(StatusMonitorMixin):
            def monitor_resource_usage(self, service_name):
                return {
                    "cpu_percent": "25%",
                    "memory_usage": "512MB",
                }

        monitor = TestMonitor()

        services = {
            "service1": ServiceStatus.READY,
            "service2": ServiceStatus.STARTING,
            "service3": ServiceStatus.FAILED,
        }

        report = monitor.create_status_report(services, include_resources=True)

        assert "✓ service1: ready" in report
        assert "✗ service2: starting" in report
        assert "✗ service3: failed" in report
        assert "CPU: 25%" in report
        assert "Memory: 512MB" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
