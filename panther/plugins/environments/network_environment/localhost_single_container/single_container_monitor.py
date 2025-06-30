from typing import Any, Dict

from ..base_environment_monitor import BaseEnvironmentMonitor, ServiceHealthState

# Use ServiceHealthState directly, no need for separate enum


class SingleContainerMonitor(BaseEnvironmentMonitor):
    """
    Background container health monitor for non-blocking localhost deployments.

    Monitors the single container health and triggers early experiment termination
    when the container fails or exits unexpectedly.
    """

    def __init__(self, localhost_env, container_name, config):
        # Initialize base monitor
        super().__init__(localhost_env, config, localhost_env.logger)

        # Localhost specific attributes
        self.localhost_env = localhost_env
        self.container_name = container_name

        # Container state tracking (specific to single container monitoring)
        self.container_state = ServiceHealthState.STARTING
        self.last_check_time = None

    def _check_health(self):
        """Check health of the container and handle failures (Localhost specific)."""
        with self.lock:
            is_healthy = self._is_container_healthy()

            if is_healthy:
                if self.container_state != ServiceHealthState.READY:
                    self.container_state = ServiceHealthState.READY
                    self.failure_count = 0
                    self.logger.info(f"✓ Container {self.container_name} is healthy")
            else:
                self._handle_container_failure()

    def _is_container_healthy(self):
        """Check if container is running and healthy"""
        # Check if container is running
        result = self.localhost_env.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name=^{self.container_name}$"],
            check=False,
        )

        if not result.stdout.strip():
            # Container not running, check exit status
            exit_result = self.localhost_env.execute_docker_command(
                docker_args=[
                    "ps",
                    "-a",
                    "-f",
                    f"name=^{self.container_name}$",
                    "--format",
                    "{{.Status}}",
                ],
                check=False,
            )

            if "Exited" in exit_result.stdout:
                self.logger.error(f"Container {self.container_name} has exited")
                return False
            else:
                self.logger.warning(f"Container {self.container_name} not found")
                return False

        # Container is running, check health status if available
        health_result = self.localhost_env.execute_docker_command(
            docker_args=[
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                self.container_name,
            ],
            check=False,
        )

        health_status = health_result.stdout.strip()
        if (
            health_status
            and health_status != "healthy"
            and health_status != "<no value>"
        ):
            self.logger.warning(
                f"Container {self.container_name} health status: {health_status}"
            )
            if health_status == "unhealthy":
                return False

        return True

    def _handle_container_failure(self):
        """Handle container failure using base class logic."""
        self.failure_count += 1

        if self.failure_count >= self.config.failure_threshold_count:
            # Container has failed beyond threshold
            self.container_state = ServiceHealthState.FAILED

            # Get container logs for debugging before handling failure
            self._log_container_debug_info()

            # Use base class failure handling
            self._handle_failure(
                f"Container '{self.container_name}' failed {self.failure_count} times"
            )
        else:
            # Container is failing but hasn't exceeded threshold yet
            self.logger.warning(
                f"⚠ Container {self.container_name} unhealthy (failures: {self.failure_count}/{self.config.failure_threshold_count})"
            )

    def _log_container_debug_info(self):
        """Log container debug information for troubleshooting."""
        logs_result = self.localhost_env.execute_docker_command(
            docker_args=["logs", "--tail", "50", self.container_name],
            check=False,
        )

        if logs_result.stdout:
            self.logger.error("Container logs (last 50 lines):")
            for line in logs_result.stdout.strip().split("\n"):
                self.logger.error(f"  {line}")

    def _get_monitor_name(self) -> str:
        """Get unique monitor name for localhost container."""
        return f"Container-{self.container_name}"

    def _should_terminate(self) -> bool:
        """Localhost containers always terminate on failure."""
        return True  # Single container failure should always terminate

    def _get_termination_details(self) -> Dict[str, Any]:
        """Get localhost container specific termination details."""
        return {
            "monitor_type": "localhost_container",
            "container_name": self.container_name,
            "container_state": self.container_state.value,
            "last_check_time": self.last_check_time,
        }

    def _get_stop_timeout(self) -> float:
        """Localhost monitoring uses shorter timeout."""
        return 5.0  # 5 seconds for container monitoring
