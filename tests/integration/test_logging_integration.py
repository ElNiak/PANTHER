"""
Integration tests for PANTHER logging system.

This module tests end-to-end logging consistency across multiple components,
configuration propagation, and log file creation.
"""

import pytest
import logging
import tempfile
import time
import yaml
from pathlib import Path
from unittest.mock import patch, Mock
import subprocess
import sys

from panther.core.utils.logger_factory import LoggerFactory
from panther.core.utils.logging_mixin import LoggerMixin
from panther.config.config_manager import ConfigLoader
from panther.core.experiment_manager import ExperimentManager
from panther.core.observer.impl.logger_observer import LoggerObserver
from panther.core.observer.management.event_manager import EventManager


class TestComponent(LoggerMixin):
    """Test component that uses LoggerMixin."""
    
    def do_work(self):
        """Simulate some work with logging."""
        self.log_operation_start("processing")
        time.sleep(0.01)  # Simulate work
        self.log_operation_complete("processing", items=10)


class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    @pytest.fixture(autouse=True)
    def reset_logging(self):
        """Reset logging system for each test."""
        # Store original state
        original_factory_state = {
            'initialized': LoggerFactory._initialized,
            'config': LoggerFactory._config.copy(),
            'handlers': LoggerFactory._handler_cache.copy()
        }
        
        # Reset LoggerFactory
        LoggerFactory._initialized = False
        LoggerFactory._root_logger_configured = False
        LoggerFactory._config = {}
        LoggerFactory._handler_cache = {}
        
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        yield
        
        # Restore original state
        LoggerFactory._initialized = original_factory_state['initialized']
        LoggerFactory._config = original_factory_state['config']
        LoggerFactory._handler_cache = original_factory_state['handlers']
        
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "outputs").mkdir()
            (workspace / "logs").mkdir()
            yield workspace
            
    @pytest.fixture
    def sample_config(self, temp_workspace):
        """Create sample configuration."""
        config = {
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s"
            },
            "observers": {
                "logger": {
                    "enabled": True,
                    "log_level": "DEBUG"
                }
            },
            "paths": {
                "output_dir": str(temp_workspace / "outputs"),
                "log_dir": str(temp_workspace / "logs")
            },
            "docker": {
                "build_docker_image": False
            },
            "tests": [{
                "name": "test_integration",
                "description": "Integration test",
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
        
        config_file = temp_workspace / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
            
        return config_file
        
    def test_end_to_end_logging_consistency(self, temp_workspace):
        """Test logging consistency across multiple components."""
        # Initialize LoggerFactory
        LoggerFactory.initialize({
            'level': 'DEBUG',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s',
            'output_file': str(temp_workspace / "test.log")
        })
        
        # Create various components
        component1 = TestComponent()
        component2 = TestComponent()
        
        # Create observer
        event_manager = EventManager()
        logger_observer = LoggerObserver(
            include_data=True,
            log_level="DEBUG"
        )
        
        # Do work with components
        component1.do_work()
        component2.do_work()
        
        # Log from observer
        logger_observer.logger.info("Observer message")
        
        # Force flush all handlers
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # Check log file
        log_file = temp_workspace / "test.log"
        assert log_file.exists()
        
        content = log_file.read_text()
        
        # All components should have consistent format
        assert "[DEBUG]" in content or "[INFO]" in content
        assert "TestComponent" in content
        assert "Starting processing" in content
        assert "Completed processing" in content
        assert "Observer message" in content
        
        # All timestamps should be in consistent format
        lines = content.strip().split('\n')
        for line in lines:
            if line:  # Skip empty lines
                # Should start with timestamp
                assert line[0].isdigit()  # Year
                assert " [" in line  # Level indicator
                assert " - " in line  # Separator
                
    def test_configuration_propagation(self, sample_config):
        """Test that logging configuration propagates correctly."""
        # Load configuration
        config_loader = ConfigLoader(
            experiment_file=str(sample_config),
            debug_override=False
        )
        
        global_config = config_loader.load_and_validate_global_config()
        
        # Configuration should be loaded
        assert global_config.logging.level.name == 'DEBUG'
        assert global_config.logging.format == '%(asctime)s [%(levelname)s] - %(name)s - %(message)s'
        
        # Initialize LoggerFactory through the run command flow
        logging_config = {
            'level': global_config.logging.level.name,
            'format': global_config.logging.format,
            'enable_colors': True
        }
        LoggerFactory.initialize(logging_config)
        
        # Create components - they should all use the same format
        component = TestComponent()
        logger = component.logger
        
        assert logger.getEffectiveLevel() == logging.DEBUG
        
    def test_multiple_component_interaction(self, temp_workspace):
        """Test logging with multiple interacting components."""
        log_file = temp_workspace / "interaction.log"
        
        LoggerFactory.initialize({
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s',
            'output_file': str(log_file)
        })
        
        # Simulate component interaction
        class ServiceA(LoggerMixin):
            def process(self):
                self.log_operation_start("service_a_process")
                # Simulate calling another service
                service_b = ServiceB()
                service_b.handle_request("data_from_a")
                self.log_operation_complete("service_a_process")
                
        class ServiceB(LoggerMixin):
            def handle_request(self, data):
                self.log_operation_start("handle_request", data=data)
                time.sleep(0.01)
                self.log_operation_complete("handle_request", status="success")
                
        # Run interaction
        service_a = ServiceA()
        service_a.process()
        
        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # Check log file
        content = log_file.read_text()
        
        # Should show interaction flow
        lines = content.strip().split('\n')
        assert len(lines) >= 4
        
        # Check order of operations
        assert "ServiceA" in lines[0] and "Starting service_a_process" in lines[0]
        assert "ServiceB" in lines[1] and "Starting handle_request" in lines[1]
        assert "ServiceB" in lines[2] and "Completed handle_request" in lines[2]
        assert "ServiceA" in lines[3] and "Completed service_a_process" in lines[3]
        
    def test_experiment_manager_logging_flow(self, temp_workspace, sample_config):
        """Test logging through ExperimentManager flow."""
        # This test simulates the actual PANTHER flow
        with patch('panther.plugins.plugin_manager.PluginManager'):
            # Load config
            config_loader = ConfigLoader(
                experiment_file=str(sample_config),
                debug_override=False
            )
            
            global_config = config_loader.load_and_validate_global_config()
            
            # Initialize LoggerFactory (as done in run command)
            if global_config and hasattr(global_config, 'logging'):
                logging_config = {
                    'level': global_config.logging.level.name,
                    'format': global_config.logging.format,
                    'enable_colors': True,
                    'output_file': str(temp_workspace / "experiment.log")
                }
                LoggerFactory.initialize(logging_config)
                
            # Create ExperimentManager
            manager = ExperimentManager(
                global_config=global_config,
                experiment_name="test_logging"
            )
            
            # Manager should use consistent logging
            assert hasattr(manager, 'logger')
            assert manager.logger is not None
            
            # Log something
            manager.logger.info("Experiment manager initialized")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                    
            # Check log
            log_file = temp_workspace / "experiment.log"
            if log_file.exists():
                content = log_file.read_text()
                assert "Experiment manager initialized" in content
                assert "[INFO]" in content
                
    def test_observer_logging_consistency(self, temp_workspace):
        """Test that all observers use consistent logging."""
        LoggerFactory.initialize({
            'level': 'DEBUG',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s',
            'output_file': str(temp_workspace / "observers.log")
        })
        
        # Create different types of observers
        from panther.core.observer.impl.logger_observer import LoggerObserver
        from panther.core.observer.impl.storage_observer import StorageObserver
        
        logger_obs = LoggerObserver(
            include_data=True,
            log_level="DEBUG"
        )
        
        storage_obs = StorageObserver(
            storage_path=str(temp_workspace / "storage")
        )
        
        # Both should log consistently
        logger_obs.logger.info("Logger observer message")
        storage_obs.logger.info("Storage observer message")
        
        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # Check log
        log_file = temp_workspace / "observers.log"
        content = log_file.read_text()
        
        # Both messages should be there with consistent format
        assert "LoggerObserver" in content
        assert "Logger observer message" in content
        assert "StorageObserver" in content  
        assert "Storage observer message" in content
        
        # Format should be consistent
        lines = [l for l in content.strip().split('\n') if l]
        for line in lines:
            assert " [" in line  # Level
            assert " - " in line  # Separator
            
    @pytest.mark.slow
    def test_concurrent_logging(self, temp_workspace):
        """Test concurrent logging from multiple threads."""
        import threading
        import queue
        
        log_file = temp_workspace / "concurrent.log"
        
        LoggerFactory.initialize({
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - [%(threadName)s] %(message)s',
            'output_file': str(log_file)
        })
        
        results = queue.Queue()
        
        class Worker(LoggerMixin):
            def __init__(self, worker_id):
                super().__init__()
                self.worker_id = worker_id
                
            def run(self):
                for i in range(5):
                    self.logger.info(f"Worker {self.worker_id} - Message {i}")
                    time.sleep(0.001)
                results.put(self.worker_id)
                
        # Create and run workers
        workers = [Worker(i) for i in range(5)]
        threads = []
        
        for worker in workers:
            thread = threading.Thread(target=worker.run, name=f"Worker-{worker.worker_id}")
            threads.append(thread)
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # Verify results
        assert results.qsize() == 5
        
        # Check log file
        content = log_file.read_text()
        lines = content.strip().split('\n')
        
        # Should have 25 lines (5 workers * 5 messages)
        assert len(lines) == 25
        
        # All lines should have thread names
        for line in lines:
            assert "[Worker-" in line
            assert "Worker" in line
            assert "Message" in line
            
    def test_log_file_rotation_readiness(self, temp_workspace):
        """Test that log files are ready for rotation (proper file handles)."""
        log_file = temp_workspace / "rotation_test.log"
        
        LoggerFactory.initialize({
            'level': 'INFO',
            'format': '%(asctime)s - %(message)s',
            'output_file': str(log_file)
        })
        
        # Log some messages
        logger = LoggerFactory.get_logger("rotation_test")
        for i in range(100):
            logger.info(f"Message {i}")
            
        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # File should exist and have content
        assert log_file.exists()
        assert log_file.stat().st_size > 0
        
        # Should be able to read while logger is active
        content = log_file.read_text()
        assert "Message 99" in content
        
    def test_cli_to_experiment_logging_flow(self, temp_workspace, sample_config):
        """Test complete CLI to experiment logging flow."""
        # This simulates the actual CLI flow
        
        # 1. CLI loads config and initializes LoggerFactory
        config_loader = ConfigLoader(
            experiment_file=str(sample_config),
            debug_override=False
        )
        
        global_config = config_loader.load_and_validate_global_config()
        
        # 2. Initialize LoggerFactory (as in run.py)
        if global_config and hasattr(global_config, 'logging'):
            logging_config = {
                'level': global_config.logging.level.name,
                'format': global_config.logging.format,
                'enable_colors': False,  # Disable for testing
                'output_file': str(temp_workspace / "cli_flow.log")
            }
            LoggerFactory.initialize(logging_config)
            
        # 3. Create various components that would be used
        cli_logger = LoggerFactory.get_logger("cli.run")
        cli_logger.info("Starting PANTHER experiment")
        
        # 4. Config manager logs
        config_logger = LoggerFactory.get_logger("config_manager")
        config_logger.debug("Loaded configuration successfully")
        
        # 5. Plugin system logs
        plugin_logger = LoggerFactory.get_logger("plugin_manager")
        plugin_logger.info("Loading plugins...")
        
        # 6. Test execution logs
        test_logger = LoggerFactory.get_logger("test_executor")
        test_logger.info("Executing test cases...")
        
        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # Check complete flow in log
        log_file = temp_workspace / "cli_flow.log"
        content = log_file.read_text()
        
        # All components should have logged with consistent format
        assert "cli.run" in content
        assert "Starting PANTHER experiment" in content
        assert "config_manager" in content
        assert "Loaded configuration successfully" in content
        assert "plugin_manager" in content
        assert "Loading plugins" in content
        assert "test_executor" in content
        assert "Executing test cases" in content
        
        # Format should be consistent throughout
        for line in content.strip().split('\n'):
            if line:
                # All lines should follow the format
                assert " [" in line  # Level
                assert "] - " in line  # Separator