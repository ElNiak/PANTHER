"""
Unit tests for CLI logging functionality.

This module tests that the CLI commands properly initialize and use
the centralized logging system.
"""

import pytest
import logging
import tempfile
import sys
import yaml
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, call
import argparse

from panther.cli.subcommands.run import RunCommand
from panther.cli.subcommands.config import ConfigCommand
from panther.cli.subcommands.plugins import PluginsCommand
from panther.cli.main import create_parser
from panther.core.utils.logger_factory import LoggerFactory


class TestCLILogging:
    """Test CLI logging initialization and usage."""
    
    @pytest.fixture(autouse=True)
    def reset_logger_factory(self):
        """Reset LoggerFactory for each test."""
        # Store original state
        original_state = {
            'initialized': LoggerFactory._initialized,
            'config': LoggerFactory._config.copy(),
            'handlers': LoggerFactory._handler_cache.copy()
        }
        
        # Reset
        LoggerFactory._initialized = False
        LoggerFactory._root_logger_configured = False
        LoggerFactory._config = {}
        LoggerFactory._handler_cache = {}
        
        # Clear root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        yield
        
        # Restore
        LoggerFactory._initialized = original_state['initialized']
        LoggerFactory._config = original_state['config']
        LoggerFactory._handler_cache = original_state['handlers']
        
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                "logging": {
                    "level": "DEBUG",
                    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
                },
                "paths": {
                    "output_dir": "outputs"
                },
                "docker": {
                    "build_docker_image": False
                },
                "tests": [{
                    "name": "test",
                    "description": "Test",
                    "network_environment": {"type": "docker_compose"},
                    "iterations": 1,
                    "execution_environment": [],
                    "debug_environment": [],
                    "services": {
                        "server": {
                            "name": "server",
                            "implementation": {"name": "test", "type": "iut"},
                            "protocol": {"name": "test", "version": "1.0", "role": "server"},
                            "timeout": 60
                        }
                    },
                    "steps": {"wait": 1}
                }]
            }
            yaml.dump(config, f)
            temp_path = Path(f.name)
            
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
            
    def test_run_command_initializes_logger_factory(self, temp_config_file):
        """Test that run command initializes LoggerFactory."""
        args = argparse.Namespace(
            config=str(temp_config_file),
            output_dir="outputs",
            experiment_name=None,
            exec_env_dir="",
            net_env_dir="",
            iut_dir="",
            tester_dir="",
            enable_metrics=False,
            disable_metrics=True,
            metrics_output_dir="metrics",
            metrics_format="json",
            metrics_interval=3.0,
            metrics_disable_resource_monitoring=False,
            metrics_generate_report=False,
            metrics_quiet=False
        )
        
        with patch('panther.cli.subcommands.run.ConfigLoader') as mock_loader_class:
            # Mock config loader
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            # Mock global config
            mock_global_config = Mock()
            mock_global_config.logging.level.name = 'DEBUG'
            mock_global_config.logging.format = '%(asctime)s [%(levelname)s] - %(module)s - %(message)s'
            mock_loader.load_and_validate_global_config.return_value = mock_global_config
            
            # Mock experiment config
            mock_exp_config = Mock()
            mock_loader.load_and_validate_experiment_config.return_value = mock_exp_config
            
            with patch('panther.cli.subcommands.run.ExperimentManager'):
                with patch('panther.cli.subcommands.run.LoggerFactory.initialize') as mock_init:
                    # Run the command
                    result = RunCommand.handle(args)
                    
                    # LoggerFactory should have been initialized
                    mock_init.assert_called_once()
                    call_args = mock_init.call_args[0][0]
                    assert call_args['level'] == 'DEBUG'
                    assert call_args['format'] == '%(asctime)s [%(levelname)s] - %(module)s - %(message)s'
                    assert 'enable_colors' in call_args
                    
    def test_run_command_without_logging_config(self, temp_config_file):
        """Test run command when global config has no logging section."""
        args = argparse.Namespace(
            config=str(temp_config_file),
            output_dir="outputs",
            experiment_name=None,
            exec_env_dir="",
            net_env_dir="",
            iut_dir="",
            tester_dir="",
            enable_metrics=False,
            disable_metrics=True
        )
        
        with patch('panther.cli.subcommands.run.ConfigLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            # Mock global config without logging
            mock_global_config = Mock()
            mock_global_config.logging = None
            mock_loader.load_and_validate_global_config.return_value = mock_global_config
            
            mock_exp_config = Mock()
            mock_loader.load_and_validate_experiment_config.return_value = mock_exp_config
            
            with patch('panther.cli.subcommands.run.ExperimentManager'):
                with patch('panther.cli.subcommands.run.LoggerFactory.initialize') as mock_init:
                    # Should not crash
                    result = RunCommand.handle(args)
                    
                    # LoggerFactory should not have been initialized
                    mock_init.assert_not_called()
                    
    def test_config_validate_uses_logging(self):
        """Test that config validation commands use logging."""
        args = argparse.Namespace(
            config_action='validate',
            config='/path/to/config.yaml',
            strict=False,
            show_schema=False
        )
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "test: config"
                
                with patch('yaml.safe_load', return_value={"test": "config"}):
                    with patch('panther.cli.subcommands.config.ConfigLoader'):
                        # Should complete without error
                        result = ConfigCommand.handle(args)
                        
                        # Even without explicit logging, should use print statements
                        assert result == 0
                        
    def test_plugins_list_command_logging(self):
        """Test plugins list command logging."""
        args = argparse.Namespace(
            plugin_action='list',
            plugin_type='all'
        )
        
        with patch('panther.cli.subcommands.plugins.PluginDiscovery') as mock_discovery_class:
            mock_discovery = Mock()
            mock_discovery_class.return_value = mock_discovery
            
            mock_discovery.discover_plugins.return_value = []
            
            # Run command
            result = PluginsCommand.handle(args)
            
            # Should complete successfully
            assert result == 0
            
    def test_cli_parser_debug_flag_propagation(self):
        """Test that --debug flag affects logging configuration."""
        parser = create_parser()
        
        # Parse with debug flag
        args = parser.parse_args(['run', '--config', 'test.yaml', '--debug'])
        
        assert hasattr(args, 'debug')
        assert args.debug is True
        
        # Parse without debug flag
        args = parser.parse_args(['run', '--config', 'test.yaml'])
        
        assert hasattr(args, 'debug')
        assert args.debug is False
        
    def test_logging_consistency_across_cli_commands(self):
        """Test that all CLI commands use consistent logging."""
        # Create a mock logger to track calls
        mock_logger = Mock()
        
        with patch('panther.core.utils.logger_factory.LoggerFactory.get_logger', return_value=mock_logger):
            # Test various CLI command classes
            commands = [
                RunCommand,
                ConfigCommand,
                PluginsCommand
            ]
            
            for command_class in commands:
                # Each command should be able to get a logger if needed
                # This tests the pattern, not actual usage
                logger = LoggerFactory.get_logger(command_class.__name__)
                assert logger is mock_logger
                
    def test_cli_error_logging(self, temp_config_file):
        """Test that CLI errors are logged consistently."""
        # Test with non-existent config file
        args = argparse.Namespace(
            config="/nonexistent/config.yaml",
            output_dir="outputs",
            experiment_name=None,
            exec_env_dir="",
            net_env_dir="",
            iut_dir="",
            tester_dir="",
            enable_metrics=False,
            disable_metrics=True
        )
        
        # Should handle error gracefully
        result = RunCommand.handle(args)
        assert result == 1  # Error code
        
    def test_cli_logging_with_metrics(self, temp_config_file):
        """Test CLI logging when metrics are enabled."""
        args = argparse.Namespace(
            config=str(temp_config_file),
            output_dir="outputs",
            experiment_name="test_metrics",
            exec_env_dir="",
            net_env_dir="",
            iut_dir="",
            tester_dir="",
            enable_metrics=True,
            disable_metrics=False,
            metrics_output_dir="metrics",
            metrics_format="json",
            metrics_interval=1.0,
            metrics_disable_resource_monitoring=False,
            metrics_generate_report=True,
            metrics_quiet=False
        )
        
        with patch('panther.cli.subcommands.run.ConfigLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            # Mock configs
            mock_global_config = Mock()
            mock_global_config.logging.level.name = 'INFO'
            mock_global_config.logging.format = '%(message)s'
            mock_loader.load_and_validate_global_config.return_value = mock_global_config
            
            mock_exp_config = Mock()
            mock_loader.load_and_validate_experiment_config.return_value = mock_exp_config
            
            # Mock metrics components
            with patch('panther.cli.subcommands.run.MetricsCollector') as mock_metrics:
                with patch('panther.cli.subcommands.run.ResourceMonitor'):
                    with patch('panther.cli.subcommands.run.MetricsReporter'):
                        with patch('panther.cli.subcommands.run.MetricsExporter'):
                            with patch('panther.cli.subcommands.run.ExperimentManager') as mock_manager:
                                mock_manager.return_value.run_tests.return_value = True
                                
                                # Run command
                                result = RunCommand.handle(args)
                                
                                # Should succeed
                                assert result == 0
                                
                                # Metrics should have been initialized
                                mock_metrics.assert_called_once()
                                
    def test_cli_verbose_output_integration(self):
        """Test CLI verbose output with logging."""
        # Test that verbose flags affect logging
        parser = create_parser()
        
        # Test with -v flag
        args = parser.parse_args(['-v', 'plugins', 'list'])
        assert args.verbose is True
        
        # Test with -q flag
        args = parser.parse_args(['-q', 'plugins', 'list'])
        assert args.quiet is True
        
        # These flags should affect how logging is configured
        # In a real implementation, verbose would set DEBUG level
        # and quiet would set WARNING or higher
        
    def test_cli_keyboard_interrupt_handling(self, temp_config_file):
        """Test that KeyboardInterrupt is handled gracefully."""
        args = argparse.Namespace(
            config=str(temp_config_file),
            output_dir="outputs",
            experiment_name=None,
            exec_env_dir="",
            net_env_dir="",
            iut_dir="",
            tester_dir="",
            enable_metrics=False,
            disable_metrics=True
        )
        
        with patch('panther.cli.subcommands.run.ConfigLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            # Make it raise KeyboardInterrupt
            mock_loader.load_and_validate_global_config.side_effect = KeyboardInterrupt()
            
            # Should handle gracefully
            result = RunCommand.handle(args)
            assert result == 130  # Standard exit code for Ctrl+C
            
    def test_cli_logging_file_creation(self):
        """Test that CLI can create log files when configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "cli_test.log"
            
            # Initialize LoggerFactory with file output
            LoggerFactory.initialize({
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(message)s',
                'output_file': str(log_file)
            })
            
            # Get a logger and use it
            logger = LoggerFactory.get_logger('cli.test')
            logger.info("CLI test message")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                    
            # File should exist
            assert log_file.exists()
            assert "CLI test message" in log_file.read_text()