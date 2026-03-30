"""Unit tests for LoggerMixin - reusable logging functionality for classes.

This module tests the LoggerMixin integration with LoggerFactory and its
convenience methods for consistent logging patterns.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from panther.core.utils.logger_factory import LoggerFactory
from panther.core.utils.logging_mixin import LoggerMixin


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
        """Test that logger is initialized during __init__."""
        instance = TestClass()

        # __init_logger__() is called during __init__, so _logger is set
        assert instance._logger is not None

        # Access logger property
        logger = instance.logger

        assert logger is not None
        # Logger name is module.ClassName
        assert "TestClass" in logger.name

    def test_logger_uses_class_name(self):
        """Test that logger name contains the class name."""
        instance1 = TestClass()
        instance2 = AnotherTestClass()

        logger1 = instance1.logger
        logger2 = instance2.logger

        assert "TestClass" in logger1.name
        assert "AnotherTestClass" in logger2.name
        assert logger1 is not logger2

    def test_logger_property_caching(self):
        """Test that logger is cached after first access."""
        instance = TestClass()

        logger1 = instance.logger
        logger2 = instance.logger

        # Should return the same logger instance
        assert logger1 is logger2

    def test_logger_uses_logger_factory(self):
        """Test that LoggerMixin uses LoggerFactory via FeatureLoggerMixin."""
        with patch(
            "panther.core.utils.feature_logger_mixin.LoggerFactory.get_feature_logger"
        ) as mock_get_feature:
            mock_logger = MagicMock()
            mock_get_feature.return_value = mock_logger

            with patch(
                "panther.core.utils.feature_logger_mixin.LoggerFactory.get_logger"
            ) as mock_get_logger:
                mock_get_logger.return_value = mock_logger

                instance = TestClass()
                logger = instance.logger

                # FeatureLoggerMixin calls get_feature_logger or get_logger
                # depending on whether a feature was auto-detected
                assert logger is mock_logger

    def test_log_initialization(self):
        """Test log_initialization convenience method."""
        instance = TestClass()

        instance._logger = MagicMock()
        instance.log_initialization("MyEntity", "with extra info")

        instance._logger.debug.assert_called_once_with(
            "Initializing TestClass for 'MyEntity' - with extra info"
        )

    def test_log_initialization_without_extra_info(self):
        """Test log_initialization without additional info."""
        instance = TestClass()

        instance._logger = MagicMock()
        instance.log_initialization("MyEntity")

        instance._logger.debug.assert_called_once_with(
            "Initializing TestClass for 'MyEntity'"
        )

    def test_log_config_loaded(self):
        """Test log_config_loaded convenience method."""
        instance = TestClass()
        config = {"key": "value", "nested": {"item": 123}}

        instance._logger = MagicMock()
        instance._logger.isEnabledFor.return_value = True
        # log_config_loaded uses ConfigSummarizer.summarize() with %s lazy formatting
        instance.log_config_loaded(config, "MyEntity")

        # Should have called debug with %s format and args
        instance._logger.debug.assert_called_once()
        call_args = instance._logger.debug.call_args[0]
        fmt = call_args[0]
        assert "%s" in fmt
        assert "Loaded" in fmt
        assert call_args[1] == "TestClass"  # class name
        assert call_args[2] == " for 'MyEntity'"  # entity_part

    def test_log_config_loaded_without_entity(self):
        """Test log_config_loaded without entity name."""
        instance = TestClass()
        config = {"key": "value"}

        instance._logger = MagicMock()
        instance._logger.isEnabledFor.return_value = True
        instance.log_config_loaded(config)

        instance._logger.debug.assert_called_once()
        call_args = instance._logger.debug.call_args[0]
        fmt = call_args[0]
        assert "%s" in fmt
        assert "Loaded" in fmt

    def test_log_operation_start(self):
        """Test log_operation_start convenience method."""
        instance = TestClass()

        instance._logger = MagicMock()
        instance._logger.isEnabledFor.return_value = True
        # log_operation_start filters kwargs to ["name", "type", "count", "target"]
        instance.log_operation_start("data_processing", name="test", count=1000)

        instance._logger.info.assert_called_once()
        call_args = instance._logger.info.call_args[0]
        assert call_args[0] == "Starting %s with %s"
        assert call_args[1] == "data_processing"
        assert "name" in str(call_args[2])
        assert "count" in str(call_args[2])

    def test_log_operation_start_no_kwargs(self):
        """Test log_operation_start without additional context."""
        instance = TestClass()

        instance._logger = MagicMock()
        instance._logger.isEnabledFor.return_value = True
        instance.log_operation_start("simple_operation")

        instance._logger.info.assert_called_once_with("Starting %s", "simple_operation")

    def test_log_operation_complete(self):
        """Test log_operation_complete convenience method."""
        instance = TestClass()

        instance._logger = MagicMock()
        instance._logger.isEnabledFor.return_value = True
        # log_operation_complete filters kwargs to ["name", "duration", "result", "count"]
        instance.log_operation_complete("data_processing", name="test", count=500)

        instance._logger.info.assert_called_once()
        call_args = instance._logger.info.call_args[0]
        assert call_args[0] == "Completed %s with %s"
        assert call_args[1] == "data_processing"

    def test_log_operation_complete_no_kwargs(self):
        """Test log_operation_complete without additional context."""
        instance = TestClass()

        instance._logger = MagicMock()
        instance._logger.isEnabledFor.return_value = True
        instance.log_operation_complete("simple_operation")

        instance._logger.info.assert_called_once_with(
            "Completed %s", "simple_operation"
        )

    def test_log_operation_failed(self):
        """Test log_operation_failed convenience method."""
        instance = TestClass()
        error = ValueError("Invalid input data")

        instance._logger = MagicMock()
        instance.log_operation_failed("data_validation", error, line_number=42)

        instance._logger.error.assert_called_once_with(
            "Failed data_validation with {'line_number': 42}: Invalid input data",
            exc_info=True,
        )

    def test_log_operation_failed_no_kwargs(self):
        """Test log_operation_failed without additional context."""
        instance = TestClass()
        error = RuntimeError("Something went wrong")

        instance._logger = MagicMock()
        instance.log_operation_failed("critical_operation", error)

        instance._logger.error.assert_called_once_with(
            "Failed critical_operation: Something went wrong",
            exc_info=True,
        )

    def test_multiple_inheritance(self):
        """Test LoggerMixin with multiple inheritance."""
        instance = ComplexInheritance()

        # Should work with dict methods
        instance["key"] = "value"
        assert instance["key"] == "value"

        # Should also have logger
        logger = instance.logger
        assert "ComplexInheritance" in logger.name

    def test_logger_in_different_instances(self):
        """Test that different instances get their own logger references."""
        instance1 = TestClass()
        instance2 = TestClass()

        # __init_logger__() runs in __init__, so _logger is set
        assert instance1._logger is not None
        assert instance2._logger is not None

        # Both get the same logger from the factory (same name)
        logger1 = instance1.logger
        logger2 = instance2.logger

        assert logger1 is logger2  # Same logger from factory
        assert instance1._logger is instance2._logger  # Same cached logger

    def test_integration_with_logger_factory_config(self):
        """Test that LoggerMixin respects LoggerFactory configuration."""
        # Initialize LoggerFactory with specific config
        LoggerFactory.initialize({"level": "DEBUG", "format": "%(name)s - %(message)s"})

        instance = TestClass()
        logger = instance.logger

        # Should respect the DEBUG level
        assert logger.getEffectiveLevel() == logging.DEBUG

    def test_convenience_methods_with_real_logger(self):
        """Test convenience methods with actual logger output."""
        import io

        # Initialize LoggerFactory
        LoggerFactory.initialize(
            {"level": "DEBUG", "format": "%(levelname)s - %(message)s"}
        )

        instance = TestClass()

        # Capture stdout
        captured_output = io.StringIO()
        handler = logging.StreamHandler(captured_output)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        handler.setLevel(logging.DEBUG)
        instance.logger.addHandler(handler)

        # Test various logging methods
        instance.log_initialization("TestEntity", "version 1.0")
        instance.log_config_loaded({"debug": True}, "TestEntity")
        instance.log_operation_start("test_run", name="run1")
        instance.log_operation_complete("test_run", name="run1")

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
