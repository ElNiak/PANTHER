import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Add the parent directory to sys.path to import the quiche module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from panther.plugins.services.iut.quic.quiche.quiche import QuicheServiceManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class TestQuicheTemplateRendering:
    """Test class for Quiche template rendering with structured arguments."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        mock_config = MagicMock()
        mock_config.name = "quiche-test"
        mock_config.timeout = 60
        mock_config.protocol.target = "test-server"
        
        # Server config
        mock_config.implementation.version.server.binary.name = "server_binary"
        mock_config.implementation.version.server.binary.dir = "/opt/quiche/bin"
        mock_config.implementation.version.server.certificates.cert_param = "--cert"
        mock_config.implementation.version.server.certificates.cert_file = "/certs/cert.pem"
        mock_config.implementation.version.server.certificates.key_param = "--key"
        mock_config.implementation.version.server.certificates.key_file = "/certs/key.pem"
        mock_config.implementation.version.server.protocol.additional_parameters = "--early-data"
        mock_config.implementation.version.server.network.port = "4433"
        mock_config.implementation.version.server.network.destination = {"param": "-a", "value": "0.0.0.0"}
        mock_config.implementation.version.server.network.interface = {"param": "-i", "value": "eth0"}
        mock_config.implementation.version.server.logging.log_path = "/logs/server.log"
        mock_config.implementation.version.server.logging.err_path = "/logs/server.err"
        
        # Client config
        mock_config.implementation.version.client.binary.name = "client_binary"
        mock_config.implementation.version.client.binary.dir = "/opt/quiche/bin"
        mock_config.implementation.version.client.certificates.cert_param = "--cert"
        mock_config.implementation.version.client.certificates.cert_file = "/certs/cert.pem"
        mock_config.implementation.version.client.certificates.key_param = "--key"
        mock_config.implementation.version.client.certificates.key_file = "/certs/key.pem"
        mock_config.implementation.version.client.protocol.additional_parameters = "--no-verify"
        mock_config.implementation.version.client.network.port = "4433"
        mock_config.implementation.version.client.network.interface = {"param": "-i", "value": "eth0"}
        mock_config.implementation.version.client.initial_version = "0xff000022"
        mock_config.implementation.version.client.logging.log_path = "/logs/client.log"
        mock_config.implementation.version.client.logging.err_path = "/logs/client.err"
        
        return mock_config
    
    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory for testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create client template
        client_template = os.path.join(temp_dir, "client_command_structured.jinja")
        with open(client_template, 'w') as f:
            f.write('''#!/bin/bash
{{ binary.name }} \\
{% for arg in command_args %}
  {{ arg|quote_shell }} {% if not loop.last %}\\{% endif %}
{% endfor %}''')
            
        # Create server template
        server_template = os.path.join(temp_dir, "server_command_structured.jinja")
        with open(server_template, 'w') as f:
            f.write('''#!/bin/bash
{{ binary.name }} \\
{% for arg in command_args %}
  {{ arg|quote_shell }} {% if not loop.last %}\\{% endif %}
{% endfor %}''')
            
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @patch('subprocess.run')
    def test_server_command_rendering(self, mock_run, mock_config, temp_template_dir):
        """Test rendering of server commands with structured arguments."""
        # Setup
        mock_protocol = MagicMock(spec=ProtocolConfig)
        mock_protocol.name = "quic"
        mock_protocol.role = RoleEnum.server
        
        # Create service manager with mock templates directory
        service_manager = QuicheServiceManager(mock_config, "iut", mock_protocol, "quiche")
        service_manager.templates_dir = temp_template_dir
        service_manager.jinja_env.loader.searchpath = [temp_template_dir]
        
        # Test
        command = service_manager.generate_deployment_commands()
        
        # Assertions
        assert "server_binary" in command
        assert "--cert '/certs/cert.pem'" in command
        assert "--key '/certs/key.pem'" in command
        assert "-a '0.0.0.0:4433'" in command
        assert "-i 'eth0'" in command
        assert "> '/logs/server.log'" in command
        assert "2> '/logs/server.err'" in command

    @patch('subprocess.run')
    def test_client_command_rendering(self, mock_run, mock_config, temp_template_dir):
        """Test rendering of client commands with structured arguments."""
        # Setup
        mock_protocol = MagicMock(spec=ProtocolConfig)
        mock_protocol.name = "quic"
        mock_protocol.role = RoleEnum.client
        
        # Create service manager with mock templates directory
        service_manager = QuicheServiceManager(mock_config, "iut", mock_protocol, "quiche")
        service_manager.templates_dir = temp_template_dir
        service_manager.jinja_env.loader.searchpath = [temp_template_dir]
        
        # Test
        command = service_manager.generate_deployment_commands()
        
        # Assertions
        assert "client_binary" in command
        assert "--cert '/certs/cert.pem'" in command
        assert "--key '/certs/key.pem'" in command
        assert "--no-verify" in command
        assert "-i 'eth0'" in command
        assert "--wire-version" in command
        assert "'0xff000022'" in command
        assert "https://test-server:4433/index.html" in command
        assert "> '/logs/client.log'" in command
        assert "2> '/logs/client.err'" in command
    
    @patch('subprocess.run')
    def test_special_characters_escaping(self, mock_run, mock_config, temp_template_dir):
        """Test proper escaping of special characters in command arguments."""
        # Setup
        mock_protocol = MagicMock(spec=ProtocolConfig)
        mock_protocol.name = "quic"
        mock_protocol.role = RoleEnum.client
        
        # Add special characters to test escaping
        mock_config.implementation.version.client.protocol.additional_parameters = "--data 'special $characters & | ; \"quotes\"'"
        
        # Create service manager with mock templates directory
        service_manager = QuicheServiceManager(mock_config, "iut", mock_protocol, "quiche")
        service_manager.templates_dir = temp_template_dir
        service_manager.jinja_env.loader.searchpath = [temp_template_dir]
        
        # Test
        command = service_manager.generate_deployment_commands()
        
        # Assertions - the special characters should be properly quoted
        assert "'--data 'special $characters & | ; \"quotes\"''" in command or "--data\\ \\'special\\ \\$characters\\ \\&\\ \\|\\ \\;\\ \\\"quotes\\\"\\''" in command
