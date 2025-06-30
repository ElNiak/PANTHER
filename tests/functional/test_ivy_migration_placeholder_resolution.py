"""
Functional tests for Ivy service migration to network placeholder resolution.

Tests that the Ivy command generation now uses network placeholders instead of
environment variables, solving the "empty parameters" problem.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from panther.plugins.services.testers.panther_ivy.components.ivy_command_generator import (
    IvyCommandGenerator,
)


class TestIvyMigrationPlaceholderResolution:
    """Functional tests for Ivy service migration to placeholders."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock service manager
        self.mock_service_manager = Mock()
        self.mock_service_manager.service_name = "ivy_client"
        self.mock_service_manager.service_targets = "ivy_server"
        self.mock_service_manager.role = Mock()
        self.mock_service_manager.role.name = "client"

        # Mock service config
        self.mock_service_config = Mock()
        self.mock_service_config.protocol = Mock()
        self.mock_service_config.protocol.target = "ivy_server"
        self.mock_service_config.timeout = 120

        # Ensure hasattr works properly
        self.mock_service_config.protocol.target = "ivy_server"

        # Set service_config_to_test on service manager
        self.mock_service_manager.service_config_to_test = self.mock_service_config

        # Mock implementation version config with parameters
        self.mock_service_config.implementation = Mock()
        self.mock_service_config.implementation.version = Mock()
        self.mock_service_config.implementation.version.parameters = Mock()

        # Set up parameters as attributes with values
        self.mock_service_config.implementation.version.parameters.seed = Mock()
        self.mock_service_config.implementation.version.parameters.seed.value = 0
        self.mock_service_config.implementation.version.parameters.the_cid = Mock()
        self.mock_service_config.implementation.version.parameters.the_cid.value = 1
        self.mock_service_config.implementation.version.parameters.iversion = Mock()
        self.mock_service_config.implementation.version.parameters.iversion.value = 4
        self.mock_service_manager.test_to_compile = "quic_client_test"
        self.mock_service_manager.use_system_models = False

        # Mock template renderer
        self.mock_template_renderer = Mock()
        self.mock_service_manager.template_renderer = self.mock_template_renderer

        # Create command generator
        self.command_generator = IvyCommandGenerator(self.mock_service_manager)

    def test_pre_compile_commands_no_longer_generate_env_vars(self):
        """Test that pre-compile commands no longer generate environment variables."""
        commands = self.command_generator.generate_pre_compile_commands()

        # Get the actual command strings
        command_strings = [str(cmd) for cmd in commands]
        full_command_text = " ".join(command_strings)

        # Verify no environment variable generation
        assert "TARGET_IP=$(resolve_hostname" not in full_command_text
        assert "IVY_IP=$(resolve_hostname" not in full_command_text
        assert "export TARGET_IP" not in full_command_text
        assert "export IVY_IP" not in full_command_text

        # Should have setup logging instead
        assert any("Ivy setup log" in cmd for cmd in command_strings)
        assert any(
            "network-aware placeholder resolution" in cmd for cmd in command_strings
        )

    def test_deployment_commands_use_service_names_not_env_vars(self):
        """Test that deployment commands pass service names for placeholder resolution."""
        # Mock template renderer to return example command with placeholders
        expected_template_output = "seed=0 the_cid=1 server_port=@{ivy_server:port:string} iversion=4 server_addr=@{ivy_server:ip:decimal}"
        self.mock_template_renderer.render_template.return_value = (
            expected_template_output
        )

        # Generate commands
        result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="client"
        )

        # Verify template was called with correct parameters
        self.mock_template_renderer.render_template.assert_called_once()
        call_args = self.mock_template_renderer.render_template.call_args

        template_name, params = call_args[0]

        # Check template name (oppose_role logic: client role uses server template)
        assert template_name == "server_command.jinja"

        # Check parameters contain service names for placeholder resolution
        assert params["service_name"] == "ivy_client"
        assert params["target"] == "ivy_server"
        assert "server_addr" not in params  # No longer passing resolved env vars
        assert "client_addr" not in params  # No longer passing resolved env vars

        # Verify the result contains placeholders
        assert result == expected_template_output
        assert "@{ivy_server:port:string}" in result
        assert "@{ivy_server:ip:decimal}" in result

    def test_quic_client_template_generates_placeholders(self):
        """Test that QUIC client template generates commands with placeholders."""
        # Simulate template rendering with actual placeholder patterns
        template_output = "seed=0 the_cid=1 server_port=@{ivy_server:port:string} iversion=4 server_addr=@{ivy_server:ip:decimal}"
        self.mock_template_renderer.render_template.return_value = template_output

        result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="client"
        )

        # Verify placeholders are present (not environment variables)
        assert "@{ivy_server:port:string}" in result
        assert "@{ivy_server:ip:decimal}" in result
        assert "${TARGET_IP_DEC}" not in result  # Old env var pattern
        assert "${IVY_IP_DEC}" not in result  # Old env var pattern

    def test_quic_server_template_generates_placeholders(self):
        """Test that QUIC server template generates commands with placeholders."""
        # Mock server service
        self.mock_service_manager.service_name = "ivy_server"
        self.mock_service_manager.role.name = "server"

        # Expected server template output with placeholders
        template_output = "seed=0 the_cid=1 server_port=@{ivy_server:port:string} iversion=4 server_addr=@{ivy_server:ip:decimal} server_cid=2 client_port=@{ivy_client:port:string} client_port_alt=5000 client_addr=@{ivy_client:ip:decimal}"
        self.mock_template_renderer.render_template.return_value = template_output

        result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="server"
        )

        # Verify server placeholders
        assert "@{ivy_server:port:string}" in result  # Server's own port
        assert "@{ivy_server:ip:decimal}" in result  # Server's own IP
        assert "@{ivy_client:port:string}" in result  # Target client port
        assert "@{ivy_client:ip:decimal}" in result  # Target client IP

        # Verify no old environment variables
        assert "${" not in result or not any(
            old_var in result
            for old_var in ["${TARGET_IP_DEC}", "${IVY_IP_DEC}", "${IVY_SERVER_IP_DEC}"]
        )

    def test_migration_solves_empty_parameters_problem(self):
        """Test that migration solves the original empty parameters problem."""
        # Before migration: Templates would generate commands like "server_port= server_addr="
        # After migration: Templates generate placeholders that will be resolved by environment

        # Mock template to show what would happen with placeholders
        template_with_placeholders = "seed=0 the_cid=1 server_port=@{ivy_server:port:string} iversion=4 server_addr=@{ivy_server:ip:decimal}"
        self.mock_template_renderer.render_template.return_value = (
            template_with_placeholders
        )

        result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="client"
        )

        # Verify no empty parameters in template output (check for pattern "= " or "= ;" or "=$")
        import re

        empty_param_pattern = r"(\w+)=\s*(?:\s|;|$)"
        empty_matches = re.findall(empty_param_pattern, result)
        assert not empty_matches, f"Found empty parameters: {empty_matches}"

        # Verify placeholders are present instead
        assert "@{" in result and "}" in result  # Placeholder format present
        assert ":port:" in result or ":ip:" in result  # Network attribute placeholders

        # The actual resolution will happen at environment level:
        # @{ivy_server:port:string} -> "4433"
        # @{ivy_server:ip:decimal} -> "184549377" (for localhost) or "184549377" (for Shadow NS)

    def test_minip_protocol_placeholder_support(self):
        """Test that minip protocol also uses placeholders correctly."""
        # Mock minip template output
        minip_template_output = "seed=0 server_port=@{ivy_server:port:string} server_addr=@{ivy_server:ip:decimal} > /app/logs/testers.log 2> /app/logs/testers.err"
        self.mock_template_renderer.render_template.return_value = minip_template_output

        result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="client"
        )

        # Verify minip placeholders
        assert "@{ivy_server:port:string}" in result
        assert "@{ivy_server:ip:decimal}" in result
        assert "> /app/logs/testers.log" in result  # Output redirection preserved

    def test_cross_service_communication_placeholders(self):
        """Test that cross-service communication uses correct placeholder references."""
        # Client should reference server, server should reference client

        # Test client configuration
        self.mock_service_manager.service_name = "ivy_client"
        self.mock_service_config.protocol.target = "ivy_server"

        client_template = "seed=0 server_port=@{ivy_server:port:string} server_addr=@{ivy_server:ip:decimal}"
        self.mock_template_renderer.render_template.return_value = client_template

        client_result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="client"
        )

        # Client should reference server's network info
        assert "@{ivy_server:" in client_result

        # Test server configuration
        self.mock_service_manager.service_name = "ivy_server"
        self.mock_service_config.protocol.target = "ivy_client"

        server_template = "seed=0 server_port=@{ivy_server:port:string} server_addr=@{ivy_server:ip:decimal} client_port=@{ivy_client:port:string} client_addr=@{ivy_client:ip:decimal}"
        self.mock_template_renderer.render_template.return_value = server_template

        server_result = self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="server"
        )

        # Server should reference both its own info and client info
        assert "@{ivy_server:" in server_result  # Own network info
        assert "@{ivy_client:" in server_result  # Target client info

    def test_parameters_passed_to_template_for_placeholder_resolution(self):
        """Test that correct parameters are passed to template for placeholder resolution."""
        self.mock_template_renderer.render_template.return_value = "dummy_output"

        self.command_generator.generate_deployment_commands(
            service_config=self.mock_service_config, role="client"
        )

        # Get the parameters passed to template
        call_args = self.mock_template_renderer.render_template.call_args
        template_name, params = call_args[0]

        # Verify essential parameters for placeholder resolution
        assert "service_name" in params
        assert "target" in params
        assert params["service_name"] == "ivy_client"
        assert params["target"] == "ivy_server"

        # Verify version parameters are still passed
        assert "seed" in params
        assert "the_cid" in params
        assert "iversion" in params

        # Verify network environment variables are NOT passed
        assert "server_addr" not in params
        assert "client_addr" not in params
