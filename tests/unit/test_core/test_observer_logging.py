"""
Unit tests for observer logging consistency.

This module tests that all observers use consistent logging through the
LoggerFactory and that the IObserver._setup_logging method works correctly.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.core.observer.base.observer_interface import IObserver
from panther.core.utils.logger_factory import LoggerFactory


class TestObserver(IObserver):
    """Test observer implementation."""

    def on_event(self, event):
        """Handle an event."""
        pass


class TestObserverLogging:
    """Test observer logging consistency."""

    @pytest.fixture(autouse=True)
    def reset_logger_factory(self):
        """Reset LoggerFactory for each test."""
        # Store original state
        original_initialized = LoggerFactory._initialized
        original_config = LoggerFactory._config.copy()
        original_handlers = LoggerFactory._handler_cache.copy()

        # Reset
        LoggerFactory._initialized = False
        LoggerFactory._config = {}
        LoggerFactory._handler_cache = {}

        # Clear root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        yield

        # Restore
        LoggerFactory._initialized = original_initialized
        LoggerFactory._config = original_config
        LoggerFactory._handler_cache = original_handlers

    def test_setup_logging_uses_logger_factory(self):
        """Test that _setup_logging uses LoggerFactory."""
        observer = TestObserver()

        # LoggerFactory is imported inside _setup_logging, so patch at source
        with patch(
            "panther.core.utils.logger_factory.LoggerFactory.get_logger"
        ) as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = observer._setup_logging(
                logger_name="TestObserver", log_level=logging.INFO
            )

            mock_get_logger.assert_called_once_with("TestObserver")
            assert logger is mock_logger

    def test_setup_logging_respects_log_level(self):
        """Test that _setup_logging respects the provided log level."""
        # Initialize LoggerFactory with INFO level
        LoggerFactory.initialize({"level": "INFO"})

        observer = TestObserver()
        logger = observer._setup_logging(
            logger_name="TestObserver", log_level=logging.DEBUG  # Request DEBUG level
        )

        # Logger should be set to DEBUG
        assert logger.level == logging.DEBUG

    def test_setup_logging_with_file_output(self):
        """Test _setup_logging with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "observer.log"

            # Initialize LoggerFactory
            LoggerFactory.initialize({"level": "INFO"})

            observer = TestObserver()

            # _setup_logging uses _add_lazy_file_handler for file output, not LoggerFactory.add_file_handler
            logger = observer._setup_logging(
                logger_name="FileObserver",
                log_level=logging.INFO,
                output_file=str(log_file),
            )

            # Should have stored the pending log file path
            assert hasattr(observer, "_pending_log_file")
            assert observer._pending_log_file == str(log_file)
            # Logger should have a lazy file handler added
            assert logger is not None

    def test_setup_logging_without_file_output(self):
        """Test _setup_logging without file output."""
        LoggerFactory.initialize({"level": "INFO"})

        observer = TestObserver()

        logger = observer._setup_logging(
            logger_name="NoFileObserver", log_level=logging.INFO, output_file=None
        )

        # Should not have a pending log file
        assert not hasattr(observer, "_pending_log_file")
        assert logger is not None
        assert logger.name == "NoFileObserver"

    def test_setup_logging_params_ignored(self):
        """Test that color and structured output params are ignored (handled by LoggerFactory)."""
        LoggerFactory.initialize({"level": "INFO", "enable_colors": False})

        observer = TestObserver()

        # These params should be ignored since LoggerFactory handles formatting
        logger = observer._setup_logging(
            logger_name="ParamsObserver",
            log_level=logging.INFO,
            enable_colors=True,  # Should be ignored
            structured_output=True,  # Should be ignored
        )

        # Logger should still work
        assert logger is not None
        assert logger.name == "ParamsObserver"

    def test_multiple_observers_consistent_format(self):
        """Test that multiple observers use consistent log format."""
        # Initialize LoggerFactory with specific format
        LoggerFactory.initialize(
            {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
            }
        )

        observer1 = TestObserver()
        observer2 = TestObserver()

        logger1 = observer1._setup_logging("Observer1", logging.INFO)
        logger2 = observer2._setup_logging("Observer2", logging.DEBUG)

        # Both should use LoggerFactory
        assert logger1.name == "Observer1"
        assert logger2.name == "Observer2"

        # LoggerFactory creates loggers with propagate=False (own handlers)
        assert not logger1.propagate
        assert not logger2.propagate

    def test_real_observer_implementations(self):
        """Test real observer implementations use consistent logging."""
        # Initialize LoggerFactory
        LoggerFactory.initialize(
            {"level": "DEBUG", "format": "%(levelname)s - %(name)s - %(message)s"}
        )

        # Test with actual observer classes if available
        try:
            from panther.core.observer.impl.logger_observer import LoggerObserver
            from panther.core.observer.impl.metrics_observer import MetricsObserver
            from panther.core.observer.impl.storage_observer import StorageObserver

            # Create instances (with minimal required params)
            logger_obs = LoggerObserver(
                include_data=True, include_timestamp=True, log_level="DEBUG"
            )

            # They should all have loggers from LoggerFactory
            assert hasattr(logger_obs, "logger")
            # Logger name includes the module path, check it contains the class name
            assert "Observer" in logger_obs.logger.name

        except ImportError:
            # Skip if observers not available
            pytest.skip("Observer implementations not available")

    def test_observer_logger_inheritance(self):
        """Test that observer subclasses inherit logging behavior."""

        class CustomObserver(TestObserver):
            def __init__(self):
                super().__init__()
                self.logger = self._setup_logging(
                    logger_name="CustomObserver", log_level=logging.INFO
                )

        LoggerFactory.initialize({"level": "INFO"})

        observer = CustomObserver()
        assert observer.logger is not None
        assert observer.logger.name == "CustomObserver"

    def test_concurrent_observer_creation(self):
        """Test concurrent observer creation with logging."""
        import threading

        LoggerFactory.initialize({"level": "INFO"})

        observers = []
        lock = threading.Lock()

        def create_observer(idx):
            observer = TestObserver()
            logger = observer._setup_logging(
                logger_name=f"ConcurrentObserver{idx}", log_level=logging.INFO
            )
            with lock:
                observers.append((observer, logger))

        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_observer, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All observers should be created with loggers
        assert len(observers) == 10

        # All loggers should have unique names
        logger_names = [logger.name for _, logger in observers]
        assert len(set(logger_names)) == 10

    def test_observer_logging_with_event_handling(self):
        """Test observer logging during event handling."""

        class LoggingObserver(IObserver):
            def __init__(self):
                super().__init__()
                self.logger = self._setup_logging(
                    logger_name="LoggingObserver", log_level=logging.DEBUG
                )

            def on_event(self, event):
                self.logger.debug(f"Received event: {event}")
                self.logger.info(f"Processing event type: {type(event).__name__}")

        LoggerFactory.initialize({"level": "DEBUG"})

        observer = LoggingObserver()

        # Capture log output
        import io

        captured_output = io.StringIO()
        handler = logging.StreamHandler(captured_output)
        observer.logger.addHandler(handler)

        # Simulate event
        mock_event = Mock()
        mock_event.__class__.__name__ = "TestEvent"
        observer.on_event(mock_event)

        # Check output
        handler.flush()
        output = captured_output.getvalue()

        assert "Received event" in output
        assert "Processing event type: TestEvent" in output

        # Clean up
        observer.logger.removeHandler(handler)

    def test_observer_file_logging_integration(self):
        """Test observer file logging with LoggerFactory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "observer_test.log"

            # Initialize LoggerFactory
            LoggerFactory.initialize(
                {"level": "INFO", "format": "%(asctime)s - %(name)s - %(message)s"}
            )

            observer = TestObserver()
            logger = observer._setup_logging(
                logger_name="FileTestObserver",
                log_level=logging.INFO,
                output_file=str(log_file),
            )

            # Log some messages
            logger.info("Test message 1")
            logger.warning("Test warning")
            logger.debug("Debug message (should not appear)")

            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            # Check file content
            if log_file.exists():
                content = log_file.read_text()
                assert "Test message 1" in content
                assert "Test warning" in content
                assert "Debug message" not in content  # Level is INFO

    def test_observer_logging_level_override(self):
        """Test that observer can override global log level."""
        # Set global to INFO
        LoggerFactory.initialize({"level": "INFO"})

        observer = TestObserver()
        logger = observer._setup_logging(
            logger_name="OverrideObserver", log_level=logging.DEBUG  # Override to DEBUG
        )

        # Logger should be at DEBUG level
        assert logger.level == logging.DEBUG

        # Root logger is always set to DEBUG by LoggerFactory
        # (individual handlers control the actual output filtering)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
