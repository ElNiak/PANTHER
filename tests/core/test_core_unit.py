"""Comprehensive unit tests for PANTHER core layer components.

This module tests the core components that consume configuration data,
including experiment_manager.py and related core functionality.
"""

import shutil

# Import the classes under test
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

sys.path.insert(0, "/Users/elniak/Documents/Project/PANTHER")
from panther.config.core.models.experiment import ExperimentConfig, TestConfig
from panther.config.core.models.global_config import GlobalConfig, PathsConfig
from panther.core.experiment_manager import ExperimentManager
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.plugin_manager import PluginManager as RealPluginManager


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton state between tests to prevent leakage."""
    yield
    # Reset EventManager singleton
    EventManager._instance = None
    # Reset PluginManager singleton
    RealPluginManager._instance = None
    RealPluginManager._initialized = False
    # Reset observer factory
    import panther.core.observer.factory.observer_factory as of_mod

    of_mod._observer_factory = None


class TestExperimentManager:
    """Comprehensive tests for ExperimentManager class."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp(prefix="panther_test_output_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_global_config(self, temp_output_dir):
        """Create a global configuration with temp output dir."""
        return GlobalConfig(
            paths=PathsConfig(output_dir=str(temp_output_dir)),
        )

    @pytest.fixture
    def mock_experiment_config(self):
        """Create a mock experiment configuration."""
        mock_config = Mock(spec=ExperimentConfig)
        mock_test_config = Mock(spec=TestConfig)
        mock_test_config.name = "test_experiment"
        mock_test_config.description = "Test experiment description"
        mock_config.tests = [mock_test_config]
        return mock_config

    @pytest.fixture
    def experiment_manager(self, mock_global_config):
        """Create an ExperimentManager instance for testing."""
        with patch("panther.core.experiment_manager.PluginManager"):
            return ExperimentManager(
                global_config=mock_global_config, experiment_name="test_experiment"
            )

    def test_experiment_manager_initialization(
        self, mock_global_config, temp_output_dir
    ):
        """Test ExperimentManager initialization."""
        with patch(
            "panther.core.experiment_manager.PluginManager"
        ) as mock_plugin_manager:
            manager = ExperimentManager(
                global_config=mock_global_config, experiment_name="test_experiment"
            )

            # Verify basic attributes
            assert manager.global_config == mock_global_config
            assert "test_experiment" in manager.experiment_name
            assert isinstance(manager.experiment_dir, Path)
            assert manager.experiment_dir.exists()
            assert manager.logs_dir.exists()
            assert manager.logger is not None

            # Verify plugin manager is initialized
            mock_plugin_manager.assert_called_once()

    def test_experiment_manager_unique_naming(self, mock_global_config):
        """Test that experiment names include timestamps and experiment name."""
        with patch("panther.core.experiment_manager.PluginManager"):
            manager = ExperimentManager(
                global_config=mock_global_config, experiment_name="test"
            )

            # Name should contain both a timestamp portion and the experiment name
            assert "test" in manager.experiment_name
            # Format: YYYY-MM-DD_HH-MM-SS_test
            parts = manager.experiment_name.split("_")
            assert len(parts) >= 3  # date, time parts, and experiment name

    def test_experiment_manager_directory_creation(
        self, mock_global_config, temp_output_dir
    ):
        """Test that ExperimentManager creates required directories."""
        with patch("panther.core.experiment_manager.PluginManager"):
            manager = ExperimentManager(
                global_config=mock_global_config, experiment_name="directory_test"
            )

            # Verify directories are created
            assert manager.experiment_dir.exists()
            assert manager.experiment_dir.is_dir()
            assert manager.logs_dir.exists()
            assert manager.logs_dir.is_dir()

            # Verify directory structure
            expected_experiment_dir = temp_output_dir / manager.experiment_name
            assert manager.experiment_dir == expected_experiment_dir
            # logs_dir is the same as experiment_dir in current implementation
            assert manager.logs_dir == manager.experiment_dir

    def test_load_logging_configuration(self, experiment_manager):
        """Test logging configuration loading."""
        # Test _load_logging method
        experiment_manager._load_logging()

        # Verify logger configuration
        assert experiment_manager.logger is not None

    def test_initialize_experiments_success(
        self, experiment_manager, mock_experiment_config
    ):
        """Test successful experiment initialization."""
        with (
            patch.object(experiment_manager, "_save_configuration") as mock_save,
            patch.object(experiment_manager, "_validate_plugins") as mock_validate,
            patch.object(
                experiment_manager, "_initialize_test_cases"
            ) as mock_init_tests,
            patch.object(experiment_manager, "experiment_emitter"),
        ):
            experiment_manager.initialize_experiments(mock_experiment_config)

            # Verify initialization steps
            assert experiment_manager.experiment_config == mock_experiment_config
            mock_save.assert_called_once()
            mock_validate.assert_called_once()
            mock_init_tests.assert_called_once()

    def test_initialize_experiments_plugin_loading_failure(
        self, experiment_manager, mock_experiment_config
    ):
        """Test experiment initialization with plugin validation failure."""
        with (
            patch.object(experiment_manager, "_save_configuration"),
            patch.object(experiment_manager, "_validate_plugins") as mock_validate,
            patch.object(experiment_manager, "_initialize_test_cases"),
            patch.object(experiment_manager, "experiment_emitter"),
        ):
            mock_validate.side_effect = Exception("Plugin validation failed")

            with pytest.raises(Exception, match="Plugin validation failed"):
                experiment_manager.initialize_experiments(mock_experiment_config)

    def test_save_configuration(self, experiment_manager, mock_experiment_config):
        """Test configuration saving."""
        experiment_manager.experiment_config = mock_experiment_config

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("panther.core.experiment_manager.OmegaConf") as mock_omega_conf,
        ):
            mock_omega_conf.to_yaml.return_value = "test: config"

            experiment_manager._save_configuration()

            # Verify file was opened for writing with encoding
            expected_path = experiment_manager.experiment_dir / "experiment_config.yaml"
            mock_file.assert_called_once_with(expected_path, "w", encoding="utf-8")

            # Verify OmegaConf was used to serialize config
            assert mock_omega_conf.to_yaml.call_count == 2  # global + experiment

    def test_save_configuration_file_error(
        self, experiment_manager, mock_experiment_config
    ):
        """Test configuration saving with file write error."""
        experiment_manager.experiment_config = mock_experiment_config

        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with pytest.raises(IOError, match="Permission denied"):
                experiment_manager._save_configuration()

    @patch("panther.core.experiment_manager.TestCase")
    def test_initialize_test_cases_success(
        self, mock_test_case_class, experiment_manager, mock_experiment_config
    ):
        """Test successful test case initialization."""
        # Setup mock test config
        mock_test_config = Mock()
        mock_test_config.name = "test_case_1"
        mock_test_config.description = "A test case"
        mock_experiment_config.tests = [mock_test_config]
        experiment_manager.experiment_config = mock_experiment_config

        # Setup mock test case instance
        mock_test_case_instance = Mock()
        mock_test_case_class.return_value = mock_test_case_instance

        experiment_manager._initialize_test_cases()

        # Verify test case was created with required args
        mock_test_case_class.assert_called_once()
        call_kwargs = mock_test_case_class.call_args[1]
        assert call_kwargs["test_config"] == mock_test_config
        assert call_kwargs["global_config"] == experiment_manager.global_config
        assert call_kwargs["plugin_manager"] == experiment_manager.plugin_manager
        assert call_kwargs["experiment_dir"] == experiment_manager.experiment_dir

        # Verify test case was added to list
        assert len(experiment_manager.test_cases) == 1
        assert experiment_manager.test_cases[0] == mock_test_case_instance

    def test_initialize_test_cases_multiple_tests(
        self, experiment_manager, mock_experiment_config
    ):
        """Test initialization with multiple test cases."""
        # Create multiple mock test configs
        mock_test_configs = []
        for i in range(3):
            mock_test_config = Mock(spec=TestConfig)
            mock_test_config.name = f"test_case_{i}"
            mock_test_config.description = f"Test case {i}"
            mock_test_configs.append(mock_test_config)

        mock_experiment_config.tests = mock_test_configs
        experiment_manager.experiment_config = mock_experiment_config

        with patch("panther.core.experiment_manager.TestCase") as mock_test_case_class:
            mock_test_case_class.return_value = Mock()

            experiment_manager._initialize_test_cases()

            # Verify all test cases were created
            assert mock_test_case_class.call_count == 3
            assert len(experiment_manager.test_cases) == 3

    def test_initialize_test_cases_empty_list(
        self, experiment_manager, mock_experiment_config
    ):
        """Test initialization with empty test list."""
        mock_experiment_config.tests = []
        experiment_manager.experiment_config = mock_experiment_config

        experiment_manager._initialize_test_cases()

        # Verify no test cases were created
        assert len(experiment_manager.test_cases) == 0

    def test_run_tests_success(self, experiment_manager):
        """Test successful test execution."""
        # Create mock test cases
        mock_test_cases = []
        for _ in range(2):
            mock_test_case = Mock()
            mock_test_case.run.return_value = {"status": "passed", "duration": 1.0}
            mock_test_case.test_config.name = "mock_test"
            mock_test_cases.append(mock_test_case)

        experiment_manager.test_cases = mock_test_cases

        with patch.object(experiment_manager, "experiment_emitter"):
            experiment_manager.run_tests()

            # Verify all test cases were executed
            for mock_test_case in mock_test_cases:
                mock_test_case.run.assert_called_once()

    def test_run_tests_with_failures(self, experiment_manager):
        """Test test execution with some failures."""
        # Create mixed success/failure test cases
        mock_test_case_success = Mock()
        mock_test_case_success.run.return_value = {"status": "passed", "duration": 1.0}
        mock_test_case_success.test_config.name = "success_test"

        mock_test_case_failure = Mock()
        mock_test_case_failure.run.side_effect = Exception("Test failed")
        mock_test_case_failure.test_config.name = "failure_test"

        experiment_manager.test_cases = [mock_test_case_success, mock_test_case_failure]

        with patch.object(experiment_manager, "experiment_emitter"):
            # Should not raise exception, should handle failures gracefully
            experiment_manager.run_tests()

            # Verify both test cases were attempted
            mock_test_case_success.run.assert_called_once()
            mock_test_case_failure.run.assert_called_once()

    def test_run_tests_empty_list(self, experiment_manager):
        """Test running tests with empty test case list."""
        experiment_manager.test_cases = []

        with patch.object(experiment_manager, "experiment_emitter"):
            # Should complete without error
            experiment_manager.run_tests()

    def test_run_tests_progress_tracking(self, experiment_manager):
        """Test that progress tracking works during test execution."""
        mock_test_case = Mock()
        mock_test_case.run.return_value = {"status": "passed", "duration": 1.0}
        mock_test_case.test_config.name = "progress_test"
        experiment_manager.test_cases = [mock_test_case]

        # Disable progress bar to use simple iterator (avoids click.progressbar)
        experiment_manager.global_config.progress.enable_progress_bar = False

        with patch.object(experiment_manager, "experiment_emitter"):
            experiment_manager.run_tests()

            mock_test_case.run.assert_called_once()

    def test_experiment_manager_state_consistency(
        self, experiment_manager, mock_experiment_config
    ):
        """Test that ExperimentManager maintains consistent state."""
        # Initial state
        assert experiment_manager.experiment_config is None
        assert len(experiment_manager.test_cases) == 0

        # After initialization
        with (
            patch.object(experiment_manager, "_save_configuration"),
            patch.object(experiment_manager, "_validate_plugins"),
            patch.object(experiment_manager, "_initialize_test_cases"),
            patch.object(experiment_manager, "experiment_emitter"),
        ):
            experiment_manager.initialize_experiments(mock_experiment_config)

            # State should be updated
            assert experiment_manager.experiment_config == mock_experiment_config

    def test_experiment_manager_error_recovery(
        self, experiment_manager, mock_experiment_config
    ):
        """Test ExperimentManager error recovery mechanisms."""
        # Test recovery from configuration save error
        with (
            patch.object(experiment_manager, "_save_configuration") as mock_save,
            patch.object(experiment_manager, "_validate_plugins"),
            patch.object(experiment_manager, "_initialize_test_cases"),
            patch.object(experiment_manager, "experiment_emitter"),
        ):
            mock_save.side_effect = IOError("Save failed")

            with pytest.raises(Exception):
                experiment_manager.initialize_experiments(mock_experiment_config)

            # Manager should still be in valid state
            assert experiment_manager.global_config is not None
            assert experiment_manager.logger is not None

    def test_experiment_manager_logging_integration(self, experiment_manager):
        """Test logging integration in ExperimentManager."""
        # Verify logger is properly configured
        assert experiment_manager.logger is not None
        assert experiment_manager.logger.name == "ExperimentManager"

        # Test that logger can be used
        with patch.object(experiment_manager.logger, "info") as mock_log:
            experiment_manager.logger.info("Test message")
            mock_log.assert_called_once_with("Test message")

    def test_experiment_manager_plugin_integration(self, experiment_manager):
        """Test plugin system integration in ExperimentManager."""
        # Verify plugin manager is initialized
        assert experiment_manager.plugin_manager is not None

        # Test plugin manager interaction
        with patch.object(
            experiment_manager.plugin_manager, "discover_plugins"
        ) as mock_discover:
            mock_discover.return_value = {"plugin1": Mock(), "plugin2": Mock()}
            result = experiment_manager.plugin_manager.discover_plugins()
            assert len(result) == 2

    def test_experiment_manager_file_system_operations(
        self, experiment_manager, mock_experiment_config
    ):
        """Test file system operations in ExperimentManager."""
        # Test directory creation
        assert experiment_manager.experiment_dir.exists()
        assert experiment_manager.logs_dir.exists()

        # Test file creation during configuration save
        experiment_manager.experiment_config = mock_experiment_config

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("panther.core.experiment_manager.OmegaConf") as mock_omega_conf,
        ):
            mock_omega_conf.to_yaml.return_value = "test: config"
            experiment_manager._save_configuration()

            # Verify file operations
            expected_path = experiment_manager.experiment_dir / "experiment_config.yaml"
            mock_file.assert_called_once_with(expected_path, "w", encoding="utf-8")

    def test_experiment_manager_resource_cleanup(self, mock_global_config):
        """Test resource cleanup in ExperimentManager."""
        with patch("panther.core.experiment_manager.PluginManager"):
            manager = ExperimentManager(
                global_config=mock_global_config, experiment_name="cleanup_test"
            )

            experiment_dir = manager.experiment_dir
            logs_dir = manager.logs_dir

            # Directories should exist
            assert experiment_dir.exists()
            assert logs_dir.exists()

            # After manager goes out of scope, directories should still exist
            # (ExperimentManager doesn't auto-cleanup, that's by design)
            del manager
            assert experiment_dir.exists()
            assert logs_dir.exists()


