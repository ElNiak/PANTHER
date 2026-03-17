"""Observer that tracks experiment lifecycle events and manages state."""

import logging
import sys
import threading
from datetime import datetime
from typing import Any, Dict, Optional, Set

import click

from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.events.experiment.events import (
    ExperimentFinishedEarlyEvent,
    ExperimentServiceFailureEvent,
)
from panther.core.observer.base.typed_observer_interface import ITypedObserver


class ExperimentObserver(ITypedObserver):
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
        """Initialize the experiment observer with optional configuration."""
        super().__init__()

        # Track what we've observed for logging purposes only
        self.observed_environments: Set[str] = set()
        self.observed_services: Set[str] = set()

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

    def on_event(self, event: BaseEvent) -> bool:
        """Thin wrapper adding event counting and already_logged check."""
        with self._state_lock:
            self.events_received += 1

        event_data = getattr(event, "data", {})
        if event_data.get("already_logged", False):
            return True

        return super().on_event(event)

    def on_unknown_event(self, event: BaseEvent) -> bool:
        """Fallback for unmatched service events."""
        if event.entity_type == EventType.SERVICE:
            return self._handle_service_event(event)
        self.logger.debug("Unhandled event type: %s", event.__class__.__name__)
        return True

    # -- Experiment events (dispatched via _type_handlers for typed subclasses) --

    def on_experiment_finished_early(self, event: ExperimentFinishedEarlyEvent) -> bool:
        """Handle early experiment termination events."""
        action = event.data.get("action", "notify")

        if action == "notify":
            with self._state_lock:
                self.current_phase = "finished_early"
                self.experiment_finished_early = True
            self.logger.info("Experiment finished early")

            reason = event.data.get("reason", "No reason provided")
            self.logger.debug("Early termination reason: %s", reason)

            if self.track_timing:
                self._record_timing_info("early_termination", self.start_time)

        elif action == "check":
            self.logger.debug(
                "Checking if experiment finished early: %s",
                self.experiment_finished_early,
            )

        return self.experiment_finished_early

    def on_experiment_service_failure(
        self, event: ExperimentServiceFailureEvent
    ) -> bool:
        """Handle experiment service failure events."""
        failed_service = event.failed_service
        reason = event.reason
        details = event.data.get("details", {})

        self.logger.error("Service failure detected: %s - %s", failed_service, reason)

        with self._state_lock:
            self._should_terminate_early = True
            self._termination_reason = f"Service failure: {reason}"
            self.experiment_finished_early = True

        if details:
            for key, value in details.items():
                self.logger.debug("  %s: %s", key, value)

        return True

    # -- Step events --

    def on_step_progress(self, event: BaseEvent) -> bool:
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
                pbar_key = f"{test_case_id or 'unknown'}_{step_name}_{step_id}"

                if pbar_key not in self._step_progress_bars:
                    self.logger.info(
                        "Started progress tracking for %s in %s",
                        step_name,
                        test_case_id or "unknown test",
                    )
                    self._step_progress_bars[pbar_key] = {
                        "current_progress": 0,
                        "step_name": step_name,
                        "test_case_id": test_case_id or "unknown test",
                        "last_message": "",
                    }

                step_state = self._step_progress_bars[pbar_key]

                new_progress = min(int(progress_percentage), 100)
                if new_progress > step_state["current_progress"]:
                    step_state["current_progress"] = new_progress

                    # click.echo intentional: \r carriage-return for in-place terminal updates
                    bar_width = 30
                    filled = int(bar_width * new_progress / 100)
                    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
                    line = f"\r  [{bar}] {new_progress}% - {progress_message}"
                    click.echo(line, nl=False, file=sys.stderr)

                    if progress_message:
                        step_state["last_message"] = progress_message

                if progress_percentage >= 100.0:
                    # click.echo intentional: finalize in-place progress bar with newline
                    click.echo("", file=sys.stderr)
                    self.logger.info(
                        "%s completed in %s", step_name, test_case_id or "unknown test"
                    )
            except Exception as e:
                self.logger.debug("Progress bar error: %s", e)
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

        if details:
            for key, value in details.items():
                self.logger.debug("  %s: %s", key, value)

        return True

    def on_step_execution_completed(self, event: BaseEvent) -> bool:
        """Handle step completion events."""
        step_id = event.data.get("step_id")
        success = event.data.get("success", False)
        result = event.data.get("result") or {}

        self.logger.info(
            "Step completed: %s - %s", step_id, "Success" if success else "Failed"
        )

        if result:
            for key, value in result.items():
                self.logger.debug("  %s: %s", key, value)

        return True

    # -- Environment events --

    def on_environment_created(self, event: BaseEvent) -> bool:
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
        self.observed_environments.add(environment_name)

        if self.track_timing:
            self._record_timing_info("environment_created", event.timestamp)

        return True

    def on_environment_setup_started(self, event: BaseEvent) -> bool:
        """Handle environment setup started events."""
        self.current_phase = "environment_setup"

        self.logger.debug("EnvironmentSetupStartedEvent data: %s", event.data)
        self.logger.debug(
            "EnvironmentSetupStartedEvent environment_type attribute: %s",
            getattr(event, "environment_type", "not found"),
        )

        environment_type = getattr(
            event, "environment_type", event.data.get("environment_type", "unknown")
        )
        environment_name = getattr(
            event, "environment_name", event.data.get("environment_instance", "unknown")
        )

        setup_config = event.data.get("setup_config", {})
        test_case = setup_config.get(
            "test_case", event.data.get("test_case", "unknown_test")
        )

        self.observed_environments.add(environment_name)

        self.logger.info(
            "Environment setup started for %s environment in test '%s'",
            environment_type,
            test_case,
        )

        if self.track_timing:
            self._record_timing_info("environment_setup_start", event.timestamp)

        return True

    def on_environment_setup_completed(self, event: BaseEvent) -> bool:
        """Handle environment setup completed events."""
        success = event.data.get("success", True)

        details = event.data.get("details", {})
        resources_allocated = event.data.get("resources_allocated", {})
        combined_details = {**details, **resources_allocated}

        environment_type = (
            event.environment_type
            if hasattr(event, "environment_type")
            else combined_details.get("environment_type", "unknown")
        )
        test_case = combined_details.get("test_case", "unknown_test")

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

    def on_environment_deployment_started(self, event: BaseEvent) -> bool:
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
        self.observed_environments.add(environment_name)

        if self.track_timing:
            self._record_timing_info("environment_deployment_started", event.timestamp)

        return True

    def on_environment_teardown_started(self, event: BaseEvent) -> bool:
        """Handle environment teardown events."""
        self.current_phase = "environment_teardown"
        env_type = event.data.get("type")
        details = event.data.get("details") or {}

        env_name = details.get("environment_name", env_type)
        self.logger.info("Environment teardown started: %s", env_name)

        if self.track_timing:
            self._record_timing_info("environment_teardown", self.start_time)

        if details:
            for key, value in details.items():
                self.logger.debug("  %s: %s", key, value)

        return True

    def on_environment_error(self, event: BaseEvent) -> bool:
        """Handle environment error events."""
        error_message = event.data.get("error_message", "Unknown error")
        error_type = event.data.get("error_type", "unknown")

        self.logger.error("Environment error: %s (type: %s)", error_message, error_type)

        with self._state_lock:
            self._should_terminate_early = True
            self._termination_reason = error_message
            self.experiment_finished_early = True
        self.logger.warning(
            "Environment requested early termination: %s", error_message
        )

        return True

    def on_environment_destroyed(self, event: BaseEvent) -> bool:
        """Handle environment destroyed events."""
        environment_type = getattr(event, "environment_type", "unknown")
        environment_name = getattr(event, "environment_name", "unknown")

        self.logger.info(
            "Environment destroyed: %s (%s)", environment_name, environment_type
        )

        if self.track_timing:
            self._record_timing_info("environment_destroyed", event.timestamp)

        return True

    # -- Service events --

    def on_service_started(self, event: BaseEvent) -> bool:
        """Handle service started events."""
        service_name = event.data.get("service_name")
        pid = event.data.get("pid")
        start_time = event.data.get("start_time")

        self.logger.info(
            "Service started: %s (PID: %s)",
            service_name,
            pid if pid is not None else "N/A",
        )

        if start_time:
            self.logger.debug("  Start time: %s", start_time)

        self.observed_services.add(service_name)
        return True

    def on_service_stopped(self, event: BaseEvent) -> bool:
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

        is_unexpected = (exit_code is not None and exit_code != 0) or reason in (
            "unexpected",
            "crashed",
            "killed",
        )
        if is_unexpected:
            with self._state_lock:
                self._should_terminate_early = True
                self.experiment_finished_early = True

        self.logger.debug("Observed service '%s' stop", service_name)

        uptime = event.data.get("uptime_seconds")
        if uptime is not None:
            self.logger.debug("  Service uptime: %.2f seconds", uptime)

        return True

    def on_service_deployment_failed(self, event: BaseEvent) -> bool:
        """Handle service deployment failure events."""
        data = event.data or {}
        environment = data.get("environment", "unknown")
        service_name = data.get("service_name", "unknown service")
        error = data.get("error", "Unknown error")
        error_type = data.get("error_type", "Unknown error type")

        self.current_phase = "service_deployment_failed"

        self.logger.error(
            "Service deployment failed in environment %s: %s - %s (%s)",
            environment,
            service_name,
            error,
            error_type,
        )

        for key, value in data.items():
            if key not in ["environment", "service_name", "error", "error_type"]:
                self.logger.debug("  %s: %s", key, value)

        return True

    def on_service_destroyed(self, event: BaseEvent) -> bool:
        """Handle service destroyed events."""
        service_name = event.data.get("service_name", "unknown")
        self.logger.info("Service destroyed: %s", service_name)

        if self.track_timing:
            self._record_timing_info("service_destroyed", event.timestamp)

        return True

    def on_service_preparation_started(self, event: BaseEvent) -> bool:
        """Handle service setup started events."""
        service_name = event.data.get("service_name") or "unknown_service"
        preparation_steps = event.data.get("preparation_steps", [])

        test_case = event.data.get("test_case") or "unknown_test"
        if test_case == "unknown_test":
            service_id = getattr(event, "service_id", "")
            if "_" in service_id:
                parts = service_id.split("_", 1)
                if len(parts) > 1:
                    test_case = parts[0]

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

    def on_service_preparation_completed(self, event: BaseEvent) -> bool:
        """Handle service setup completed events."""
        service_name = event.data.get("service_name") or "unknown_service"
        duration = event.data.get("duration_seconds")

        service_id = getattr(event, "service_id", "")
        test_case = "unknown_test"
        if "_" in service_id:
            parts = service_id.split("_", 1)
            if len(parts) > 1:
                test_case = parts[0]

        self.logger.info(
            "Service preparation completed for '%s' in test '%s'%s",
            service_name,
            self.name if self.test_name else test_case,
            f" (duration: {duration:.2f}s)" if duration else "",
        )

        if self.track_timing:
            self._record_timing_info("service_setup_end", event.timestamp)

        return True

    # -- Test events --

    def on_test_execution_started(self, event: BaseEvent) -> bool:
        """Handle test execution started events."""
        self.current_phase = "test_execution_started"
        test_name = event.data.get("test_name")

        self.logger.info("Test execution started: %s", test_name)

        if self.track_timing:
            self.start_time = datetime.now()
            self._record_timing_info("test_execution_started", self.start_time)

        return True

    def on_test_execution_failed(self, event: BaseEvent) -> bool:
        """Handle test execution failed events."""
        self.current_phase = "test_execution_failed"
        test_name = event.data.get("test_name", "unknown test")
        error_message = event.data.get("error_message", "Unknown error")
        stack_trace = event.data.get("stack_trace")
        error_details = event.data.get("error_details", {})

        self.logger.error("Test execution failed: %s - %s", test_name, error_message)

        if stack_trace:
            for line in stack_trace.splitlines():
                self.logger.debug("  %s", line)

        if error_details:
            for key, value in error_details.items():
                self.logger.debug("  %s: %s", key, value)

        if self.track_timing:
            self._record_timing_info("test_execution_failed", self.start_time)

        return True

    def on_test_completed(self, event: BaseEvent) -> bool:
        """Handle test completed events."""
        self.current_phase = "test_completed"
        test_name = event.data.get("test_name")
        success = event.data.get("success", True)
        result = event.data.get("result") or {}

        self.logger.info(
            "Test completed: %s - %s", test_name, "Success" if success else "Failed"
        )

        self._cleanup_step_progress_bars(test_name)

        if self.track_timing:
            self._record_timing_info("test_completed", self.start_time)

        if result:
            for key, value in result.items():
                self.logger.debug("  %s: %s", key, value)

        return True

    def on_test_failed(self, event: BaseEvent) -> bool:
        """Handle test failed events."""
        self.current_phase = "test_failed"
        test_name = event.data.get("test_name")
        error_message = event.data.get("error_message", "Unknown error")

        self.logger.error("Test failed: %s - %s", test_name, error_message)

        self._cleanup_step_progress_bars(test_name)

        if self.track_timing:
            self._record_timing_info("test_failed", self.start_time)

        return True

    def on_test_execution_completed(self, event: BaseEvent) -> bool:
        """Handle test execution completed events."""
        self.current_phase = "test_execution_completed"
        test_name = event.data.get("test_name")
        success = event.data.get("success", True)
        results = event.data.get("results") or {}
        duration_ms = event.data.get("duration_ms")

        self.logger.info(
            "Test execution completed: %s - %s (Duration: %s ms)",
            test_name,
            "Success" if success else "Failed",
            duration_ms if duration_ms is not None else "unknown",
        )

        self._cleanup_step_progress_bars(test_name)

        if results:
            for key, value in results.items():
                self.logger.debug("  %s: %s", key, value)

        if self.track_timing:
            self._record_timing_info("test_execution_completed", self.start_time)

        return True

    # -- Metrics events (dispatched via _type_handlers for MetricCollectedEvent) --

    def on_metric_collected(self, event: BaseEvent) -> bool:
        """Handle metric collected events."""
        metric_name = event.data.get("metric_name")
        metric_type = event.data.get("metric_type")
        value = event.data.get("value")

        self.logger.debug(
            "Metric collected: %s (%s) = %s", metric_name, metric_type, value
        )

        return True

    # -- Internal helpers --

    def _handle_service_event(self, event: BaseEvent) -> bool:
        """Handle generic/unmatched service events."""
        event_name = event.name
        data = event.data or {}

        if event_name in ("service.setup", "services_setup"):
            self.current_phase = "services_setup"
            service_name = data.get("service_name", "unknown")
            self.logger.info("Service setup started: %s", service_name)

        elif event_name in ("service.deployed", "services_deployed"):
            self.current_phase = "services_deployed"
            services = data.get("services", [data.get("service_name", "unknown")])

            if isinstance(services, str):
                services = [services]

            self.logger.info(
                "Services deployed: %s", ", ".join(services) if services else "None"
            )

            if "service_instances" in data:
                service_instances = data["service_instances"]
                if isinstance(service_instances, dict):
                    for name in service_instances.keys():
                        self.observed_services.add(name)
                        self.logger.debug("Observed service '%s' deployment", name)

            if self.track_timing:
                self._record_timing_info("services_deployed", self.start_time)

        elif event_name in ("service.teardown", "service_teardown"):
            self.current_phase = "services_teardown"
            self.logger.info("Service teardown in progress")

            if self.track_timing:
                self._record_timing_info("services_teardown", self.start_time)

        for key, value in data.items():
            if key not in ["service_instances", "services"]:
                self.logger.debug("  %s: %s", key, value)

        return True

    def _cleanup_step_progress_bars(self, test_name: str = None) -> None:
        """Clean up step progress bars for a specific test or all tests."""
        if not hasattr(self, "_step_progress_bars"):
            return

        try:
            keys_to_remove = []

            for pbar_key, step_state in list(self._step_progress_bars.items()):
                if test_name and not pbar_key.startswith(test_name.replace(" ", "_")):
                    continue

                try:
                    if (
                        isinstance(step_state, dict)
                        and step_state.get("current_progress", 0) < 100
                    ):
                        step_name = step_state.get("step_name", "Unknown Step")
                        test_case_id = step_state.get("test_case_id", "unknown test")
                        self.logger.info("%s completed in %s", step_name, test_case_id)

                    keys_to_remove.append(pbar_key)

                    if test_name:
                        self.logger.info(
                            "Cleaned up progress tracking for %s", test_name
                        )

                except Exception as e:
                    self.logger.debug(
                        "Error cleaning up progress tracking %s: %s", pbar_key, e
                    )

            for key in keys_to_remove:
                del self._step_progress_bars[key]

        except Exception as e:
            self.logger.debug("Error during progress tracking cleanup: %s", e)

    def _record_timing_info(
        self, checkpoint_name: str, reference_time: datetime
    ) -> None:
        """Record timing information for experiment metrics."""
        duration = (datetime.now() - reference_time).total_seconds()
        self.logger.debug(
            "Checkpoint '%s' reached after %.2f seconds", checkpoint_name, duration
        )

    def get_experiment_status(self) -> Dict[str, Any]:
        """Get a summary of the current experiment status (thread-safe)."""
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

    def get_priority(self) -> int:
        """Get the priority for this observer."""
        return 50

    def should_terminate_early(self) -> bool:
        """Check if the experiment should terminate early (thread-safe)."""
        with self._state_lock:
            return self._should_terminate_early or self.experiment_finished_early

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in an event type."""
        return True
