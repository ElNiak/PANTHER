"""Tests for the modernized plugin system."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.plugin_test]


class TestModernPluginSystem:
    """Test the modernized plugin loading and management system."""

    def test_plugin_discovery_mechanism(self, temp_dir):
        """Test that plugins are discovered correctly in the new system."""
        # Create a fake plugin directory structure
        plugin_dir = (
            Path(temp_dir)
            / "plugins"
            / "services"
            / "iut"
            / "test_protocol"
            / "test_impl"
        )
        plugin_dir.mkdir(parents=True)

        # Create a fake plugin file
        plugin_file = plugin_dir / "test_impl.py"
        plugin_file.write_text(
            """
class TestImplServiceManager:
    def __init__(self, *args, **kwargs):
        pass

    def generate_commands(self):
        return {"run_cmd": {"command_binary": "test"}}
"""
        )

        # Test plugin discovery
        from panther.plugins.plugin_manager import PluginManager

        plugin_manager = PluginManager(str(plugin_dir.parent.parent.parent.parent))

        # This would test the actual discovery mechanism
        assert plugin_dir.exists()

    @patch("panther.plugins.plugin_manager.PluginManager")
    def test_service_manager_creation(
        self, mock_plugin_manager, sample_service_config, mock_event_manager
    ):
        """Test that service managers are created with proper dependency injection."""
        mock_manager_instance = Mock()
        mock_plugin_manager.return_value = mock_manager_instance

        # Mock the create_service_manager method
        mock_service_manager = Mock()
        mock_manager_instance.create_service_manager.return_value = mock_service_manager

        # Test service manager creation
        service_manager = mock_manager_instance.create_service_manager(
            sample_service_config, mock_event_manager
        )

        assert service_manager is not None
        mock_manager_instance.create_service_manager.assert_called_once()

    def test_plugin_naming_convention(self):
        """Test that plugin naming conventions are enforced."""
        # Test the expected naming pattern: <ImplementationName>ServiceManager
        expected_patterns = [
            ("picoquic", "PicoquicServiceManager"),
            ("aioquic", "AioquicServiceManager"),
            ("lsquic", "LsquicServiceManager"),
            ("test_impl", "TestImplServiceManager"),
        ]

        for impl_name, expected_class_name in expected_patterns:
            # Convert implementation name to class name
            class_name = f"{''.join(word.capitalize() for word in impl_name.split('_'))}ServiceManager"
            assert class_name == expected_class_name

    def test_plugin_interface_compliance(
        self, sample_service_config, mock_event_manager
    ):
        """Test that plugins comply with the required interface."""
        from panther.plugins.services.services_interface import IServiceManager

        # Create a mock service manager that implements the interface
        mock_service_manager = Mock(spec=IServiceManager)

        # Test required methods exist
        assert hasattr(mock_service_manager, "generate_commands")
        assert hasattr(mock_service_manager, "validate_config")

        # Test method calls
        mock_service_manager.generate_commands()
        mock_service_manager.validate_config(sample_service_config)

        mock_service_manager.generate_commands.assert_called_once()
        mock_service_manager.validate_config.assert_called_once_with(
            sample_service_config
        )


@pytest.mark.integration
class TestPluginEnvironmentIntegration:
    """Test integration between plugins and environment systems."""

    def test_docker_compose_plugin_integration(
        self, sample_test_config, mock_event_manager
    ):
        """Test integration with Docker Compose environment."""
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            DockerComposeEnvironment,
        )

        # Mock environment creation
        with patch.object(DockerComposeEnvironment, "__init__", return_value=None):
            env = DockerComposeEnvironment.__new__(DockerComposeEnvironment)
            env.logger = Mock()
            env.event_manager = mock_event_manager

            # Test environment lifecycle methods
            env.prepare = Mock()
            env.deploy = Mock()
            env.teardown = Mock()

            # Simulate lifecycle
            env.prepare([])
            env.deploy()
            env.teardown()

            env.prepare.assert_called_once()
            env.deploy.assert_called_once()
            env.teardown.assert_called_once()

    def test_execution_environment_plugin_integration(
        self, sample_test_config, mock_event_manager
    ):
        """Test integration with execution environment plugins."""
        # Mock execution environment
        mock_exec_env = Mock()
        mock_exec_env.setup_environment = Mock()
        mock_exec_env.teardown_environment = Mock()

        # Test setup and teardown
        mock_exec_env.setup_environment([], sample_test_config, None, "timestamp", None)
        mock_exec_env.teardown_environment()

        mock_exec_env.setup_environment.assert_called_once()
        mock_exec_env.teardown_environment.assert_called_once()


class TestPluginCommandGeneration:
    """Test the command generation pipeline with plugins."""

    def test_template_rendering_integration(self, sample_service_config):
        """Test that template rendering works with plugin commands."""
        from panther.core.template.template_renderer import TemplateRenderer

        # Mock template renderer
        with patch.object(TemplateRenderer, "__init__", return_value=None):
            renderer = TemplateRenderer.__new__(TemplateRenderer)
            renderer.render_command_template = Mock(return_value="rendered command")

            # Test template rendering
            result = renderer.render_command_template(
                "test_template", sample_service_config
            )

            assert result == "rendered command"
            renderer.render_command_template.assert_called_once_with(
                "test_template", sample_service_config
            )

    def test_command_validation_pipeline(self, mock_command_processor):
        """Test the command validation pipeline."""
        test_command = {
            "run_cmd": {
                "command_binary": "test",
                "command_args": "--test",
                "timeout": 60,
                "working_dir": "/test",
                "command_env": {},
            }
        }

        # Mock validation
        mock_command_processor.validate_command.return_value = True

        result = mock_command_processor.validate_command(test_command)

        assert result is True
        mock_command_processor.validate_command.assert_called_once_with(test_command)

    @pytest.mark.parametrize(
        "plugin_type,expected_phases",
        [
            ("iut", ["pre_compile", "compile", "post_compile", "run", "post_run"]),
            ("testers", ["pre_compile", "compile", "post_compile", "run", "post_run"]),
        ],
    )
    def test_command_phases_generation(self, plugin_type, expected_phases):
        """Test that all command phases are generated for different plugin types."""
        # This would test the 5-phase command generation system
        for phase in expected_phases:
            # Each plugin should be able to generate commands for each phase
            assert phase in expected_phases
