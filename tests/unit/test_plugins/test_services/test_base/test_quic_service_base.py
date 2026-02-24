"""Unit tests for BaseQUICServiceManager."""

from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.core.events.base.event_base import BaseEvent
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


class TestQUICImplementation(BaseQUICServiceManager):
    """Test implementation of BaseQUICServiceManager."""

    def _get_implementation_name(self) -> str:
        return "testquic"

    def _get_binary_name(self) -> str:
        return "testquic_demo"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        args = []
        if kwargs.get("test_mode"):
            args.extend(["--test", "server"])
        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        args = []
        if kwargs.get("test_mode"):
            args.extend(["--test", "client"])
        if kwargs.get("request_size"):
            args.extend(["--size", str(kwargs["request_size"])])
        return args

    def generate_deployment_commands(self) -> str:
        return ""

    def handle_event(self, event: BaseEvent) -> None:
        pass


def _make_mock_service_config(role="client"):
    """Create a mock service config suitable for BaseQUICServiceManager."""
    config = MagicMock()
    config.name = "test_service"
    config.protocol.name = "quic"
    config.protocol.version = "rfc9000"
    config.protocol.role = role
    config.protocol.target = "localhost"
    config.timeout = 60
    config.implementation.version_config = None
    config.implementation.use_system_models = False
    return config


def _make_mock_protocol():
    """Create a mock protocol config."""
    protocol = MagicMock()
    protocol.name = "quic"
    protocol.version = "rfc9000"
    protocol.role = "client"
    protocol.target = "localhost"
    return protocol


