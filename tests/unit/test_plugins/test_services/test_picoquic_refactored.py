"""Unit tests for refactored PicoQUIC implementation."""

from unittest.mock import Mock, patch

import pytest

from panther.plugins.services.iut.quic.picoquic.picoquic_clean import (
    PicoquicServiceManager,
)


class TestPicoquicRefactored:
    """Test the refactored PicoQUIC implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = PicoquicServiceManager("picoquic_test", "client")

    def test_implementation_name(self):
        """Test implementation name is correct."""
        assert self.manager._get_implementation_name() == "picoquic"
        assert self.manager.implementation_name == "picoquic"

    def test_binary_name(self):
        """Test binary name is correct."""
        assert self.manager._get_binary_name() == "picoquicdemo"

    def test_protocol_name(self):
        """Test protocol name is set correctly."""
        assert self.manager.protocol_name == "quic"

    def test_server_specific_args(self):
        """Test server-specific arguments."""
        args = self.manager._get_server_specific_args()
        assert args == []  # PicoQUIC server uses only common args

    def test_client_specific_args_basic(self):
        """Test client-specific arguments without options."""
        args = self.manager._get_client_specific_args()
        assert args == []

    def test_client_specific_args_with_ticket(self):
        """Test client-specific arguments with ticket file."""
        args = self.manager._get_client_specific_args(ticket_file="/tmp/ticket.bin")
        assert args == ["-t", "/tmp/ticket.bin"]

    def test_client_specific_args_with_request(self):
        """Test client-specific arguments with request file."""
        args = self.manager._get_client_specific_args(request_file="index.html")
        assert args == ["-o", "index.html"]

    def test_client_specific_args_full(self):
        """Test client-specific arguments with all options."""
        args = self.manager._get_client_specific_args(
            ticket_file="/tmp/ticket.bin", request_file="large.bin"
        )
        assert args == ["-t", "/tmp/ticket.bin", "-o", "large.bin"]

    @patch("panther.plugins.services.base.quic_service_base.CommandUtils")
    def test_generate_server_command(self, mock_command_utils):
        """Test server command generation."""
        mock_command_utils.build_command.return_value = (
            "picoquicdemo -c /certs/cert.pem -k /certs/key.pem -p 4443"
        )

        # Create server manager
        server_manager = PicoquicServiceManager("picoquic_server", "server")

        command = server_manager.generate_run_command(
            role="server",
            cert_file="/certs/cert.pem",
            key_file="/certs/key.pem",
            port=4443,
        )

        assert "picoquicdemo" in command
        mock_command_utils.build_command.assert_called_once()

    @patch("panther.plugins.services.base.quic_service_base.CommandUtils")
    def test_generate_client_command(self, mock_command_utils):
        """Test client command generation."""
        mock_command_utils.build_command.return_value = (
            "picoquicdemo example.com 4443 -v 1 -t /tmp/ticket.bin"
        )

        command = self.manager.generate_run_command(
            role="client",
            host="example.com",
            port=4443,
            version="rfc9000",
            ticket_file="/tmp/ticket.bin",
        )

        assert "picoquicdemo" in command
        mock_command_utils.build_command.assert_called_once()

    def test_post_run_commands(self):
        """Test post-run commands."""
        commands = self.manager.generate_post_run_commands()
        assert len(commands) == 1
        assert "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;" in commands[0]

    def test_compile_commands(self):
        """Test compile commands use base class default."""
        command = self.manager.generate_compile_command()
        assert "cmake" in command
        assert "make" in command

    def test_version_mapping(self):
        """Test QUIC version mapping."""
        assert self.manager._map_version("rfc9000") == "1"
        assert self.manager._map_version("draft29") == "ff00001d"
        assert self.manager._map_version("draft27") == "ff00001b"

    def test_supported_features(self):
        """Test supported features."""
        features = self.manager.get_supported_features()
        assert features["client"] is True
        assert features["server"] is True
        assert features["0rtt"] is True
        assert features["migration"] is True
        assert features["qlog"] is True

    def test_validate_configuration(self):
        """Test configuration validation."""
        # Valid config
        errors = self.manager.validate_configuration(
            role="client", port=4443, version="rfc9000"
        )
        assert errors == []

        # Invalid config
        errors = self.manager.validate_configuration(
            role="proxy", port=99999, version="unknown"
        )
        assert len(errors) == 3
