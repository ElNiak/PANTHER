"""Functional tests for Shadow NS placeholder resolution.

Tests end-to-end placeholder resolution scenarios that demonstrate
the solution to the original "empty parameters" problem for Shadow NS environment.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import (
    ShadowNsEnvironment,
)


class TestShadowPlaceholderResolutionFunctional:
    """Functional tests for Shadow NS placeholder resolution scenarios."""

    def setup_method(self):
        """Set up test environment."""
        # Mock configuration
        self.mock_env_config = Mock()
        self.mock_env_config.shadow = {"duration": "120s", "topology": "simple"}
        self.mock_event_manager = Mock()

        # Create environment
        self.environment = ShadowNsEnvironment(
            env_config_to_test=self.mock_env_config,
            output_dir="/tmp/test_shadow",
            env_type="shadow_ns",
            env_sub_type="test",
            event_manager=self.mock_event_manager,
        )

    def test_ivy_server_client_placeholder_resolution(self):
        """Test Ivy server-client setup with placeholders resolves correctly."""
        # Mock Ivy services like in real scenario
        mock_ivy_server = Mock()
        mock_ivy_server.service_name = "ivy_server"
        mock_ivy_server.role = Mock()
        mock_ivy_server.role.name = "server"

        mock_ivy_client = Mock()
        mock_ivy_client.service_name = "ivy_client"
        mock_ivy_client.role = Mock()
        mock_ivy_client.role.name = "client"

        self.environment.services_managers = [mock_ivy_server, mock_ivy_client]

        # Original problematic command with empty parameters
        original_commands = {
            "run_cmds": [
                "ivy_server --seed= --server_port= --server_addr=",
                "ivy_client --seed= --the_cid= --server_port= --iversion= --server_addr=",
            ]
        }

        # Commands with placeholders (what they should become)
        placeholder_commands = {
            "run_cmds": [
                "ivy_server --seed=@{ivy_server:service_name:string} --server_port=@{ivy_server:port:string} --server_addr=@{ivy_server:ip:decimal}",
                "ivy_client --seed=@{ivy_client:service_name:string} --the_cid=@{ivy_client:service_name:string} --server_port=@{ivy_server:port:string} --iversion=4 --server_addr=@{ivy_server:ip:decimal}",
            ]
        }

        # Resolve placeholders
        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            placeholder_commands, mock_ivy_server
        )

        # Verify resolution
        expected_server_cmd = (
            "ivy_server --seed=ivy_server --server_port=4433 --server_addr=184549377"
        )
        expected_client_cmd = "ivy_client --seed=ivy_client --the_cid=ivy_client --server_port=4433 --iversion=4 --server_addr=184549377"

        assert resolved_commands["run_cmds"][0] == expected_server_cmd
        assert resolved_commands["run_cmds"][1] == expected_client_cmd

        # Verify the problem is solved: no empty parameters
        for cmd in resolved_commands["run_cmds"]:
            # Check for empty parameter patterns (parameter= followed by space or end)
            assert not any(
                pattern in cmd for pattern in ["= ", "=\t", "=\n"]
            )  # No empty values
            assert not cmd.endswith("=")  # No trailing empty parameters
            assert "--seed= " not in cmd  # No empty seed
            assert "--server_port= " not in cmd  # No empty port
            assert "--server_addr= " not in cmd  # No empty address

    def test_shadow_ns_specific_ip_assignment(self):
        """Test Shadow NS-specific IP assignment (11.0.0.x pattern)."""
        # Mock multiple services
        mock_server1 = Mock()
        mock_server1.service_name = "server_one"
        mock_server1.role = Mock()
        mock_server1.role.name = "server"

        mock_server2 = Mock()
        mock_server2.service_name = "server_two"
        mock_server2.role = Mock()
        mock_server2.role.name = "server"

        mock_client = Mock()
        mock_client.service_name = "client_one"
        mock_client.role = Mock()
        mock_client.role.name = "client"

        self.environment.services_managers = [mock_server1, mock_server2, mock_client]

        commands = {
            "network_test": [
                "ping @{server_one:ip:dotted}",
                "ping @{server_two:ip:dotted}",
                "ping @{client_one:ip:dotted}",
            ]
        }

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_server1
        )

        # All servers should get 11.0.0.1
        assert "ping 11.0.0.1" == resolved_commands["network_test"][0]
        assert "ping 11.0.0.1" == resolved_commands["network_test"][1]

        # Client should get 11.0.0.2
        assert "ping 11.0.0.2" == resolved_commands["network_test"][2]

    def test_mixed_placeholder_formats_resolution(self):
        """Test resolution of mixed placeholder formats in Shadow NS."""
        mock_service = Mock()
        mock_service.service_name = "mixed_service"
        mock_service.role = Mock()
        mock_service.role.name = "server"

        self.environment.services_managers = [mock_service]

        commands = {
            "mixed_formats": [
                "app --ip-dotted=@{mixed_service:ip:dotted} --ip-decimal=@{mixed_service:ip:decimal}",
                "app --hostname=@{mixed_service:hostname:string} --port=@{mixed_service:port:string}",
                "app --name=@{mixed_service:service_name:string}",
            ]
        }

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_service
        )

        # Check all format types work
        expected_cmd1 = "app --ip-dotted=11.0.0.1 --ip-decimal=184549377"
        expected_cmd2 = "app --hostname=11.0.0.1 --port=4433"
        expected_cmd3 = "app --name=mixed_service"

        assert resolved_commands["mixed_formats"][0] == expected_cmd1
        assert resolved_commands["mixed_formats"][1] == expected_cmd2
        assert resolved_commands["mixed_formats"][2] == expected_cmd3

    def test_command_phases_placeholder_resolution(self):
        """Test placeholder resolution across different command phases."""
        mock_service = Mock()
        mock_service.service_name = "phase_service"
        mock_service.role = Mock()
        mock_service.role.name = "client"

        self.environment.services_managers = [mock_service]

        commands = {
            "pre_run_cmds": ["setup --target=@{phase_service:ip:dotted}"],
            "run_cmds": [
                "start --listen=@{phase_service:ip:dotted}:@{phase_service:port:string}"
            ],
            "post_run_cmds": ["cleanup --host=@{phase_service:hostname:string}"],
        }

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_service
        )

        # Check all phases are resolved
        assert "setup --target=11.0.0.2" == resolved_commands["pre_run_cmds"][0]
        assert "start --listen=11.0.0.2:4433" == resolved_commands["run_cmds"][0]
        assert "cleanup --host=11.0.0.2" == resolved_commands["post_run_cmds"][0]

    def test_cross_service_communication_placeholders(self):
        """Test placeholders for cross-service communication scenarios."""
        # Mock client-server setup
        mock_http_server = Mock()
        mock_http_server.service_name = "http_server"
        mock_http_server.role = Mock()
        mock_http_server.role.name = "server"

        mock_http_client = Mock()
        mock_http_client.service_name = "http_client"
        mock_http_client.role = Mock()
        mock_http_client.role.name = "client"

        self.environment.services_managers = [mock_http_server, mock_http_client]

        # Client needs to connect to server
        client_commands = {
            "run_cmds": [
                "curl http://@{http_server:ip:dotted}:@{http_server:port:string}/api",
                "wget @{http_server:hostname:string}:@{http_server:port:string}/download",
            ]
        }

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            client_commands, mock_http_client
        )

        # Client should connect to server's IP
        expected_curl = "curl http://11.0.0.1:4433/api"
        expected_wget = "wget 11.0.0.1:4433/download"

        assert resolved_commands["run_cmds"][0] == expected_curl
        assert resolved_commands["run_cmds"][1] == expected_wget

    def test_complex_command_template_resolution(self):
        """Test resolution of complex command templates with multiple placeholders."""
        mock_quic_server = Mock()
        mock_quic_server.service_name = "quic_server"
        mock_quic_server.role = Mock()
        mock_quic_server.role.name = "server"

        self.environment.services_managers = [mock_quic_server]

        # Complex command template
        commands = {
            "complex_cmd": [
                (
                    "quic_server "
                    "--bind-addr=@{quic_server:ip:dotted} "
                    "--bind-port=@{quic_server:port:string} "
                    "--server-name=@{quic_server:service_name:string} "
                    "--server-addr-decimal=@{quic_server:ip:decimal} "
                    "--hostname=@{quic_server:hostname:string}"
                )
            ]
        }

        resolved_commands = self.environment._resolve_network_placeholders_in_commands(
            commands, mock_quic_server
        )

        expected_cmd = (
            "quic_server "
            "--bind-addr=11.0.0.1 "
            "--bind-port=4433 "
            "--server-name=quic_server "
            "--server-addr-decimal=184549377 "
            "--hostname=11.0.0.1"
        )

        assert resolved_commands["complex_cmd"][0] == expected_cmd
