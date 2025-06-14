import pytest
import os
from unittest.mock import patch, MagicMock
from panther.plugins.services.iut.quic.quiche.quiche import QuicheServiceManager
from panther.plugins.protocols.config_schema import RoleEnum


@pytest.fixture
def mock_service_config():
    config = MagicMock()
    config.name = "test_quiche_service"
    config.protocol.name = "quic"
    config.protocol.version = "version_1"
    config.protocol.role = RoleEnum.client
    config.protocol.target = "test_server"
    config.implementation.version.client.binary.name = "quiche-client"
    config.implementation.version.client.binary.dir = "/opt/quiche"
    config.implementation.version.client.certificates = {
        "cert_param": "--cert",
        "cert_file": "/path/to/cert.pem",
        "key_param": "--key",
        "key_file": "/path/to/key.pem",
    }
    config.implementation.version.client.protocol = {"additional_parameters": "--no-verify"}
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
    protocol.role = RoleEnum.client
    protocol.target = "test_server"
    return protocol


def test_structured_command_generation(mock_service_config, mock_protocol_config):
    """Test that structured command generation properly escapes special characters."""
    # Create a service manager with paths that contain special characters
    service_config = mock_service_config
    service_config.implementation.version.client.certificates["cert_file"] = (
        "/path/with spaces/cert$.pem"
    )
    service_config.implementation.version.client.certificates["key_file"] = (
        "/path/with'quote/key~.pem"
    )

    # Create the service manager
    with patch("subprocess.run"):
        manager = QuicheServiceManager(
            service_config_to_test=service_config,
            service_type="iut",
            protocol=mock_protocol_config,
            implementation_name="quiche",
        )

    # Make sure the template exists (skips test if not)
    template_path = os.path.join(
        manager.templates_dir, f"{str(manager.role.name)}_command_structured.jinja"
    )
    if not os.path.exists(template_path):
        pytest.skip(f"Structured template not found at {template_path}")

    # Generate the command
    command = manager.generate_deployment_commands()

    # Verify that special characters are properly escaped
    assert "'/path/with spaces/cert$.pem'" in command or '"/path/with spaces/cert$.pem"' in command
    assert "'/path/with'\\''quote/key~.pem'" in command or '"/path/with\'quote/key~.pem"' in command


def test_structured_command_fallback(mock_service_config, mock_protocol_config):
    """Test that the service falls back to the original template if the structured one fails."""
    with patch("subprocess.run"):
        manager = QuicheServiceManager(
            service_config_to_test=mock_service_config,
            service_type="iut",
            protocol=mock_protocol_config,
            implementation_name="quiche",
        )

    # Mock the render_template_with_structured_args method to raise an exception
    with patch.object(
        manager, "render_template_with_structured_args", side_effect=Exception("Test error")
    ):
        # Also mock the render_commands method to return a known value
        with patch.object(manager, "render_commands", return_value="fallback_command"):
            command = manager.generate_deployment_commands()
            assert command == "fallback_command"
