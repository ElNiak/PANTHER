import os
from unittest.mock import MagicMock, patch

import pytest

from panther.config.core.models import ProtocolRole
from panther.plugins.services.iut.quic.quiche.quiche import QuicheServiceManager


@pytest.fixture
def mock_service_config():
    config = MagicMock()
    config.name = "test_quiche_service"
    config.protocol.name = "quic"
    config.protocol.version = "version_1"
    config.protocol.role = ProtocolRole.CLIENT
    config.protocol.target = "test_server"
    config.implementation.version.client.binary.name = "quiche-client"
    config.implementation.version.client.binary.dir = "/opt/quiche"
    config.implementation.version.client.certificates = {
        "cert_param": "--cert",
        "cert_file": "/path/to/cert.pem",
        "key_param": "--key",
        "key_file": "/path/to/key.pem",
    }
    config.implementation.version.client.protocol = {
        "additional_parameters": "--no-verify"
    }
    config.implementation.version.client.network = {
        "port": 4433,
        "interface": {"param": "--interface", "value": "eth0"},
    }
    config.implementation.version.client.initial_version = "1"
    config.implementation.version.client.logging = {
        "log_path": "/app/logs/client.log",
        "err_path": "/app/logs/client.err",
    }
    config.timeout = 30
    return config


@pytest.fixture
def mock_protocol_config():
    protocol = MagicMock()
    protocol.name = "quic"
    protocol.version = "version_1"
    protocol.role = ProtocolRole.CLIENT
    protocol.target = "test_server"
    return protocol


def test_structured_command_generation(mock_service_config, mock_protocol_config):
    """Test that structured command generation produces a valid command string."""
    # Create the service manager
    with patch("subprocess.run"):
        manager = QuicheServiceManager(
            service_config_to_test=mock_service_config,
            service_type="iut",
            protocol=mock_protocol_config,
            implementation_name="quiche",
        )

    # Generate the command
    command = manager.generate_deployment_commands()

    # Quiche generate_deployment_commands returns a simple string for client role
    assert isinstance(command, str)
    assert "quiche-client" in command
    assert "--http3" in command
    assert "localhost:4443" in command


def test_structured_command_fallback(mock_service_config, mock_protocol_config):
    """Test that generate_deployment_commands produces expected output for both roles."""
    with patch("subprocess.run"):
        manager = QuicheServiceManager(
            service_config_to_test=mock_service_config,
            service_type="iut",
            protocol=mock_protocol_config,
            implementation_name="quiche",
        )

    # Client role (default from mock)
    command = manager.generate_deployment_commands()
    assert "quiche-client" in command

    # Test server role
    manager.role = "server"
    command = manager.generate_deployment_commands()
    assert "quiche-server" in command
    assert "--listen" in command
