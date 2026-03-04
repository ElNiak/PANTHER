"""Unit tests for ServiceCommandBuilder."""

from unittest.mock import Mock, patch

import pytest

from panther.core.command_processor import ShellCommand
from panther.plugins.services.base import service_command_builder as _scb_mod
from panther.plugins.services.base.service_command_builder import ServiceCommandBuilder


class TestServiceCommandBuilder:
    """Test cases for ServiceCommandBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = ServiceCommandBuilder()

    def test_build_command_basic(self):
        """Test basic command building."""
        parts = ["testquic", "-p", "4443", "-v", "1"]
        command = ServiceCommandBuilder.build_command(parts)

        assert command == "testquic -p 4443 -v 1"

    def test_build_command_with_spaces(self):
        """Test command building with spaces in arguments."""
        parts = ["testquic", "-f", "my file.txt", "-d", "/path with spaces/"]
        command = ServiceCommandBuilder.build_command(parts)

        assert "'my file.txt'" in command
        assert "'/path with spaces/'" in command

    def test_build_command_empty_parts(self):
        """Test command building with empty parts."""
        parts = ["testquic", "", "-p", None, "4443", ""]
        command = ServiceCommandBuilder.build_command(parts)

        assert command == "testquic -p 4443"

    def test_build_command_with_shell_operators(self):
        """Test command building with shell operators."""
        parts = ["testquic", "-o", "output.log", ">", "/dev/null", "2>&1"]
        command = ServiceCommandBuilder.build_command(parts)

        # Shell operators should not be quoted
        assert "> /dev/null 2>&1" in command

    def test_build_command_already_quoted(self):
        """Test command building with already quoted arguments."""
        parts = ["testquic", '"my file.txt"', "'another file.txt'"]
        command = ServiceCommandBuilder.build_command(parts)

        # Already quoted parts should not be re-quoted
        assert '"my file.txt"' in command
        assert "'another file.txt'" in command

    def test_build_quic_command_server(self):
        """Test building QUIC server command."""
        command = ServiceCommandBuilder.build_quic_command(
            binary="picoquicdemo",
            role="server",
            port=5000,
            certs={
                "cert_file": "/certs/server.crt",
                "key_file": "/certs/server.key",
            },
            extra_args=["-G", "bbr"],
        )

        assert "picoquicdemo" in command
        assert "-c /certs/server.crt" in command
        assert "-k /certs/server.key" in command
        assert "-p 5000" in command
        assert "-G bbr" in command

    def test_build_quic_command_client(self):
        """Test building QUIC client command."""
        command = ServiceCommandBuilder.build_quic_command(
            binary="picoquicdemo",
            role="client",
            host="example.com",
            port=4433,
            version="ff00001d",
            extra_args=["-o", "index.html"],
        )

        assert "picoquicdemo" in command
        assert "example.com 4433" in command
        assert "-v ff00001d" in command
        assert "-o index.html" in command

    def test_build_quic_command_server_cert_dir(self):
        """Test building QUIC server command with cert directory."""
        command = ServiceCommandBuilder.build_quic_command(
            binary="testquic",
            role="server",
            certs={"cert_dir": "/path/to/certs"},
        )

        assert "-c /path/to/certs" in command

    @patch.object(_scb_mod, "CommandUtils")
    @patch.object(_scb_mod, "ShellCommand")
    def test_create_service_command_structure(
        self, mock_shell_command, mock_command_utils
    ):
        """Test creating complete service command structure."""
        # Mock the necessary methods
        mock_command_utils.generate_basic_service_commands.return_value = {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "post_run_cmds": [],
        }
        mock_command_utils.create_shell_commands_from_list.side_effect = lambda x: x
        mock_command_utils.create_run_command.return_value = {
            "working_dir": "/app",
            "command_binary": "testquic",
            "command_args": "-p 4443",
            "timeout": 60,
            "environment": {},
        }
        mock_command_utils.validate_command_structure.return_value = True

        mock_shell_command.from_string.return_value = Mock(spec=ShellCommand)

        structure = ServiceCommandBuilder.create_service_command_structure(
            role="server",
            binary_path="testquic",
            working_dir="/app",
            run_args="-p 4443",
            compile_cmd="make",
            pre_compile_cmds=["git submodule update"],
            post_compile_cmds=["make test"],
            pre_run_cmds=["ulimit -n 65536"],
            post_run_cmds=["cp logs/* /output/"],
            environment={"QUIC_DEBUG": "1"},
            timeout=120,
        )

        # Verify the structure was created correctly
        mock_command_utils.create_run_command.assert_called_once_with(
            working_dir="/app",
            command_binary="testquic",
            command_args="-p 4443",
            timeout=120,
            environment={"QUIC_DEBUG": "1"},
        )

        assert "run_cmd" in structure
        assert mock_command_utils.validate_command_structure.called

    def test_add_logging_to_command_basic(self):
        """Test adding logging to a command."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.add_logging_to_command(
            command,
            log_file="/logs/server.log",
        )

        assert result == "testquic -p 4443 > /logs/server.log 2>&1"

    def test_add_logging_to_command_append(self):
        """Test adding logging with append mode."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.add_logging_to_command(
            command,
            log_file="/logs/server.log",
            append=True,
        )

        assert result == "testquic -p 4443 >> /logs/server.log 2>&1"

    def test_add_logging_to_command_existing_redirect(self):
        """Test adding logging when command already has redirection."""
        command = "testquic -p 4443 2>&1"
        result = ServiceCommandBuilder.add_logging_to_command(
            command,
            log_file="/logs/server.log",
        )

        assert result == "testquic -p 4443 > /logs/server.log 2>&1"

    def test_add_logging_to_command_no_file(self):
        """Test adding logging without log file."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.add_logging_to_command(command)

        assert result == command

    def test_create_certificate_generation_command(self):
        """Test certificate generation command."""
        command = ServiceCommandBuilder.create_certificate_generation_command(
            cert_dir="/certs",
            cert_name="server",
            key_name="server_key",
            common_name="test.example.com",
            days=730,
        )

        assert "openssl req -x509" in command
        assert "-keyout /certs/server_key.pem" in command
        assert "-out /certs/server.pem" in command
        assert "-days 730" in command
        assert "/CN=test.example.com" in command

    def test_create_network_namespace_command(self):
        """Test network namespace command wrapping."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.create_network_namespace_command(
            command,
            namespace="test_ns",
        )

        assert result == "sudo ip netns exec test_ns testquic -p 4443"

    def test_create_network_namespace_command_no_sudo(self):
        """Test network namespace command without sudo."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.create_network_namespace_command(
            command,
            namespace="test_ns",
            use_sudo=False,
        )

        assert result == "ip netns exec test_ns testquic -p 4443"

    def test_create_resource_limit_command_timeout(self):
        """Test resource limit command with timeout."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.create_resource_limit_command(
            command,
            timeout_seconds=30,
        )

        assert result == "timeout 30s testquic -p 4443"

    def test_create_resource_limit_command_memory(self):
        """Test resource limit command with memory limit."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.create_resource_limit_command(
            command,
            memory_mb=512,
        )

        assert "ulimit -v 524288" in result
        assert "testquic -p 4443" in result

    def test_create_resource_limit_command_combined(self):
        """Test resource limit command with multiple limits."""
        command = "testquic -p 4443"
        result = ServiceCommandBuilder.create_resource_limit_command(
            command,
            memory_mb=512,
            timeout_seconds=30,
        )

        assert "timeout 30s" in result
        assert "ulimit -v 524288" in result
        assert "testquic -p 4443" in result
