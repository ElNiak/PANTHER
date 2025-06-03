import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

import yaml
import shlex
from panther.plugins.services.services_interface import quote_shell, quote_yaml
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.config.config_experiment_schema import ServiceConfig

# Import the service implementations to test
from panther.plugins.services.iut.quic.aioquic.aioquic import AioquicServiceManager
from panther.plugins.services.iut.quic.aioquic.config_schema import AioquicConfig
from panther.plugins.services.iut.quic.lsquic.lsquic import LsquicServiceManager
from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig
from panther.plugins.services.iut.quic.quant.quant import QuantServiceManager
from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig


@pytest.fixture
def mock_protocol_config():
    """Create a mock protocol config for testing."""
    protocol_config = MagicMock(spec=ProtocolConfig)
    protocol_config.name = "quic"
    protocol_config.version = "draft-29"
    protocol_config.role = RoleEnum.server
    protocol_config.target = "127.0.0.1"
    return protocol_config


@pytest.fixture
def mock_aioquic_service_config(mock_protocol_config):
    """Create a mock aioquic service config for testing."""
    service_config = MagicMock(spec=AioquicConfig)
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
            "key_file": "/opt/aioquic/tests/ssl_key.pem"
        },
        "protocol": {
            "alpn": {
                "param": "--alpn",
                "value": "h3-29"
            },
            "additional_parameters": "--host 0.0.0.0 --quic-log /app/logs/quic-log"
        },
        "network": {
            "port": 4433,
            "interface": {
                "param": "--interface",
                "value": "0.0.0.0"
            }
        },
        "logging": {
            "log_path": "/app/logs/aioquic_server.log",
            "err_path": "/app/logs/aioquic_server_error.log"
        }
    }
    
    return service_config


@pytest.fixture
def mock_lsquic_service_config(mock_protocol_config):
    """Create a mock lsquic service config for testing."""
    service_config = MagicMock(spec=LsquicConfig)
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
            "key_file": "/opt/lsquic/bin/certs/server-key.pem"
        },
        "protocol": {
            "alpn": {
                "param": "-a",
                "value": "h3-29"
            },
            "additional_parameters": "-l debug -o no_delay=1"
        },
        "network": {
            "port": 4433,
            "interface": {
                "param": "-i",
                "value": "0.0.0.0"
            }
        },
        "logging": {
            "log_path": "/app/logs/lsquic_server.log",
            "err_path": "/app/logs/lsquic_server_error.log"
        },
        "environment": {
            "LSQUIC_LOG_LEVEL": "debug"
        }
    }
    
    return service_config


class TestStructuredCommandGenerationQuicIUT:
    """Test the structured command generation for QUIC IUT plugins."""
    
    def test_aioquic_structured_commands_server(self, mock_aioquic_service_config):
        """Test structured command generation for the aioquic server."""
        service_manager = AioquicServiceManager(
            mock_aioquic_service_config,
            "iut",
            mock_aioquic_service_config.protocol,
            "aioquic"
        )
        
        # Test command argument generation
        cmd_args = service_manager.generate_deployment_commands()
        assert isinstance(cmd_args, list), "Command arguments should be a list"
        
        # Verify command arguments contain expected elements
        assert "-c" in cmd_args
        assert "/opt/aioquic/tests/ssl_cert.pem" in cmd_args
        assert "--alpn" in cmd_args
        assert "h3-29" in cmd_args
        
        # Test that command args with spaces are properly handled
        assert "--quic-log" in cmd_args
        assert "/app/logs/quic-log" in cmd_args
        
        # Test run command
        run_cmd = service_manager.generate_run_command()
        assert isinstance(run_cmd, dict)
        assert "working_dir" in run_cmd
        assert "command_binary" in run_cmd
        assert "command_args" in run_cmd
        assert "command_env" in run_cmd
        assert isinstance(run_cmd["command_env"], dict)
        assert "PYTHONPATH" in run_cmd["command_env"]
    
    @patch('subprocess.run')  
    def test_lsquic_structured_commands_server(self, mock_subprocess, mock_lsquic_service_config):
        """Test structured command generation for the lsquic server."""
        service_manager = LsquicServiceManager(
            mock_lsquic_service_config,
            "iut",
            mock_lsquic_service_config.protocol,
            "lsquic"
        )
        
        # Test command argument generation
        cmd_args = service_manager.generate_deployment_commands()
        assert isinstance(cmd_args, list), "Command arguments should be a list"
        
        # Verify command arguments contain expected elements
        assert "-c" in cmd_args
        assert "/opt/lsquic/bin/certs/server-cert.pem" in cmd_args
        assert "-a" in cmd_args
        assert "h3-29" in cmd_args
        
        # Test that command args with spaces are properly handled
        assert "-l" in cmd_args
        assert "debug" in cmd_args
        
        # Test server address parameter
        assert "-s" in cmd_args
        assert "127.0.0.1:4433" in cmd_args
        
        # Test run command
        run_cmd = service_manager.generate_run_command()
        assert isinstance(run_cmd, dict)
        assert "working_dir" in run_cmd
        assert "command_binary" in run_cmd
        assert "command_args" in run_cmd
        assert "command_env" in run_cmd
        assert isinstance(run_cmd["command_env"], dict)
        assert "LD_LIBRARY_PATH" in run_cmd["command_env"]
        assert "LSQUIC_LOG_LEVEL" in run_cmd["command_env"]
        assert run_cmd["command_env"]["LSQUIC_LOG_LEVEL"] == "debug"
        
    def test_command_quoting_functions(self):
        """Test the command quoting functions."""
        # Test shell quoting
        test_string = "arg with spaces and 'quotes'"
        quoted = quote_shell(test_string)
        assert "'" in quoted
        assert ' ' in test_string and ' ' not in quoted.strip("'")
        
        # Test yaml quoting
        test_string = "value with: yaml special chars"
        quoted = quote_yaml(test_string)
        assert isinstance(quoted, str)
        
    def test_build_command_args_with_special_chars(self, mock_aioquic_service_config):
        """Test build_command_args with strings containing special characters."""
        service_manager = AioquicServiceManager(
            mock_aioquic_service_config,
            "iut",
            mock_aioquic_service_config.protocol,
            "aioquic"
        )
        
        # Test with string containing spaces and special characters
        special_args = '--test "value with spaces" --option=test;echo hello'
        args_list = service_manager.build_command_args(special_args)
        
        assert isinstance(args_list, list)
        # Check that the string was properly split
        assert len(args_list) > 1
        # Check that quoted parts stay together
        assert '"value with spaces"' in ' '.join(args_list) or "'value with spaces'" in ' '.join(args_list)
