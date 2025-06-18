"""
Unit tests for ExperimentManager logging behavior.

This module tests that ExperimentManager properly uses LoggerMixin
and doesn't try to assign to the logger property.
"""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from panther.core.experiment_manager import ExperimentManager
from panther.core.utils.logger_factory import LoggerFactory
from panther.config.config_global_schema import GlobalConfig


class TestExperimentManagerLogging:
    """Test ExperimentManager logging functionality."""
    
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
    def mock_global_config(self):
        """Create a mock global configuration."""
        config = Mock(spec=GlobalConfig)
        config.logging.level.name = 'INFO'
        config.logging.format = '%(asctime)s [%(levelname)s] - %(module)s - %(message)s'
        config.paths.output_dir = 'outputs'
        config.fast_fail.enabled = True
        return config
        
    @pytest.fixture
    def mock_plugin_manager(self):
        """Mock PluginManager to avoid plugin loading."""
        with patch('panther.core.experiment_manager.PluginManager') as mock_pm:
            yield mock_pm
            
    def test_experiment_manager_no_logger_assignment(self, mock_global_config, mock_plugin_manager):
        """Test that ExperimentManager doesn't assign to logger property."""
        # Initialize LoggerFactory
        LoggerFactory.initialize({'level': 'INFO'})
        
        # Create ExperimentManager without passing logger
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="test_experiment"
        )
        
        # Should have logger property from LoggerMixin
        assert hasattr(manager, 'logger')
        assert manager.logger is not None
        assert manager.logger.name == "ExperimentManager"
        
    def test_experiment_manager_with_provided_logger(self, mock_global_config, mock_plugin_manager):
        """Test ExperimentManager with a provided logger."""
        # Initialize LoggerFactory
        LoggerFactory.initialize({'level': 'DEBUG'})
        
        # Create a custom logger
        custom_logger = logging.getLogger("custom.experiment.logger")
        
        # Create ExperimentManager with custom logger
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="test_experiment",
            logger=custom_logger
        )
        
        # Should use the provided logger
        assert manager._logger is custom_logger
        assert manager.logger is custom_logger
        assert manager.logger.name == "custom.experiment.logger"
        
    def test_experiment_manager_logger_inheritance(self, mock_global_config, mock_plugin_manager):
        """Test that ExperimentManager inherits from LoggerMixin correctly."""
        from panther.core.utils.logging_mixin import LoggerMixin
        from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
        
        # Verify inheritance chain
        assert issubclass(ExperimentManager, ErrorHandlerMixin)
        assert issubclass(ErrorHandlerMixin, LoggerMixin)
        
        # Create instance
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="test"
        )
        
        # Should have LoggerMixin methods
        assert hasattr(manager, 'log_initialization')
        assert hasattr(manager, 'log_config_loaded')
        assert hasattr(manager, 'log_operation_start')
        assert hasattr(manager, 'log_operation_complete')
        assert hasattr(manager, 'log_operation_failed')
        
    def test_experiment_manager_logging_during_initialization(self, mock_global_config, mock_plugin_manager):
        """Test logging during ExperimentManager initialization."""
        # Initialize LoggerFactory with captured output
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "experiment.log"
            
            LoggerFactory.initialize({
                'level': 'DEBUG',
                'format': '%(levelname)s - %(name)s - %(message)s',
                'output_file': str(log_file)
            })
            
            # Create ExperimentManager
            manager = ExperimentManager(
                global_config=mock_global_config,
                experiment_name="init_test"
            )
            
            # Should have logged initialization
            manager.logger.info("Test initialization complete")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                    
            # Check log
            content = log_file.read_text()
            assert "ExperimentManager" in content
            assert "Test initialization complete" in content
            
    def test_experiment_manager_logging_methods(self, mock_global_config, mock_plugin_manager):
        """Test ExperimentManager using LoggerMixin convenience methods."""
        LoggerFactory.initialize({'level': 'DEBUG'})
        
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="method_test"
        )
        
        # Capture log output
        with patch.object(manager, 'logger') as mock_logger:
            # Test various logging methods
            manager.log_initialization("TestExperiment", "version 2.0")
            mock_logger.debug.assert_called_with(
                "Initializing ExperimentManager for 'TestExperiment' - version 2.0"
            )
            
            manager.log_config_loaded({"test": "config"}, "TestExperiment")
            mock_logger.debug.assert_called_with(
                "Loaded ExperimentManager configuration for 'TestExperiment': %s",
                {"test": "config"}
            )
            
            manager.log_operation_start("experiment_execution", phase=1)
            mock_logger.info.assert_called_with(
                "Starting experiment_execution with {'phase': 1}"
            )
            
            manager.log_operation_complete("experiment_execution", success=True)
            mock_logger.info.assert_called_with(
                "Completed experiment_execution with {'success': True}"
            )
            
    def test_experiment_manager_error_logging(self, mock_global_config, mock_plugin_manager):
        """Test error logging in ExperimentManager."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="error_test"
        )
        
        # Test error logging
        error = ValueError("Test error in experiment")
        
        with patch.object(manager, 'logger') as mock_logger:
            manager.log_operation_failed("test_execution", error, test_case="test1")
            
            mock_logger.error.assert_called_once_with(
                "Failed test_execution with {'test_case': 'test1'}: Test error in experiment",
                exc_info=True
            )
            
    def test_experiment_manager_phase_logging(self, mock_global_config, mock_plugin_manager):
        """Test logging during experiment phases."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        # Mock additional dependencies
        with patch('panther.core.experiment_manager.EventManager'):
            with patch('panther.core.experiment_manager.get_observer_factory'):
                with patch('panther.core.experiment_manager.WorkflowStateTracker'):
                    with patch('panther.core.experiment_manager.EmitterRegistry'):
                        manager = ExperimentManager(
                            global_config=mock_global_config,
                            experiment_name="phase_test"
                        )
                        
                        # Capture actual log output
                        import io
                        log_capture = io.StringIO()
                        handler = logging.StreamHandler(log_capture)
                        manager.logger.addHandler(handler)
                        
                        # Log phase transitions
                        manager.logger.info("Starting Phase 1: Initialization")
                        manager.logger.info("Starting Phase 2: Plugin Loading")
                        manager.logger.info("Starting Phase 3: Environment Deployment")
                        manager.logger.info("Starting Phase 4: Test Execution")
                        
                        # Get output
                        handler.flush()
                        output = log_capture.getvalue()
                        
                        # All phases should be logged
                        assert "Phase 1" in output
                        assert "Phase 2" in output
                        assert "Phase 3" in output
                        assert "Phase 4" in output
                        
                        # Clean up
                        manager.logger.removeHandler(handler)
                        
    def test_experiment_manager_concurrent_logging(self, mock_global_config, mock_plugin_manager):
        """Test concurrent logging from ExperimentManager."""
        import threading
        
        LoggerFactory.initialize({'level': 'INFO'})
        
        results = []
        
        def create_and_log(idx):
            manager = ExperimentManager(
                global_config=mock_global_config,
                experiment_name=f"concurrent_test_{idx}"
            )
            manager.logger.info(f"Manager {idx} initialized")
            results.append(manager.logger.name)
            
        # Create multiple managers concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_log, args=(i,))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # All should have the same logger name
        assert len(results) == 5
        assert all(name == "ExperimentManager" for name in results)
        
    def test_experiment_manager_logging_consistency(self, mock_global_config, mock_plugin_manager):
        """Test that ExperimentManager maintains logging consistency."""
        # Initialize LoggerFactory with specific format
        LoggerFactory.initialize({
            'level': 'DEBUG',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s'
        })
        
        # Create manager
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="consistency_test"
        )
        
        # Create other components that might be used
        from panther.core.test_cases.test_case_impl import TestCase
        
        # Mock test case to also use LoggerMixin
        mock_test_case = Mock(spec=TestCase)
        mock_test_case.logger = LoggerFactory.get_logger("TestCase")
        
        # Both should use consistent format
        import io
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] - %(name)s - %(message)s'))
        
        # Add handler to root logger (both loggers propagate to root)
        logging.getLogger().addHandler(handler)
        
        # Log from both
        manager.logger.info("Manager message")
        mock_test_case.logger.info("Test case message")
        
        # Get output
        handler.flush()
        log_output = output.getvalue()
        
        # Both should have consistent format
        lines = log_output.strip().split('\n')
        assert len(lines) == 2
        
        for line in lines:
            assert " [INFO] - " in line
            assert " - " in line
            
        # Clean up
        logging.getLogger().removeHandler(handler)
        
    def test_experiment_manager_no_logging_before_init(self, mock_global_config, mock_plugin_manager):
        """Test that ExperimentManager can be created even if LoggerFactory not initialized."""
        # Don't initialize LoggerFactory
        
        # Should still work (LoggerFactory will auto-initialize with defaults)
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="no_init_test"
        )
        
        # Should have logger
        assert manager.logger is not None
        assert manager.logger.name == "ExperimentManager"
        
        # LoggerFactory should have been auto-initialized
        assert LoggerFactory._initialized
        
    def test_experiment_manager_custom_logger_preserved(self, mock_global_config, mock_plugin_manager):
        """Test that custom logger is preserved through lifecycle."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        # Create custom logger with specific handler
        custom_logger = logging.getLogger("custom.experiment")
        custom_handler = logging.StreamHandler()
        custom_logger.addHandler(custom_handler)
        
        # Create manager with custom logger
        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="custom_logger_test",
            logger=custom_logger
        )
        
        # Logger should be preserved
        assert manager.logger is custom_logger
        assert custom_handler in manager.logger.handlers
        
        # Should work throughout lifecycle
        manager.logger.info("Custom logger message")
        
        # Clean up
        custom_logger.removeHandler(custom_handler)