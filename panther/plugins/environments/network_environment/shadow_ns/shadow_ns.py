"""Shadow NS network environment plugin - version.

This module provides a Shadow network simulator environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import os
import subprocess
import threading
import time
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.events.experiment.events import ExperimentFinishedEarlyEvent
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.execution_environment_mixins import (
    StandardOutputCollectorMixin,
)
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.environment_event_methods import (
    EnvironmentPluginEventMixin,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)
from panther.plugins.environments.network_environment.mixins import (
    ConfigurationProcessorMixin,
    ErrorHandlerMixin,
    StatusMonitorMixin,
    SubprocessExecutorMixin,
)
from panther.plugins.environments.network_environment.utils import (
    NetworkEnvironmentUtils,
)
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


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
            "elapsed_time": time.time() - self.simulation_start_time
            if self.simulation_start_time
            else 0,
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


@register_plugin(
    plugin_type="environment",
    name="shadow_ns",
    version="2.0.0",
    description="Shadow network simulator environment with reduced duplication",
    author="PANTHER Team",
    capabilities=["network_simulation", "deterministic_testing", "scalability_testing"],
    external_dependencies=["docker", "shadow>=2.0"],
)
class ShadowNSEnvironment(
    BaseNetworkEnvironment,
    SubprocessExecutorMixin,
    ErrorHandlerMixin,
    ConfigurationProcessorMixin,
    StatusMonitorMixin,
    StandardOutputCollectorMixin,
    EnvironmentPluginEventMixin,
):
    """
    Shadow NS environment using base class and mixins.

    This implementation reduces code duplication from 305 lines to ~100 lines
    by leveraging shared functionality from the base class and mixins.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        # Shadow specific configuration
        self.name = f"shadow_ns_{env_sub_type}"
        self.env_name = self.name
        self.docker_version = "v1"
        self.docker_name = "shadow_ns"

        # Shadow specific attributes
        self.shadow_config = self._get_shadow_config()
        self.simulation_duration = self.shadow_config.get("duration", "300s")
        self.network_topology = self.shadow_config.get("topology", "simple")

        # Define Shadow specific paths
        self.services_network_config_file_path = Path(
            self._plugin_dir, env_type, env_sub_type, "shadow.generated.yml"
        )
        self.rendered_services_network_config_file_path = self.output_dir / "shadow.yml"

        self.services_network_docker_file_path = Path(
            self._plugin_dir, env_type, env_sub_type, "Dockerfile"
        )

        # Shadow process reference
        self.shadow_process = None

    def prepare_environment(self) -> bool:
        """Prepare Shadow NS environment."""
        # Use base implementation
        success = super().prepare()

        if success:
            # Create Shadow-specific directories
            shadow_dirs = ["shadow-data", "shadow-results", "shadow-hosts"]
            for dir_name in shadow_dirs:
                dir_path = self.output_dir / dir_name
                dir_path.mkdir(exist_ok=True)

        return success

    def generate_environment_services(
        self, paths: Dict[str, str], timestamp: str
    ) -> None:
        """Generate Shadow configuration files."""
        self.logger.info("Generating Shadow NS configuration")

        # Add Shadow-specific paths
        paths.update(
            {
                "shadow_data": str(self.output_dir / "shadow-data"),
                "shadow_results": str(self.output_dir / "shadow-results"),
                "shadow_hosts": str(self.output_dir / "shadow-hosts"),
            }
        )

        # Generate Shadow configuration
        self.generate_from_template(
            template_name="shadow.yml.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_config_file_path),
            out_file=str(self.services_network_config_file_path),
            additional_param={
                "simulation_duration": self.simulation_duration,
                "network_topology": self.network_topology,
                "services": self._prepare_shadow_services(),
                "network_config": self._get_network_config(),
            },
        )

        # Generate host configuration files
        self._generate_host_configs(paths, timestamp)

        self.logger.info("Generated Shadow NS configuration files")

    def launch_environment_services(self) -> None:
        """Launch Shadow network simulator."""
        self.logger.info("Launching Shadow NS environment")

        # Build Docker image if needed
        if self.global_config.docker.build_docker_image:
            self._build_shadow_image()

        # Get Docker container name
        self.get_docker_name()

        # Run Shadow container
        shadow_run_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self.docker_name,
            "--privileged",  # Required for Shadow NS
            "--cap-add=SYS_PTRACE",  # Required for ptrace
            "-v",
            f"{self.output_dir}:/output",
            "-v",
            f"{self.log_dirs}:/logs",
            "-v",
            f"{self.output_dir}/shadow-data:/data",
            "-v",
            f"{self.output_dir}/shadow-results:/results",
            self.docker_name,
            "shadow",
            str(self.rendered_services_network_config_file_path),
        ]

        result = self.execute_command(
            command=shadow_run_cmd,
            timeout=60,
            log_prefix="shadow_run",
        )

        self.logger.info(f"Shadow NS container started: {self.docker_name}")

    def deploy_services(self) -> bool:
        """Deploy and monitor Shadow simulation with optional non-blocking monitoring."""

        # Access configuration to determine monitoring mode
        enable_background = getattr(
            self.env_config_to_test, "enable_background_monitoring", True
        )
        self.logger.info(f"Shadow simulation monitoring enabled: {enable_background}")

        if not enable_background:
            # Use existing blocking monitoring for backward compatibility
            self.logger.info(
                "Using blocking Shadow monitoring (backward compatibility mode)"
            )
            return self._deploy_services_blocking()
        else:
            # Use new non-blocking monitoring
            self.logger.info(
                "Using non-blocking Shadow monitoring with background monitoring"
            )
            return self._deploy_services_non_blocking()

    def _deploy_services_blocking(self) -> bool:
        """Original blocking deployment - monitor simulation before returning"""
        self.logger.info("Deploying Shadow NS simulation (blocking mode)")

        # Monitor Shadow container
        if not self.monitor_docker_container(
            container_name=self.docker_name,
            timeout=30,
        ):
            self.logger.error("Shadow container failed to start")
            return False

        # Monitor simulation progress
        if not self._monitor_simulation():
            self.logger.error("Shadow simulation failed")
            return False

        self.logger.info("Shadow NS simulation deployed successfully")
        return True

    def _deploy_services_non_blocking(self) -> bool:
        """Non-blocking deployment - start background monitoring and return quickly"""
        self.logger.info("Starting Shadow NS simulation (non-blocking mode)")

        config = self.env_config_to_test

        # Quick initial check - wait briefly for container to start
        initial_wait = min(5, config.monitoring_interval_seconds)
        self.logger.info(
            f"Waiting {initial_wait} seconds for initial Shadow startup..."
        )
        time.sleep(initial_wait)

        # Check if container started
        result = self.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name=^{self.docker_name}$"],
            check=False,
        )

        if not result.stdout.strip():
            self.logger.error("Shadow container failed to start")
            return False

        # Get the Shadow process from container
        # In Docker mode, we monitor the container itself
        shadow_output_file = self.output_dir / "shadow-results" / "shadow.log"

        # Start background monitoring for the simulation
        self.background_monitor = ShadowSimulationMonitor(self, config)
        # For Docker-based Shadow, we pass None as process since we monitor the container
        self.background_monitor.start_monitoring(None, str(shadow_output_file))

        self.logger.info(f"Started background monitoring for Shadow simulation")

        # Return True to allow experiment to proceed immediately
        return True

    def _teardown_environment(self) -> None:
        """Perform Shadow NS specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down Shadow NS environment")

        # Stop background monitoring if active
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info("Stopping background Shadow monitoring...")
            self.background_monitor.stop_monitoring()
            self.background_monitor = None

        # Collect Shadow results before teardown
        self._collect_shadow_results()

        # Stop and remove container
        self.safe_docker_cleanup(self.docker_name)

        # Clean up Shadow resources
        NetworkEnvironmentUtils.cleanup_docker_resources(
            prefix="shadow_ns",
            remove_volumes=True,
        )

    def _get_shadow_config(self) -> Dict[str, Any]:
        """Get Shadow-specific configuration."""
        if hasattr(self.env_config_to_test, "shadow"):
            return self.env_config_to_test.shadow
        return {}

    def _prepare_shadow_services(self) -> List[Dict[str, Any]]:
        """Prepare service configurations for Shadow."""
        shadow_services = []

        for service in self.services_managers:
            shadow_service = {
                "name": service.service_name,
                "type": service.implementation_type,
                "protocol": service.protocol_name,
                "role": service.role,
                "command": service.get_run_command(),
            }
            shadow_services.append(shadow_service)

        return shadow_services

    def _get_network_config(self) -> Dict[str, Any]:
        """Get network topology configuration."""
        return {
            "bandwidth": "1Gbit",
            "latency": "10ms",
            "jitter": "1ms",
            "packet_loss": "0.1%",
        }

    def _generate_host_configs(self, paths: Dict[str, str], timestamp: str) -> None:
        """Generate individual host configuration files."""
        for service in self.services_managers:
            host_config_path = (
                self.output_dir / "shadow-hosts" / f"{service.service_name}.yaml"
            )

            self.generate_from_template(
                template_name="shadow_host.yaml.jinja",
                paths=paths,
                timestamp=timestamp,
                rendered_out_file=str(host_config_path),
                out_file=str(host_config_path),
                additional_param={"service": service},
            )

    def _build_shadow_image(self) -> None:
        """Build Shadow Docker image."""
        self.logger.info("Building Shadow NS Docker image")

        build_cmd = [
            "docker",
            "build",
            "-t",
            f"{self.docker_name}:latest",
            "-f",
            str(self.services_network_docker_file_path),
            str(self.services_network_docker_file_path.parent),
        ]

        self.execute_with_retry(
            command=build_cmd,
            max_retries=2,
            log_prefix="shadow_build",
            timeout=600,
        )

    def _monitor_simulation(self) -> bool:
        """Monitor Shadow simulation progress."""
        # Check simulation status periodically
        return self.monitor_service_status(
            service_name="shadow_simulation",
            timeout=int(self.simulation_duration.rstrip("s")) + 60,
            ready_check=self._is_simulation_complete,
        ).is_healthy

    def _is_simulation_complete(self) -> bool:
        """Check if Shadow simulation is complete."""
        results_file = self.output_dir / "shadow-results" / "shadow.results"
        return results_file.exists()

    def _collect_shadow_results(self) -> None:
        """Collect Shadow simulation results."""
        self.logger.info("Collecting Shadow NS results")

        # Copy results from container
        copy_cmd = [
            "docker",
            "cp",
            f"{self.docker_name}:/results/.",
            str(self.output_dir / "shadow-results/"),
        ]

        try:
            self.execute_command(copy_cmd, timeout=60)
        except Exception as e:
            self.logger.error(f"Failed to collect Shadow results: {e}")

    # Required abstract method implementations from IEnvironmentPlugin

    def _do_setup_environment(
        self,
        services_managers: List["IServiceManager"],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: Optional["PluginManager"],
        execution_environment: List["IExecutionEnvironment"],
    ) -> bool:
        """Implementation of setup environment for Shadow NS."""
        return self.setup_environment(
            services_managers,
            test_config,
            global_config,
            timestamp,
            plugin_manager,
            execution_environment,
        )

    def _do_deploy_services(self) -> None:
        """Implementation of service deployment for Shadow NS."""
        if not self.deploy_services():
            raise RuntimeError("Failed to deploy Shadow NS services")

    def _do_teardown_environment(self) -> None:
        """Implementation of environment teardown for Shadow NS."""
        self._teardown_environment()

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """Initialize the Shadow NS environment."""
        if not hasattr(self, "test_config"):
            self.test_config = test_config
        if not hasattr(self, "global_config"):
            self.global_config = global_config

    def handle_event(self, event):
        """Handle events for Shadow NS environment."""
        # Shadow NS doesn't need special event handling beyond base class
        pass

    def is_network_environment(self):
        """Returns True since this is a network environment plugin."""
        return True
