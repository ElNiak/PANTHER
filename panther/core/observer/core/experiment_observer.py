import logging
from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime

from panther.core.observer.core.observer_interface import IObserver
from panther.core.observer.events import (
    Event,
    ExperimentFinishedEarlyEvent,
    StepProgressEvent,
    StepCompletedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentTeardownEvent,
    ServiceEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    TestExecutionStartedEvent,
    TestCompletedEvent,
    TestExecutionCompletedEvent,
    MetricCollectedEvent,
)
from panther.plugins.environments.environment_interface import IEnvironmentPlugin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.plugins.services.services_interface import IServiceManager


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
        self.environment_plugins: dict[str, IEnvironmentPlugin] = {}
        self.service_managers: dict[str, "IServiceManager"] = {}

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
            StepCompletedEvent: self._handle_step_completed,
            EnvironmentSetupStartedEvent: self._handle_environment_setup_started,
            EnvironmentSetupCompletedEvent: self._handle_environment_setup_completed,
            EnvironmentTeardownEvent: self._handle_environment_teardown,
            ServiceEvent: self._handle_service_event,
            ServiceStartedEvent: self._handle_service_started,
            ServiceStoppedEvent: self._handle_service_stopped,
            TestExecutionStartedEvent: self._handle_test_execution_started,
            TestCompletedEvent: self._handle_test_completed,
            TestExecutionCompletedEvent: self._handle_test_execution_completed,
            MetricCollectedEvent: self._handle_metric_collected,
        }

    def on_event(self, event: Event) -> bool:
        """
        Handles an experiment-related event with enhanced tracking.

        Uses type-based dispatch to specialized handler methods.

        Args:
            event: The event to handle

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

            # Tear down any active environments
            for env_name, env_plugin in self.environment_plugins.items():
                env_plugin.teardown_environment()

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
        progress = event.data.get("progress")
        details = event.data.get("details") or {}

        # Track step progress
        if self.track_steps and step_id:
            if step_id not in self.step_progress:
                self.step_progress[step_id] = []
            self.step_progress[step_id].append(progress)

        # Log progress
        self.logger.debug(
            "Step progress: %s at %s",
            step_id,
            progress if isinstance(progress, (int, float)) else "",
        )

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

        # Monitor active environments if available
        for env_name, env_plugin in self.environment_plugins.items():
            if hasattr(env_plugin, "monitor_environment"):
                try:
                    env_plugin.monitor_environment()
                    self.logger.debug(f"  Environment monitoring triggered for {env_name}")
                except Exception as e:
                    self.logger.warning(f"  Failed to monitor environment {env_name}: {e}")

        return True

    def _handle_step_completed(self, event: StepCompletedEvent) -> bool:
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
        """Handle environment setup start events."""
        self.current_phase = "environment_setup"
        env_type = event.data.get("type")
        details = event.data.get("details") or {}

        self.logger.info("Environment setup started: %s", env_type)

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_environment_setup_completed(self, event: EnvironmentSetupCompletedEvent) -> bool:
        """Handle environment setup completion events."""
        self.current_phase = "environment_ready"
        env_type = event.data.get("environment_type")
        success = event.data.get("success", False)
        details = event.data.get("details") or {}

        # Extract and store the environment instance if available
        if "environment_instance" in details:
            env_instance = details["environment_instance"]
            if env_instance:
                env_name = details.get("environment_name", env_type)
                self.environment_plugins[env_name] = env_instance
                self.logger.info(f"Stored environment '{env_name}' instance for monitoring")

        self.logger.info(
            "Environment setup completed: %s - %s", env_type, "Success" if success else "Failed"
        )

        # Record timing information if tracking is enabled
        if self.track_timing:
            self._record_timing_info("environment_setup", self.start_time)

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                if key != "environment_instance":  # Don't log the instance object
                    self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_environment_teardown(self, event: EnvironmentTeardownEvent) -> bool:
        """Handle environment teardown events."""
        self.current_phase = "environment_teardown"
        env_type = event.data.get("type")
        success = event.data.get("success", False)
        details = event.data.get("details") or {}

        self.logger.info(
            "Environment teardown: %s - %s", env_type, "Success" if success else "Failed"
        )

        # Find and remove the environment from our tracking
        env_name = details.get("environment_name", env_type)
        if env_name in self.environment_plugins:
            del self.environment_plugins[env_name]
            self.logger.debug(f"Removed environment '{env_name}' from tracking")

        # Record timing information
        if self.track_timing:
            self._record_timing_info("environment_teardown", self.start_time)

        # Log details with consistent indentation
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")

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

            # Store service instances if available
            if "service_instances" in data:
                service_instances = data["service_instances"]
                if isinstance(service_instances, dict):
                    for name, instance in service_instances.items():
                        if instance:
                            self.service_managers[name] = instance
                            self.logger.debug(f"Stored service '{name}' instance for monitoring")

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
        service_name = event.service_name
        service_type = event.service_type
        details = event.details or {}

        self.logger.info("Service started: %s (%s)", service_name, service_type)

        # Store service instance if available
        if "service_instance" in details:
            service_instance = details["service_instance"]
            if service_instance:
                self.service_managers[service_name] = service_instance
                self.logger.debug(f"Stored service '{service_name}' instance for monitoring")

        # Log details with consistent indentation
        for key, value in details.items():
            if key != "service_instance":  # Don't log instance object
                self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_service_stopped(self, event: ServiceStoppedEvent) -> bool:
        """Handle service stopped events."""
        service_name = event.service_name
        success = event.success
        details = event.details or {}

        self.logger.info(
            "Service stopped: %s - %s",
            service_name,
            "Clean shutdown" if success else "Forced shutdown",
        )

        # Remove service from tracking
        if service_name in self.service_managers:
            del self.service_managers[service_name]
            self.logger.debug(f"Removed service '{service_name}' from tracking")

        # Log details with consistent indentation
        for key, value in details.items():
            self.logger.debug(f"  {key}: {value}")

        return True

    def _handle_test_execution_started(self, event: "TestExecutionStartedEvent") -> bool:
        """Handle test execution started events."""
        self.current_phase = "test_execution_started"
        test_id = event.data.get("test_id")
        test_name = event.data.get("test_name")
        start_time = event.data.get("start_time")

        self.logger.info("Test execution started: %s", test_name)

        if self.track_timing:
            self.start_time = datetime.now()
            self._record_timing_info("test_execution_started", self.start_time)

        return True

    def _handle_test_completed(self, event: "TestCompletedEvent") -> bool:
        """Handle test completed events."""
        self.current_phase = "test_completed"
        test_name = event.data.get("test_name")
        success = event.data.get("success", False)
        result = event.data.get("result") or {}

        self.logger.info("Test completed: %s - %s", test_name, "Success" if success else "Failed")

        if self.track_timing:
            self._record_timing_info("test_completed", self.start_time)

        return True

    def _handle_test_execution_completed(self, event: "TestExecutionCompletedEvent") -> bool:
        """Handle test execution completed events."""
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
            duration_ms,
        )

        if self.track_timing:
            self._record_timing_info("test_execution_completed", self.start_time)

        return True

    def _handle_metric_collected(self, event: "MetricCollectedEvent") -> bool:
        """Handle metric collected events."""
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
            "environments": list(self.environment_plugins.keys()),
            "services": list(self.service_managers.keys()),
            "events_received": self.events_received,
            "experiment_finished_early": self.experiment_finished_early,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
            "step_progress": self.step_progress,
        }

    def get_active_environment(self, name: str = None) -> IEnvironmentPlugin | None:
        """
        Get an active environment instance by name.

        Args:
            name: Name of the environment to retrieve, or None for any environment

        Returns:
            IEnvironmentPlugin instance or None if not found
        """
        if name:
            return self.environment_plugins.get(name)
        elif self.environment_plugins:
            # Return any environment if name not specified
            return next(iter(self.environment_plugins.values()))
        return None

    def get_active_service(self, name: str = None) -> Optional["IServiceManager"]:
        """
        Get an active service instance by name.

        Args:
            name: Name of the service to retrieve, or None for any service

        Returns:
            IServiceManager instance or None if not found
        """
        if name:
            return self.service_managers.get(name)
        elif self.service_managers:
            # Return any service if name not specified
            return next(iter(self.service_managers.values()))
        return None

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
