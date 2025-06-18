import threading
import time
from enum import Enum


class ServiceHealthState(Enum):
    """State management for individual service health monitoring"""

    STARTING = "starting"
    READY = "ready"
    FAILING = "failing"
    FAILED = "failed"
    STOPPED = "stopped"


class BackgroundServiceMonitor:
    """
    Background service health monitor for non-blocking Docker Compose deployments.

    Continuously monitors service health in a background daemon thread and triggers
    early experiment termination when services fail beyond configured thresholds.
    """

    def __init__(self, docker_compose_env, services, config):
        self.docker_compose_env = docker_compose_env
        self.services = services  # list of service names
        self.config = config
        self.logger = docker_compose_env.logger

        # Service state tracking
        self.service_states = {
            service: ServiceHealthState.STARTING for service in services
        }
        self.failure_counts = {service: 0 for service in services}

        # Thread management
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def start_monitoring(self):
        """Start background monitoring in a daemon thread"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"ServiceMonitor-{self.docker_compose_env.env_name}",
            daemon=True,
        )
        self.monitor_thread.start()
        self.logger.info(
            f"Started background service monitoring thread: {self.monitor_thread.name}"
        )

    def stop_monitoring(self):
        """Stop background monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.stop_event.set()  # Signal the thread to stop

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.info("Stopping background service monitoring...")
            self.monitor_thread.join(timeout=10)  # Increased timeout
            if self.monitor_thread.is_alive():
                self.logger.warning("Background monitoring thread did not stop cleanly")
        self.monitor_thread = None

    def _monitor_loop(self):
        """Main monitoring loop running in background thread"""
        self.logger.debug(
            f"Background monitoring loop started for services: {self.services}"
        )

        while self.monitoring_active and not self.stop_event.is_set():
            try:
                self._check_all_services()
                # Use interruptible sleep instead of blocking sleep
                if self.stop_event.wait(
                    timeout=self.config.monitoring_interval_seconds
                ):
                    break  # Stop event was set
            except Exception as e:
                self.logger.error(f"Error in background monitoring: {e}")
                if self.stop_event.wait(
                    timeout=self.config.monitoring_interval_seconds
                ):
                    break

        self.logger.debug("Background monitoring loop ended")

    def _check_all_services(self):
        """Check health of all services and handle failures"""
        with self.lock:
            for service_name in self.services:
                current_state = self.service_states[service_name]
                is_healthy = self.docker_compose_env._is_service_ready(service_name)

                if is_healthy:
                    if current_state != ServiceHealthState.READY:
                        self.service_states[service_name] = ServiceHealthState.READY
                        self.failure_counts[service_name] = 0  # Reset failure count
                        self.logger.info(f"✓ Service {service_name} is now ready")
                else:
                    self._handle_service_failure(service_name, current_state)

    def _handle_service_failure(self, service_name, current_state):
        """Handle service failure and potentially trigger early termination"""
        self.failure_counts[service_name] += 1
        failure_count = self.failure_counts[service_name]

        if failure_count >= self.config.failure_threshold_count:
            # Service has failed beyond threshold
            self.service_states[service_name] = ServiceHealthState.FAILED
            self.logger.error(
                f"✗ Service {service_name} failed (failures: {failure_count})"
            )

            # Check if this should trigger early termination
            if self._should_terminate_experiment(service_name):
                self._trigger_early_termination(service_name, failure_count)
        else:
            # Service is failing but hasn't exceeded threshold yet
            self.service_states[service_name] = ServiceHealthState.FAILING
            self.logger.warning(
                f"⚠ Service {service_name} failing (failures: {failure_count}/{self.config.failure_threshold_count})"
            )

    def _should_terminate_experiment(self, failed_service):
        """Determine if experiment should terminate early"""
        if not self.config.allow_partial_deployment:
            return True  # Any service failure should terminate

        if failed_service in self.config.critical_services:
            return True  # Critical service failure should terminate

        # Check if too many services have failed
        failed_services = [
            s
            for s, state in self.service_states.items()
            if state == ServiceHealthState.FAILED
        ]
        return len(failed_services) > len(self.services) // 2  # More than half failed

    def _trigger_early_termination(self, failed_service, failure_count):
        """Trigger early experiment termination"""
        reason = f"Service '{failed_service}' failed {failure_count} times (threshold: {self.config.failure_threshold_count})"

        failed_services = [
            s
            for s, state in self.service_states.items()
            if state == ServiceHealthState.FAILED
        ]

        details = {
            "failed_service": failed_service,
            "failure_count": failure_count,
            "all_failed_services": failed_services,
            "service_states": {
                s: state.value for s, state in self.service_states.items()
            },
            "monitoring_config": {
                "failure_threshold": self.config.failure_threshold_count,
                "critical_services": self.config.critical_services,
                "allow_partial_deployment": self.config.allow_partial_deployment,
            },
        }

        self.logger.error(f"Triggering early experiment termination: {reason}")

        # Set termination flag on environment
        self.docker_compose_env.request_early_termination(reason, details)

        # Stop monitoring since experiment is terminating
        self.monitoring_active = False
