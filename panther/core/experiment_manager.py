"""Experiment manager for PANTHER framework.

This module contains the ExperimentManager class which manages the lifecycle
of experiments including initialization, configuration, and execution.
"""


import contextlib
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml
from colorlog import ColoredFormatter
from omegaconf import OmegaConf

from panther.config.core.models import ExperimentConfig, GlobalConfig
from panther.core.events.emitter_registry import EmitterRegistry
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions.experiment_exceptions import (
    ExperimentInitializationError,
    PantherExperimentError,
    PluginValidationError,
    TestCaseInitializationError,
    TestExecutionError,
)
from panther.core.exceptions.fast_fail import (
    CertificateException,
    ConfigurationException,
    DockerComposeException,
    FastFailHandler,
    IvyCompilationException,
    PortConflictException,
    ResourceExhaustionException,
    TimeoutCascadeException,
)
from panther.core.experiment_analysis import ExperimentAnalysisMixin
from panther.core.experiment_observer import ExperimentObserverMixin
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.metrics.enums import Phase
from panther.core.observer.factory import get_observer_factory
from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.workflow import (  # pylint: disable=import-outside-toplevel
    WorkflowStateTracker,
)
from panther.core.test_cases.test_case_impl import TestCase
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.utils.logger_factory import LoggerFactory
from panther.plugins.plugin_manager import PluginManager


