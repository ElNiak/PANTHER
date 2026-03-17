"""Central orchestrator for PANTHER experiment lifecycle.

``ExperimentManager`` drives the four-phase execution model:

1. **Initialization** – parse YAML config, set up logging, register emitters.
2. **Plugin Loading** – discover plugins, create service managers, generate
   commands, build Docker images.
3. **Environment Deployment** – set up network (Docker Compose / Shadow NS),
   deploy containers, run health checks.
4. **Test Execution** – iterate test scenarios, collect metrics, teardown,
   generate reports.

The manager delegates to ``ErrorHandlerMixin`` for structured
error recovery and ``FastFailHandler`` for early termination on
unrecoverable failures (certificate, Ivy compilation, port conflicts,
resource exhaustion, etc.).  Experiment initialization/execution phases
and resource cleanup are implemented directly in this class.

See Also:
    `panther.core.test_cases`
        Mixin-based test runners invoked by the manager.
    `panther.core.events`
        Event bus wiring configured during initialization.
"""

import contextlib
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import click
import yaml
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
from panther.core.metrics.enums import Phase
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.observer.factory import get_observer_factory
from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.workflow import (  # pylint: disable=import-outside-toplevel
    WorkflowStateTracker,
)
from panther.core.outputs.output_index import OutputIndexBuilder
from panther.core.test_cases.test_case_impl import TestCase
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.utils.console_formatter import ConsoleFormatter
from panther.core.utils.log_context import log_context
from panther.core.utils.logger_factory import LoggerFactory
from panther.plugins.plugin_manager import PluginManager

# ---------------------------------------------------------------------------
# Test execution display helpers
# ---------------------------------------------------------------------------

_HEADER_WIDTH = 50


def format_test_header(index: int, total: int, test_name: str) -> str:
    """Build a structured header line for a test case.

    Produces output like::

        -- Test 1/3: QUIC Handshake Test --------------------

    Args:
        index: Zero-based index of the current test.
        total: Total number of tests in the run.
        test_name: Human-readable name of the test case.

    Returns:
        Formatted header string.
    """
    prefix = f"\n\u2500\u2500 Test {index + 1}/{total}: {test_name} "
    # Pad with box-drawing dashes to a fixed width
    padding = max(2, _HEADER_WIDTH - len(prefix) + 1)  # +1 for leading \n
    return prefix + "\u2500" * padding


def format_test_result(
    *,
    passed: bool,
    elapsed: float,
    use_emojis: bool = True,
    error_message: Optional[str] = None,
) -> str:
    """Build a structured result line for a completed test.

    Produces output like::

        PASSED (26.4s)
        FAILED (3.1s): Docker build failed for picoquic:rfc9000

    Args:
        passed: Whether the test passed.
        elapsed: Wall-clock duration in seconds.
        use_emojis: Whether to prefix the line with an emoji indicator.
        error_message: Error description shown on failure. Ignored when
            *passed* is ``True``.

    Returns:
        Formatted result string (indented with two spaces).
    """
    duration = f"({elapsed:.1f}s)"
    if passed:
        icon = "\u2705 " if use_emojis else ""
        return f"  {icon}PASSED {duration}"
    else:
        icon = "\u274c " if use_emojis else ""
        msg = f": {error_message}" if error_message else ""
        hint = "\n    Check logs for details." if error_message else ""
        return f"  {icon}FAILED {duration}{msg}{hint}"


