import os
import time
from enum import Enum
from typing import Any, Dict

from ..base_environment_monitor import BaseEnvironmentMonitor, ServiceHealthState


class ShadowSimulationState(Enum):
    """State management for Shadow NS simulation phases"""

    INITIALIZING = "initializing"
    STARTING_SIMULATION = "starting_simulation"
    SIMULATION_RUNNING = "simulation_running"
    MONITORING_HOSTS = "monitoring_hosts"
    HOSTS_READY = "hosts_ready"
    FAILED = "failed"


class ShadowSimulationMonitor(BaseEnvironmentMonitor):
    """
    Background Shadow simulation monitor for non-blocking deployments.

    Monitors the Shadow simulation process and network health, triggering
    early experiment termination when simulation fails or critical events occur.
    """

    def __init__(self, shadow_env, config):
        # Initialize base monitor
        super().__init__(shadow_env, config, shadow_env.logger)

        # Shadow NS specific attributes
        self.shadow_env = shadow_env
        self.expected_duration = shadow_env.simulation_duration

        # Simulation state tracking (specific to Shadow simulation monitoring)
        self.simulation_state = ServiceHealthState.STARTING
        self.simulation_start_time = None

        # Process monitoring (Shadow specific)
        self.shadow_process = None
        self.shadow_output_file = None

    def start_monitoring(self, shadow_process, output_file=None):
        """Start Shadow simulation monitoring with process and output file."""
        # Store Shadow-specific monitoring parameters
        self.shadow_process = shadow_process
        self.shadow_output_file = output_file
        self.simulation_start_time = time.time()

        # Use base class start_monitoring (no args needed)
        super().start_monitoring()

    def _check_health(self):
        """Check health of Shadow simulation and handle failures (Shadow NS specific)."""
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
                        self._handle_failure("Simulation timeout exceeded")

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
                        self.simulation_state = ServiceHealthState.COMPLETED
                        self.logger.info("Shadow simulation completed successfully")
                        self.monitoring_active = False
                        return

                # Update state based on content
                if self.simulation_state == ServiceHealthState.STARTING:
                    for line in last_lines:
                        if "starting simulation" in line.lower():
                            self.simulation_state = ServiceHealthState.RUNNING
                            self.logger.info("Shadow simulation is now running")
                            break

        except Exception as e:
            self.logger.debug(f"Could not read simulation output: {e}")

    def _handle_process_termination(self, exit_code):
        """Handle Shadow process termination using base class logic."""
        if exit_code == 0:
            self.simulation_state = ServiceHealthState.COMPLETED
            self.logger.info("Shadow simulation completed successfully")
            self.monitoring_active = False
        else:
            self.simulation_state = ServiceHealthState.FAILED
            self.logger.error(f"Shadow simulation failed with exit code: {exit_code}")
            # Use base class failure handling
            self._handle_failure(f"Shadow process exited with code {exit_code}")

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

    def _get_monitor_name(self) -> str:
        """Get unique monitor name for Shadow simulation."""
        return f"ShadowSim-{self.shadow_env.env_name}"

    def _should_terminate(self) -> bool:
        """Shadow simulations should terminate on critical failures."""
        return True  # Simulation failures should always terminate

    def _get_termination_details(self) -> Dict[str, Any]:
        """Get Shadow simulation specific termination details."""
        return {
            "monitor_type": "shadow_simulation",
            "simulation_state": self.simulation_state.value,
            "expected_duration": self.expected_duration,
            "simulation_start_time": self.simulation_start_time,
            "shadow_process_id": (
                self.shadow_process.pid if self.shadow_process else None
            ),
            "shadow_output_file": self.shadow_output_file,
            "duration_seconds": self._parse_duration(self.expected_duration),
        }
