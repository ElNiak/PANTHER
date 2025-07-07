"""Base class for TestCase with core initialization and configuration."""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List

from colorlog import ColoredFormatter

from panther.config.core.models.experiment import TestConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.core.exceptions.fast_fail import FastFailHandler, TimeoutCascadeException
from panther.core.observer.factory import get_observer_factory
from panther.core.observer.factory.factory_builders import (
    create_logger,
    create_metrics,
    create_storage,
)
from panther.core.observer.impl.experiment_observer import ExperimentObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.plugins.plugin_manager import PluginManager


class TestCaseBase(ITestCase):
    """Base class providing core initialization and configuration for test cases."""

    def __init__(
        self,
        test_config: TestConfig,
        global_config: GlobalConfig,
        plugin_manager: PluginManager,
        experiment_dir: Path,
        metrics_collector=None,
        emitter_registry=None,
        workflow_tracker=None,
    ):
        super().__init__(test_config, global_config)

        self.metrics_collector = metrics_collector
        self.plugin_manager = plugin_manager
        self.experiment_dir = experiment_dir
        self.emitter_registry = emitter_registry
        self.workflow_tracker = workflow_tracker

        # Initialize basic attributes
        self.available_implementations_per_protocol = None
        self.iut_path = None
        self.test_defined_testers = None
        self.testers_path = None
        self.available_testers = None
        self.available_protocols = None
        self.test_defined_implementation = None

        # Logging configuration
        # Handle both string and enum for logging level
        if hasattr(self.global_config.logging.level, "name"):
            level_name = self.global_config.logging.level.name
        else:
            level_name = str(self.global_config.logging.level).upper()

        self.log_level = getattr(logging, level_name, logging.INFO)
        self.log_format = self.global_config.logging.format

        # Test identification
        self.test_name = re.sub(r"[^a-zA-Z0-9_]", "_", test_config.name.strip())
        self.test_experiment_dir = experiment_dir / self.test_name

        # Initialize collections
        self.result_collectors = None
        self.service_managers: List[Any] = []
        self.environment_plugin_manager: List[Any] = []
        self.event_manager = None
        # Runtime list for execution environment plugin instances
        self.execution_environment_plugins: List[Any] = []
        # Configuration data accessed via self.test_config.execution_environment
        self.services = self.test_config.services

        # Ensure experiment directory exists
        self.test_experiment_dir.mkdir(parents=True, exist_ok=True)

        if (
            not plugin_manager
            or not hasattr(plugin_manager, "event_manager")
            or plugin_manager.event_manager is None
        ):
            self.logger.warning(
                "No EventManager provided by plugin_manager, using singleton instance."
            )
            self.event_manager = EventManager.get_instance()
        else:
            # Plugin manager should now always have the singleton EventManager
            self.event_manager = plugin_manager.event_manager

        # Verify we have the singleton instance
        if self.event_manager is not EventManager.get_instance():
            self.logger.warning(
                "EventManager instance mismatch detected. This may cause event propagation issues. "
                "Switching to singleton instance."
            )
            self.event_manager = EventManager.get_instance()

        # Setup logging
        self._setup_logging()

        # Initialize test-level fast-fail behavior
        self._init_fast_fail_handler(test_config, global_config)

    def __str__(self) -> str:
        return f"TestCase(name={self.test_name})"

    def __repr__(self) -> str:
        return self.__str__()

    def _setup_logging(self):
        """Load and configure logging for the test case."""
        # Set up the logger
        self.logger = logging.getLogger(self.test_name)
        self.logger.setLevel(self.log_level)

        # Configure formatter based on color preference
        if getattr(self.global_config.logging, "enable_colors", True):
            formatter = ColoredFormatter(
                "%(log_color)s" + self.log_format,
                datefmt="%Y-%m-%d %H:%M:%S",
                reset=True,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                style="%",
            )
        else:
            formatter = logging.Formatter(self.log_format, datefmt="%Y-%m-%d %H:%M:%S")

        if not self.logger.hasHandlers():
            # Prevent duplicate handlers if logger is already configured
            self.logger.propagate = False
        else:
            # Clear existing handlers to avoid duplicates
            self.logger.handlers.clear()

        # Create file handler for logging
        self.test_experiment_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug("Creating log directory at '%s'", self.test_experiment_dir)
        file_handler = logging.FileHandler(self.test_experiment_dir / "test.log")
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)

        # Add console handler for colored output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)

        # Add both handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Add file handler if specified
        if hasattr(self.global_config.logging, "file_path"):
            file_handler = logging.FileHandler(
                self.test_experiment_dir / "test_case.log"
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(logging.Formatter(self.log_format))
            self.logger.addHandler(file_handler)

    def _init_fast_fail_handler(
        self, test_config: TestConfig, global_config: GlobalConfig
    ):
        """Initialize test-level fast-fail handler based on configuration."""
        fast_fail_config = global_config.fast_fail

        # Determine if fast-fail should be enabled for this test
        if fast_fail_config.test_level and test_config.fast_fail_enabled is not None:
            # Test-level override is active and test specifies its preference
            fast_fail_enabled = test_config.fast_fail_enabled
            self.logger.debug(
                "Using test-level fast-fail setting: %s for test '%s'",
                fast_fail_enabled,
                test_config.name,
            )
        else:
            # Use global setting
            fast_fail_enabled = fast_fail_config.enabled
            if fast_fail_config.test_level:
                self.logger.debug(
                    "Test-level fast-fail enabled but test '%s' has no override, using global: %s",
                    test_config.name,
                    fast_fail_enabled,
                )

        # Initialize fast-fail handler for this test
        self.fast_fail_handler = FastFailHandler(
            enabled=fast_fail_enabled, logger=self.logger
        )

        # Keep backward compatibility
        self._fail_on_error = fast_fail_enabled

        self.logger.debug(
            "Initialized fast-fail handler for test '%s': enabled=%s",
            test_config.name,
            fast_fail_enabled,
        )

    def _check_timeout_cascade(self, service_name: str) -> None:
        """Check for timeout cascade and raise exception if detected."""
        now = datetime.now()
        self.timeout_history.append((now, service_name))

        # Check recent timeouts (within 5 minutes)
        cutoff_time = now - timedelta(minutes=5)
        recent_timeouts = [(t, s) for t, s in self.timeout_history if t > cutoff_time]

        threshold = self.global_config.fast_fail.timeout_cascade_threshold
        if len(recent_timeouts) >= threshold:
            services = list(set(s for _, s in recent_timeouts))
            raise TimeoutCascadeException(
                f"Timeout cascade detected in test '{self.test_config.name}'",
                len(recent_timeouts),
                services,
            )
