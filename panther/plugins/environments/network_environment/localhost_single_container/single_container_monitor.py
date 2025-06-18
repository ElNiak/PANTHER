import threading
import time
from enum import Enum


class ContainerState(Enum):
    """State management for single container lifecycle"""

    INITIALIZING = "initializing"
    BUILDING = "building"
    STARTING = "starting"
    RUNNING = "running"
    MONITORING = "monitoring"
    FAILED = "failed"
    STOPPED = "stopped"


class SingleContainerMonitor:
    """
    Background container health monitor for non-blocking localhost deployments.

    Monitors the single container health and triggers early experiment termination
    when the container fails or exits unexpectedly.
    """

    def __init__(self, localhost_env, container_name, config):
        self.localhost_env = localhost_env
        self.container_name = container_name
        self.config = config
        self.logger = localhost_env.logger

        # Container state tracking
        self.container_state = ContainerState.INITIALIZING
        self.failure_count = 0
        self.last_check_time = None

        # Thread management
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()

    def start_monitoring(self):
        """Start background monitoring in a daemon thread"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"ContainerMonitor-{self.container_name}",
            daemon=True,
        )
        self.monitor_thread.start()
        self.logger.info(
            f"Started background container monitoring thread: {self.monitor_thread.name}"
        )

    def stop_monitoring(self):
        """Stop background monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.info("Stopping background container monitoring...")
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                self.logger.warning("Background monitoring thread did not stop cleanly")
        self.monitor_thread = None

    def _monitor_loop(self):
        """Main monitoring loop running in background thread"""
        self.logger.debug(
            f"Background monitoring loop started for container: {self.container_name}"
        )

        while self.monitoring_active:
            try:
                self._check_container_health()
                time.sleep(self.config.monitoring_interval_seconds)
            except Exception as e:
                self.logger.error(f"Error in background monitoring: {e}")
                time.sleep(self.config.monitoring_interval_seconds)

        self.logger.debug("Background monitoring loop ended")

    def _check_container_health(self):
        """Check health of the container and handle failures"""
        with self.lock:
            is_healthy = self._is_container_healthy()

            if is_healthy:
                if self.container_state != ContainerState.RUNNING:
                    self.container_state = ContainerState.RUNNING
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
        """Handle container failure and potentially trigger early termination"""
        self.failure_count += 1

        if self.failure_count >= self.config.failure_threshold_count:
            # Container has failed beyond threshold
            self.container_state = ContainerState.FAILED
            self.logger.error(
                f"✗ Container {self.container_name} failed (failures: {self.failure_count})"
            )

            # Get container logs for debugging
            logs_result = self.localhost_env.execute_docker_command(
                docker_args=["logs", "--tail", "50", self.container_name],
                check=False,
            )

            if logs_result.stdout:
                self.logger.error("Container logs (last 50 lines):")
                for line in logs_result.stdout.strip().split("\n"):
                    self.logger.error(f"  {line}")

            # Trigger early termination
            self._trigger_early_termination(self.failure_count)
        else:
            # Container is failing but hasn't exceeded threshold yet
            self.logger.warning(
                f"⚠ Container {self.container_name} unhealthy (failures: {self.failure_count}/{self.config.failure_threshold_count})"
            )

    def _trigger_early_termination(self, failure_count):
        """Trigger early experiment termination"""
        reason = f"Container '{self.container_name}' failed {failure_count} times (threshold: {self.config.failure_threshold_count})"

        details = {
            "container_name": self.container_name,
            "failure_count": failure_count,
            "container_state": self.container_state.value,
            "monitoring_config": {
                "failure_threshold": self.config.failure_threshold_count,
                "monitoring_interval": self.config.monitoring_interval_seconds,
            },
        }

        self.logger.error(f"Triggering early experiment termination: {reason}")

        # Set termination flag on environment
        self.localhost_env.request_early_termination(reason, details)

        # Stop monitoring since experiment is terminating
        self.monitoring_active = False
