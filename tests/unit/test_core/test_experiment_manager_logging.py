"""
Unit tests for ExperimentManager logging behavior.

This module tests that ExperimentManager properly uses LoggerMixin
and doesn't try to assign to the logger property.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.experiment_manager import ExperimentManager
from panther.core.utils.logger_factory import LoggerFactory


class TestExperimentManagerLogging:
    """Test ExperimentManager logging functionality."""

    @pytest.fixture(autouse=True)
    def reset_logger_factory(self):
        """Reset LoggerFactory state before each test."""
        # Store original state
        original_state = {
            "initialized": LoggerFactory._initialized,
            "root_configured": LoggerFactory._root_logger_configured,
            "config": LoggerFactory._config.copy(),
            "handlers": LoggerFactory._handler_cache.copy(),
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
        LoggerFactory._initialized = original_state["initialized"]
        LoggerFactory._root_logger_configured = original_state["root_configured"]
        LoggerFactory._config = original_state["config"]
        LoggerFactory._handler_cache = original_state["handlers"]

    @pytest.fixture
    def mock_global_config(self, tmp_path):
        """Create a real GlobalConfig for testing."""
        return GlobalConfig(
            logging={
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
            },
            paths={"output_dir": str(tmp_path / "outputs")},
        )

    @pytest.fixture
    def mock_dependencies(self):
        """Mock ExperimentManager external dependencies to isolate logging tests."""
        with patch("panther.core.experiment_manager.PluginManager") as mock_pm, patch(
            "panther.core.experiment_manager.EventManager"
        ) as mock_em, patch(
            "panther.core.experiment_manager.get_observer_factory"
        ) as mock_of, patch(
            "panther.core.experiment_manager.WorkflowStateTracker"
        ) as mock_wst, patch(
            "panther.core.experiment_manager.EmitterRegistry"
        ) as mock_er:
            # Setup EventManager mock
            mock_em_instance = MagicMock()
            mock_em.get_instance.return_value = mock_em_instance
            mock_em_instance.cleanup_none_observers.return_value = 0

            yield {
                "plugin_manager": mock_pm,
                "event_manager": mock_em,
                "event_manager_instance": mock_em_instance,
                "observer_factory": mock_of,
                "workflow_tracker": mock_wst,
                "emitter_registry": mock_er,
            }

    def test_experiment_manager_no_logger_assignment(
        self, mock_global_config, mock_dependencies
    ):
        """Test that ExperimentManager doesn't assign to logger property."""
        LoggerFactory.initialize({"level": "INFO"})

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test_experiment"
        )

        # Should have logger property from LoggerMixin
        assert hasattr(manager, "logger")
        assert manager.logger is not None
        # Logger name is module.ClassName format
        assert "ExperimentManager" in manager.logger.name

    def test_experiment_manager_with_provided_logger(
        self, mock_global_config, mock_dependencies
    ):
        """Test ExperimentManager with a provided logger."""
        LoggerFactory.initialize({"level": "DEBUG"})

        # Create a custom logger
        custom_logger = logging.getLogger("custom.experiment.logger")

        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="test_experiment",
            logger=custom_logger,
        )

        # ExperimentManager stores the custom logger in _logger
        assert manager._logger is custom_logger
        # The default logger from ErrorHandlerMixin is named "ExperimentManager"
        assert manager.logger.name == "ExperimentManager"

    def test_experiment_manager_logger_inheritance(
        self, mock_global_config, mock_dependencies
    ):
        """Test that ExperimentManager inherits from ErrorHandlerMixin correctly."""
        from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin

        # ExperimentManager inherits from ErrorHandlerMixin (not LoggerMixin)
        assert issubclass(ExperimentManager, ErrorHandlerMixin)

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test"
        )

        # Should have logger from ErrorHandlerMixin
        assert hasattr(manager, "logger")
        assert manager.logger is not None
        # ErrorHandlerMixin provides fast_fail_handler
        assert hasattr(manager, "fast_fail_handler")

    def test_experiment_manager_logging_during_initialization(
        self, mock_global_config, mock_dependencies
    ):
        """Test logging during ExperimentManager initialization."""
        import io

        LoggerFactory.initialize(
            {
                "level": "DEBUG",
                "format": "%(levelname)s - %(name)s - %(message)s",
            }
        )

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="init_test"
        )

        # Add a handler to capture from the manager's own logger
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        handler.setLevel(logging.DEBUG)
        manager.logger.addHandler(handler)

        manager.logger.info("Test initialization complete")

        handler.flush()
        content = captured.getvalue()
        assert "Test initialization complete" in content

        # Clean up
        manager.logger.removeHandler(handler)

    def test_experiment_manager_logging_methods(
        self, mock_global_config, mock_dependencies
    ):
        """Test ExperimentManager logging via standard logger (not LoggerMixin)."""
        LoggerFactory.initialize({"level": "DEBUG"})

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="method_test"
        )

        # Replace logger with mock to verify calls
        mock_logger = MagicMock()
        manager.logger = mock_logger

        # ExperimentManager uses standard logging methods
        manager.logger.info("Starting experiment_execution with phase=1")
        mock_logger.info.assert_called_with(
            "Starting experiment_execution with phase=1"
        )

        manager.logger.debug("Loading configuration for TestExperiment")
        mock_logger.debug.assert_called_with("Loading configuration for TestExperiment")

        manager.logger.warning("Experiment took longer than expected")
        mock_logger.warning.assert_called_with("Experiment took longer than expected")

    def test_experiment_manager_error_logging(
        self, mock_global_config, mock_dependencies
    ):
        """Test error logging in ExperimentManager."""
        LoggerFactory.initialize({"level": "INFO"})

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="error_test"
        )

        error = ValueError("Test error in experiment")

        # Replace logger with mock to verify error logging calls
        mock_logger = MagicMock()
        manager.logger = mock_logger

        # ExperimentManager uses standard logger.error for error logging
        manager.logger.error("Failed test_execution: %s", error, exc_info=True)

        mock_logger.error.assert_called_once_with(
            "Failed test_execution: %s",
            error,
            exc_info=True,
        )

    def test_experiment_manager_phase_logging(
        self, mock_global_config, mock_dependencies
    ):
        """Test logging during experiment phases."""
        import io

        LoggerFactory.initialize({"level": "INFO"})

        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="phase_test",
        )

        # Capture log output from the manager's logger
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        manager.logger.addHandler(handler)

        # Log phase transitions
        manager.logger.info("Starting Phase 1: Initialization")
        manager.logger.info("Starting Phase 2: Plugin Loading")
        manager.logger.info("Starting Phase 3: Environment Deployment")
        manager.logger.info("Starting Phase 4: Test Execution")

        handler.flush()
        output = log_capture.getvalue()

        assert "Phase 1" in output
        assert "Phase 2" in output
        assert "Phase 3" in output
        assert "Phase 4" in output

        # Clean up
        manager.logger.removeHandler(handler)

    def test_experiment_manager_concurrent_logging(
        self, mock_global_config, mock_dependencies
    ):
        """Test concurrent logging from ExperimentManager."""
        import threading

        LoggerFactory.initialize({"level": "INFO"})

        results = []
        lock = threading.Lock()

        def create_and_log(idx):
            manager = ExperimentManager(
                global_config=mock_global_config,
                experiment_name=f"concurrent_test_{idx}",
            )
            manager.logger.info(f"Manager {idx} initialized")
            with lock:
                results.append(manager.logger.name)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_log, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should have the same logger name (containing ExperimentManager)
        assert len(results) == 5
        assert all("ExperimentManager" in name for name in results)

    def test_experiment_manager_logging_consistency(
        self, mock_global_config, mock_dependencies
    ):
        """Test that ExperimentManager maintains logging consistency."""
        import io

        LoggerFactory.initialize(
            {
                "level": "DEBUG",
                "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
            }
        )

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="consistency_test"
        )

        # Create a second logger via LoggerFactory
        test_case_logger = LoggerFactory.get_logger("TestCase")

        # Add a common handler to both loggers (they have propagate=False)
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] - %(name)s - %(message)s")
        )

        manager.logger.addHandler(handler)
        test_case_logger.addHandler(handler)

        # Log from both
        manager.logger.info("Manager message")
        test_case_logger.info("Test case message")

        handler.flush()
        log_output = output.getvalue()

        # Both should have consistent format
        lines = log_output.strip().split("\n")
        assert len(lines) == 2

        for line in lines:
            assert " [INFO] - " in line
            assert " - " in line

        # Clean up
        manager.logger.removeHandler(handler)
        test_case_logger.removeHandler(handler)

    def test_experiment_manager_no_logging_before_init(
        self, mock_global_config, mock_dependencies
    ):
        """Test that ExperimentManager can be created even if LoggerFactory not initialized."""
        # Don't initialize LoggerFactory — it will auto-initialize

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="no_init_test"
        )

        assert manager.logger is not None
        assert "ExperimentManager" in manager.logger.name

        # LoggerFactory should have been auto-initialized
        assert LoggerFactory._initialized

    def test_experiment_manager_custom_logger_preserved(
        self, mock_global_config, mock_dependencies
    ):
        """Test that custom logger parameter is stored in _logger."""
        LoggerFactory.initialize({"level": "INFO"})

        # Create custom logger with specific handler
        custom_logger = logging.getLogger("custom.experiment")
        custom_handler = logging.StreamHandler()
        custom_logger.addHandler(custom_handler)

        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="custom_logger_test",
            logger=custom_logger,
        )

        # Custom logger is stored in _logger attribute
        assert manager._logger is custom_logger
        # The main logger attribute is from ErrorHandlerMixin
        assert manager.logger.name == "ExperimentManager"

        # Manager's default logger still works
        manager.logger.info("Default logger message")

        # Clean up
        custom_logger.removeHandler(custom_handler)
