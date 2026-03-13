"""Experiment initialization and test execution phases.

Provides ExperimentPhasesMixin with methods for the initialization and
execution phases of the experiment lifecycle.
"""

import contextlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml
from omegaconf import OmegaConf

from panther.config.core.models import ExperimentConfig
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
    IvyCompilationException,
    PortConflictException,
    ResourceExhaustionException,
    TimeoutCascadeException,
)
from panther.core.metrics.enums import Phase
from panther.core.test_cases.test_case_impl import TestCase


class ExperimentPhasesMixin:
    """Mixin providing experiment initialization and test execution phases.

    Expects the host class to provide:
        - self.logger
        - self.global_config, self.experiment_config
        - self.experiment_name, self.experiment_dir
        - self.experiment_emitter, self.emitter_registry
        - self.plugin_manager
        - self.metrics_collector
        - self.workflow_tracker
        - self.test_cases: List
        - self.fast_fail_handler
        - self.dry_run: bool
        - self.event_manager
        - self._handle_test_error(), self.record_failed_test()
        - self._record_test_metric()
    """

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
            self.experiment_config = experiment_config
            self._save_configuration()

            self.experiment_emitter.emit_initialized(
                config={
                    "experiment_name": self.experiment_name,
                    "test_count": len(experiment_config.tests),
                }
            )

            self.experiment_emitter.emit_plugin_loading_started()
            self._validate_plugins()
            self.experiment_emitter.emit_plugin_loading_completed()

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
            raise ExperimentInitializationError(f"Import error: {str(e)}") from e

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
                f"Failed to initialize experiment: {str(e)}"
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
                self.logger.info("  %s: %s", plugin_type, plugins)

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

            self.logger.info(f"Saved test configuration to: {config_file_path}")

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
                f"Failed to initialize test cases: {str(e)}"
            ) from e

    def run_tests(self) -> bool:
        """Execute all test cases with progress tracking and error handling.

        Returns:
            bool: True if any tests succeeded, False if all failed

        Raises:
            TestExecutionError: When execution infrastructure fails
        """
        try:
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
                    "Starting test execution for experiment: %s", self.experiment_name
                )

            successful_tests = 0
            failed_tests = 0

            if self.global_config.progress.enable_progress_bar:
                self.logger.debug("Using Click progress bar for test execution")
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
                        pass

                progress_context = SimpleProgressIterator(self.test_cases)

            with progress_context as progress_bar:
                for i, test_case in enumerate(self.test_cases):
                    if self.global_config.progress.enable_progress_bar:
                        progress_bar.label = f"Test {i+1}/{len(self.test_cases)} - {test_case.test_config.name}"

                    if self.global_config.progress.show_test_status:
                        emoji = "🧪 " if self.global_config.progress.use_emojis else ""
                        self.logger.info(
                            f"{emoji}Starting: {test_case.test_config.name}"
                        )
                    self.logger.info(
                        "Running test case: %s", test_case.test_config.name
                    )

                    test_specific_emitter = self.emitter_registry.get_test_emitter(
                        test_case.test_config.name
                    )

                    test_specific_emitter.emit_execution_started(
                        steps=["setup", "execute", "assertions", "teardown"]
                    )
                    try:
                        self._save_test_configuration(
                            test_case.test_config, test_case.test_experiment_dir
                        )

                        self.logger.info(
                            "Executing test case: %s", test_case.test_config.name
                        )
                        test_result = test_case.run()

                        if test_result is False:
                            failed_tests += 1
                            self._record_test_metric("failed")
                            if self.global_config.progress.show_test_status:
                                emoji = (
                                    "❌ "
                                    if self.global_config.progress.use_emojis
                                    else ""
                                )
                                self.logger.info(
                                    f"{emoji}Failed: {test_case.test_config.name} - Test analysis failed"
                                )
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
                        self._record_test_metric("successful")
                        if self.global_config.progress.show_test_status:
                            emoji = (
                                "✅ " if self.global_config.progress.use_emojis else ""
                            )
                            self.logger.info(
                                f"{emoji}Completed: {test_case.test_config.name}"
                            )

                        test_specific_emitter.emit_completed(
                            summary={
                                "status": "success",
                                "test_name": test_case.test_config.name,
                            }
                        )

                    except (KeyboardInterrupt, SystemExit):
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
                        failed_tests += 1
                        self._record_test_metric("failed")

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
                                    test_case.test_config.name,
                                )
                                self.experiment_emitter.emit_finished_early(
                                    reason=f"Critical {test_error.category.value} Failure",
                                    details={
                                        "test_name": test_case.test_config.name,
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
                                test_case.test_config.name,
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
                        failed_tests += 1
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

            self.logger.info("")

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
            except Exception as metrics_err:  # pylint: disable=broad-exception-caught
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
            raise TestExecutionError(f"Failed during test execution: {str(e)}") from e

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

            self._save_test_configuration(
                test_case.test_config, test_case.test_experiment_dir
            )

            try:
                if test_case.perform_dry_run():
                    self.logger.info("  ✅ DRY-RUN: Configuration valid")
                else:
                    self.logger.info("  ❌ DRY-RUN: Configuration issues detected")
            except AttributeError:
                self.logger.info("  📋 DRY-RUN: Basic configuration analysis")
                self._analyze_test_case_config(test_case)

        self.logger.info("🔍 DRY-RUN: Analysis complete - no commands executed")
        return True
