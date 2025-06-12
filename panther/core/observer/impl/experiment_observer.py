import logging
from typing import Any, TYPE_CHECKING
from datetime import datetime

from panther.core.observer.base.observer_interface import IObserver
from panther.core.events import (
    BaseEvent,
    # Experiment events
    ExperimentFinishedEarlyEvent,
    # Test events
    TestExecutionStartedEvent,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    TestCompletedEvent,
    # Step events
    StepExecutionCompletedEvent,
    StepProgressEvent,
    # Environment events
    EnvironmentSetupStartedEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentTeardownStartedEvent,
    # Service events
    ServiceEvent,
    ServicePreparationStartedEvent,
    ServicePreparationCompletedEvent,
    ServiceDeploymentFailedEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    # Metrics events
    MetricCollectedEvent,
)

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    pass


class ExperimentObserver(IObserver):
    """
    Enhanced ExperimentObserver that monitors experiment execution and tracks experiment state.

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
        output_dir: str | None = None,
        test_name: str | None = None,
        track_timing: bool = True,
        track_steps: bool = True,
        global_config: Any = None,
        log_level: str = "INFO",
    ) -> None:
        """
        Initialize the experiment observer with optional configuration.

        Args:
            name: Name identifier for this observer
            output_dir: Directory for any output files
            test_name: Name of the test being observed
            track_timing: Whether to track timing metrics
            track_steps: Whether to track step completion
            global_config: Global configuration object with logging settings
        """
        # Track what we've observed for logging purposes only
        self.observed_environments: set[str] = set()  # Just track what we've seen
        self.observed_services: set[str] = set()  # Just track what we've seen

        # Remove all state dictionaries - state is managed centrally by StateManager
        # These were causing orchestration behavior

        # Set up logging using the interface method
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.enable_colors = True
        self.logger = self._setup_logging(
            logger_name="ExperimentObserver",
            log_level=self.log_level,
            enable_colors=self.enable_colors,
            output_file=output_dir + "/experiment_events.log" if output_dir else None,
            structured_output=True,
        )
        self.experiment_finished_early = False

        self.name = name
        self.output_dir = output_dir
        self.test_name = test_name
        self.track_timing = track_timing
        self.track_steps = track_steps
        self.global_config = global_config

        # Track experiment state
        self.start_time = datetime.now()
        self.current_phase = "initialized"
        self.step_progress = {}
        self.events_received = 0

        # Define mapping of event classes to their handler methods
        self.event_handlers = {
            ExperimentFinishedEarlyEvent: self._handle_experiment_finished_early,
            StepProgressEvent: self._handle_step_progress,
            StepExecutionCompletedEvent: self._handle_step_completed,
            EnvironmentSetupStartedEvent: self._handle_environment_setup_started,
            EnvironmentSetupCompletedEvent: self._handle_environment_setup_completed,
            EnvironmentTeardownStartedEvent: self._handle_environment_teardown,
            ServiceEvent: self._handle_service_event,
            ServiceStartedEvent: self._handle_service_started,
            ServiceStoppedEvent: self._handle_service_stopped,
            ServiceDeploymentFailedEvent: self._handle_service_deployment_failed,
            ServicePreparationStartedEvent: self._handle_service_setup_started,
            ServicePreparationCompletedEvent: self._handle_service_setup_completed,
            TestExecutionFailedEvent: self._handle_test_execution_failed,
            TestExecutionStartedEvent: self._handle_test_execution_started,
            TestCompletedEvent: self._handle_test_completed,
            TestExecutionCompletedEvent: self._handle_test_execution_completed,
            MetricCollectedEvent: self._handle_metric_collected,
        }

    def on_event(self, event: BaseEvent) -> bool:
        """
        Handles an experiment-related event with enhanced tracking.

        Uses type-based dispatch to specialized handler methods.

        Args:
            event: BaseEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        self.events_received += 1

        # Skip if already processed
        event_data = getattr(event, "data", {})
        if event_data.get("already_logged", False):
            return True

        # Find a handler for this event type using inheritance
        best_match = None
        best_match_cls = None

        # Debug output to see registered handlers and event type
        self.logger.debug("Event received: %s", event.__class__.__name__)

        # Find the most specific handler based on class hierarchy
        for event_cls, handler in self.event_handlers.items():
            if isinstance(event, event_cls):
                # If we don't have a match yet, or this class is more specific (subclass of our current best)
                if best_match_cls is None or issubclass(event_cls, best_match_cls):
                    best_match = handler
                    best_match_cls = event_cls

        # Call the handler if we found one
        if best_match:
            self.logger.debug(
                "Handling event %s with handler for %s",
                event.__class__.__name__,
                best_match_cls.__name__,
            )
            return best_match(event)

        # Default handling for unrecognized events
        self.logger.debug("Unhandled event type: %s", event.__class__.__name__)
        return True

    def _handle_experiment_finished_early(self, event: ExperimentFinishedEarlyEvent) -> bool:
        """Handle early experiment termination events."""
        action = event.data.get("action", "notify")

        if action == "notify":
            self.current_phase = "finished_early"
            self.logger.info("Experiment finished early")
            self.experiment_finished_early = True

            reason = event.data.get("reason", "No reason provided")
            self.logger.debug(f"Reason: {reason}")

            # Just log that experiment finished early - no orchestration
            self.logger.info("Experiment finished early notification received")

            if self.track_timing:
                self._record_timing_info("early_termination", self.start_time)

        elif action == "check":
            self.logger.debug(
                "Checking if experiment finished early: %s", self.experiment_finished_early
            )

        return self.experiment_finished_early

    def _handle_step_progress(self, event: StepProgressEvent) -> bool:
        """Handle step progress events."""
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

        # Log progress with proper formatting
        if progress_percentage is not None:
            self.logger.debug(
                "Step progress: %s (%s) at %.1f%% - %s",
                step_name,
                test_case_id if test_case_id else "unknown test",
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

    def _handle_step_completed(self, event: StepExecutionCompletedEvent) -> bool:
        """Handle step completion events."""
        step_id = event.data.get("step_id")
        success = event.data.get("success", False)
        result = event.data.get("result") or {}

        self.logger.info("Step completed: %s - %s", step_id, "Success" if success else "Failed")

        # Log details with consistent indentation
        if result:
            for key, value in result.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_environment_setup_started(self, event: EnvironmentSetupStartedEvent) -> bool:
        """Handle environment setup started events with enhanced state tracking."""
        self.current_phase = "environment_setup"
        environment_type = event.data.get("environment_type", "unknown")
        environment_name = event.data.get("environment_instance", "unknown")
        test_case = event.data.get("test_case", "unknown_test")

        # Just track that we've seen this environment
        self.observed_environments.add(environment_name)

        self.logger.info(
            "Environment setup started for %s environment in test '%s'", environment_type, test_case
        )

        if self.track_timing:
            self._record_timing_info("environment_setup_start", event.timestamp)

        return True

    def _handle_environment_setup_completed(self, event: EnvironmentSetupCompletedEvent) -> bool:
        """Handle environment setup completed events with enhanced state tracking."""
        success = event.data.get("success", False)
        details = event.data.get("details", {})
        environment_type = details.get("environment_type", "unknown")
        test_case = details.get("test_case", "unknown_test")

        # Get environment name if available
        environment_name = details.get("environment_instance", environment_type)

        # Just log the completion status
        status_msg = "successfully" if success else "with errors"

        if success:
            self.logger.info(
                "Environment setup completed successfully for %s environment in test '%s'",
                environment_type,
                test_case,
            )
        else:
            error_msg = details.get("error", "Unknown error")
            self.logger.error(
                "Environment setup failed for %s environment in test '%s': %s",
                environment_type,
                test_case,
                error_msg,
            )

        if self.track_timing:
            self._record_timing_info("environment_setup_end", event.timestamp)

        return True

    def _handle_environment_teardown(self, event: EnvironmentTeardownStartedEvent) -> bool:
        """Handle environment teardown events."""
        self.current_phase = "environment_teardown"
        env_type = event.data.get("type")
        success = event.data.get("success", False)
        details = event.data.get("details") or {}

        self.logger.info(
            "Environment teardown: %s - %s", env_type, "Success" if success else "Failed"
        )

        # Just note that we've seen this environment teardown
        env_name = details.get("environment_name", env_type)
        self.logger.debug(f"Observed environment '{env_name}' teardown")

        # Record timing information
        if self.track_timing:
            self._record_timing_info("environment_teardown", self.start_time)

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

        # Just log the teardown
        self.logger.debug(f"Environment '{env_name}' teardown observed")

        return True

    def _handle_service_event(self, event: ServiceEvent) -> bool:
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

            self.logger.info("Services deployed: %s", ", ".join(services) if services else "None")

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
            if key not in ["service_instances", "services"]:  # Don't log instance objects
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_service_started(self, event: ServiceStartedEvent) -> bool:
        """Handle service started events."""
        service_name = event.data.get("service_name")
        pid = event.data.get("pid")
        start_time = event.data.get("start_time")

        self.logger.info(
            "Service started: %s (PID: %s)", service_name, pid if pid is not None else "N/A"
        )

        # Log start time if available
        if start_time:
            self.logger.debug(f"  Start time: {start_time}")

        # Just track that we've seen this service
        self.observed_services.add(service_name)

        return True

    def _handle_service_stopped(self, event: ServiceStoppedEvent) -> bool:
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

        # Just log that the service stopped
        self.logger.debug(f"Observed service '{service_name}' stop")

        # Log uptime if available
        uptime = event.data.get("uptime_seconds")
        if uptime is not None:
            self.logger.debug(f"  Service uptime: {uptime:.2f} seconds")

        # Service stop observed

        return True

    def _handle_service_deployment_failed(self, event: ServiceDeploymentFailedEvent) -> bool:
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

    def _handle_service_setup_started(self, event: ServicePreparationStartedEvent) -> bool:
        """Handle service setup started events with enhanced state tracking."""
        # Extract data from the actual event structure
        service_name = event.data.get("service_name", "unknown_service")
        preparation_steps = event.data.get("preparation_steps", [])

        # Try to get test_case from event data (added by emitter)
        test_case = event.data.get("test_case", "unknown_test")

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

    def _handle_service_setup_completed(self, event: ServicePreparationCompletedEvent) -> bool:
        """Handle service setup completed events with enhanced state tracking."""
        # Extract data from the actual event structure
        service_name = event.data.get("service_name", "unknown_service")
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
            test_case,
            f" (duration: {duration:.2f}s)" if duration else "",
        )

        if self.track_timing:
            self._record_timing_info("service_setup_end", event.timestamp)

        return True

    def _handle_test_execution_failed(self, event: TestExecutionFailedEvent) -> bool:
        """
        Handle test execution failed events.

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

    def _handle_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
        """
        Handle test execution started events.

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

    def _handle_test_completed(self, event: TestCompletedEvent) -> bool:
        """
        Handle test completed events.

        Args:
            event: The TestCompletedEvent to handle

        Returns:
            bool: True if the event was processed successfully
        """
        self.current_phase = "test_completed"
        test_name = event.data.get("test_name")
        success = event.data.get("success", False)
        result = event.data.get("result") or {}

        self.logger.info("Test completed: %s - %s", test_name, "Success" if success else "Failed")

        if self.track_timing:
            self._record_timing_info("test_completed", self.start_time)

        # Log result details with consistent indentation
        if result:
            for key, value in result.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_test_execution_completed(self, event: TestExecutionCompletedEvent) -> bool:
        """
        Handle test execution completed events.

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

        # Log results details with consistent indentation
        if results:
            for key, value in results.items():
                self.logger.debug(f"  {key}: {value}")

        if self.track_timing:
            self._record_timing_info("test_execution_completed", self.start_time)

        return True

    def _handle_metric_collected(self, event: MetricCollectedEvent) -> bool:
        """
        Handle metric collected events.

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

        self.logger.debug("Metric collected: %s (%s) = %s", metric_name, metric_type, value)

        return True

    def _record_timing_info(self, checkpoint_name: str, reference_time: datetime) -> None:
        """
        Record timing information for experiment metrics.

        Args:
            checkpoint_name: Name of the checkpoint being recorded
            reference_time: Reference time to calculate duration from
        """
        duration = (datetime.now() - reference_time).total_seconds()
        self.logger.debug("Checkpoint '%s' reached after %.2f seconds", checkpoint_name, duration)

    def get_experiment_status(self) -> dict[str, Any]:
        """
        Get a summary of the current experiment status.

        Returns:
            Dict containing experiment status information
        """
        return {
            "current_phase": self.current_phase,
            "observed_environments": list(self.observed_environments),
            "observed_services": list(self.observed_services),
            "events_received": self.events_received,
            "experiment_finished_early": self.experiment_finished_early,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
            "step_progress": self.step_progress,
        }

    # Orchestration methods removed - ExperimentObserver is now purely observational

    def get_priority(self) -> int:
        """
        Get the priority for this observer.

        Returns:
            int: Priority value (lower number = higher priority)
        """
        return 50  # Medium priority

    def should_terminate_early(self) -> bool:
        """
        Check if the experiment should terminate early.

        Returns:
            bool: True if the experiment should finish early
        """
        return self.experiment_finished_early

    def is_interested(self, event_type: str) -> bool:
        """
        Check if this observer is interested in an event type.

        Args:
            event_type: Type of event to check interest for

        Returns:
            bool: True if the observer is interested in events of this type
        """
        # The type-based handlers in on_event make this unnecessary,
        # but keeping for compatibility with observer registry
        return True

    # All orchestration methods have been removed.
    # State management is now handled centrally by StateManager.
    # ExperimentObserver only observes and logs events.
