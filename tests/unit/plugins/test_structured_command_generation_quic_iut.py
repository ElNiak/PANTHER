from unittest.mock import MagicMock, patch

import pytest

from panther.config.core.models import ProtocolConfig, ProtocolRole

# Import the service implementations to test
from panther.plugins.services.iut.quic.aioquic.aioquic import AioquicServiceManager
from panther.plugins.services.iut.quic.aioquic.config_schema import AioquicConfig
from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig
from panther.plugins.services.iut.quic.lsquic.lsquic import LsquicServiceManager
from panther.plugins.services.services_interface import quote_shell, quote_yaml


@pytest.fixture
def mock_protocol_config():
    """Create a mock protocol config for testing."""
    protocol_config = MagicMock(spec=ProtocolConfig)
    protocol_config.name = "quic"
    protocol_config.version = "draft-29"
    protocol_config.role = ProtocolRole.SERVER
    protocol_config.target = "127.0.0.1"
    return protocol_config


@pytest.fixture
def mock_aioquic_service_config(mock_protocol_config):
    """Create a mock aioquic service config for testing."""
    service_config = MagicMock()
    service_config.name = "aioquic-server"
    service_config.protocol = mock_protocol_config
    service_config.timeout = 60

    # Mock implementation version structure
    service_config.implementation.version.server = {
        "binary": {"name": "python3", "dir": "/opt/aioquic"},
        "certificates": {
            "cert_param": "-c",
            "cert_file": "/opt/aioquic/tests/ssl_cert.pem",
            "key_param": "-k",
            "key_file": "/opt/aioquic/tests/ssl_key.pem",
        },
        "protocol": {
            "alpn": {"param": "--alpn", "value": "h3-29"},
            "additional_parameters": "--host 0.0.0.0 --quic-log /app/logs/quic-log",
        },
        "network": {
            "port": 4433,
            "interface": {"param": "--interface", "value": "0.0.0.0"},
        },
        "logging": {
            "log_path": "/app/logs/aioquic_server.log",
            "err_path": "/app/logs/aioquic_server_error.log",
        },
    }

    return service_config


@pytest.fixture
def mock_lsquic_service_config(mock_protocol_config):
    """Create a mock lsquic service config for testing."""
    service_config = MagicMock()
    service_config.name = "lsquic-server"
    service_config.protocol = mock_protocol_config
    service_config.timeout = 60

    # Mock implementation version structure
    service_config.implementation.version.server = {
        "binary": {"name": "http_server", "dir": "/opt/lsquic/bin"},
        "certificates": {
            "cert_param": "-c",
            "cert_file": "/opt/lsquic/bin/certs/server-cert.pem",
            "key_param": "-k",
            "key_file": "/opt/lsquic/bin/certs/server-key.pem",
        },
        "protocol": {
            "alpn": {"param": "-a", "value": "h3-29"},
            "additional_parameters": "-l debug -o no_delay=1",
        },
        "network": {"port": 4433, "interface": {"param": "-i", "value": "0.0.0.0"}},
        "logging": {
            "log_path": "/app/logs/lsquic_server.log",
            "err_path": "/app/logs/lsquic_server_error.log",
        },
        "environment": {"LSQUIC_LOG_LEVEL": "debug"},
    }

    return service_config


class TestStructuredCommandGenerationQuicIUT:
    """Test the structured command generation for QUIC IUT plugins."""

    def test_aioquic_structured_commands_server(self, mock_aioquic_service_config):
        """Test structured command generation for the aioquic server."""
        # The refactored AioquicServiceManager constructor doesn't match the
        # base class chain; test its methods by constructing via __new__ and
        # setting needed attributes directly.
        service_manager = AioquicServiceManager.__new__(AioquicServiceManager)
        service_manager.service_config_to_test = mock_aioquic_service_config
        service_manager.service_config = mock_aioquic_service_config
        service_manager.service_name = mock_aioquic_service_config.name
        service_manager.service_protocol = mock_aioquic_service_config.protocol
        service_manager.role = "server"
        service_manager.implementation_name = "aioquic"
        service_manager.global_config = None
        service_manager._plugin_config = None
        service_manager._logger = MagicMock()
        service_manager._quic_logger = MagicMock()
        service_manager.event_emitter = None

        # Test that deployment commands return a string
        deploy_cmd = service_manager.generate_deployment_commands()
        assert isinstance(deploy_cmd, str)
        assert "aioquic" in deploy_cmd or "python" in deploy_cmd

    @patch("subprocess.run")
    def test_lsquic_structured_commands_server(
        self, mock_subprocess, mock_lsquic_service_config
    ):
        """Test structured command generation for the lsquic server."""
        service_manager = LsquicServiceManager.__new__(LsquicServiceManager)
        service_manager.service_config_to_test = mock_lsquic_service_config
        service_manager.service_config = mock_lsquic_service_config
        service_manager.service_name = mock_lsquic_service_config.name
        service_manager.service_protocol = mock_lsquic_service_config.protocol
        service_manager.role = "server"
        service_manager.implementation_name = "lsquic"
        service_manager.global_config = None
        service_manager._plugin_config = None
        service_manager._logger = MagicMock()
        service_manager._quic_logger = MagicMock()
        service_manager.event_emitter = None

        # Test that deployment commands return a string
        deploy_cmd = service_manager.generate_deployment_commands()
        assert isinstance(deploy_cmd, str)
        # lsquic server returns "http_server -s /var/www -p 4443"
        assert "http_server" in deploy_cmd

    def test_command_quoting_functions(self):
        """Test the command quoting functions."""
        import shlex

        # Test shell quoting
        test_string = "arg with spaces and 'quotes'"
        quoted = quote_shell(test_string)
        # shlex.quote wraps strings with special chars; verify round-trip
        assert shlex.quote(test_string) == quoted
        # Verify the quoted string is not identical to the original (it is quoted)
        assert quoted != test_string

        # Test yaml quoting
        test_string = "value with: yaml special chars"
        quoted = quote_yaml(test_string)
        assert isinstance(quoted, str)

    def test_build_command_args_with_special_chars(self, mock_aioquic_service_config):
        """Test build_command_args with strings containing special characters."""
        service_manager = AioquicServiceManager.__new__(AioquicServiceManager)
        service_manager.service_config_to_test = mock_aioquic_service_config
        service_manager._logger = MagicMock()
        service_manager.event_emitter = None

        # Test with string containing spaces and special characters
        special_args = '--test "value with spaces" --option=test;echo hello'
        args_list = service_manager.build_command_args(special_args)

        assert isinstance(args_list, list)
        # Check that the string was properly split
        assert len(args_list) > 1
        # shlex.split will parse quoted parts as single args
        assert "value with spaces" in args_list
