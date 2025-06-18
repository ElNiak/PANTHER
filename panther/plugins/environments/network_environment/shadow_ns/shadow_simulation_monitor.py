import os
import threading
import time
from enum import Enum


class ShadowSimulationState(Enum):
    """State management for Shadow simulation lifecycle"""

    INITIALIZING = "initializing"
    PREPARING = "preparing"
    STARTING = "starting"
    RUNNING = "running"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ShadowSimulationMonitor:
    """
    Background Shadow simulation monitor for non-blocking deployments.

    Monitors the Shadow simulation process and network health, triggering
    early experiment termination when simulation fails or critical events occur.
    """

    def __init__(self, shadow_env, config):
        self.shadow_env = shadow_env
        self.config = config
        self.logger = shadow_env.logger

        # Simulation state tracking
        self.simulation_state = ShadowSimulationState.INITIALIZING
        self.failure_count = 0
        self.simulation_start_time = None
        self.expected_duration = shadow_env.simulation_duration

        # Process monitoring
        self.shadow_process = None
        self.shadow_output_file = None

        # Thread management
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()

    def start_monitoring(self, shadow_process, output_file=None):
        """Start background monitoring in a daemon thread"""
        if self.monitoring_active:
            return

        self.shadow_process = shadow_process
        self.shadow_output_file = output_file
        self.simulation_start_time = time.time()

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"ShadowMonitor-{self.shadow_env.env_name}",
            daemon=True,
        )
        self.monitor_thread.start()
        self.logger.info(
            f"Started background Shadow simulation monitoring thread: {self.monitor_thread.name}"
        )

    def stop_monitoring(self):
        """Stop background monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.info("Stopping background Shadow monitoring...")
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                self.logger.warning("Background monitoring thread did not stop cleanly")
        self.monitor_thread = None

    def _monitor_loop(self):
        """Main monitoring loop running in background thread"""
        self.logger.debug("Background Shadow monitoring loop started")

        while self.monitoring_active:
            try:
                self._check_simulation_health()
                time.sleep(self.config.monitoring_interval_seconds)
            except Exception as e:
                self.logger.error(f"Error in background monitoring: {e}")
                time.sleep(self.config.monitoring_interval_seconds)

        self.logger.debug("Background Shadow monitoring loop ended")

    def _check_simulation_health(self):
        """Check health of Shadow simulation and handle failures"""
        with self.lock:
            # Check if process is still running
            if self.shadow_process and self.shadow_process.poll() is not None:
                # Process has terminated
                exit_code = self.shadow_process.returncode
                self._handle_process_termination(exit_code)
                return

            # Check simulation progress from output
            if self.shadow_output_file and os.path.exists(self.shadow_output_file):
                self._check_simulation_progress()

            # Check for timeout
            if self.simulation_start_time:
                elapsed = time.time() - self.simulation_start_time
                # Parse duration (e.g., "300s" -> 300)
                duration_seconds = self._parse_duration(self.expected_duration)
                if elapsed > duration_seconds * 1.5:  # 50% over expected duration
                    self.logger.warning(
                        f"Simulation running longer than expected: {elapsed:.1f}s (expected: {duration_seconds}s)"
                    )
                    self.failure_count += 1
                    if self.failure_count >= self.config.failure_threshold_count:
                        self._trigger_early_termination("Simulation timeout exceeded")

    def _check_simulation_progress(self):
        """Check Shadow simulation progress from output logs"""
        try:
            # Read last few lines of output to check for errors
            with open(self.shadow_output_file, "r") as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines

                for line in last_lines:
                    # Check for Shadow error patterns
                    if "ERROR" in line or "CRITICAL" in line:
                        self.logger.error(f"Shadow error detected: {line.strip()}")
                        self.failure_count += 1
                    elif "simulation complete" in line.lower():
                        self.simulation_state = ShadowSimulationState.COMPLETED
                        self.logger.info("Shadow simulation completed successfully")
                        self.monitoring_active = False
                        return

                # Update state based on content
                if self.simulation_state == ShadowSimulationState.STARTING:
                    for line in last_lines:
                        if "starting simulation" in line.lower():
                            self.simulation_state = ShadowSimulationState.RUNNING
                            self.logger.info("Shadow simulation is now running")
                            break

        except Exception as e:
            self.logger.debug(f"Could not read simulation output: {e}")

    def _handle_process_termination(self, exit_code):
        """Handle Shadow process termination"""
        if exit_code == 0:
            self.simulation_state = ShadowSimulationState.COMPLETED
            self.logger.info("Shadow simulation completed successfully")
        else:
            self.simulation_state = ShadowSimulationState.FAILED
            self.logger.error(f"Shadow simulation failed with exit code: {exit_code}")
            self._trigger_early_termination(
                f"Shadow process exited with code {exit_code}"
            )

        self.monitoring_active = False

    def _parse_duration(self, duration_str):
        """Parse duration string (e.g., '300s') to seconds"""
        if isinstance(duration_str, (int, float)):
            return float(duration_str)

        if duration_str.endswith("s"):
            return float(duration_str[:-1])
        elif duration_str.endswith("m"):
            return float(duration_str[:-1]) * 60
        elif duration_str.endswith("h"):
            return float(duration_str[:-1]) * 3600
        else:
            # Assume seconds if no unit
            return float(duration_str)

    def _trigger_early_termination(self, reason):
        """Trigger early experiment termination"""
        details = {
            "simulation_state": self.simulation_state.value,
            "failure_count": self.failure_count,
            "elapsed_time": (
                time.time() - self.simulation_start_time
                if self.simulation_start_time
                else 0
            ),
            "monitoring_config": {
                "failure_threshold": self.config.failure_threshold_count,
                "monitoring_interval": self.config.monitoring_interval_seconds,
            },
        }

        self.logger.error(f"Triggering early experiment termination: {reason}")

        # Set termination flag on environment
        self.shadow_env.request_early_termination(reason, details)

        # Stop monitoring since experiment is terminating
        self.monitoring_active = False