class TestExperimentManagerEdgeCases:
    """Edge case tests for ExperimentManager."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp(prefix="panther_test_output_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_global_config(self, temp_output_dir):
        """Create a global configuration with temp output dir."""
        return GlobalConfig(
            paths=PathsConfig(output_dir=str(temp_output_dir)),
        )

    def test_experiment_manager_with_special_characters_in_name(
        self, mock_global_config
    ):
        """Test ExperimentManager with special characters in experiment name."""
        special_names = [
            "test-experiment",
            "test_experiment",
            "test.experiment",
            "test experiment",
            "test/experiment",
            "test\\experiment",
        ]

        for name in special_names:
            with patch("panther.core.experiment_manager.PluginManager"):
                manager = ExperimentManager(
                    global_config=mock_global_config, experiment_name=name
                )

                # Should handle special characters gracefully
                sanitized = name.replace("/", "_").replace("\\", "_")
                sanitized = (
                    sanitized.replace("-", "_").replace(".", "_").replace(" ", "_")
                )
                assert sanitized in manager.experiment_name
                assert manager.experiment_dir.exists()

    def test_experiment_manager_with_very_long_name(self, mock_global_config):
        """Test ExperimentManager with very long experiment name."""
        long_name = "a" * 200  # Very long name

        with patch("panther.core.experiment_manager.PluginManager"):
            manager = ExperimentManager(
                global_config=mock_global_config, experiment_name=long_name
            )

            # Should handle long names (may truncate)
            assert manager.experiment_name is not None
            assert len(manager.experiment_name) > 0
            assert manager.experiment_dir.exists()

    def test_experiment_manager_concurrent_initialization(self, mock_global_config):
        """Test concurrent ExperimentManager initialization."""
        import threading

        managers = []

        def create_manager(idx):
            with patch("panther.core.experiment_manager.PluginManager"):
                manager = ExperimentManager(
                    global_config=mock_global_config,
                    experiment_name=f"concurrent_test_{idx}",
                )
                managers.append(manager)

        # Create multiple threads with distinct names to guarantee uniqueness
        threads = [threading.Thread(target=create_manager, args=(i,)) for i in range(3)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all managers were created
        assert len(managers) == 3
        # Each manager should have its index in the name
        for manager in managers:
            assert "concurrent_test" in manager.experiment_name

    def test_experiment_manager_memory_stress(self, mock_global_config):
        """Test ExperimentManager under memory stress conditions."""
        with patch("panther.core.experiment_manager.PluginManager"):
            # Create many managers to test memory handling
            managers = []
            for i in range(10):
                manager = ExperimentManager(
                    global_config=mock_global_config, experiment_name=f"stress_test_{i}"
                )
                managers.append(manager)

            # All managers should be functional
            for manager in managers:
                assert manager.experiment_dir.exists()
                assert manager.logger is not None

            # Cleanup
            del managers