def format_experiment_summary(
    *,
    successful_tests: int,
    failed_tests: int,
    total_tests: int,
    elapsed_seconds: float,
    output_dir: str,
    failed_test_names: List[Tuple[str, str]],
    use_emojis: bool = True,
) -> str:
    """Build a structured experiment summary banner.

    Produces output like::

        ==================================================
         Experiment Complete
        --------------------------------------------------
         Tests:  3 passed, 1 failed (75.0%)
         Time:   5m 12s
         Output: outputs/2026-03-16_14-30/quic_test

         Failed tests:
           X QUIC Stream Test -- Docker build failed
           X TLS Resumption -- Timeout after 60s

         Next steps:
           panther report diagnose <output_dir>
           panther logs errors <output_dir>
        ==================================================

    Args:
        successful_tests: Number of tests that passed.
        failed_tests: Number of tests that failed.
        total_tests: Total number of tests executed.
        elapsed_seconds: Wall-clock duration of the entire run in seconds.
        output_dir: Path to the experiment output directory.
        failed_test_names: List of ``(test_name, error_message)`` tuples for
            each failed test.  The error_message may be empty.
        use_emojis: Whether to use emoji indicators in the output.

    Returns:
        Formatted multi-line summary string (without leading/trailing newlines
        from the banner helper -- those are handled by ``ConsoleFormatter.banner``).
    """
    width = _HEADER_WIDTH
    double_line = "\u2550" * width  # BOX DRAWINGS DOUBLE HORIZONTAL
    single_line = "\u2500" * width  # BOX DRAWINGS LIGHT HORIZONTAL

    # Duration formatting
    if elapsed_seconds >= 60:
        minutes = int(elapsed_seconds) // 60
        seconds = int(elapsed_seconds) % 60
        duration = f"{minutes}m {seconds}s"
    else:
        duration = f"{elapsed_seconds:.0f}s"

    # Success percentage
    percentage = (successful_tests / total_tests * 100) if total_tests > 0 else 0.0

    lines: List[str] = []
    lines.append("")
    lines.append(double_line)
    lines.append(" Experiment Complete")
    lines.append(single_line)
    lines.append(
        f" Tests:  {successful_tests} passed, {failed_tests} failed ({percentage:.1f}%)"
    )
    lines.append(f" Time:   {duration}")
    lines.append(f" Output: {output_dir}")

    if failed_test_names:
        lines.append("")
        lines.append(" Failed tests:")
        fail_icon = "\u274c " if use_emojis else "X "
        for name, reason in failed_test_names:
            reason_part = f" \u2014 {reason}" if reason else ""
            lines.append(f"   {fail_icon}{name}{reason_part}")

    lines.append("")
    lines.append(" Next steps:")
    lines.append(f"   panther report diagnose {output_dir}")
    lines.append(f"   panther logs errors {output_dir}")
    lines.append(double_line)

    return "\n".join(lines)


