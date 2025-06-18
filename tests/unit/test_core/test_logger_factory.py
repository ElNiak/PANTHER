"""
Unit tests for LoggerFactory - centralized logging configuration system.

This module tests all aspects of the LoggerFactory including initialization,
logger creation, format consistency, and dynamic configuration updates.
"""

import pytest
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from panther.core.utils.logger_factory import LoggerFactory


class TestLoggerFactory:
    """Test LoggerFactory functionality."""
    
    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset LoggerFactory state before each test."""
        # Store original state
        original_initialized = LoggerFactory._initialized
        original_root_configured = LoggerFactory._root_logger_configured
        original_config = LoggerFactory._config.copy()
        original_handlers = LoggerFactory._handler_cache.copy()
        
        # Reset state
        LoggerFactory._initialized = False
        LoggerFactory._root_logger_configured = False
        LoggerFactory._config = {}
        LoggerFactory._handler_cache = {}
        
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        yield
        
        # Restore original state
        LoggerFactory._initialized = original_initialized
        LoggerFactory._root_logger_configured = original_root_configured
        LoggerFactory._config = original_config
        LoggerFactory._handler_cache = original_handlers
        
    def test_initialize_default_config(self):
        """Test initialization with default configuration."""
        config = {
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] - %(module)s - %(message)s'
        }
        LoggerFactory.initialize(config)
        
        assert LoggerFactory._initialized
        assert LoggerFactory._config == config
        assert LoggerFactory._root_logger_configured
        
    def test_initialize_only_once(self):
        """Test that factory can only be initialized once."""
        config1 = {'level': 'INFO', 'format': '%(levelname)s - %(message)s'}
        config2 = {'level': 'DEBUG', 'format': '%(asctime)s - %(message)s'}
        
        LoggerFactory.initialize(config1)
        LoggerFactory.initialize(config2)  # Should not change config
        
        assert LoggerFactory._config == config1
        
    def test_get_logger_auto_initialize(self):
        """Test that get_logger auto-initializes with defaults if needed."""
        logger = LoggerFactory.get_logger('test_logger')
        
        assert LoggerFactory._initialized
        assert logger is not None
        assert logger.name == 'test_logger'
        assert LoggerFactory._config['level'] == 'INFO'
        
    def test_get_logger_creates_consistent_format(self):
        """Test that all loggers use consistent format."""
        config = {
            'level': 'DEBUG',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s'
        }
        LoggerFactory.initialize(config)
        
        # Create multiple loggers
        logger1 = LoggerFactory.get_logger('logger1')
        logger2 = LoggerFactory.get_logger('logger2')
        logger3 = LoggerFactory.get_logger('module.submodule')
        
        # All should have same effective level
        assert logger1.getEffectiveLevel() == logging.DEBUG
        assert logger2.getEffectiveLevel() == logging.DEBUG
        assert logger3.getEffectiveLevel() == logging.DEBUG
        
        # All should propagate to root (which has our formatter)
        assert logger1.propagate
        assert logger2.propagate
        assert logger3.propagate
        
    def test_logger_caching(self):
        """Test that loggers are properly cached."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        logger1 = LoggerFactory.get_logger('cached_logger')
        logger2 = LoggerFactory.get_logger('cached_logger')
        
        # Should return the same logger instance
        assert logger1 is logger2
        
    def test_child_logger_creation(self):
        """Test child logger creation."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        parent_logger = LoggerFactory.get_logger('parent')
        child_logger = LoggerFactory.get_child_logger('parent', 'child')
        
        assert child_logger.name == 'parent.child'
        assert child_logger.parent == parent_logger
        
    def test_update_level_dynamically(self):
        """Test dynamic log level updates."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        LoggerFactory.update_level('DEBUG')
        assert root_logger.level == logging.DEBUG
        assert LoggerFactory._config['level'] == 'DEBUG'
        
    def test_update_level_before_init(self):
        """Test that update_level does nothing before initialization."""
        # Should not raise error
        LoggerFactory.update_level('DEBUG')
        assert not LoggerFactory._initialized
        
    def test_color_formatter_with_colorlog(self):
        """Test color formatter when colorlog is available."""
        with patch('panther.core.utils.logger_factory.colorlog') as mock_colorlog:
            mock_formatter = MagicMock()
            mock_colorlog.ColoredFormatter.return_value = mock_formatter
            
            config = {
                'level': 'INFO',
                'format': '%(message)s',
                'enable_colors': True
            }
            LoggerFactory.initialize(config)
            
            # Should have tried to create ColoredFormatter
            mock_colorlog.ColoredFormatter.assert_called_once()
            
    def test_fallback_formatter_without_colorlog(self):
        """Test fallback to regular formatter when colorlog unavailable."""
        with patch('panther.core.utils.logger_factory.colorlog', None):
            config = {
                'level': 'INFO',
                'format': '%(message)s',
                'enable_colors': True
            }
            LoggerFactory.initialize(config)
            
            # Should still work with regular formatter
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0
            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, logging.Formatter)
            
    def test_file_handler_addition(self):
        """Test adding file handlers dynamically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            
            LoggerFactory.initialize({'level': 'INFO'})
            LoggerFactory.add_file_handler(log_file, level='DEBUG')
            
            # Log something and check file
            logger = LoggerFactory.get_logger('file_test')
            logger.info("Test message")
            logger.debug("Debug message")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                    
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content
            assert "Debug message" in content
            
    def test_file_handler_without_init(self):
        """Test that add_file_handler does nothing before initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            
            # Should not raise error
            LoggerFactory.add_file_handler(log_file)
            assert not LoggerFactory._initialized
            
    def test_handler_deduplication(self):
        """Test that handlers are not duplicated."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        # Force recreation of handlers
        LoggerFactory._setup_root_logger()
        LoggerFactory._setup_root_logger()
        
        # Should still have only one console handler
        root_logger = logging.getLogger()
        console_handlers = [h for h in root_logger.handlers 
                          if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) == 1
        
    def test_thread_safety(self):
        """Test LoggerFactory is thread-safe."""
        config = {
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s'
        }
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Try to initialize (only first should succeed)
                LoggerFactory.initialize(config)
                
                # Create logger
                logger = LoggerFactory.get_logger(f'worker_{worker_id}')
                
                # Use logger
                logger.info(f"Message from worker {worker_id}")
                
                results.append({
                    'worker_id': worker_id,
                    'logger_name': logger.name,
                    'initialized': LoggerFactory._initialized
                })
            except Exception as e:
                errors.append((worker_id, str(e)))
                
        # Run multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()
                
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 10
        
        # All should see initialized state
        assert all(r['initialized'] for r in results)
        
        # All should have unique logger names
        logger_names = [r['logger_name'] for r in results]
        assert len(set(logger_names)) == 10
        
    def test_concurrent_logger_creation(self):
        """Test concurrent logger creation doesn't cause issues."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        loggers = []
        lock = threading.Lock()
        
        def create_logger(name):
            logger = LoggerFactory.get_logger(name)
            with lock:
                loggers.append(logger)
                
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_logger, args=(f'logger_{i}',))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # All loggers should be created
        assert len(loggers) == 20
        
        # All should have unique names
        names = [logger.name for logger in loggers]
        assert len(set(names)) == 20
        
    def test_output_file_in_config(self):
        """Test output file configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'configured.log'
            
            config = {
                'level': 'INFO',
                'format': '%(levelname)s - %(message)s',
                'output_file': str(log_file)
            }
            LoggerFactory.initialize(config)
            
            logger = LoggerFactory.get_logger('file_config_test')
            logger.info("Configured file test")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                    
            assert log_file.exists()
            assert "Configured file test" in log_file.read_text()
            
    def test_logging_levels(self):
        """Test all logging levels work correctly."""
        LoggerFactory.initialize({'level': 'DEBUG'})
        
        logger = LoggerFactory.get_logger('level_test')
        
        # All these should work without error
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
    def test_custom_format_string(self):
        """Test custom format strings."""
        custom_format = '%(name)s | %(levelname)s | %(message)s'
        LoggerFactory.initialize({
            'level': 'INFO',
            'format': custom_format
        })
        
        # Capture log output
        with patch('sys.stdout', new_callable=MagicMock) as mock_stdout:
            logger = LoggerFactory.get_logger('format_test')
            logger.info("Test message")
            
            # Get what was written
            write_calls = mock_stdout.write.call_args_list
            output = ''.join(call[0][0] for call in write_calls if call[0])
            
            # Should contain our format elements
            assert 'format_test' in output
            assert 'INFO' in output
            assert 'Test message' in output
            
    def test_get_logger_with_dots(self):
        """Test logger names with dots (module paths)."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        logger = LoggerFactory.get_logger('panther.core.utils.test')
        assert logger.name == 'panther.core.utils.test'
        
        # Parent loggers should exist
        parent = logging.getLogger('panther.core.utils')
        assert parent is not None
        
    def test_formatter_with_exception(self):
        """Test that formatter handles exceptions properly."""
        LoggerFactory.initialize({'level': 'INFO'})
        
        logger = LoggerFactory.get_logger('exception_test')
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Should not raise error
            logger.exception("An error occurred")