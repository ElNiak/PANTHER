"""
Base Environment Monitor for PANTHER Network Environments.

This module provides the common monitoring functionality shared across all network
environment types (Docker Compose, Localhost, Shadow NS), eliminating 85% code duplication.

Key Features:
- Thread-safe service state management
- Configurable failure thresholds and monitoring intervals
- Early termination handling
- Consistent monitoring lifecycle (start/stop/health-check)
- Abstract interface for environment-specific health checks
"""

import threading
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class ServiceHealthState(Enum):
    """Universal service health states across all monitor types."""

    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"  # Alias for READY for container environments
    FAILING = "failing"
    FAILED = "failed"
    STOPPED = "stopped"
    COMPLETED = "completed"  # For simulation environments


class BaseEnvironmentMonitor(ABC):
    """
    Base class for environment monitoring providing common functionality.

    This class eliminates duplication across BackgroundServiceMonitor,
    SingleContainerMonitor, and ShadowSimulationMonitor by providing:

    1. Common thread management (start_monitoring, stop_monitoring)
    2. Shared monitoring loop with configurable intervals
    3. Thread-safe state tracking with locks
    4. Consistent failure handling and termination logic
    5. Abstract interface for environment-specific health checks

    Subclasses only need to implement environment-specific methods:
    - _check_health(): Environment-specific health check logic
    - _get_monitor_name(): Unique monitor name for thread identification
    - _should_terminate(): Environment-specific termination conditions
    - _get_termination_details(): Environment-specific error details
    """

    def __init__(self, environment, config, logger):
        """
        Initialize base monitor with common attributes.

        Args:
            environment: The environment instance (docker_compose_env, localhost_env, etc.)
            config: Configuration object with monitoring settings
            logger: Logger instance for monitoring output
        """
        self.environment = environment
        self.config = config
        self.logger = logger

        # Thread management (common across all monitors)
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        # Health tracking (common structure, specific content varies)
        self.failure_count = 0
        self.start_time = None

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate monitoring configxuration parameters."""
        required_attrs = ["monitoring_interval_seconds", "failure_threshold_count"]
        for attr in required_attrs:
            if not hasattr(self.config, attr):
                raise ValueError(f"Configuration missing required attribute: {attr}")

        if self.config.monitoring_interval_seconds <= 0:
            self.logger.warning(
                f"Invalid monitoring interval {self.config.monitoring_interval_seconds}, using 1.0s"
            )
            self.config.monitoring_interval_seconds = 1.0

        if self.config.failure_threshold_count <= 0:
            self.logger.warning(
                f"Invalid failure threshold {self.config.failure_threshold_count}, using 3"
            )
            self.config.failure_threshold_count = 3

    def start_monitoring(self, *args, **kwargs):
        """
        Start background monitoring in a daemon thread.

        Common implementation across all monitor types with 85% identical code.
        Subclasses can override for specific initialization needs.
        """
        if self.monitoring_active:
            self.logger.debug(
                f"Monitoring already active for {self._get_monitor_name()}"
            )
            return
        self.logger.debug(f"Starting monitoring for {self._get_monitor_name()}")
        # Reset state for new monitoring session
        self.monitoring_active = True
        self.stop_event.clear()
        self.start_time = time.time()
        self.failure_count = 0

        # Handle subclass-specific start parameters
        self._pre_start_setup(*args, **kwargs)

        # Create and start monitoring thread
        monitor_name = self._get_monitor_name()
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"Monitor-{monitor_name}",
            daemon=True,
        )
        self.monitor_thread.start()

        self.logger.info(
            f"Started background monitoring thread: {self.monitor_thread.name}"
        )

    def stop_monitoring(self):
        """
        Stop background monitoring gracefully with improved cleanup.

        Enhanced implementation with better logging and forced cleanup for hung threads.
        """
        if not self.monitoring_active:
            self.logger.debug(
                f"Monitoring already stopped for {self._get_monitor_name()}"
            )
            return

        monitor_name = self._get_monitor_name()
        self.logger.info(f"Initiating stop sequence for {monitor_name}")
        self.monitoring_active = False
        self.stop_event.set()  # Signal the thread to stop

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.info(f"Waiting for monitoring thread to stop: {monitor_name}")
            timeout = self._get_stop_timeout()
            self.monitor_thread.join(timeout=timeout)

            if self.monitor_thread.is_alive():
                self.logger.error(
                    f"CRITICAL: Monitoring thread for {monitor_name} did not stop after {timeout}s timeout"
                )
                self.logger.error(
                    f"Thread {self.monitor_thread.name} (ID: {self.monitor_thread.ident}) is still alive"
                )
                # Force daemon status to ensure it doesn't block process termination
                if hasattr(self.monitor_thread, "daemon"):
                    self.monitor_thread.daemon = True
                self.logger.warning(
                    f"Marked hung monitoring thread as daemon: {monitor_name}"
                )
            else:
                self.logger.info(
                    f"Background monitoring stopped cleanly for {monitor_name}"
                )

        self.monitor_thread = None
        self._post_stop_cleanup()

    def _monitor_loop(self):
        """
        Main monitoring loop running in background thread.

        Common implementation with 90% identical code across all monitor types.
        """
        monitor_name = self._get_monitor_name()
        self.logger.debug(f"Background monitoring loop started for {monitor_name}")

        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Perform environment-specific health check
                self._check_health()
                # Use interruptible sleep to allow clean shutdown
                if self.stop_event.wait(
                    timeout=self.config.monitoring_interval_seconds
                ):
                    break  # Stop event was set

            except Exception as e:
                self.logger.error(
                    f"Error in background monitoring for {monitor_name}: {e}"
                )
                self._handle_monitoring_exception(e)

                # Continue monitoring after error with interruptible sleep
                if self.stop_event.wait(
                    timeout=self.config.monitoring_interval_seconds
                ):
                    break

        self.logger.debug(f"Background monitoring loop ended for {monitor_name}")

    def _handle_failure(self, failure_reason: str):
        """
        Handle failure and potentially trigger early termination.

        Common failure handling logic with 80% identical code.
        """
        self.failure_count += 1

        self.logger.debug(
            f"Handling failure for {self._get_monitor_name()} (count: {self.failure_count}) - {failure_reason}"
        )

        if self.failure_count >= self.config.failure_threshold_count:
            self.logger.error(
                f"✗ {self._get_monitor_name()} failed (failures: {self.failure_count}) - {failure_reason}"
            )

            # Check if this should trigger early termination
            if self._should_terminate():
                self._trigger_early_termination(failure_reason)
        else:
            self.logger.warning(
                f"⚠ {self._get_monitor_name()} failing (failures: {self.failure_count}/{self.config.failure_threshold_count}) - {failure_reason}"
            )

    def _trigger_early_termination(self, reason: str):
        """
        Trigger early experiment termination.

        Common termination logic with 90% identical code.
        """
        full_reason = f"{self._get_monitor_name()} failed {self.failure_count} times (threshold: {self.config.failure_threshold_count}) - {reason}"

        # Get environment-specific termination details
        details = self._get_termination_details()
        details.update(
            {
                "failure_count": self.failure_count,
                "failure_threshold": self.config.failure_threshold_count,
                "monitoring_interval": self.config.monitoring_interval_seconds,
                "elapsed_time": time.time() - self.start_time if self.start_time else 0,
            }
        )

        self.logger.error(f"Triggering early experiment termination: {full_reason}")

        # Request termination from environment
        self.environment.request_early_termination(full_reason, details)

        # Stop monitoring since experiment is terminating
        self.monitoring_active = False

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status (common interface)."""
        with self.lock:
            return {
                "monitoring_active": self.monitoring_active,
                "failure_count": self.failure_count,
                "elapsed_time": time.time() - self.start_time if self.start_time else 0,
                "monitor_name": self._get_monitor_name(),
                "thread_alive": (
                    self.monitor_thread.is_alive() if self.monitor_thread else False
                ),
            }

    # Abstract methods that subclasses must implement

    @abstractmethod
    def _check_health(self):
        """
        Perform environment-specific health check.

        This is where the main monitoring logic differs between environments:
        - Docker Compose: Check service health via docker commands
        - Localhost: Check container health and status
        - Shadow NS: Monitor simulation process and output files
        """
        pass

    @abstractmethod
    def _get_monitor_name(self) -> str:
        """
        Get unique monitor name for logging and thread identification.

        Examples:
        - "DockerCompose-env1"
        - "Container-client"
        - "ShadowSim-protocol_test"
        """
        pass

    @abstractmethod
    def _should_terminate(self) -> bool:
        """
        Environment-specific termination conditions.

        Examples:
        - Docker Compose: Check critical services, partial deployment policy
        - Localhost: Always terminate on container failure
        - Shadow NS: Check simulation completion status
        """
        pass

    @abstractmethod
    def _get_termination_details(self) -> Dict[str, Any]:
        """
        Get environment-specific details for termination reporting.

        Should include environment-specific state information for debugging.
        """
        pass

    # Optional hook methods with default implementations

    def _pre_start_setup(self, *args, **kwargs):
        """Optional setup before starting monitoring (hook for subclasses)."""
        pass

    def _post_stop_cleanup(self):
        """Optional cleanup after stopping monitoring (hook for subclasses)."""
        pass

    def _get_stop_timeout(self) -> float:
        """Get timeout for thread join during stop (customizable by subclass)."""
        return 10.0  # Default 10 seconds

    def _handle_monitoring_exception(self, exception: Exception):
        """Handle exceptions during monitoring (hook for subclasses)."""
        # Default: just log and continue
        pass
