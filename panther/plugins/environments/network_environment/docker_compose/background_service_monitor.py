"""Background service health monitor for Docker Compose deployments."""

import threading
import time
from typing import Any, Dict

from ..base_environment_monitor import BaseEnvironmentMonitor, ServiceHealthState


class BackgroundServiceMonitor(BaseEnvironmentMonitor):
    """Background service health monitor for non-blocking Docker Compose deployments.

    Continuously monitors service health in a background daemon thread and triggers
    early experiment termination when services fail beyond configured thresholds.
    """

    def __init__(self, docker_compose_env, services, config):
        """Initialize the background service monitor for Docker Compose."""
        # Initialize base monitor
        super().__init__(docker_compose_env, config, docker_compose_env.logger)

        # Docker Compose specific attributes
        self.docker_compose_env = docker_compose_env
        self.services = services  # list of service names
        # Service state tracking (specific to multi-service monitoring)
        self.service_states = {
            service: ServiceHealthState.STARTING for service in services
        }
        self.failure_counts = {service: 0 for service in services}

        # Circuit breaker for Docker daemon health
        self.docker_failure_count = 0
        self.docker_circuit_open = False
        self.docker_circuit_opened_at = None
        self.docker_circuit_timeout = 30.0  # 30 seconds before retry

        # Watchdog timer for deadlock detection
        self.last_health_check = time.time()
        self.health_check_timeout = 60.0  # 60 seconds max for health check

    def _check_health(self):
        """Check health of all Docker Compose services and handle failures."""
        start_time = time.time()
        self.logger.debug("Checking health of Docker Compose services")

        # Update watchdog timer
        self.last_health_check = start_time

        # Check circuit breaker state
        if self._is_docker_circuit_open():
            self.logger.debug("Docker circuit breaker is open, skipping health checks")
            return

        # Watchdog timer check - detect if previous health check is still running
        if hasattr(self, "_health_check_running") and self._health_check_running:
            self.logger.error(
                "Previous health check still running - potential deadlock detected!"
            )
            return

        try:
            self._health_check_running = True

            # Collect service health status outside of lock to minimize critical section
            service_health_status = {}
            for service_name in self.services:
                self.logger.debug(f"Checking health of service: {service_name}")
                try:
                    # Add timeout protection to service readiness check
                    is_healthy = self._is_service_ready_with_timeout(
                        service_name, timeout=10.0
                    )
                    service_health_status[service_name] = is_healthy
                    self._reset_docker_circuit()  # Reset circuit breaker on success
                except Exception as e:
                    self.logger.warning(f"Error checking service {service_name}: {e}")
                    service_health_status[service_name] = False
                    self._handle_docker_failure(e)
        finally:
            self._health_check_running = False

        # Update state in critical section with minimal lock time
        try:
            if not self.lock.acquire(timeout=5.0):
                self.logger.warning(
                    "Could not acquire lock for health check, skipping this cycle"
                )
                return

            for service_name, is_healthy in service_health_status.items():
                current_state = self.service_states[service_name]
                self.logger.debug(
                    f"Service {service_name} is healthy: {is_healthy} and current state: {current_state}"
                )
                if is_healthy:
                    if current_state != ServiceHealthState.READY:
                        self.service_states[service_name] = ServiceHealthState.READY
                        self.failure_counts[service_name] = 0  # Reset failure count
                        self.logger.info(f"✓ Service {service_name} is now ready")
                else:
                    self._handle_service_failure(service_name, current_state)
        finally:
            self.lock.release()

        # Log health check duration for deadlock diagnosis
        duration = time.time() - start_time
        if duration > 5.0:
            self.logger.warning(
                f"Health check took {duration:.2f}s (longer than expected)"
            )
        else:
            self.logger.debug(f"Health check completed in {duration:.2f}s")

    def _is_service_ready_with_timeout(
        self, service_name: str, timeout: float = 10.0
    ) -> bool:
        """Check if a specific service is ready with timeout protection."""
        start_time = time.time()

        try:
            # First try the service name directly (for modern Docker Compose with container_name)
            result = self.docker_compose_env.execute_docker_command(
                docker_args=["ps", "-q", "-f", f"name=^{service_name}$"],
                check=False,
                timeout=timeout,  # Add timeout to Docker command
            )

            self.logger.debug(
                f"Checking if service '{service_name}' is ready: {result.stdout.strip()}"
            )

            if result.stdout.strip():
                return True

            # Check if we have time for fallback check
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self.logger.warning(
                    f"Service check for {service_name} timed out after {elapsed:.2f}s"
                )
                return False

            # Fallback to legacy naming convention for backward compatibility
            container_name = f"{self.docker_compose_env.network_name}_{service_name}_1"
            remaining_timeout = timeout - elapsed
            result = self.docker_compose_env.execute_docker_command(
                docker_args=["ps", "-q", "-f", f"name={container_name}"],
                check=False,
                timeout=remaining_timeout,
            )
            return bool(result.stdout.strip())

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.warning(
                f"Service readiness check for {service_name} failed after {elapsed:.2f}s: {e}"
            )
            return False

    def _is_service_ready(self, service_name: str) -> bool:
        """Check if a specific service is ready (backward compatibility wrapper)."""
        return self._is_service_ready_with_timeout(service_name, timeout=5.0)

    def _handle_service_failure(self, service_name, current_state):
        """Handle individual service failure using base class logic."""
        self.failure_counts[service_name] += 1
        failure_count = self.failure_counts[service_name]

        if failure_count >= self.config.failure_threshold_count:
            # Service has failed beyond threshold
            self.service_states[service_name] = ServiceHealthState.FAILED
            # Use base class failure handling
            self._handle_failure(
                f"Service '{service_name}' failed {failure_count} times"
            )
        else:
            # Service is failing but hasn't exceeded threshold yet
            self.service_states[service_name] = ServiceHealthState.FAILING
            self.logger.warning(
                f"⚠ Service {service_name} failing (failures: {failure_count}/{self.config.failure_threshold_count})"
            )

    def _get_monitor_name(self) -> str:
        """Get unique monitor name for Docker Compose environment."""
        return f"DockerCompose-{self.docker_compose_env.env_name}"

    def _should_terminate(self) -> bool:
        """Docker Compose specific termination conditions."""
        if (
            not hasattr(self.config, "allow_partial_deployment")
            or not self.config.allow_partial_deployment
        ):
            return True  # Any service failure should terminate

        # Check for critical service failures
        if hasattr(self.config, "critical_services"):
            for service_name, state in self.service_states.items():
                if (
                    state == ServiceHealthState.FAILED
                    and service_name in self.config.critical_services
                ):
                    return True

        # Check if too many services have failed
        failed_services = [
            s
            for s, state in self.service_states.items()
            if state == ServiceHealthState.FAILED
        ]
        return len(failed_services) > len(self.services) // 2  # More than half failed

    def _get_termination_details(self) -> Dict[str, Any]:
        """Get Docker Compose specific termination details."""
        failed_services = [
            s
            for s, state in self.service_states.items()
            if state == ServiceHealthState.FAILED
        ]

        return {
            "monitor_type": "docker_compose",
            "services": self.services,
            "failed_services": failed_services,
            "service_states": {
                s: state.value for s, state in self.service_states.items()
            },
            "service_failure_counts": self.failure_counts,
            "config": {
                "critical_services": getattr(self.config, "critical_services", []),
                "allow_partial_deployment": getattr(
                    self.config, "allow_partial_deployment", False
                ),
            },
        }

    def _is_docker_circuit_open(self) -> bool:
        """Check if Docker circuit breaker is currently open."""
        if not self.docker_circuit_open:
            return False

        # Check if circuit should be reset
        if (
            self.docker_circuit_opened_at
            and (time.time() - self.docker_circuit_opened_at)
            > self.docker_circuit_timeout
        ):
            self.logger.info(
                "Docker circuit breaker timeout expired, attempting to reset"
            )
            self.docker_circuit_open = False
            self.docker_circuit_opened_at = None
            return False

        return True

    def _handle_docker_failure(self, exception: Exception):
        """Handle Docker daemon failure and manage circuit breaker."""
        self.docker_failure_count += 1
        self.logger.warning(
            f"Docker operation failed (count: {self.docker_failure_count}): {exception}"
        )

        # Open circuit breaker after 3 consecutive failures
        if self.docker_failure_count >= 3 and not self.docker_circuit_open:
            self.docker_circuit_open = True
            self.docker_circuit_opened_at = time.time()
            self.logger.error("Docker circuit breaker opened due to repeated failures")

    def _reset_docker_circuit(self):
        """Reset Docker circuit breaker on successful operation."""
        if self.docker_failure_count > 0:
            self.docker_failure_count = 0
            if self.docker_circuit_open:
                self.docker_circuit_open = False
                self.docker_circuit_opened_at = None
                self.logger.info(
                    "Docker circuit breaker reset after successful operation"
                )
