"""Integration tests for localhost network environment placeholder resolution."""

from unittest.mock import Mock, patch

import pytest

from panther.config.core.models.environment import EnvironmentConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
    LocalhostSingleContainerEnvironment,
)


class TestLocalhostNetworkIntegration:
    """Integration tests for localhost network environment."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_config = EnvironmentConfig(type="localhost_single_container")
        self.output_dir = "/tmp/test_output"
        self.env_type = "network_environment"
        self.env_sub_type = "localhost_single_container"
        self.event_manager = Mock(spec=EventManager)

    def test_localhost_environment_initialization(self):
        """Test localhost environment initializes network resolver."""
        env = LocalhostSingleContainerEnvironment(
            self.env_config,
            self.output_dir,
            self.env_type,
            self.env_sub_type,
            self.event_manager,
        )

        # Check network resolver is initialized
        assert hasattr(env, "network_resolver")
        assert env.network_resolver is not None
        assert env.network_resolver.localhost_ip == "127.0.0.1"

    def test_command_resolution_integration(self):
        """Test command resolution integration in localhost environment."""
        env = LocalhostSingleContainerEnvironment(
            self.env_config,
            self.output_dir,
            self.env_type,
            self.env_sub_type,
            self.event_manager,
        )

        # Mock service managers
        mock_service1 = Mock()
        mock_service1.service_name = "ivy_service"
        mock_service1.finalize_commands.return_value = {
            "main": [
                "ivy_client --server_addr=@{picoquic_server:ip:decimal} --server_port=@{picoquic_server:port}"
            ]
        }

        mock_service2 = Mock()
        mock_service2.service_name = "picoquic_server"
        mock_service2.finalize_commands.return_value = {
            "main": ["picoquic_server --port=@{picoquic_server:port}"]
        }

        env.services_managers = [mock_service1, mock_service2]

        # Test command resolution
        test_commands = {
            "main": [
                "ivy_client --server_addr=@{picoquic_server:ip:decimal} --server_port=@{picoquic_server:port}"
            ]
        }

        resolved_commands = env._resolve_network_placeholders_in_commands(
            test_commands, mock_service1
        )

        # Check resolution worked
        assert "main" in resolved_commands
        resolved_command = resolved_commands["main"][0]
        assert "2130706433" in resolved_command  # Decimal IP format
        assert "5010" in resolved_command  # picoquic_server port (index 1)

    def test_placeholder_resolution_in_simple_commands(self):
        """Test placeholder resolution in simple command formats."""
        env = LocalhostSingleContainerEnvironment(
            self.env_config,
            self.output_dir,
            self.env_type,
            self.env_sub_type,
            self.event_manager,
        )

        # Mock service manager
        mock_service = Mock()
        mock_service.service_name = "test_service"
        mock_service.finalize_commands.return_value = [
            "simple_command --host=@{test_service:hostname} --port=@{test_service:port}"
        ]

        env.services_managers = [mock_service]

        # Test with list format commands
        test_commands = [
            "simple_command --host=@{test_service:hostname} --port=@{test_service:port}"
        ]

        resolved_commands = env._resolve_network_placeholders_in_commands(
            {"main": test_commands}, mock_service
        )

        resolved_command = resolved_commands["main"][0]
        assert "127.0.0.1" in resolved_command  # Hostname resolved
        assert "5000" in resolved_command  # First service gets port 5000

    def test_error_handling_in_command_resolution(self):
        """Test error handling during command resolution."""
        env = LocalhostSingleContainerEnvironment(
            self.env_config,
            self.output_dir,
            self.env_type,
            self.env_sub_type,
            self.event_manager,
        )

        # Mock service manager with commands that will cause errors
        mock_service = Mock()
        mock_service.service_name = "error_service"

        # Commands with invalid placeholders should not crash the system
        invalid_commands = {"main": ["command_with_@{invalid:placeholder:format}"]}

        # Should return original commands on error
        resolved_commands = env._resolve_network_placeholders_in_commands(
            invalid_commands, mock_service
        )

        # Should gracefully handle error and return original commands
        assert resolved_commands == invalid_commands

    def test_network_resolver_capabilities(self):
        """Test localhost network resolver capabilities."""
        env = LocalhostSingleContainerEnvironment(
            self.env_config,
            self.output_dir,
            self.env_type,
            self.env_sub_type,
            self.event_manager,
        )

        capabilities = env.network_resolver.get_resolution_capabilities()

        # Verify localhost-specific capabilities
        assert capabilities["static_ip_resolution"] is True
        assert capabilities["runtime_ip_resolution"] is False
        assert capabilities["calculated_ports"] is True
        assert capabilities["decimal_ip_format"] is True