class TestBaseQUICServiceManager:
    """Test cases for BaseQUICServiceManager."""

    def setup_method(self):
        """Set up test fixtures."""
        service_config = _make_mock_service_config("client")
        protocol = _make_mock_protocol()
        self.manager = TestQUICImplementation(
            service_config_to_test=service_config,
            service_type="iut",
            protocol=protocol,
            implementation_name="testquic",
        )

    def test_initialization(self):
        """Test proper initialization of base class."""
        assert self.manager.protocol_name == "quic"
        assert self.manager.implementation_name == "testquic"
        assert self.manager.service_name == "test_service"
        assert self.manager.role == "client"

    def test_extract_common_params_defaults(self):
        """Test extraction of common parameters with defaults."""
        params = self.manager._extract_common_params()

        assert params["host"] == "localhost"
        assert params["port"] == 4443
        assert params["cert_dir"] == "/opt/certs"
        assert params["key_file"] == "/opt/certs/key.pem"
        assert params["cert_file"] == "/opt/certs/cert.pem"
        assert params["version"] == "rfc9000"
        assert params["log_level"] == "info"
        assert params["output_dir"] == "/logs"

    def test_extract_common_params_custom(self):
        """Test extraction of common parameters with custom values."""
        custom_params = {
            "host": "example.com",
            "port": 8443,
            "cert_dir": "/custom/certs",
            "version": "draft29",
            "log_file": "/logs/test.log",
        }

        params = self.manager._extract_common_params(**custom_params)

        assert params["host"] == "example.com"
        assert params["port"] == 8443
        assert params["cert_dir"] == "/custom/certs"
        assert params["version"] == "draft29"
        assert params["log_file"] == "/logs/test.log"

    def test_build_server_args(self):
        """Test building common server arguments."""
        params = {
            "cert_file": "/certs/server.crt",
            "key_file": "/certs/server.key",
            "port": 5000,
            "log_file": "/logs/server.log",
        }

        args = self.manager._build_server_args(params)

        assert args == [
            "-c",
            "/certs/server.crt",
            "-k",
            "/certs/server.key",
            "-p",
            "5000",
            "-l",
            "/logs/server.log",
        ]

    def test_build_client_args(self):
        """Test building common client arguments."""
        params = {
            "host": "test.example.com",
            "port": 4433,
            "version": "draft29",
            "log_file": "/logs/client.log",
        }

        # Mock the version mapping
        self.manager._map_version = Mock(return_value="ff00001d")

        args = self.manager._build_client_args(params)

        assert args == [
            "test.example.com",
            "4433",
            "-v",
            "ff00001d",
            "-l",
            "/logs/client.log",
        ]

    def test_map_version(self):
        """Test version mapping."""
        assert self.manager._map_version("rfc9000") == "1"
        assert self.manager._map_version("draft29") == "ff00001d"
        assert self.manager._map_version("draft27") == "ff00001b"
        assert self.manager._map_version("unknown") == "1"

    def test_generate_run_command_server(self):
        """Test server command generation."""
        command = self.manager.generate_run_command(
            role="server",
            test_mode=True,
        )

        # The command is now built by shlex.quote joining parts
        assert isinstance(command, str)
        assert "testquic_demo" in command
        assert "-c" in command
        assert "-k" in command
        assert "-p" in command
        assert "4443" in command
        assert "--test" in command
        assert "server" in command

    def test_generate_run_command_client(self):
        """Test client command generation."""
        command = self.manager.generate_run_command(
            role="client",
            test_mode=True,
            request_size=1024,
        )

        # The command is now built by shlex.quote joining parts
        assert isinstance(command, str)
        assert "testquic_demo" in command
        assert "localhost" in command
        assert "4443" in command
        assert "-v" in command
        assert "--test" in command
        assert "client" in command
        assert "--size" in command
        assert "1024" in command

    def test_generate_compile_command_default(self):
        """Test default compile command generation."""
        command = self.manager.generate_compile_command()
        assert command == "cmake -DCMAKE_BUILD_TYPE=Release . && make -j$(nproc)"

    def test_generate_compile_command_custom(self):
        """Test compile command with custom options."""
        command = self.manager.generate_compile_command(
            build_type="Debug",
            jobs="4",
        )
        assert command == "cmake -DCMAKE_BUILD_TYPE=Debug . && make -j4"

    def test_generate_pre_compile_command(self):
        """Test pre-compile command generation."""
        command = self.manager.generate_pre_compile_command()
        assert command == ""

    def test_generate_post_compile_command(self):
        """Test post-compile command generation."""
        command = self.manager.generate_post_compile_command()
        assert command == ""

    def test_generate_post_run_command(self):
        """Test post-run command generation."""
        command = self.manager.generate_post_run_command()
        assert command == ""

    def test_get_supported_features(self):
        """Test getting supported features."""
        features = self.manager.get_supported_features()

        assert features["client"] is True
        assert features["server"] is True
        assert features["0rtt"] is True
        assert features["migration"] is True
        assert features["multipath"] is False
        assert features["qlog"] is True

    def test_validate_configuration_valid(self):
        """Test configuration validation with valid config."""
        errors = self.manager.validate_configuration(
            role="client",
            port=4443,
            version="rfc9000",
        )
        assert errors == []

    def test_validate_configuration_invalid_role(self):
        """Test configuration validation with invalid role."""
        errors = self.manager.validate_configuration(
            role="proxy",
            port=4443,
        )
        assert len(errors) == 1
        assert "Invalid role: proxy" in errors[0]

    def test_validate_configuration_invalid_port(self):
        """Test configuration validation with invalid port."""
        errors = self.manager.validate_configuration(
            role="server",
            port=70000,
        )
        assert len(errors) == 1
        assert "Invalid port: 70000" in errors[0]

    def test_validate_configuration_invalid_version(self):
        """Test configuration validation with invalid version."""
        errors = self.manager.validate_configuration(
            role="client",
            version="draft25",
        )
        assert len(errors) == 1
        assert "Unsupported version: draft25" in errors[0]

    def test_validate_configuration_multiple_errors(self):
        """Test configuration validation with multiple errors."""
        errors = self.manager.validate_configuration(
            role="invalid",
            port=0,
            version="unknown",
        )
        assert len(errors) == 3