# TODO implement errors management strategy (e.g., retry, fail, etc.)
class ExperimentManager(
    ErrorHandlerMixin,
    ExperimentObserverMixin,
    ExperimentAnalysisMixin,
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
        console_level: Optional numeric log level for console handlers.
            When provided, ``LoggerFactory.set_console_level()`` is called
            after logging initialization so that CLI flags (``--verbose``,
            ``--debug``) take final precedence over YAML configuration.

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
        console_level: Optional[int] = None,
    ):
        """Initialize ExperimentManager."""
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

        # Apply CLI console-level override (--verbose / --debug) if provided.
        # This runs after feature-level configuration so that the CLI flag
        # takes final precedence for console handlers.
        if console_level is not None:
            LoggerFactory.set_console_level(console_level)

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

        # Initialize output index builder for tracking experiment artifacts
        self.output_index_builder = OutputIndexBuilder(
            experiment_dir=self.experiment_dir,
            experiment_id=self.experiment_name,
        )

    def configure_logging_features(self):
        """Configure feature-level logging from global config."""
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

    def record_failed_test(self, test_case, test_error):
        """Record a failed test case and log the error."""
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
            "output_file": str(self.logs_dir / "structured.jsonl"),
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

        # Wire metrics collector to structured.jsonl if present
        if self.metrics_collector is not None:
            self.metrics_collector._structured_log_path = (
                self.logs_dir / "structured.jsonl"
            )

        # The logger is already configured through LoggerFactory, just log initialization
        self.logger.info(
            "ExperimentManager initialized for experiment: %s", self.experiment_name
        )

    def _record_test_metric(self, outcome: str) -> None:
        """Record test outcome metrics (total + outcome-specific counter).

        Args:
            outcome: The test outcome to record (e.g., "failed", "successful").
        """
        try:
            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "test_cases_total", phase=Phase.TEST_EXECUTION
                )
                self.metrics_collector.increment_counter(
                    f"test_cases_{outcome}", phase=Phase.TEST_EXECUTION
                )
        except Exception as metrics_err:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Failed to record test %s metrics: %s",
                outcome,
                metrics_err,
            )

    # -- Experiment phases (formerly ExperimentPhasesMixin) ------------------

    def initialize_experiments(self, experiment_config: ExperimentConfig) -> None:
        """Initialize experiment with plugins, environment validation, and test case setup.

        Args:
            experiment_config: Complete experiment configuration

        Raises:
            ExperimentInitializationError: When initialization fails
            PluginValidationError: When required plugins are missing
            TestCaseInitializationError: When test cases cannot be initialized
        """
        try:
            ConsoleFormatter.banner("Phase 1: Initialization")
            with log_context(
                experiment_id=self.experiment_name, phase="initialization"
            ):
                self.experiment_config = experiment_config
                self._save_configuration()

                # Register the saved config in the output index
                self.output_index_builder.register(
                    "experiment_config.yaml",
                    file_type="config",
                    file_format="yaml",
                    description="Experiment configuration snapshot",
                )

                self.experiment_emitter.emit_initialized(
                    config={
                        "experiment_name": self.experiment_name,
                        "test_count": len(experiment_config.tests),
                    }
                )

                click.echo("  \u2713 Initialization complete")

                ConsoleFormatter.banner("Phase 2: Plugin Loading")
                with log_context(phase="plugin_loading"):
                    self.experiment_emitter.emit_plugin_loading_started()
                    self._validate_plugins()
                    self.experiment_emitter.emit_plugin_loading_completed()
                click.echo("  \u2713 Plugin loading complete")

                with log_context(phase="test_case_initialization"):
                    self._initialize_test_cases()

                test_names = [test.test_config.name for test in self.test_cases]
                self.experiment_emitter.emit_test_cases_initialized(
                    test_count=len(self.test_cases), test_names=test_names
                )

        except PluginValidationError as e:
            self.logger.error("Plugin validation failed: %s", e)
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
            raise ExperimentInitializationError(f"Import error: {e}") from e

        except Exception as e:  # pylint: disable=broad-except
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
                f"Failed to initialize experiment: {e}"
            ) from e

    def _validate_plugins(self):
        """Validate that all required plugins are available and compatible."""
        self.logger.info("Validating plugins for experiment...")

        is_valid, errors = self.plugin_manager.validate_experiment_plugins(
            self.experiment_config
        )

        if not is_valid:
            error_message = "Plugin validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            self.logger.error(error_message)

            available_plugins = self.plugin_manager.plugins
            self.logger.info("Available plugins:")
            for plugin_type, plugins in available_plugins.items():
                self.logger.debug("  %s: %s", plugin_type, plugins)

            raise PluginValidationError(error_message)

        self.logger.info("All required plugins validated successfully")

    def _save_configuration(self):
        """Save the experiment configuration file in the experiment folder."""
        config_file_path = self.experiment_dir / "experiment_config.yaml"
        try:
            with open(config_file_path, "w", encoding="utf-8") as config_file:
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
        except OSError as e:
            raise ExperimentInitializationError(
                f"Failed to save experiment config to {config_file_path}: {e}"
            ) from e

    def _save_test_configuration(self, test_config, test_dir: Path):
        """Save a complete test configuration file for a specific test."""
        try:
            test_dir.mkdir(parents=True, exist_ok=True)
            config_file_path = test_dir / "test_config.yaml"

            def convert_config_for_yaml(config):
                """Convert a config object to a YAML-serializable dictionary."""
                if hasattr(config, "dict"):
                    config_dict = config.dict()
                else:
                    config_dict = config
                import json

                return json.loads(json.dumps(config_dict, default=str))

            global_config_dict = convert_config_for_yaml(self.global_config)
            test_config_dict = convert_config_for_yaml(test_config)

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

            with open(config_file_path, "w", encoding="utf-8") as config_file:
                yaml.dump(
                    complete_config, config_file, default_flow_style=False, indent=2
                )

            self.logger.info("Saved test configuration to: %s", config_file_path)

        except Exception as e:
            self.logger.warning(
                "Failed to save test configuration to %s: %s", test_dir, e
            )
            self.logger.debug("Traceback:", exc_info=True)

    def _initialize_test_cases(self):
        """Initialize test cases from the experiment configuration."""
        try:
            test_count = len(self.experiment_config.tests)
            test_names = [test.name for test in self.experiment_config.tests]

            test_index = 0

            for test_config in self.experiment_config.tests:
                self.logger.info("Initializing test case: %s", test_config.name)

                test_specific_emitter = self.emitter_registry.get_test_emitter(
                    test_config.name
                )

                test_specific_emitter.emit_created(
                    test_name=test_config.name,
                    description=test_config.description,
                    config={"phase": "initialization"},
                )

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

            self.logger.debug("Initialized %d test cases: %s", test_count, test_names)
            self.logger.info("Initialized %s test cases.", len(self.test_cases))

        except Exception as e:  # pylint: disable=broad-except
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
                f"Failed to initialize test cases: {e}"
            ) from e

    def run_tests(self) -> bool:
        """Execute all test cases with progress tracking and error handling.

        Returns:
            bool: True if any tests succeeded, False if all failed

        Raises:
            TestExecutionError: When execution infrastructure fails
        """
        try:
            ConsoleFormatter.banner(
                f"Phase 3: Test Execution ({len(self.test_cases)} tests)"
            )
            with log_context(
                experiment_id=self.experiment_name, phase="test_execution"
            ):
                self.experiment_emitter.emit_execution_started(
                    test_count=len(self.test_cases)
                )

                if self.metrics_collector:
                    self.metrics_collector.increment_counter(
                        "experiments_total", phase=Phase.TEST_EXECUTION
                    )

                if self.dry_run:
                    self.logger.info(
                        "DRY-RUN: Would execute %d test cases for experiment: %s",
                        len(self.test_cases),
                        self.experiment_name,
                    )
                    return self._perform_dry_run()
                else:
                    self.logger.info(
                        "Starting test execution for experiment: %s",
                        self.experiment_name,
                    )

                successful_tests = 0
                failed_tests = 0
                total_tests = len(self.test_cases)
                use_emojis = self.global_config.progress.use_emojis
                show_status = self.global_config.progress.show_test_status
                experiment_start = time.monotonic()
                failed_test_info: List[Tuple[str, str]] = []

                for i, test_case in enumerate(self.test_cases):
                    with log_context(test_id=test_case.test_name):
                        test_name = test_case.test_config.name

                        if show_status:
                            click.echo(format_test_header(i, total_tests, test_name))

                        self.logger.info("Running test case: %s", test_name)

                        test_specific_emitter = self.emitter_registry.get_test_emitter(
                            test_name
                        )

                        test_specific_emitter.emit_execution_started(
                            steps=["setup", "execute", "assertions", "teardown"]
                        )
                        test_start = time.monotonic()
                        try:
                            self._save_test_configuration(
                                test_case.test_config,
                                test_case.test_experiment_dir,
                            )

                            self.logger.info(
                                "Executing test case: %s",
                                test_name,
                            )
                            test_result = test_case.run()
                            elapsed = time.monotonic() - test_start

                            if test_result is False:
                                failed_tests += 1
                                failed_test_info.append(
                                    (test_name, "Test analysis failed")
                                )
                                self._record_test_metric("failed")
                                if show_status:
                                    click.echo(
                                        format_test_result(
                                            passed=False,
                                            elapsed=elapsed,
                                            use_emojis=use_emojis,
                                            error_message="Test analysis failed",
                                        )
                                    )
                                test_specific_emitter.emit_failed(
                                    error_message="Test analysis failed",
                                    error_type="TestAnalysisFailure",
                                    phase="analysis",
                                    summary={
                                        "test_name": test_name,
                                        "reason": "Tester analysis determined test failure",
                                    },
                                )
                                continue

                            successful_tests += 1
                            self._record_test_metric("successful")
                            if show_status:
                                click.echo(
                                    format_test_result(
                                        passed=True,
                                        elapsed=elapsed,
                                        use_emojis=use_emojis,
                                    )
                                )

                            test_specific_emitter.emit_completed(
                                summary={
                                    "status": "success",
                                    "test_name": test_name,
                                }
                            )

                        except (KeyboardInterrupt, SystemExit):
                            self.logger.warning(
                                "Test interrupted: %s",
                                test_name,
                                exc_info=True,
                            )
                            test_specific_emitter.emit_failed(
                                error_message="Test interrupted",
                                error_type="KeyboardInterrupt",
                                phase="execution",
                            )
                            raise

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
                            elapsed = time.monotonic() - test_start
                            failed_tests += 1
                            failed_test_info.append((test_name, str(test_error)[:80]))
                            self._record_test_metric("failed")

                            if show_status:
                                click.echo(
                                    format_test_result(
                                        passed=False,
                                        elapsed=elapsed,
                                        use_emojis=use_emojis,
                                        error_message=str(test_error),
                                    )
                                )

                            self.record_failed_test(test_case, test_error)

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
                                should_continue = self.fast_fail_handler.handle_error(
                                    test_error, raise_on_critical=False
                                )
                                if not should_continue:
                                    self.logger.critical(
                                        "Critical %s error in test %s, terminating experiment",
                                        test_error.category.value,
                                        test_name,
                                    )
                                    self.experiment_emitter.emit_finished_early(
                                        reason=f"Critical {test_error.category.value} Failure",
                                        details={
                                            "test_name": test_name,
                                            "error_type": type(test_error).__name__,
                                            "error_category": test_error.category.value,
                                            "error_context": test_error.context,
                                        },
                                    )
                                    raise test_error

                            if isinstance(
                                test_error, AttributeError
                            ) and "emit_service_setup_completed" in str(test_error):
                                self.logger.error(
                                    "Test case %s failed due to missing event emitter method: %s",
                                    test_name,
                                    str(test_error),
                                )
                                with contextlib.suppress(Exception):
                                    test_specific_emitter.emit_failed(
                                        error_message=str(test_error),
                                        error_type="AttributeError",
                                        phase="setup",
                                    )
                            else:
                                self._handle_test_error(test_case, test_error)

                        except Exception as test_error:  # pylint: disable=broad-except
                            elapsed = time.monotonic() - test_start
                            failed_tests += 1
                            self._record_test_metric("failed")
                            failed_test_info.append((test_name, str(test_error)[:80]))

                            if show_status:
                                click.echo(
                                    format_test_result(
                                        passed=False,
                                        elapsed=elapsed,
                                        use_emojis=use_emojis,
                                        error_message=str(test_error),
                                    )
                                )

                            self._handle_test_error(test_case, test_error)
                            self.logger.warning(
                                "Unexpected error type %s caught. Consider adding specific handling.",
                                type(test_error).__name__,
                            )

                        finally:
                            try:
                                self.event_manager.cleanup_scoped_observers("test")
                                self.logger.debug(
                                    "Cleaned up test-scoped observers for test: %s",
                                    test_name,
                                )
                            except (
                                Exception
                            ) as cleanup_error:  # pylint: disable=broad-except
                                self.logger.warning(
                                    "Failed to cleanup test observers for %s: %s",
                                    test_name,
                                    cleanup_error,
                                )

                try:
                    if self.metrics_collector:
                        if failed_tests == 0:
                            self.metrics_collector.increment_counter(
                                "experiments_successful", phase=Phase.TEST_EXECUTION
                            )
                        else:
                            self.metrics_collector.increment_counter(
                                "experiments_failed", phase=Phase.TEST_EXECUTION
                            )
                except (
                    Exception
                ) as metrics_err:  # pylint: disable=broad-exception-caught
                    self.logger.warning(
                        "Failed to record experiment outcome metrics: %s",
                        metrics_err,
                    )

                self.logger.info(
                    "Experiment execution summary - Total: %d, Success: %d, Failed: %d",
                    len(self.test_cases),
                    successful_tests,
                    failed_tests,
                )

                experiment_elapsed = time.monotonic() - experiment_start
                click.echo(
                    format_experiment_summary(
                        successful_tests=successful_tests,
                        failed_tests=failed_tests,
                        total_tests=total_tests,
                        elapsed_seconds=experiment_elapsed,
                        output_dir=str(self.experiment_dir),
                        failed_test_names=failed_test_info,
                        use_emojis=use_emojis,
                    )
                )

                return successful_tests > 0

        except (KeyboardInterrupt, SystemExit):
            self.logger.warning(
                "Experiment execution interrupted by user", exc_info=True
            )
            raise

        except Exception as e:
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
            raise TestExecutionError(f"Failed during test execution: {e}") from e

    def _perform_dry_run(self) -> bool:
        """Perform a dry-run analysis of the experiment without executing commands."""
        self.logger.info("DRY-RUN: Analyzing experiment configuration...")

        for i, test_case in enumerate(self.test_cases, 1):
            self.logger.info(
                "DRY-RUN: Test %d/%d - %s",
                i,
                len(self.test_cases),
                test_case.test_config.name,
            )

            self._save_test_configuration(
                test_case.test_config, test_case.test_experiment_dir
            )

            try:
                if test_case.perform_dry_run():
                    self.logger.info("  DRY-RUN: Configuration valid")
                else:
                    self.logger.info("  DRY-RUN: Configuration issues detected")
            except AttributeError:
                self.logger.info("  DRY-RUN: Basic configuration analysis")
                self._analyze_test_case_config(test_case)

        self.logger.info("DRY-RUN: Analysis complete - no commands executed")
        return True

    # -- Experiment cleanup (formerly ExperimentCleanupMixin) ---------------

    def cleanup(self):
        """Clean up resources including observers and event handlers.

        Each cleanup step has its own error handling so that a failure in one
        step does not prevent subsequent steps (e.g., metrics export) from running.
        """
        # Push cleanup phase context (no with-block to avoid re-indenting entire method)
        ConsoleFormatter.banner("Phase 4: Cleanup")
        _cleanup_ctx = log_context(experiment_id=self.experiment_name, phase="cleanup")
        _cleanup_ctx.__enter__()
        try:
            self.logger.info("Starting experiment cleanup")

            # Generate final log statistics report if enabled
            try:
                self._generate_final_log_report()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to generate final log report: %s", e)

            # Stop log statistics display if running
            try:
                if self.log_statistics_display and self.log_statistics_display.running:
                    self.log_statistics_display.stop_display()
                    self.logger.info("Stopped log statistics display")
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to stop log statistics display: %s", e)

            # Clean up state observer
            try:
                if hasattr(self, "state_observer"):
                    self.event_manager.unregister_observer(self.state_observer)
                    self.logger.debug("Unregistered StateEventObserver")
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to unregister state observer: %s", e)

            # Clean up other observers through factory
            try:
                factory = get_observer_factory()
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
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to unregister observers: %s", e)

            # Clear workflow tracker states for this experiment
            try:
                if hasattr(self, "workflow_tracker"):
                    self.workflow_tracker.clear_workflow_state(self.experiment_name)
                    self.logger.debug("Cleared workflow state for experiment")
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to clear workflow state: %s", e)

            # Generate experiment report
            try:
                self._generate_experiment_report()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to generate report: %s", e)

            # Finalize metrics collector (metrics already written to structured.jsonl)
            if self.metrics_collector is not None:
                try:
                    self.metrics_collector.finalize()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.warning("Failed to finalize metrics: %s", e)

            # Clean up empty directories from the experiment output tree
            try:
                from panther.core.outputs.output_cleanup import remove_empty_directories

                removed = remove_empty_directories(self.experiment_dir)
                if removed:
                    self.logger.info(
                        "Cleaned %d empty directories from experiment output", removed
                    )
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning(
                    "Empty directory cleanup failed: %s", e, exc_info=True
                )

            # Register generated reports and metrics in the output index, then flush
            try:
                report_files = {
                    "EXPERIMENT_REPORT.md": ("report", "markdown", "Experiment report"),
                    "experiment_summary.json": ("report", "json", "Experiment summary"),
                    "experiment_summary.txt": (
                        "report",
                        "text",
                        "Experiment summary (text)",
                    ),
                }
                for filename, (ftype, ffmt, desc) in report_files.items():
                    if (self.experiment_dir / filename).exists():
                        self.output_index_builder.register(
                            filename,
                            file_type=ftype,
                            file_format=ffmt,
                            description=desc,
                        )

                # Register structured log if present
                structured_log = self.experiment_dir / "structured.jsonl"
                if structured_log.exists():
                    self.output_index_builder.register(
                        "structured.jsonl",
                        file_type="log",
                        file_format="jsonl",
                        description="Structured event log",
                    )

                self.output_index_builder.flush()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to write output index: %s", e)

            # Clean up stale Docker resources (dangling images, exited containers, orphan volumes)
            try:
                self._cleanup_docker_resources()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Docker resource cleanup failed: %s", e)

            click.echo("  \u2713 Cleanup complete")

        finally:
            # Pop cleanup phase context — guaranteed even if cleanup raises
            _cleanup_ctx.__exit__(None, None, None)

    def _cleanup_docker_resources(self):
        """Remove stale Docker resources left over from the experiment.

        Cleans up dangling images, exited panther containers, and orphaned
        panther volumes. Each step is independent so a failure in one does
        not block the others.
        """
        from panther.core.docker_builder import DockerBuilder

        try:
            builder = DockerBuilder.get_instance(enable_cache=False)
        except Exception:
            self.logger.debug("DockerBuilder unavailable, skipping Docker cleanup")
            return

        if not builder.is_docker_available():
            self.logger.debug("Docker daemon unavailable, skipping Docker cleanup")
            return

        client = builder.client
        cleaned = []

        # 1. Remove dangling images (<none>:<none>)
        try:
            if builder.remove_dangling_images():
                cleaned.append("dangling images")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.debug("Dangling image cleanup failed: %s", e)

        # 2. Remove exited containers with panther label
        try:
            exited = client.containers.list(
                all=True,
                filters={"status": "exited", "label": "panther"},
            )
            for container in exited:
                container.remove(force=True)
            if exited:
                cleaned.append(f"{len(exited)} exited containers")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.debug("Exited container cleanup failed: %s", e)

        # 3. Remove orphaned panther volumes
        try:
            volumes = client.volumes.list(filters={"name": "panther"})
            removed_count = 0
            for volume in volumes:
                try:
                    volume.remove()
                    removed_count += 1
                except Exception as e:
                    self.logger.debug("Could not remove volume %s: %s", volume.name, e)
            if removed_count:
                cleaned.append(f"{removed_count} orphaned volumes")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.debug("Volume cleanup failed: %s", e)

        if cleaned:
            self.logger.info("Docker cleanup: removed %s", ", ".join(cleaned))

    # -- Context manager ----------------------------------------------------

    def __enter__(self):
        """Context manager entry - return self for use in with statements."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup happens."""
        self.cleanup()
        # Don't suppress exceptions
        return False