# TODO implement errors management strategy (e.g., retry, fail, etc.)
class ExperimentManager(
    ErrorHandlerMixin, ExperimentObserverMixin, ExperimentAnalysisMixin
):
    """Orchestrate experiment lifecycle with event-driven coordination.

    ExperimentManager implements the Facade pattern, coordinating multiple subsystems for
    reproducible network protocol testing. The class provides centralized control over
    experiment initialization, execution, monitoring, and cleanup.

    This class is the primary entry point for running PANTHER experiments and manages
    the complete lifecycle from configuration validation to result collection.

    Args:
        global_config: Global configuration containing paths and defaults.
        experiment_name: Optional name for the experiment (sanitized automatically).
        plugin_dir: Directory containing plugin implementations.
        logger: Optional logger instance (creates default if None).
        metrics_collector: Optional metrics collection system.
        fast_fail_enabled: Whether to terminate on critical errors.
        dry_run: Execute in validation mode without running actual tests.

    Attributes:
        global_config (GlobalConfig): Global configuration for the experiment.
        experiment_name (str): Sanitized experiment identifier with timestamp.
        experiment_dir (Path): Output directory for experiment artifacts.
        plugin_manager (PluginManager): Plugin discovery and management system.
        test_cases (List[ITestCase]): Configured test scenarios for execution.
        event_manager (EventManager): Central event coordination system.
        fast_fail_handler (FastFailHandler): Critical error management system.

    Raises:
        ExperimentInitializationError: When configuration validation fails.
        PluginValidationError: When required plugins cannot be loaded.
        TestCaseInitializationError: When test cases cannot be created.

    Examples:
        >>> config = GlobalConfig.load("config.yaml")
        >>> manager = ExperimentManager(config, experiment_name="quic_test")
        >>> manager.initialize_experiments(experiment_config)
        >>> manager.run_tests()
        >>> manager.cleanup()

        Using as context manager:
        >>> with ExperimentManager(config) as manager:
        ...     manager.initialize_experiments(experiment_config)
        ...     manager.run_tests()

    Note:
        - Not thread-safe: designed for single-threaded execution
        - Uses event-driven architecture for loose coupling between components
        - Implements observer pattern for extensible monitoring and analysis
        - Resource cleanup happens automatically when used as context manager

    Architecture:
        The manager coordinates four main phases:
        1. Initialization: Plugin validation and observer setup
        2. Preparation: Test case creation and environment validation
        3. Execution: Progress-tracked test running with error recovery
        4. Cleanup: Resource teardown and result aggregation
    """

    def __init__(
        self,
        global_config: GlobalConfig,
        experiment_name: str = None,
        plugin_dir: str = "panther/plugins/",
        logger: logging.Logger = None,
        metrics_collector: Optional[MetricsCollector] = None,
        fast_fail_enabled: bool = True,
        dry_run: bool = False,
    ):
        # Initialize parent class
        super().__init__()

        self.experiment_config = None
        self.global_config = global_config
        self.metrics_collector = metrics_collector
        self.dry_run = dry_run
        if experiment_name:
            experiment_name = re.sub(r"[^a-zA-Z0-9_]", "_", experiment_name.strip())
            experiment_name = re.sub(r"_+", "_", experiment_name)

        self.experiment_name = (
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{experiment_name}"
            if experiment_name
            else f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        self.experiment_dir = (
            Path(global_config.paths.output_dir) / self.experiment_name
        )
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        # Handle logging level - could be string or enum
        level_name = (
            self.global_config.logging.level.name
            if hasattr(self.global_config.logging.level, "name")
            else str(self.global_config.logging.level)
        )
        self.log_level = getattr(logging, level_name, logging.INFO)
        self.log_format = self.global_config.logging.format

        logging_config = {
            "level": (
                self.global_config.logging.level.name
                if hasattr(self.global_config.logging.level, "name")
                else str(self.global_config.logging.level)
            ),
            "format": self.global_config.logging.format,
            "enable_colors": getattr(self.global_config.logging, "enable_colors", True),
            "feature_levels": getattr(
                self.global_config.logging, "feature_levels", None
            ),
        }
        LoggerFactory.initialize(logging_config)

        # Update any existing loggers with the new feature levels
        # This handles loggers created during config loading before LoggerFactory was initialized
        self.configure_logging_features()

        # Initialize log statistics if enabled
        self.log_statistics_display = None
        self._setup_log_statistics()

        self.logs_dir = self.experiment_dir
        self.plugin_dir = plugin_dir
        # Don't assign to self.logger directly as it's a property from LoggerMixin
        if logger:
            self._logger = logger
        self._load_logging()

        # Configure fast fail handler based on global config
        fast_fail_config = global_config.fast_fail
        self.fast_fail_handler = FastFailHandler(
            enabled=fast_fail_enabled and fast_fail_config.enabled, logger=self.logger
        )
        self.plugin_dir = Path(plugin_dir)

        # Initialize event manager for experiment-level events
        self.event_manager = EventManager.get_instance()
        factory = get_observer_factory(self.global_config)
        factory.set_event_manager(self.event_manager)

        # Initialize workflow state tracker for experiment coordination
        self.workflow_tracker = WorkflowStateTracker()

        # Initialize centralized emitter registry
        self.emitter_registry = EmitterRegistry(self.event_manager)

        # Access emitters through the registry
        self.experiment_emitter = self.emitter_registry.experiment_emitter
        self.service_emitter = self.emitter_registry.service_emitter
        self.environment_emitter = self.emitter_registry.environment_emitter
        self.metrics_emitter = self.emitter_registry.metrics_emitter
        self.plugin_emitter = self.emitter_registry.plugin_emitter

        # Setup plugin manager with event manager and fast fail handler
        self.plugin_manager = PluginManager(
            plugin_directories=None,  # Use default plugin directories
            event_manager=self.event_manager,
            global_config=self.global_config,
            fast_fail_handler=self.fast_fail_handler,
            experiment_context=self,
        )

        self._setup_observers()

        # Clean up any None observers that might exist
        cleaned = self.event_manager.cleanup_none_observers()
        if cleaned > 0:
            self.logger.info(
                "Cleaned up %d None observers during initialization", cleaned
            )

        self.test_cases: List[ITestCase] = []

    def configure_logging_features(self):
        if (
            not hasattr(self.global_config.logging, "feature_levels")
            or not self.global_config.logging.feature_levels
        ):
            return
        feature_levels_dict = {}
        # Convert feature_levels dataclass to dictionary
        if hasattr(self.global_config.logging.feature_levels, "__dict__"):
            self.logger.debug(
                f"Feature_levels in global_config: {list(list(self.global_config.logging.feature_levels.__dict__.items())[:3])}"
            )
            for (
                attr_name,
                attr_value,
            ) in self.global_config.logging.feature_levels.__dict__.items():
                # Skip None values and omega_config
                if attr_value is None or attr_name == "_omega_config":
                    continue
                if hasattr(attr_value, "name"):  # It's an enum
                    feature_levels_dict[attr_name] = attr_value.name
                else:
                    feature_levels_dict[attr_name] = str(attr_value)
        # Only update if we have actual feature levels to set
        if feature_levels_dict:
            LoggerFactory.update_all_feature_levels(feature_levels_dict)

    def initialize_experiments(self, experiment_config: ExperimentConfig) -> None:
        """Initialize experiment with plugins, environment validation, and test case setup.

        This method orchestrates the complete experiment initialization lifecycle:
        1. Configuration validation and persistence
        2. Plugin loading and validation using PluginManager
        3. Test case initialization with shared emitter registry
        4. Event emission for state tracking through observers

        The method implements comprehensive error handling for different failure modes:
        - PluginValidationError: Missing or incompatible plugins
        - ImportError/ModuleNotFoundError: Missing dependencies
        - TestCaseInitializationError: Test configuration issues

        **Architecture Integration**:
        - Uses EventManager + EmitterRegistry for loose coupling
        - StateEventObserver automatically handles workflow state transitions
        - Plugin validation prevents runtime failures during test execution

        Args:
            experiment_config: Complete experiment configuration including tests,
                              plugins, and execution parameters

        Raises:
            ExperimentInitializationError: When initialization fails at any stage
            PluginValidationError: When required plugins are missing or incompatible
            TestCaseInitializationError: When test cases cannot be initialized

        Events Emitted:
            - experiment.initialized: When basic setup completes
            - experiment.plugin_loading_started/completed: During plugin phase
            - experiment.test_cases_initialized: When all tests are ready
            - experiment.finished_early: On any initialization failure
        """
        try:
            # State tracking now happens automatically through events

            self.experiment_config = experiment_config
            self._save_configuration()

            # Emit experiment initialized event using the experiment emitter
            self.experiment_emitter.emit_initialized(
                config={
                    "experiment_name": self.experiment_name,
                    "test_count": len(experiment_config.tests),
                }
            )

            # State transitions are handled automatically by StateEventObserver

            # Emit plugin loading started event
            self.experiment_emitter.emit_plugin_loading_started()

            # Validate plugins before loading
            self._validate_plugins()

            # Emit plugin loading completed event
            self.experiment_emitter.emit_plugin_loading_completed()

            self._initialize_test_cases()

            # Emit test cases initialized event to trigger workflow transition
            test_names = [test.test_config.name for test in self.test_cases]
            self.experiment_emitter.emit_test_cases_initialized(
                test_count=len(self.test_cases), test_names=test_names
            )

        except PluginValidationError as e:
            # Handle plugin validation errors specifically
            self.logger.error("Plugin validation failed: %s", e)
            # State transitions are handled automatically by StateEventObserver
            self.experiment_emitter.emit_finished_early(
                reason="Plugin Validation Failed",
                details={
                    "phase": "initialization",
                    "error": str(e),
                    "type": "PluginValidationError",
                },
            )
            raise
        except (ImportError, ModuleNotFoundError) as e:
            # Handle import-related errors separately
            # State transitions are handled automatically by StateEventObserver
            # Emit experiment finished early event with error details
            self.experiment_emitter.emit_finished_early(
                reason=f"Import Error: {type(e).__name__}",
                details={
                    "phase": "initialization",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "details": "Failed to import a required module",
                },
            )

            self.logger.error(
                "Initialization failed due to import error: %s", e, exc_info=True
            )
            raise ExperimentInitializationError(f"Import error: {str(e)}") from e

        # We need to catch all exceptions to properly handle them as initialization errors
        except Exception as e:  # pylint: disable=broad-except
            # State transitions are handled automatically by StateEventObserver

            # Emit experiment finished early event with error details
            self.experiment_emitter.emit_finished_early(
                reason=f"Initialization Error: {type(e).__name__}",
                details={
                    "phase": "initialization",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            self.logger.error("Initialization failed: %s", e, exc_info=True)
            raise ExperimentInitializationError(
                f"Failed to initialize experiment: {str(e)}"
            ) from e

    def _validate_plugins(self):
        """
        Validate that all required plugins are available and compatible
        before attempting to run the experiment.
        """
        self.logger.info("Validating plugins for experiment...")

        # Use PluginManager's validation method
        (
            is_valid,
            errors,
        ) = self.plugin_manager.validate_experiment_plugins(self.experiment_config)

        if not is_valid:
            error_message = "Plugin validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            self.logger.error(error_message)

            # Log additional helpful information
            available_plugins = self.plugin_manager.plugins
            self.logger.info("Available plugins:")
            for plugin_type, plugins in available_plugins.items():
                self.logger.info("  %s: %s", plugin_type, plugins)

            raise PluginValidationError(error_message)

        self.logger.info("All required plugins validated successfully")

    def _save_configuration(self):
        """Save the experiment configuration file in the experiment folder."""
        config_file_path = self.experiment_dir / "experiment_config.yaml"
        with open(config_file_path, "w", encoding="utf-8") as config_file:
            # Convert Pydantic models to dicts for OmegaConf compatibility
            global_config_dict = (
                self.global_config.dict()
                if hasattr(self.global_config, "dict")
                else self.global_config
            )
            experiment_config_dict = (
                self.experiment_config.dict()
                if hasattr(self.experiment_config, "dict")
                else self.experiment_config
            )

            config_file.write("# Global Configuration\n")
            config_file.write(OmegaConf.to_yaml(global_config_dict))
            config_file.write("\n# Experiment Configuration\n")
            config_file.write(OmegaConf.to_yaml(experiment_config_dict))

    def _save_test_configuration(self, test_config, test_dir: Path):
        """Save a complete test configuration file for a specific test.

        Args:
            test_config: The test configuration object
            test_dir: Directory path for the test output
        """
        try:
            # Ensure test directory exists
            test_dir.mkdir(parents=True, exist_ok=True)

            # Create test config file path
            config_file_path = test_dir / "test_config.yaml"

            # Convert configurations to dictionaries with enum handling
            def convert_config_for_yaml(config):
                """Convert a config object to a YAML-serializable dictionary."""
                if hasattr(config, "dict"):
                    config_dict = config.dict()
                else:
                    config_dict = config

                # Use json.loads(json.dumps()) to handle enum serialization properly
                import json

                return json.loads(json.dumps(config_dict, default=str))

            global_config_dict = convert_config_for_yaml(self.global_config)
            test_config_dict = convert_config_for_yaml(test_config)

            # Create complete self-contained test configuration
            complete_config = {
                "metadata": {
                    "test_name": test_config.name,
                    "timestamp": datetime.now().isoformat(),
                    "panther_version": getattr(self, "version", "unknown"),
                    "experiment_name": self.experiment_name,
                    "source_file": str(getattr(self, "experiment_file", "unknown")),
                },
                "global_config": global_config_dict,
                "test_config": test_config_dict,
            }

            # Save the test configuration
            with open(config_file_path, "w", encoding="utf-8") as config_file:
                yaml.dump(
                    complete_config, config_file, default_flow_style=False, indent=2
                )

            self.logger.info(f"Saved test configuration to: {config_file_path}")

        except Exception as e:
            self.logger.error(f"Failed to save test configuration: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            test_count = len(self.experiment_config.tests)
            test_names = [test.name for test in self.experiment_config.tests]
            
            test_index = 0

            for test_config in self.experiment_config.tests:
                self.logger.info("Initializing test case: %s", test_config.name)

                # Get or create a test-specific emitter for this test case
                test_specific_emitter = self.emitter_registry.get_test_emitter(
                    test_config.name
                )

                # Emit test initialization start event with test-specific emitter
                test_specific_emitter.emit_created(
                    test_name=test_config.name,
                    description=test_config.description,
                    config={"phase": "initialization"},
                )

                # Create the test case with shared emitter registry and workflow tracker
                test_case = TestCase(
                    test_config=test_config,
                    global_config=self.global_config,
                    plugin_manager=self.plugin_manager,
                    experiment_dir=self.experiment_dir,
                    metrics_collector=self.metrics_collector,
                    emitter_registry=self.emitter_registry,
                    workflow_tracker=self.workflow_tracker,
                    test_index=test_index,
                )
                test_index += 1
                self.logger.info("Initialized test case '%s'", test_case)
                self.test_cases.append(test_case)

                # Test initialization is already tracked by emit_created above

            # Summary of test case initialization is handled at experiment level
            self.logger.debug("Initialized %d test cases: %s", test_count, test_names)

            self.logger.info("Initialized %s test cases.", len(self.test_cases))

        # We need to catch all exceptions to properly handle them as test initialization errors
        except Exception as e:  # pylint: disable=broad-except
            # Emit experiment finished early event with error details
            self.experiment_emitter.emit_finished_early(
                reason=f"Test Case Initialization Error: {type(e).__name__}",
                details={
                    "phase": "test_case_initialization",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            self.logger.error("Failed to initialize test cases: %s", e, exc_info=True)
            raise TestCaseInitializationError(
                f"Failed to initialize test cases: {str(e)}"
            ) from e

    def run_tests(self) -> bool:
        """Execute all test cases with comprehensive progress tracking and error handling.

        Implements the core test execution loop with:
        - Progress bar integration (tqdm) with configurable logging redirection
        - Per-test error handling with fast-fail capability for critical errors
        - Event emission for detailed test lifecycle tracking
        - Cleanup of test-scoped observers between test executions

        **Fast-fail behavior** triggers on critical errors:
        - DockerComposeException: Container orchestration failures
        - PortConflictException: Network resource conflicts
        - ResourceExhaustionException: System resource limits
        - IvyCompilationException: Protocol compilation failures

        **Error Handling Strategy**:
        - Individual test failures don't stop experiment execution
        - Critical infrastructure errors terminate entire experiment
        - All errors are tracked through event emission for analysis
        - Test-scoped observers are cleaned up after each test

        **Progress Tracking**:
        - Configurable tqdm progress bar with status updates
        - Optional emoji support for visual feedback
        - Logging redirection through tqdm to prevent progress corruption
        - Real-time status updates for test start/completion/failure

        Returns:
            bool: True if any tests succeeded, False if all failed

        Raises:
            TestExecutionError: When execution infrastructure fails
            KeyboardInterrupt: On user interruption (propagated)
            Critical exceptions: On fast-fail conditions (DockerComposeException, etc.)

        Events Emitted:
            - experiment.execution_started: Before test loop begins
            - test.execution_started: For each individual test
            - test.completed/failed: Based on test outcomes
            - experiment.finished_early: On critical failures
        """
        try:
            # State transitions are handled automatically by StateEventObserver

            # Emit execution started event to trigger proper workflow transition
            self.experiment_emitter.emit_execution_started(
                test_count=len(self.test_cases)
            )

            # Track experiment start in metrics
            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "experiments_total", phase=Phase.TEST_EXECUTION
                )

            # Experiment-level execution tracking is handled by experiment_emitter
            if self.dry_run:
                self.logger.info(
                    "DRY-RUN: Would execute %d test cases for experiment: %s",
                    len(self.test_cases),
                    self.experiment_name,
                )
                return self._perform_dry_run()
            else:
                self.logger.info(
                    "Starting test execution for experiment: %s", self.experiment_name
                )

            # Initialize test counters before progress handling
            successful_tests = 0
            failed_tests = 0

            # Use Click progress bar if enabled, otherwise use a simple iterator
            if self.global_config.progress.enable_progress_bar:
                self.logger.debug("Using Click progress bar for test execution")

                # Click progress bar context
                progress_context = click.progressbar(
                    self.test_cases,
                    length=len(self.test_cases),
                    label="Running test cases",
                    show_eta=True,
                    show_percent=True,
                    show_pos=True,
                    file=sys.stdout,
                    color=True,
                )
            else:
                self.logger.debug("Progress bar disabled, using simple iterator")

                # Simple iterator wrapper for compatibility
                class SimpleProgressIterator:
                    def __init__(self, iterable):
                        self.iterable = iterable
                        self.current_test = None

                    def __iter__(self):
                        return iter(self.iterable)

                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        pass

                    def update_label(self, label):
                        # No-op for simple iterator
                        pass

                progress_context = SimpleProgressIterator(self.test_cases)

            with progress_context as progress_bar:
                for i, test_case in enumerate(self.test_cases):
                    # Update progress bar label for Click progress bar
                    if self.global_config.progress.enable_progress_bar:
                        # Click progress bar handles the iteration automatically
                        # We'll update the label if needed
                        progress_bar.label = f"Test {i+1}/{len(self.test_cases)} - {test_case.test_config.name}"

                    # Show important status updates (configurable)
                    if self.global_config.progress.show_test_status:
                        emoji = "🧪 " if self.global_config.progress.use_emojis else ""
                        self.logger.info(
                            f"{emoji}Starting: {test_case.test_config.name}"
                        )
                    self.logger.info(
                        "Running test case: %s", test_case.test_config.name
                    )

                    # Get test-specific emitter for this test case
                    test_specific_emitter = self.emitter_registry.get_test_emitter(
                        test_case.test_config.name
                    )

                    # Emit test execution started event
                    test_specific_emitter.emit_execution_started(
                        steps=["setup", "execute", "assertions", "teardown"]
                    )
                    try:
                        # Save test-specific configuration before execution
                        self._save_test_configuration(
                            test_case.test_config, test_case.test_experiment_dir
                        )

                        self.logger.info(
                            "Executing test case: %s", test_case.test_config.name
                        )
                        test_result = test_case.run()

                        # Click progress bar updates automatically via iteration

                        # Check if test actually passed (returns None or True for success, False for failure)
                        if test_result is False:
                            failed_tests += 1
                            if self.metrics_collector:
                                self.metrics_collector.increment_counter(
                                    "test_cases_total", phase=Phase.TEST_EXECUTION
                                )
                                self.metrics_collector.increment_counter(
                                    "test_cases_failed", phase=Phase.TEST_EXECUTION
                                )
                            if self.global_config.progress.show_test_status:
                                emoji = (
                                    "❌ "
                                    if self.global_config.progress.use_emojis
                                    else ""
                                )
                                self.logger.info(
                                    f"{emoji}Failed: {test_case.test_config.name} - Test analysis failed"
                                )
                            # Emit test failed event
                            test_specific_emitter.emit_failed(
                                error_message="Test analysis failed",
                                error_type="TestAnalysisFailure",
                                phase="analysis",
                                summary={
                                    "test_name": test_case.test_config.name,
                                    "reason": "Tester analysis determined test failure",
                                },
                            )
                            continue

                        successful_tests += 1
                        if self.metrics_collector:
                            self.metrics_collector.increment_counter(
                                "test_cases_total", phase=Phase.TEST_EXECUTION
                            )
                            self.metrics_collector.increment_counter(
                                "test_cases_successful", phase=Phase.TEST_EXECUTION
                            )
                        if self.global_config.progress.show_test_status:
                            emoji = (
                                "✅ " if self.global_config.progress.use_emojis else ""
                            )
                            self.logger.info(
                                f"{emoji}Completed: {test_case.test_config.name}"
                            )

                        # Emit test completed successfully event
                        test_specific_emitter.emit_completed(
                            summary={
                                "status": "success",
                                "test_name": test_case.test_config.name,
                            }
                        )

                    except (KeyboardInterrupt, SystemExit):
                        # Handle interrupted test - Click progress bar handles iteration automatically

                        # Emit interrupted test event
                        self.logger.warning(
                            "Test interrupted: %s",
                            test_case.test_config.name,
                            exc_info=True,
                        )
                        test_specific_emitter.emit_failed(
                            error_message="Test interrupted",
                            error_type="KeyboardInterrupt",
                            phase="execution",
                        )
                        raise  # Re-raise to break out of the loop

                    except (
                        TestCaseInitializationError,
                        TestExecutionError,
                        ValueError,
                        TypeError,
                        AttributeError,
                        RuntimeError,
                        OSError,
                        PantherExperimentError,
                        subprocess.CalledProcessError,
                        DockerComposeException,
                        PortConflictException,
                        IvyCompilationException,
                        ResourceExhaustionException,
                        CertificateException,
                        ConfigurationException,
                        TimeoutCascadeException,
                    ) as test_error:
                        # Handle all expected error types with a single handler
                        failed_tests += 1
                        if self.metrics_collector:
                            self.metrics_collector.increment_counter(
                                "test_cases_total", phase=Phase.TEST_EXECUTION
                            )
                            self.metrics_collector.increment_counter(
                                "test_cases_failed", phase=Phase.TEST_EXECUTION
                            )

                        # Click progress bar handles iteration automatically

                        self.record_failed_test(test_case, test_error)

                        # Check for critical errors that should terminate experiment
                        if isinstance(
                            test_error,
                            (
                                DockerComposeException,
                                PortConflictException,
                                IvyCompilationException,
                                ResourceExhaustionException,
                                CertificateException,
                            ),
                        ):
                            # Use fast-fail handler to determine if we should continue
                            should_continue = self.fast_fail_handler.handle_error(
                                test_error, raise_on_critical=False
                            )
                            if not should_continue:
                                self.logger.critical(
                                    "Critical %s error in test %s, terminating experiment",
                                    test_error.category.value,
                                    test_case.test_config.name,
                                )
                                # Emit experiment failure and re-raise to stop execution
                                self.experiment_emitter.emit_finished_early(
                                    reason=f"Critical {test_error.category.value} Failure",
                                    details={
                                        "test_name": test_case.test_config.name,
                                        "error_type": type(test_error).__name__,
                                        "error_category": test_error.category.value,
                                        "error_context": test_error.context,
                                    },
                                )
                                raise test_error  # This will break out of the test loop

                        # Add recursion protection for AttributeError
                        if isinstance(
                            test_error, AttributeError
                        ) and "emit_service_setup_completed" in str(test_error):
                            self.logger.error(
                                "Test case %s failed due to missing event emitter method: %s",
                                test_case.test_config.name,
                                str(test_error),
                            )
                            # Emit a simple failed event without triggering more errors
                            with contextlib.suppress(Exception):
                                test_specific_emitter.emit_failed(
                                    error_message=str(test_error),
                                    error_type="AttributeError",
                                    phase="setup",
                                )
                        else:
                            self._handle_test_error(test_case, test_error)
                            # Continue with other tests unless critical error occurred

                    except Exception as test_error:  # pylint: disable=broad-except
                        # Generic error handling as a fallback
                        # This is necessary to ensure all tests run even if some fail
                        failed_tests += 1
                        self._handle_test_error(test_case, test_error)
                        self.logger.warning(
                            "Unexpected error type %s caught. Consider adding specific handling.",
                            type(test_error).__name__,
                        )

                    finally:
                        # Clean up test-specific observers after each test completes
                        # This prevents observer duplication when multiple tests run
                        try:
                            self.event_manager.cleanup_scoped_observers("test")
                            self.logger.debug(
                                "Cleaned up test-scoped observers for test: %s",
                                test_case.test_config.name,
                            )
                        except (
                            Exception
                        ) as cleanup_error:  # pylint: disable=broad-except
                            self.logger.warning(
                                "Failed to cleanup test observers for %s: %s",
                                test_case.test_config.name,
                                cleanup_error,
                            )

            self.logger.info("")  # Add final newline for clean output formatting

            # Track experiment outcome in metrics
            if self.metrics_collector:
                if failed_tests == 0:
                    self.metrics_collector.increment_counter(
                        "experiments_successful", phase=Phase.TEST_EXECUTION
                    )
                else:
                    self.metrics_collector.increment_counter(
                        "experiments_failed", phase=Phase.TEST_EXECUTION
                    )

            # Experiment-level summary is handled by experiment_emitter
            self.logger.info(
                "Experiment execution summary - Total: %d, Success: %d, Failed: %d",
                len(self.test_cases),
                successful_tests,
                failed_tests,
            )

            self.logger.info(
                "All experiment tests completed. Success: %s, Failed: %s",
                successful_tests,
                failed_tests,
            )

            return successful_tests > 0

        except (KeyboardInterrupt, SystemExit):
            self.logger.warning(
                "Experiment execution interrupted by user", exc_info=True
            )
            # Just re-raise these exceptions
            raise

        except Exception as e:
            # Emit test execution failed event with all necessary information for metrics
            self.experiment_emitter.emit_finished_early(
                reason=f"Test Execution Error: {type(e).__name__}",
                details={
                    "phase": "test_execution",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "component": "experiment_manager",
                    "experiment_name": self.experiment_name,
                },
            )
            self.logger.error("Failed during test execution: %s", e, exc_info=True)
            raise TestExecutionError(f"Failed during test execution: {str(e)}") from e

    def record_failed_test(self, test_case, test_error):
        if self.global_config.progress.show_test_status:
            emoji = "❌ " if self.global_config.progress.use_emojis else ""
            self.logger.info(
                f"{emoji}Failed: {test_case.test_config.name} - {str(test_error)[:50]}..."
            )

    def _handle_test_error(self, test_case, test_error):
        """Helper method to handle test errors consistently."""
        # Get test-specific emitter for this test case
        test_specific_emitter = self.emitter_registry.get_test_emitter(
            test_case.test_config.name
        )

        # Emit test failed event
        test_specific_emitter.emit_failed(
            error_message=str(test_error),
            error_type=type(test_error).__name__,
            phase="execution",
            summary={"test_name": test_case.test_config.name},
        )
        self.logger.error(
            "Test case %s failed: %s",
            test_case.test_config.name,
            test_error,
            exc_info=True,
        )

    def _perform_dry_run(self) -> bool:
        """Perform a dry-run analysis of the experiment without executing commands."""
        self.logger.info("🔍 DRY-RUN: Analyzing experiment configuration...")

        for i, test_case in enumerate(self.test_cases, 1):
            self.logger.info(
                "🔍 DRY-RUN: Test %d/%d - %s",
                i,
                len(self.test_cases),
                test_case.test_config.name,
            )

            # Save test-specific configuration for dry run as well
            self._save_test_configuration(
                test_case.test_config, test_case.test_experiment_dir
            )

            # Perform dry-run for each test case
            try:
                if test_case.perform_dry_run():
                    self.logger.info("  ✅ DRY-RUN: Configuration valid")
                else:
                    self.logger.info("  ❌ DRY-RUN: Configuration issues detected")
            except AttributeError:
                # Fallback for test cases that don't support dry-run yet
                self.logger.info("  📋 DRY-RUN: Basic configuration analysis")
                self._analyze_test_case_config(test_case)

        self.logger.info("🔍 DRY-RUN: Analysis complete - no commands executed")
        return True

    def _load_logging(self):
        """Load and configure logging for the experiment manager with dual-level support."""
        # Initialize LoggerFactory with experiment-specific configuration
        # Handle both enum and string values for logging level
        level_value = self.global_config.logging.level
        if hasattr(level_value, "value"):
            level_str = level_value.value
        else:
            level_str = str(level_value)

        logging_config = {
            "level": level_str,
            "format": self.log_format,
            "enable_colors": getattr(self.global_config.logging, "enable_colors", True),
            "debug_file_logging": getattr(
                self.global_config.logging, "debug_file_logging", True
            ),
            "output_file": str(self.logs_dir / "experiment.log"),
        }

        # Add feature levels if available
        if (
            hasattr(self.global_config.logging, "feature_levels")
            and self.global_config.logging.feature_levels
        ):
            logging_config["feature_levels"] = self.global_config.logging.feature_levels

        # Initialize LoggerFactory with the configuration
        LoggerFactory.initialize(logging_config)

        # Create a directory for logs if it doesn't exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # The logger is already configured through LoggerFactory, just log initialization
        self.logger.info(
            "ExperimentManager initialized for experiment: %s", self.experiment_name
        )

    def cleanup(self):
        """Clean up resources including observers and event handlers."""
        self.logger.info("Starting experiment cleanup")

        try:
            # Generate final log statistics report if enabled
            self._generate_final_log_report()

            # Stop log statistics display if running
            if self.log_statistics_display and self.log_statistics_display.running:
                self.log_statistics_display.stop_display()
                self.logger.info("Stopped log statistics display")

            # Clean up state observer
            if hasattr(self, "state_observer"):
                self.event_manager.unregister_observer(self.state_observer)
                self.logger.debug("Unregistered StateEventObserver")

            # Clean up other observers through factory
            factory = get_observer_factory()

            # List of observer names we created
            observer_names = [
                "experiment_logger",
                "experiment_metrics",
                "experiment_observer",
            ]

            for observer_name in observer_names:
                if factory.unregister_observer(observer_name):
                    self.logger.debug("Unregistered %s", observer_name)
                else:
                    self.logger.debug(
                        "%s was not registered or already removed", observer_name
                    )

            # Clear workflow tracker states for this experiment
            if hasattr(self, "workflow_tracker"):
                self.workflow_tracker.clear_workflow_state(self.experiment_name)
                self.logger.debug("Cleared workflow state for experiment")

            # Generate experiment report
            try:
                self._generate_experiment_report()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to generate report: %s", e)

            # Export metrics to disk if collector is present
            if self.metrics_collector is not None:
                try:
                    from panther.core.metrics import MetricsExporter

                    self.metrics_collector.finalize()
                    exporter = MetricsExporter(self.metrics_collector)
                    metrics_dir = self.experiment_dir / "metrics"
                    metrics_dir.mkdir(parents=True, exist_ok=True)
                    exporter.export_to_json(metrics_dir / "metrics.json")
                    exporter.export_to_csv(metrics_dir)
                    self.logger.info("Metrics exported to: %s", metrics_dir)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.warning("Failed to export metrics: %s", e)

            # Export metrics to disk if collector is present
            if self.metrics_collector is not None:
                try:
                    from panther.core.metrics import MetricsExporter

                    self.metrics_collector.finalize()
                    exporter = MetricsExporter(self.metrics_collector)
                    metrics_dir = self.experiment_dir / "metrics"
                    metrics_dir.mkdir(parents=True, exist_ok=True)
                    exporter.export_to_json(metrics_dir / "metrics.json")
                    exporter.export_to_csv(metrics_dir)
                    self.logger.info("Metrics exported to: %s", metrics_dir)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.warning("Failed to export metrics: %s", e)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error during cleanup: %s", e, exc_info=True)
            # Don't raise - we want cleanup to be best-effort

    def __enter__(self):
        """Context manager entry - return self for use in with statements."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup happens."""
        self.cleanup()
        # Don't suppress exceptions
        return False
