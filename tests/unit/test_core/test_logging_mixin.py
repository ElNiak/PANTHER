"""
Unit tests for LoggerMixin - reusable logging functionality for classes.

This module tests the LoggerMixin integration with LoggerFactory and its
convenience methods for consistent logging patterns.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock, call

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.utils.logger_factory import LoggerFactory


class TestClass(LoggerMixin):
    """Test class that uses LoggerMixin."""
    
    def __init__(self):
        super().__init__()
        self.name = "TestClass"


class AnotherTestClass(LoggerMixin):
    """Another test class to verify different logger names."""
    
    def __init__(self):
        super().__init__()
        self.name = "AnotherTestClass"


class ComplexInheritance(LoggerMixin, dict):
    """Test multiple inheritance scenarios."""
    
    def __init__(self):
        super().__init__()
        self.complex_name = "Complex"


class TestLoggerMixin:
    """Test LoggerMixin functionality."""
    
    @pytest.fixture(autouse=True)
    def reset_logger_factory(self):
        """Reset LoggerFactory for each test."""
        # Store original state
        original_initialized = LoggerFactory._initialized
        original_config = LoggerFactory._config.copy()
        
        # Reset
        LoggerFactory._initialized = False
        LoggerFactory._config = {}
        
        yield
        
        # Restore
        LoggerFactory._initialized = original_initialized
        LoggerFactory._config = original_config
        
    def test_logger_property_initialization(self):
        """Test that logger property is lazily initialized."""
        instance = TestClass()
        
        # Logger should not be created yet
        assert instance._logger is None
        
        # Access logger property
        logger = instance.logger
        
        # Now it should be created
        assert instance._logger is not None
        assert logger is not None
        assert logger.name == "TestClass"
        
    def test_logger_uses_class_name(self):
        """Test that logger name matches the class name."""
        instance1 = TestClass()
        instance2 = AnotherTestClass()
        
        logger1 = instance1.logger
        logger2 = instance2.logger
        
        assert logger1.name == "TestClass"
        assert logger2.name == "AnotherTestClass"
        assert logger1 is not logger2
        
    def test_logger_property_caching(self):
        """Test that logger is cached after first access."""
        instance = TestClass()
        
        logger1 = instance.logger
        logger2 = instance.logger
        
        # Should return the same logger instance
        assert logger1 is logger2
        
    def test_logger_uses_logger_factory(self):
        """Test that LoggerMixin uses LoggerFactory."""
        with patch('panther.core.utils.logging_mixin.LoggerFactory.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            instance = TestClass()
            logger = instance.logger
            
            mock_get_logger.assert_called_once_with("TestClass")
            assert logger is mock_logger
            
    def test_log_initialization(self):
        """Test log_initialization convenience method."""
        instance = TestClass()
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_initialization("MyEntity", "with extra info")
            
            mock_logger.debug.assert_called_once_with(
                "Initializing TestClass for 'MyEntity' - with extra info"
            )
            
    def test_log_initialization_without_extra_info(self):
        """Test log_initialization without additional info."""
        instance = TestClass()
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_initialization("MyEntity")
            
            mock_logger.debug.assert_called_once_with(
                "Initializing TestClass for 'MyEntity'"
            )
            
    def test_log_config_loaded(self):
        """Test log_config_loaded convenience method."""
        instance = TestClass()
        config = {"key": "value", "nested": {"item": 123}}
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_config_loaded(config, "MyEntity")
            
            mock_logger.debug.assert_called_once_with(
                "Loaded TestClass configuration for 'MyEntity': %s",
                config
            )
            
    def test_log_config_loaded_without_entity(self):
        """Test log_config_loaded without entity name."""
        instance = TestClass()
        config = {"key": "value"}
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_config_loaded(config)
            
            mock_logger.debug.assert_called_once_with(
                "Loaded TestClass configuration: %s",
                config
            )
            
    def test_log_operation_start(self):
        """Test log_operation_start convenience method."""
        instance = TestClass()
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_operation_start("data_processing", input_size=1000, mode="fast")
            
            mock_logger.info.assert_called_once_with(
                "Starting data_processing with {'input_size': 1000, 'mode': 'fast'}"
            )
            
    def test_log_operation_start_no_kwargs(self):
        """Test log_operation_start without additional context."""
        instance = TestClass()
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_operation_start("simple_operation")
            
            mock_logger.info.assert_called_once_with(
                "Starting simple_operation"
            )
            
    def test_log_operation_complete(self):
        """Test log_operation_complete convenience method."""
        instance = TestClass()
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_operation_complete("data_processing", records_processed=500)
            
            mock_logger.info.assert_called_once_with(
                "Completed data_processing with {'records_processed': 500}"
            )
            
    def test_log_operation_complete_no_kwargs(self):
        """Test log_operation_complete without additional context."""
        instance = TestClass()
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_operation_complete("simple_operation")
            
            mock_logger.info.assert_called_once_with(
                "Completed simple_operation"
            )
            
    def test_log_operation_failed(self):
        """Test log_operation_failed convenience method."""
        instance = TestClass()
        error = ValueError("Invalid input data")
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_operation_failed("data_validation", error, line_number=42)
            
            mock_logger.error.assert_called_once_with(
                "Failed data_validation with {'line_number': 42}: Invalid input data",
                exc_info=True
            )
            
    def test_log_operation_failed_no_kwargs(self):
        """Test log_operation_failed without additional context."""
        instance = TestClass()
        error = RuntimeError("Something went wrong")
        
        with patch.object(instance, 'logger') as mock_logger:
            instance.log_operation_failed("critical_operation", error)
            
            mock_logger.error.assert_called_once_with(
                "Failed critical_operation: Something went wrong",
                exc_info=True
            )
            
    def test_multiple_inheritance(self):
        """Test LoggerMixin with multiple inheritance."""
        instance = ComplexInheritance()
        
        # Should work with dict methods
        instance['key'] = 'value'
        assert instance['key'] == 'value'
        
        # Should also have logger
        logger = instance.logger
        assert logger.name == "ComplexInheritance"
        
    def test_logger_in_different_instances(self):
        """Test that different instances get their own logger references."""
        instance1 = TestClass()
        instance2 = TestClass()
        
        # Each instance should have its own _logger attribute
        assert instance1._logger is None
        assert instance2._logger is None
        
        # But they should get the same logger from LoggerFactory
        logger1 = instance1.logger
        logger2 = instance2.logger
        
        assert logger1 is logger2  # Same logger from factory
        assert instance1._logger is instance2._logger  # Same cached logger
        
    def test_integration_with_logger_factory_config(self):
        """Test that LoggerMixin respects LoggerFactory configuration."""
        # Initialize LoggerFactory with specific config
        LoggerFactory.initialize({
            'level': 'DEBUG',
            'format': '%(name)s - %(message)s'
        })
        
        instance = TestClass()
        logger = instance.logger
        
        # Should respect the DEBUG level
        assert logger.getEffectiveLevel() == logging.DEBUG
        
    def test_convenience_methods_with_real_logger(self):
        """Test convenience methods with actual logger output."""
        import io
        import sys
        
        # Initialize LoggerFactory
        LoggerFactory.initialize({
            'level': 'DEBUG',
            'format': '%(levelname)s - %(message)s'
        })
        
        instance = TestClass()
        
        # Capture stdout
        captured_output = io.StringIO()
        handler = logging.StreamHandler(captured_output)
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        instance.logger.addHandler(handler)
        
        # Test various logging methods
        instance.log_initialization("TestEntity", "version 1.0")
        instance.log_config_loaded({"debug": True}, "TestEntity")
        instance.log_operation_start("test_run", iterations=5)
        instance.log_operation_complete("test_run", success=True)
        
        # Get output
        handler.flush()
        output = captured_output.getvalue()
        
        # Verify output contains expected messages
        assert "Initializing TestClass" in output
        assert "TestEntity" in output
        assert "version 1.0" in output
        assert "Loaded TestClass configuration" in output
        assert "Starting test_run" in output
        assert "Completed test_run" in output
        
        # Clean up
        instance.logger.removeHandler(handler)
        
    def test_error_logging_with_exception_info(self):
        """Test that error logging includes exception information."""
        instance = TestClass()
        
        # Create a real logger with captured output
        import io
        captured_output = io.StringIO()
        handler = logging.StreamHandler(captured_output)
        instance.logger.addHandler(handler)
        instance.logger.setLevel(logging.ERROR)
        
        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            instance.log_operation_failed("test_operation", e, detail="important")
            
        # Get output
        handler.flush()
        output = captured_output.getvalue()
        
        # Should contain exception details
        assert "Failed test_operation" in output
        assert "Test exception" in output
        assert "detail" in output
        assert "Traceback" in output  # exc_info=True should include traceback
        
        # Clean up
        instance.logger.removeHandler(handler)
        
    def test_subclass_with_custom_logger_name(self):
        """Test that subclasses can override logger name if needed."""
        class CustomLoggerClass(LoggerMixin):
            def __init__(self):
                super().__init__()
                # Override the logger name
                self._logger = LoggerFactory.get_logger("custom.logger.name")
                
        instance = CustomLoggerClass()
        assert instance.logger.name == "custom.logger.name"