"""Integration tests for Shadow NS network resolution.

Tests the complete Shadow NS environment integration with network-aware
command resolution using role-based IP assignment.
"""

from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest

from panther.config.core.models.network_resolution import (
    NetworkResolutionContext,
    NetworkServiceInfo,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_network_resolver import (
    ShadowNetworkResolver,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import (
    ShadowNsEnvironment,
)


class TestShadowNetworkResolutionIntegration:
    """Integration tests for Shadow NS network resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock configuration objects
        self.mock_env_config = Mock()
        self.mock_env_config.shadow = {"duration": "120s", "topology": "simple"}
        self.mock_env_config.enable_background_monitoring = True

        self.mock_event_manager = Mock()

        # Create environment instance
        self.environment = ShadowNsEnvironment(
            env_config_to_test=self.mock_env_config,
            output_dir="/tmp/test_shadow",
            env_type="shadow_ns",
            env_sub_type="test",
            event_manager=self.mock_event_manager,
        )

    def test_shadow_environment_has_network_resolver(self):
        """Test that Shadow NS environment has network resolver initialized."""
        assert hasattr(self.environment, "network_resolver")
        assert isinstance(self.environment.network_resolver, ShadowNetworkResolver)

    def test_resolve_network_placeholders_in_commands_with_server_client(self):
        """Test network placeholder resolution with server and client services."""
        # Mock service managers
        mock_server = Mock()
        mock_server.service_name = "ivy_server"
        mock_server.role = Mock()
        mock_server.role.name = "server"

        mock_client = Mock()
        mock_client.service_name = "ivy_client"
        mock_client.role = Mock()
        mock_client.role.name = "client"

        self.environment.services_managers = [mock_server, mock_client]

        # Test commands with placeholders
        commands = {
            "run_cmds": [
                "ivy_server --server_addr=@{ivy_server:ip:decimal} --server_port=@{ivy_server:port:string}",
                "ivy_client --target_ip=@{ivy_server:ip:dotted} --target_port=@{ivy_server:port:string}",
            ]
        }

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_server
        )

        # Verify resolution
        assert "run_cmds" in resolved_commands
        assert len(resolved_commands["run_cmds"]) == 2

        # Check server command resolution (11.0.0.1 = 184549377 in decimal)
        server_cmd = resolved_commands["run_cmds"][0]
        assert "ivy_server --server_addr=184549377 --server_port=4433" == server_cmd

        # Check client command resolution
        client_cmd = resolved_commands["run_cmds"][1]
        assert "ivy_client --target_ip=11.0.0.1 --target_port=4433" == client_cmd

    def test_resolve_network_placeholders_role_detection(self):
        """Test service role detection from service manager."""
        # Mock services with different role formats
        mock_server = Mock()
        mock_server.service_name = "test_server"
        mock_server.role = "SERVER"  # String instead of object

        mock_client = Mock()
        mock_client.service_name = "test_client"
        mock_client.role = Mock()
        mock_client.role.name = "CLIENT"

        self.environment.services_managers = [mock_server, mock_client]

        commands = {"main": ["echo @{test_server:ip:dotted} @{test_client:ip:dotted}"]}

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_server
        )

        # Verify role-based IP assignment
        resolved_cmd = resolved_commands["main"][0]
        assert "echo 11.0.0.1 11.0.0.2" == resolved_cmd

    def test_resolve_network_placeholders_no_role_defaults_server(self):
        """Test that services without role default to server."""
        # Mock service without role
        mock_service = Mock()
        mock_service.service_name = "unknown_service"
        mock_service.role = None

        self.environment.services_managers = [mock_service]

        commands = {"setup": ["connect @{unknown_service:ip:dotted}"]}

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_service
        )

        # Should default to server IP
        resolved_cmd = resolved_commands["setup"][0]
        assert "connect 11.0.0.1" == resolved_cmd

    def test_resolve_placeholders_in_command_multiple_placeholders(self):
        """Test resolving multiple placeholders in single command."""
        # Set up context
        context = NetworkResolutionContext("shadow_ns")

        # Add service info
        server_info = NetworkServiceInfo(
            service_name="ivy_server",
            hostname="11.0.0.1",
            ip_address="11.0.0.1",
            port=4433,
        )
        context.add_service(server_info)

        command = "start --ip=@{ivy_server:ip:dotted} --port=@{ivy_server:port:string} --name=@{ivy_server:service_name:string}"

        resolved_command = self.environment._resolve_placeholders_in_command(
            command, context
        )

        expected = "start --ip=11.0.0.1 --port=4433 --name=ivy_server"
        assert resolved_command == expected

    def test_resolve_placeholders_in_command_no_placeholders(self):
        """Test command without placeholders passes through unchanged."""
        context = NetworkResolutionContext("shadow_ns")
        command = "echo 'Hello World'"

        resolved_command = self.environment._resolve_placeholders_in_command(
            command, context
        )

        assert resolved_command == command

    def test_resolve_placeholders_in_command_exception_handling(self):
        """Test exception handling during placeholder resolution."""
        context = NetworkResolutionContext("shadow_ns")

        # Command with invalid placeholder
        command = "invalid @{nonexistent:invalid:format}"

        # Should not raise exception, just return original command with warning
        resolved_command = self.environment._resolve_placeholders_in_command(
            command, context
        )

        assert resolved_command == command

    def test_resolve_network_placeholders_exception_fallback(self):
        """Test that resolution exceptions fall back to original commands."""
        # Mock service with no name (will cause error)
        mock_service = Mock()
        mock_service.service_name = None  # This will cause issues

        self.environment.services_managers = [mock_service]

        original_commands = {"run": ["test command @{service:ip:dotted}"]}

        # Should return original commands on error
        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            original_commands, mock_service
        )

        assert resolved_commands == original_commands

    def test_network_resolver_service_role_registration(self):
        """Test that service roles are properly registered with resolver."""
        # Mock services
        mock_server = Mock()
        mock_server.service_name = "test_server"
        mock_server.role = Mock()
        mock_server.role.name = "server"

        mock_client = Mock()
        mock_client.service_name = "test_client"
        mock_client.role = Mock()
        mock_client.role.name = "client"

        self.environment.services_managers = [mock_server, mock_client]

        commands = {"test": ["dummy"]}

        # Trigger resolution to register roles
        self.environment._resolve_network_placeholders_in_commands(
            commands, mock_server
        )

        # Check that roles were registered
        registered_roles = self.environment.network_resolver.get_service_roles()
        assert registered_roles["test_server"] == "server"
        assert registered_roles["test_client"] == "client"

    def test_shadow_ip_assignment_consistency(self):
        """Test that Shadow NS IP assignment is consistent across resolutions."""
        # Mock services
        mock_server = Mock()
        mock_server.service_name = "consistent_server"
        mock_server.role = Mock()
        mock_server.role.name = "server"

        self.environment.services_managers = [mock_server]

        commands1 = {"test1": ["connect @{consistent_server:ip:dotted}"]}
        commands2 = {"test2": ["ping @{consistent_server:ip:decimal}"]}

        # Resolve twice
        resolved1 = self.environment._resolve_network_placeholders_in_commands(
            commands1, mock_server
        )
        resolved2 = self.environment._resolve_network_placeholders_in_commands(
            commands2, mock_server
        )

        # Should get same server IP in different formats
        assert "connect 11.0.0.1" == resolved1["test1"][0]
        assert "ping 184549377" == resolved2["test2"][0]  # 11.0.0.1 in decimal
