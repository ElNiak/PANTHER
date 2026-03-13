"""Observer that tracks experiment lifecycle events and manages state."""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional, Set

from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.events.experiment.events import (
    ExperimentFinishedEarlyEvent,
    ExperimentServiceFailureEvent,
)
from panther.core.observer.base.observer_interface import IObserver


class ExperimentObserver(IObserver):
    """Enhanced ExperimentObserver that monitors experiment execution and tracks experiment state.

    This observer handles experiment-specific events, tracks environment monitoring,
    and provides status reporting for experiment execution.

    It integrates with the global logging configuration and supports:
    - Tracking experiment state and progress
    - Environment monitoring coordination
    - Consistent formatting with other observers
    - Integration with metrics collection
    """

    def __init__(
        self,
        name: str = "experiment",
        output_dir: Optional[str] = None,
        test_name: Optional[str] = None,
        track_timing: bool = True,
        track_steps: bool = True,
        global_config: Any = None,
        log_level: str = "INFO",
    ) -> None:
        """Initialize the experiment observer with optional configuration.

        Args:
            name: Name identifier for this observer
            output_dir: Directory for any output files
            test_name: Name of the test being observed
            track_timing: Whether to track timing metrics
            track_steps: Whether to track step completion
            global_config: Global configuration object with logging settings
            log_level: Log level string (default "INFO")
        """
        # Track what we've observed for logging purposes only
        self.observed_environments: Set[str] = set()  # Just track what we've seen
        self.observed_services: Set[str] = set()  # Just track what we've seen

        # Remove all state dictionaries - state is managed centrally by StateManager
        # These were causing orchestration behavior

        # Set up logging using the interface method
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.enable_colors = True

        self.logger = self._setup_logging(
            logger_name="ExperimentObserver",
            log_level=self.log_level,
            enable_colors=self.enable_colors,
            output_file=(f"{output_dir}/experiment_events.log" if output_dir else None),
            structured_output=True,
        )

        # Create or update progress bar for this step
        if not hasattr(self, "_step_progress_bars"):
            self._step_progress_bars = {}

        self.experiment_finished_early = False
        self._should_terminate_early = False
        self._termination_reason = None

        self.name = name
        self.output_dir = output_dir
        self.test_name = test_name
        self.track_timing = track_timing
        self.track_steps = track_steps
        self.global_config = global_config

        # Track experiment state (guarded by _state_lock for cross-thread access)
        self._state_lock = threading.Lock()
        self.start_time = datetime.now()
        self.current_phase = "initialized"
        self.step_progress = {}
        self.events_received = 0

        # Dispatch by (entity_type, event_name) → handler.
        # This avoids isinstance() on backward-compat alias functions.
        self._event_handlers = {
            (
                EventType.EXPERIMENT,
                "finished_early",
            ): self._handle_experiment_finished_early,
            (
                EventType.EXPERIMENT,
                "service_failure",
            ): self._handle_experiment_service_failure,
            (EventType.STEP, "progress"): self._handle_step_progress,
            (EventType.STEP, "execution_completed"): self._handle_step_completed,
            (EventType.ENVIRONMENT, "created"): self._handle_environment_created,
            (
                EventType.ENVIRONMENT,
                "setup_started",
            ): self._handle_environment_setup_started,
            (
                EventType.ENVIRONMENT,
                "setup_completed",
            ): self._handle_environment_setup_completed,
            (
                EventType.ENVIRONMENT,
                "deployment_started",
            ): self._handle_environment_deployment_started,
            (
                EventType.ENVIRONMENT,
                "teardown_started",
            ): self._handle_environment_teardown,
            (EventType.ENVIRONMENT, "error"): self._handle_environment_error,
            (EventType.ENVIRONMENT, "destroyed"): self._handle_environment_destroyed,
            (EventType.SERVICE, "started"): self._handle_service_started,
            (EventType.SERVICE, "stopped"): self._handle_service_stopped,
            (
                EventType.SERVICE,
                "deployment_failed",
            ): self._handle_service_deployment_failed,
            (EventType.SERVICE, "destroyed"): self._handle_service_destroyed,
            (
                EventType.SERVICE,
                "preparation_started",
            ): self._handle_service_setup_started,
            (
                EventType.SERVICE,
                "preparation_completed",
            ): self._handle_service_setup_completed,
            (EventType.TEST, "execution_failed"): self._handle_test_execution_failed,
            (EventType.TEST, "execution_started"): self._handle_test_execution_started,
            (EventType.TEST, "completed"): self._handle_test_completed,
            (
                EventType.TEST,
                "execution_completed",
            ): self._handle_test_execution_completed,
            (EventType.METRICS, "metric_collected"): self._handle_metric_collected,
        }

    def on_event(self, event: BaseEvent) -> bool:
        """Handles an experiment-related event with enhanced tracking.

        Uses (entity_type, event_name) dispatch to specialized handler methods.

        Args:
            event: BaseEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        with self._state_lock:
            self.events_received += 1

        # Skip if already processed
        event_data = getattr(event, "data", {})
        if event_data.get("already_logged", False):
            return True

        # Look up handler by (entity_type, event_name) tuple
        handler = self._event_handlers.get((event.entity_type, event.name))

        # Fallback for unmatched service events
        if handler is None and event.entity_type == EventType.SERVICE:
            handler = self._handle_service_event

        if handler:
            return handler(event)

        # Default handling for unrecognized events
        self.logger.debug("Unhandled event type: %s", event.__class__.__name__)
        return True

    def _handle_experiment_finished_early(
        self, event: ExperimentFinishedEarlyEvent
    ) -> bool:
        """Handle early experiment termination events."""
        action = event.data.get("action", "notify")

        if action == "notify":
            with self._state_lock:
                self.current_phase = "finished_early"
                self.experiment_finished_early = True
            self.logger.info("Experiment finished early")

            reason = event.data.get("reason", "No reason provided")
            self.logger.debug(f"Reason: {reason}")

            # Just log that experiment finished early - no orchestration
            self.logger.info("Experiment finished early notification received")

            if self.track_timing:
                self._record_timing_info("early_termination", self.start_time)

        elif action == "check":
            self.logger.debug(
                "Checking if experiment finished early: %s",
                self.experiment_finished_early,
            )

        return self.experiment_finished_early

    def _handle_step_progress(self, event: BaseEvent) -> bool:
        """Handle step progress events with progress bar support."""
        self.current_phase = "running_steps"
        step_id = event.data.get("step_id")
        step_name = event.data.get("step_name", step_id)
        progress_percentage = event.data.get("progress_percentage")
        progress_message = event.data.get("progress_message", "")
        test_case_id = event.data.get("test_case_id")
        details = event.data.get("details") or {}

        # Track step progress
        if self.track_steps and step_id:
            if step_id not in self.step_progress:
                self.step_progress[step_id] = []
            self.step_progress[step_id].append(
                {
                    "percentage": progress_percentage,
                    "message": progress_message,
                    "timestamp": datetime.now(),
                }
            )

        # Handle progress bar for waiting/long-running steps
        if (
            progress_percentage is not None
            and self.global_config
            and self.global_config.progress.enable_progress_bar
        ):
            try:
                # Create unique key for this step
                pbar_key = f"{test_case_id or 'unknown'}_{step_name}_{step_id}"

                if pbar_key not in self._step_progress_bars:
                    # Create new Click progress bar for this waiting step
                    # Note: Click progressbar doesn't support position like tqdm, so we'll use coordinated messages

                    # Log initial progress bar creation using logger for coordination
                    self.logger.info(
                        f"🚀 Started progress tracking for {step_name} in {test_case_id or 'unknown test'}"
                    )

                    # Store progress state for this step
                    self._step_progress_bars[pbar_key] = {
                        "current_progress": 0,
                        "step_name": step_name,
                        "test_case_id": test_case_id or "unknown test",
                        "last_message": "",
                    }

                step_state = self._step_progress_bars[pbar_key]

                # Update progress
                new_progress = min(int(progress_percentage), 100)
                if new_progress > step_state["current_progress"]:
                    step_state["current_progress"] = new_progress

                    # Update message if provided
                    if (
                        progress_message
                        and progress_message != step_state["last_message"]
                    ):
                        step_state["last_message"] = progress_message
                        self.logger.info(
                            f"⏳ {step_name} ({test_case_id or 'unknown test'}): {progress_message} [{new_progress}%]"
                        )

                # Close progress bar when complete (only when step is truly finished)
                if progress_percentage >= 100.0:
                    # Use logger for coordinated completion message
                    self.logger.info(
                        f"✅ {step_name} completed in {test_case_id or 'unknown test'}"
                    )
                    # Don't close immediately - let test completion handle cleanup
                    # This prevents premature disappearing during step execution
            except Exception as e:
                # If progress bar fails, continue with regular logging
                self.logger.debug("Progress bar error: %s", e)
        # Log progress with proper formatting
        elif progress_percentage is not None:
            self.logger.debug(
                "Step progress: %s (%s) at %.1f%% - %s",
                step_name,
                test_case_id or "unknown test",
                progress_percentage,
                progress_message,
            )
        else:
            self.logger.debug("Step progress: %s - %s", step_name, progress_message)

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _cleanup_step_progress_bars(self, test_name: str = None) -> None:
        """Clean up step progress bars for a specific test or all tests.

        Args:
            test_name: Optional test name to clean up bars for. If None, cleans up all bars.
        """
        if not hasattr(self, "_step_progress_bars"):
            return

        try:
            # Get list of keys to remove (to avoid modifying dict during iteration)
            keys_to_remove = []

            for pbar_key, step_state in list(self._step_progress_bars.items()):
                # If test_name is specified, only clean up bars for that test
                if test_name and not pbar_key.startswith(test_name.replace(" ", "_")):
                    continue

                try:
                    # Mark step as complete if it hasn't reached 100%
                    if (
                        isinstance(step_state, dict)
                        and step_state.get("current_progress", 0) < 100
                    ):
                        step_name = step_state.get("step_name", "Unknown Step")
                        test_case_id = step_state.get("test_case_id", "unknown test")
                        self.logger.info(f"✅ {step_name} completed in {test_case_id}")

                    keys_to_remove.append(pbar_key)

                    # Use logger for coordinated cleanup message
                    if test_name:
                        self.logger.info(
                            f"🧹 Cleaned up progress tracking for {test_name}"
                        )

                except Exception as e:
                    self.logger.debug(
                        f"Error cleaning up progress tracking {pbar_key}: {e}"
                    )

            # Remove cleaned up progress trackers from our tracking dict
            for key in keys_to_remove:
                del self._step_progress_bars[key]

        except Exception as e:
            self.logger.debug(f"Error during progress tracking cleanup: {e}")

    def _handle_step_completed(self, event: BaseEvent) -> bool:
        """Handle step completion events."""
        step_id = event.data.get("step_id")
        success = event.data.get("success", False)
        result = event.data.get("result") or {}

        self.logger.info(
            "Step completed: %s - %s", step_id, "Success" if success else "Failed"
        )

        # Log details with consistent indentation
        if result:
            for key, value in result.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_environment_setup_started(self, event: BaseEvent) -> bool:
        """Handle environment setup started events with enhanced state tracking."""
        self.current_phase = "environment_setup"

        # Debug: Log the event structure
        self.logger.debug("EnvironmentSetupStartedEvent data: %s", event.data)
        self.logger.debug(
            "EnvironmentSetupStartedEvent environment_type attribute: %s",
            getattr(event, "environment_type", "not found"),
        )

        # Try to get environment_type from event attribute first, then from data
        environment_type = getattr(
            event, "environment_type", event.data.get("environment_type", "unknown")
        )
        environment_name = getattr(
            event, "environment_name", event.data.get("environment_instance", "unknown")
        )

        # Test case might be in setup_config
        setup_config = event.data.get("setup_config", {})
        test_case = setup_config.get(
            "test_case", event.data.get("test_case", "unknown_test")
        )

        # Just track that we've seen this environment
        self.observed_environments.add(environment_name)

        self.logger.info(
            "Environment setup started for %s environment in test '%s'",
            environment_type,
            test_case,
        )

        if self.track_timing:
            self._record_timing_info("environment_setup_start", event.timestamp)

        return True

    def _handle_environment_setup_completed(self, event: BaseEvent) -> bool:
        """Handle environment setup completed events with enhanced state tracking."""
        success = event.data.get(
            "success", True
        )  # Default to True unless explicitly set to False

        # Check both data.details and data.resources_allocated for backward compatibility
        details = event.data.get("details", {})
        resources_allocated = event.data.get("resources_allocated", {})

        # Merge both sources to get complete information
        combined_details = {**details, **resources_allocated}

        environment_type = (
            event.environment_type
            if hasattr(event, "environment_type")
            else combined_details.get("environment_type", "unknown")
        )
        test_case = combined_details.get("test_case", "unknown_test")

        # Get environment name if available
        environment_name = combined_details.get(
            "environment_instance", environment_type
        )

        if success:
            self.logger.info(
                "Environment setup completed successfully for %s environment in test '%s'",
                environment_type,
                test_case,
            )
        else:
            error_msg = combined_details.get("error", "Unknown error")
            self.logger.error(
                "Environment setup failed for %s environment in test '%s': %s",
                environment_type,
                test_case,
                error_msg,
            )

        if self.track_timing:
            self._record_timing_info("environment_setup_end", event.timestamp)

        return True

    def _handle_environment_teardown(self, event: BaseEvent) -> bool:
        """Handle environment teardown events."""
        self.current_phase = "environment_teardown"
        env_type = event.data.get("type")
        details = event.data.get("details") or {}

        env_name = details.get("environment_name", env_type)
        self.logger.info("Environment teardown started: %s", env_name)

        # Record timing information
        if self.track_timing:
            self._record_timing_info("environment_teardown", self.start_time)

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_service_event(self, event: BaseEvent) -> bool:
        """Handle generic service events."""
        event_name = event.name
        data = event.data or {}

        if event_name == "service.setup" or event_name == "services_setup":
            self.current_phase = "services_setup"
            service_name = data.get("service_name", "unknown")
            self.logger.info("Service setup started: %s", service_name)

        elif event_name == "service.deployed" or event_name == "services_deployed":
            self.current_phase = "services_deployed"
            services = data.get("services", [data.get("service_name", "unknown")])

            if isinstance(services, str):
                services = [services]

            self.logger.info(
                "Services deployed: %s", ", ".join(services) if services else "None"
            )

            # Just track that we've seen these services
            if "service_instances" in data:
                service_instances = data["service_instances"]
                if isinstance(service_instances, dict):
                    for name in service_instances.keys():
                        self.observed_services.add(name)
                        self.logger.debug(f"Observed service '{name}' deployment")

            # Record timing information
            if self.track_timing:
                self._record_timing_info("services_deployed", self.start_time)

        elif event_name == "service.teardown" or event_name == "service_teardown":
            self.current_phase = "services_teardown"
            self.logger.info("Service teardown in progress")

            # Record timing information
            if self.track_timing:
                self._record_timing_info("services_teardown", self.start_time)

        # Log details with consistent indentation
        for key, value in data.items():
            if key not in [
                "service_instances",
                "services",
            ]:  # Don't log instance objects
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_service_started(self, event: BaseEvent) -> bool:
        """Handle service started events."""
        service_name = event.data.get("service_name")
        pid = event.data.get("pid")
        start_time = event.data.get("start_time")

        self.logger.info(
            "Service started: %s (PID: %s)",
            service_name,
            pid if pid is not None else "N/A",
        )

        # Log start time if available
        if start_time:
            self.logger.debug(f"  Start time: {start_time}")

        # Just track that we've seen this service
        self.observed_services.add(service_name)

        return True

    def _handle_service_stopped(self, event: BaseEvent) -> bool:
        """Handle service stopped events."""
        service_name = event.data.get("service_name")
        exit_code = event.data.get("exit_code")
        reason = event.data.get("reason", "Unknown")

        self.logger.info(
            "Service stopped: %s - Exit code: %s, Reason: %s",
            service_name,
            exit_code if exit_code is not None else "N/A",
            reason,
        )

        # Only flag early termination for unexpected stops (non-zero exit code
        # or explicit "unexpected" reason).  Normal post-test shutdowns should
        # not trigger early termination.
        is_unexpected = (exit_code is not None and exit_code != 0) or reason in (
            "unexpected",
            "crashed",
            "killed",
        )
        if is_unexpected:
            with self._state_lock:
                self._should_terminate_early = True
                self.experiment_finished_early = True

        # Just log that the service stopped
        self.logger.debug(f"Observed service '{service_name}' stop")

        # Log uptime if available
        uptime = event.data.get("uptime_seconds")
        if uptime is not None:
            self.logger.debug(f"  Service uptime: {uptime:.2f} seconds")

        # Service stop observed

        return True

    def _handle_service_deployment_failed(self, event: BaseEvent) -> bool:
        """Handle service deployment failure events."""
        data = event.data or {}
        environment = data.get("environment", "unknown")
        service_name = data.get("service_name", "unknown service")
        error = data.get("error", "Unknown error")
        error_type = data.get("error_type", "Unknown error type")

        self.current_phase = "service_deployment_failed"

        # Log the error with appropriate severity
        self.logger.error(
            "Service deployment failed in environment %s: %s - %s (%s)",
            environment,
            service_name,
            error,
            error_type,
        )

        # Log additional details with consistent indentation
        for key, value in data.items():
            if key not in ["environment", "service_name", "error", "error_type"]:
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_service_setup_started(self, event: BaseEvent) -> bool:
        """Handle service setup started events with enhanced state tracking."""
        # Extract data from the actual event structure
        service_name = event.data.get("service_name") or "unknown_service"
        preparation_steps = event.data.get("preparation_steps", [])

        # Try to get test_case from event data (added by emitter)
        test_case = event.data.get("test_case") or "unknown_test"

        # Extract test case from service_id if not in data
        if test_case == "unknown_test":
            service_id = getattr(event, "service_id", "")
            if "_" in service_id:
                parts = service_id.split("_", 1)
                if len(parts) > 1:
                    test_case = parts[0]

        # Just track that we've seen this service
        self.observed_services.add(service_name)

        self.logger.info(
            "Service preparation started for '%s' in test '%s'%s",
            service_name,
            test_case,
            f" with steps: {preparation_steps}" if preparation_steps else "",
        )

        if self.track_timing:
            self._record_timing_info("service_setup_start", event.timestamp)

        return True

    def _handle_service_setup_completed(self, event: BaseEvent) -> bool:
        """Handle service setup completed events with enhanced state tracking."""
        # Extract data from the actual event structure
        service_name = event.data.get("service_name") or "unknown_service"
        duration = event.data.get("duration_seconds")
        artifacts = event.data.get("artifacts", {})

        # Extract test case from service_id if available
        service_id = getattr(event, "service_id", "")
        test_case = "unknown_test"
        if "_" in service_id:
            # Service ID format is typically "test_case_service_name"
            parts = service_id.split("_", 1)
            if len(parts) > 1:
                test_case = parts[0]

        # Service setup completion observed

        self.logger.info(
            "Service preparation completed for '%s' in test '%s'%s",
            service_name,
            self.name if self.test_name else test_case,
            f" (duration: {duration:.2f}s)" if duration else "",
        )

        if self.track_timing:
            self._record_timing_info("service_setup_end", event.timestamp)

        return True

    def _handle_test_execution_failed(self, event: BaseEvent) -> bool:
        """Handle test execution failed events.

        Args:
            event: The TestExecutionFailedEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        self.current_phase = "test_execution_failed"
        test_name = event.data.get("test_name", "unknown test")
        error_message = event.data.get("error_message", "Unknown error")
        stack_trace = event.data.get("stack_trace")
        error_details = event.data.get("error_details", {})

        # Log the error with appropriate severity
        self.logger.error("Test execution failed: %s - %s", test_name, error_message)

        # Log stack trace if available
        if stack_trace:
            for line in stack_trace.splitlines():
                self.logger.debug("  %s", line)

        # Log error details with consistent indentation
        if error_details:
            for key, value in error_details.items():
                self.logger.debug(f"  {key}: {value}")

        # Record timing information
        if self.track_timing:
            self._record_timing_info("test_execution_failed", self.start_time)

        return True

    def _handle_test_execution_started(self, event: BaseEvent) -> bool:
        """Handle test execution started events.

        Args:
            event: The TestExecutionStartedEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        self.current_phase = "test_execution_started"
        test_id = event.data.get("test_id")
        test_name = event.data.get("test_name")
        start_time = event.data.get("start_time")

        self.logger.info("Test execution started: %s", test_name)

        if self.track_timing:
            self.start_time = datetime.now()
            self._record_timing_info("test_execution_started", self.start_time)

        return True

    def _handle_test_completed(self, event: BaseEvent) -> bool:
        """Handle test completed events.

        Args:
            event: The TestCompletedEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        self.current_phase = "test_completed"
        test_name = event.data.get("test_name")
        success = event.data.get("success", False)
        result = event.data.get("result") or {}

        self.logger.info(
            "Test completed: %s - %s", test_name, "Success" if success else "Failed"
        )

        # Clean up step progress bars for this test
        self._cleanup_step_progress_bars(test_name)

        if self.track_timing:
            self._record_timing_info("test_completed", self.start_time)

        # Log result details with consistent indentation
        if result:
            for key, value in result.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_test_execution_completed(self, event: BaseEvent) -> bool:
        """Handle test execution completed events.

        Args:
            event: The TestExecutionCompletedEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        self.current_phase = "test_execution_completed"
        test_id = event.data.get("test_id")
        test_name = event.data.get("test_name")
        success = event.data.get("success", False)
        results = event.data.get("results") or {}
        duration_ms = event.data.get("duration_ms")

        self.logger.info(
            "Test execution completed: %s - %s (Duration: %s ms)",
            test_name,
            "Success" if success else "Failed",
            duration_ms if duration_ms is not None else "unknown",
        )

        # Clean up step progress bars for this test
        self._cleanup_step_progress_bars(test_name)

        # Log results details with consistent indentation
        if results:
            for key, value in results.items():
                self.logger.debug(f"  {key}: {value}")

        if self.track_timing:
            self._record_timing_info("test_execution_completed", self.start_time)

        return True

    def _handle_metric_collected(self, event: BaseEvent) -> bool:
        """Handle metric collected events.

        Args:
            event: The MetricCollectedEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        # Generally, we don't need to do much with metrics since they're already being collected
        # but we can log them at debug level
        metric_name = event.data.get("metric_name")
        metric_type = event.data.get("metric_type")
        value = event.data.get("value")

        self.logger.debug(
            "Metric collected: %s (%s) = %s", metric_name, metric_type, value
        )

        return True

    def _record_timing_info(
        self, checkpoint_name: str, reference_time: datetime
    ) -> None:
        """Record timing information for experiment metrics.

        Args:
            checkpoint_name: Name of the checkpoint being recorded
            reference_time: Reference time to calculate duration from
        """
        duration = (datetime.now() - reference_time).total_seconds()
        self.logger.debug(
            "Checkpoint '%s' reached after %.2f seconds", checkpoint_name, duration
        )

    def get_experiment_status(self) -> Dict[str, Any]:
        """Get a summary of the current experiment status (thread-safe).

        Returns:
            Dict containing experiment status information
        """
        with self._state_lock:
            return {
                "current_phase": self.current_phase,
                "observed_environments": list(self.observed_environments),
                "observed_services": list(self.observed_services),
                "events_received": self.events_received,
                "experiment_finished_early": self.experiment_finished_early,
                "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
                "step_progress": dict(self.step_progress),
            }

    # Orchestration methods removed - ExperimentObserver is now purely observational

    def get_priority(self) -> int:
        """Get the priority for this observer.

        Returns:
            int: Priority value (lower number = higher priority)
        """
        return 50  # Medium priority

    def should_terminate_early(self) -> bool:
        """Check if the experiment should terminate early (thread-safe).

        Returns:
            bool: True if the experiment should finish early
        """
        with self._state_lock:
            return self._should_terminate_early or self.experiment_finished_early

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in an event type.

        Args:
            event_type: Type of event to check interest for

        Returns:
            bool: True if the observer is interested in events of this type
        """
        # The type-based handlers in on_event make this unnecessary,
        # but keeping for compatibility with observer registry
        return True

    def _handle_environment_created(self, event: BaseEvent) -> bool:
        """Handle environment created events."""
        environment_type = (
            event.environment_type if hasattr(event, "environment_type") else "unknown"
        )
        environment_name = (
            event.environment_name if hasattr(event, "environment_name") else "unknown"
        )

        self.logger.info(
            "Environment created: %s (%s)", environment_name, environment_type
        )

        # Just track that we've seen this environment
        self.observed_environments.add(environment_name)

        if self.track_timing:
            self._record_timing_info("environment_created", event.timestamp)

        return True

    def _handle_environment_deployment_started(self, event: BaseEvent) -> bool:
        """Handle environment deployment started events."""
        self.current_phase = "environment_deployment"

        environment_type = (
            event.environment_type if hasattr(event, "environment_type") else "unknown"
        )
        environment_name = (
            event.environment_name if hasattr(event, "environment_name") else "unknown"
        )

        self.logger.info(
            "Environment deployment started: %s (%s)",
            environment_name,
            environment_type,
        )

        # Just track that we've seen this environment deployment
        self.observed_environments.add(environment_name)

        if self.track_timing:
            self._record_timing_info("environment_deployment_started", event.timestamp)

        return True

    def _handle_environment_destroyed(self, event: BaseEvent) -> bool:
        """Handle environment destroyed events."""
        environment_type = getattr(event, "environment_type", "unknown")
        environment_name = getattr(event, "environment_name", "unknown")

        self.logger.info(
            "Environment destroyed: %s (%s)", environment_name, environment_type
        )

        if self.track_timing:
            self._record_timing_info("environment_destroyed", event.timestamp)

        return True

    def _handle_service_destroyed(self, event: BaseEvent) -> bool:
        """Handle service destroyed events."""
        service_name = event.data.get("service_name", "unknown")

        self.logger.info("Service destroyed: %s", service_name)

        if self.track_timing:
            self._record_timing_info("service_destroyed", event.timestamp)

        return True

    def _handle_environment_error(self, event: BaseEvent) -> bool:
        """Handle environment error events and check for early termination.

        Args:
            event: The EnvironmentErrorEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        error_message = event.data.get("error_message", "Unknown error")
        error_type = event.data.get("error_type", "unknown")

        self.logger.error("Environment error: %s (type: %s)", error_message, error_type)

        # Check if this is an early termination request
        with self._state_lock:
            self._should_terminate_early = True
            self._termination_reason = error_message
            self.experiment_finished_early = True
        self.logger.warning(
            "Environment requested early termination: %s", error_message
        )

        return True

    def _handle_experiment_service_failure(
        self, event: ExperimentServiceFailureEvent
    ) -> bool:
        """Handle experiment service failure events.

        Args:
            event: The ExperimentServiceFailureEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        failed_service = event.failed_service
        reason = event.reason
        details = event.data.get("details", {})

        self.logger.error("Service failure detected: %s - %s", failed_service, reason)

        # Mark for early termination
        with self._state_lock:
            self._should_terminate_early = True
            self._termination_reason = f"Service failure: {reason}"
            self.experiment_finished_early = True

        # Log additional details
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    # All orchestration methods have been removed.
    # State management is now handled centrally by StateManager.
    # ExperimentObserver only observes and logs events.
