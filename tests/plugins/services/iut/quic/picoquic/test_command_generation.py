import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Add the parent directory to sys.path to import the picoquic module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from panther.plugins.services.iut.quic.picoquic.picoquic import PicoquicServiceManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class TestPicoquicTemplateRendering:
    """Test class for Picoquic template rendering with structured arguments."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        mock_config = MagicMock()
        mock_config.name = "picoquic-test"
        mock_config.timeout = 60
        mock_config.protocol.target = "test-server"
        
        # Server config
        mock_config.implementation.version.server.binary.name = "picoquicdemo"
        mock_config.implementation.version.server.binary.dir = "/opt/picoquic"
        mock_config.implementation.version.server.certificates.cert_param = "-c"
        mock_config.implementation.version.server.certificates.cert_file = "/certs/cert.pem"
        mock_config.implementation.version.server.certificates.key_param = "-k"
        mock_config.implementation.version.server.certificates.key_file = "/certs/key.pem"
        mock_config.implementation.version.server.protocol.alpn.param = "-a"
        mock_config.implementation.version.server.protocol.alpn.value = "hq-29"
        mock_config.implementation.version.server.protocol.additional_parameters = "-l /logs/qlog"
        mock_config.implementation.version.server.network.port = "4433"
        mock_config.implementation.version.server.network.interface = {"param": "-i", "value": "eth0"}
        mock_config.implementation.version.server.logging.log_path = "/logs/server.log"
        mock_config.implementation.version.server.logging.err_path = "/logs/server.err"
        
        # Client config
        mock_config.implementation.version.client.binary.name = "picoquicdemo"
        mock_config.implementation.version.client.binary.dir = "/opt/picoquic"
        mock_config.implementation.version.client.certificates.cert_param = "-c"
        mock_config.implementation.version.client.certificates.cert_file = "/certs/cert.pem"
        mock_config.implementation.version.client.certificates.key_param = "-k"
        mock_config.implementation.version.client.certificates.key_file = "/certs/key.pem"
        mock_config.implementation.version.client.ticket_file = {"param": "-t", "file": "/tmp/ticket.bin"}
        mock_config.implementation.version.client.protocol.alpn.param = "-a"
        mock_config.implementation.version.client.protocol.alpn.value = "hq-29"
        mock_config.implementation.version.client.protocol.additional_parameters = "-l /logs/qlog"
        mock_config.implementation.version.client.network.port = "4433"
        mock_config.implementation.version.client.network.interface = {"param": "-i", "value": "eth0"}
        mock_config.implementation.version.client.initial_version = "0xff00001d"
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
    
    def test_server_command_rendering(self, mock_config, temp_template_dir):
        """Test rendering of server commands with structured arguments."""
        # Setup
        mock_protocol = MagicMock(spec=ProtocolConfig)
        mock_protocol.name = "quic"
        mock_protocol.role = RoleEnum.server
        
        # Create service manager with mock templates directory
        service_manager = PicoquicServiceManager(mock_config, "iut", mock_protocol, "picoquic")
        service_manager.templates_dir = temp_template_dir
        service_manager.jinja_env.loader.searchpath = [temp_template_dir]
        
        # Test
        command = service_manager.generate_deployment_commands()
        
        # Assertions
        assert "picoquicdemo" in command
        assert "-c '/certs/cert.pem'" in command
        assert "-k '/certs/key.pem'" in command
        assert "-a 'hq-29'" in command
        assert "-l '/logs/qlog'" in command
        assert "-p '4433'" in command
        assert "-i 'eth0'" in command
        assert "> '/logs/server.log'" in command
        assert "2> '/logs/server.err'" in command

    def test_client_command_rendering(self, mock_config, temp_template_dir):
        """Test rendering of client commands with structured arguments."""
        # Setup
        mock_protocol = MagicMock(spec=ProtocolConfig)
        mock_protocol.name = "quic"
        mock_protocol.role = RoleEnum.client
        
        # Create service manager with mock templates directory
        service_manager = PicoquicServiceManager(mock_config, "iut", mock_protocol, "picoquic")
        service_manager.templates_dir = temp_template_dir
        service_manager.jinja_env.loader.searchpath = [temp_template_dir]
        
        # Test
        command = service_manager.generate_deployment_commands()
        
        # Assertions
        assert "picoquicdemo" in command
        assert "-c '/certs/cert.pem'" in command
        assert "-k '/certs/key.pem'" in command
        assert "-t '/tmp/ticket.bin'" in command
        assert "-a 'hq-29'" in command
        assert "-l '/logs/qlog'" in command
        assert "-i 'eth0'" in command
        assert "-v '0xff00001d'" in command
        assert "'test-server'" in command
        assert "'4433'" in command
        assert "> '/logs/client.log'" in command
        assert "2> '/logs/client.err'" in command
    
    def test_special_characters_escaping(self, mock_config, temp_template_dir):
        """Test proper escaping of special characters in command arguments."""
        # Setup
        mock_protocol = MagicMock(spec=ProtocolConfig)
        mock_protocol.name = "quic"
        mock_protocol.role = RoleEnum.client
        
        # Add special characters to test escaping
        mock_config.implementation.version.client.protocol.additional_parameters = "--data 'special $characters & | ; \"quotes\"'"
        
        # Create service manager with mock templates directory
        service_manager = PicoquicServiceManager(mock_config, "iut", mock_protocol, "picoquic")
        service_manager.templates_dir = temp_template_dir
        service_manager.jinja_env.loader.searchpath = [temp_template_dir]
        
        # Test
        command = service_manager.generate_deployment_commands()
        
        # Assertions - the special characters should be properly quoted
        assert "'--data 'special $characters & | ; \"quotes\"''" in command or "--data\\ \\'special\\ \\$characters\\ \\&\\ \\|\\ \\;\\ \\\"quotes\\\"\\''" in command
