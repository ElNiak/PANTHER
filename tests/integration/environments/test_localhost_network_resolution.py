"""Integration tests for localhost network resolution in environment context."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from panther.config.core.models.network_resolution import (
    NetworkResolutionContext,
    NetworkServiceInfo,
)
from panther.plugins.environments.network_environment.localhost_single_container.localhost_network_resolver import (
    LocalhostNetworkResolver,
)


class TestLocalhostNetworkResolutionIntegration:
    """Integration tests for localhost network resolution."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.resolver = LocalhostNetworkResolver()
        self.test_services = ["ivy_service", "picoquic_server", "quiche_client"]

    def test_service_command_resolution_workflow(self):
        """Test the complete workflow of resolving service commands."""
        # Arrange: Set up mock service managers
        mock_services = []
        for i, service_name in enumerate(self.test_services):
            mock_service = Mock()
            mock_service.service_name = service_name
            mock_service.finalize_commands.return_value = {
                "main": [
                    f"command_{service_name} --target=@{{{self.test_services[(i+1) % len(self.test_services)]}:ip:decimal}} --port=@{{{service_name}:port}}"
                ]
            }
            mock_services.append(mock_service)

        # Act: Register services and create context
        self.resolver.register_services(self.test_services)
        service_managers = {s.service_name: s for s in mock_services}
        context = self.resolver.create_resolution_context(
            "localhost_single_container", service_managers
        )

        # Assert: Verify context creation
        assert context.environment_type == "localhost_single_container"
        assert len(context.available_services) == 3

        # Act: Resolve commands for each service
        resolved_results = {}
        for service in mock_services:
            finalized_commands = service.finalize_commands()

            for phase, command_list in finalized_commands.items():
                for command in command_list:
                    if isinstance(command, str):
                        results = self.resolver.resolve_network_placeholders(
                            command, context
                        )
                        resolved_command = command

                        for result in results:
                            placeholder, value = result.to_substitution_pair()
                            resolved_command = resolved_command.replace(
                                placeholder, value
                            )

                        resolved_results[service.service_name] = resolved_command

        # Assert: Verify all commands were resolved correctly
        assert len(resolved_results) == 3

        # Verify ivy_service command (should target picoquic_server)
        ivy_command = resolved_results["ivy_service"]
        assert "2130706433" in ivy_command  # Decimal IP
        assert "5000" in ivy_command  # ivy_service port (index 0)

        # Verify picoquic_server command (should target quiche_client)
        picoquic_command = resolved_results["picoquic_server"]
        assert "2130706433" in picoquic_command  # Decimal IP
        assert "5010" in picoquic_command  # picoquic_server port (index 1)

    def test_environment_command_processing_simulation(self):
        """Test simulating how localhost environment would process commands."""
        # Arrange: Create realistic service commands
        mock_ivy_service = Mock()
        mock_ivy_service.service_name = "ivy_service"
        mock_ivy_service.finalize_commands.return_value = {
            "setup": ["mkdir -p /logs"],
            "main": [
                "ivy_client --server_addr=@{picoquic_server:ip:decimal} --server_port=@{picoquic_server:port} --log=/logs/ivy.log"
            ],
            "cleanup": ["echo 'ivy_service completed'"],
        }

        mock_picoquic_service = Mock()
        mock_picoquic_service.service_name = "picoquic_server"
        mock_picoquic_service.finalize_commands.return_value = {
            "setup": ["mkdir -p /server_logs"],
            "main": [
                "picoquic_server --port=@{picoquic_server:port} --cert=/certs/server.crt"
            ],
            "cleanup": ["echo 'picoquic_server completed'"],
        }

        services = [mock_ivy_service, mock_picoquic_service]

        # Act: Simulate the environment's _resolve_network_placeholders_in_commands method
        self.resolver.register_services([s.service_name for s in services])
        service_managers = {s.service_name: s for s in services}
        context = self.resolver.create_resolution_context(
            "localhost_single_container", service_managers
        )

        all_resolved_commands = {}
        for service in services:
            finalized_commands = service.finalize_commands()

            # Resolve placeholders in each command phase
            resolved_commands = {}
            for phase, command_list in finalized_commands.items():
                resolved_commands[phase] = []

                for command in command_list:
                    if isinstance(command, str):
                        # Check if command has placeholders
                        if "@{" in command:
                            results = self.resolver.resolve_network_placeholders(
                                command, context
                            )
                            resolved_command = command

                            for result in results:
                                placeholder, value = result.to_substitution_pair()
                                resolved_command = resolved_command.replace(
                                    placeholder, value
                                )

                            resolved_commands[phase].append(resolved_command)
                        else:
                            # No placeholders, keep original
                            resolved_commands[phase].append(command)
                    else:
                        # Non-string commands pass through unchanged
                        resolved_commands[phase].append(command)

            all_resolved_commands[service.service_name] = resolved_commands

        # Assert: Verify resolution worked correctly
        ivy_commands = all_resolved_commands["ivy_service"]
        assert "setup" in ivy_commands
        assert "main" in ivy_commands
        assert "cleanup" in ivy_commands

        # Check main command resolution
        ivy_main_command = ivy_commands["main"][0]
        assert "2130706433" in ivy_main_command  # Decimal IP for picoquic_server
        assert "5010" in ivy_main_command  # picoquic_server port
        assert (
            "--log=/logs/ivy.log" in ivy_main_command
        )  # Non-placeholder parts preserved

        picoquic_commands = all_resolved_commands["picoquic_server"]
        picoquic_main_command = picoquic_commands["main"][0]
        assert "5010" in picoquic_main_command  # picoquic_server's own port
        assert (
            "--cert=/certs/server.crt" in picoquic_main_command
        )  # Non-placeholder parts preserved

    def test_error_resilience_in_command_resolution(self):
        """Test that command resolution handles errors gracefully."""
        # Arrange: Create service with invalid placeholder
        mock_service = Mock()
        mock_service.service_name = "error_service"
        mock_service.finalize_commands.return_value = {
            "main": ["command --invalid=@{nonexistent:invalid_attr:bad_format}"]
        }

        # Act: Attempt resolution
        try:
            self.resolver.register_services(["error_service"])
            service_managers = {"error_service": mock_service}
            context = self.resolver.create_resolution_context(
                "localhost_single_container", service_managers
            )

            command = "command --invalid=@{nonexistent:invalid_attr:bad_format}"
            results = self.resolver.resolve_network_placeholders(command, context)

            # Should not crash, but may not resolve properly
            assert isinstance(results, list)

        except Exception as e:
            # If it does raise an exception, it should be a known type
            assert "resolution" in str(e).lower() or "placeholder" in str(e).lower()

    def test_multiple_placeholder_types_in_single_command(self):
        """Test commands with multiple different placeholder types."""
        # Arrange
        self.resolver.register_services(self.test_services)
        mock_service_managers = {name: Mock() for name in self.test_services}
        context = self.resolver.create_resolution_context(
            "localhost_single_container", mock_service_managers
        )

        # Act: Test command with multiple placeholder types
        complex_command = (
            "multi_tool "
            "--server=@{picoquic_server:hostname} "
            "--port=@{picoquic_server:port} "
            "--client_ip=@{ivy_service:ip:decimal} "
            "--service_name=@{quiche_client:service_name}"
        )

        results = self.resolver.resolve_network_placeholders(complex_command, context)

        # Apply all substitutions
        resolved_command = complex_command
        for result in results:
            placeholder, value = result.to_substitution_pair()
            resolved_command = resolved_command.replace(placeholder, value)

        # Assert: Verify all placeholders were resolved
        assert "@{" not in resolved_command  # No unresolved placeholders
        assert "127.0.0.1" in resolved_command  # Hostname
        assert "5010" in resolved_command  # picoquic_server port
        assert "2130706433" in resolved_command  # Decimal IP
        assert "quiche_client" in resolved_command  # Service name

    def test_port_consistency_across_multiple_resolutions(self):
        """Test that port assignments remain consistent across multiple resolution calls."""
        # Arrange
        self.resolver.register_services(self.test_services)
        mock_service_managers = {name: Mock() for name in self.test_services}
        context = self.resolver.create_resolution_context(
            "localhost_single_container", mock_service_managers
        )

        # Act: Resolve the same service port multiple times
        command = "test --port=@{picoquic_server:port}"

        ports = []
        for _ in range(5):  # Multiple resolution calls
            results = self.resolver.resolve_network_placeholders(command, context)
            resolved_command = command

            for result in results:
                placeholder, value = result.to_substitution_pair()
                resolved_command = resolved_command.replace(placeholder, value)
                if "test --port=" in resolved_command:
                    port = resolved_command.split("test --port=")[1]
                    ports.append(port)

        # Assert: All port assignments should be identical
        assert len(set(ports)) == 1  # All ports should be the same
        assert ports[0] == "5010"  # picoquic_server should always get port 5010

    def test_service_registry_independence(self):
        """Test that different resolver instances maintain independent service registries."""
        # Arrange: Create two separate resolvers
        resolver1 = LocalhostNetworkResolver()
        resolver2 = LocalhostNetworkResolver()

        # Act: Register different services to each
        resolver1.register_services(["service_a", "service_b"])
        resolver2.register_services(["service_x", "service_y", "service_z"])

        # Assert: Registries should be independent
        registry1 = resolver1.get_service_registry()
        registry2 = resolver2.get_service_registry()

        assert len(registry1) == 2
        assert len(registry2) == 3
        assert "service_a" in registry1
        assert "service_x" in registry2
        assert "service_x" not in registry1
        assert "service_a" not in registry2
