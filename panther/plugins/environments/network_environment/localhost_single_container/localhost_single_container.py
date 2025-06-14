"""Localhost single container environment plugin - version.

This module provides a single container environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import os
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


@register_plugin(
    plugin_type="environment",
    name="localhost_single_container",
    version="2.0.0",
    description="single container environment with reduced duplication",
    author="PANTHER Team",
    capabilities=["single_container", "fast_deployment", "local_testing"],
    external_dependencies=["docker"],
)
class LocalhostSingleContainerEnvironment(
    BaseNetworkEnvironment,
    SubprocessExecutorMixin,
    ErrorHandlerMixin,
    ConfigurationProcessorMixin,
    StatusMonitorMixin,
    StandardOutputCollectorMixin,
    EnvironmentPluginEventMixin,
):
    """
    localhost single container environment using base class and mixins.

    This implementation reduces code duplication from 376 lines to ~100 lines
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

        # Localhost specific configuration
        self.name = f"localhost_single_container_{env_sub_type}"
        self.env_name = self.name
        self.docker_version = "v1"
        self.docker_name = "localhost_"

        # Define localhost specific paths
        self.services_network_config_file_path = Path(
            self._plugin_dir, env_type, env_sub_type, "run.generated.sh"
        )
        self.rendered_services_network_config_file_path = self.output_dir / "run.sh"

        self.services_network_docker_file_path = Path(
            self._plugin_dir, env_type, env_sub_type, "Dockerfile.generated"
        )
        self.rendered_services_network_docker_file_path = self.output_dir / "Dockerfile"

        # Container process reference
        self.container_process = None

    def prepare_environment(self) -> bool:
        """Prepare localhost environment."""
        # Use base implementation
        return super().prepare()

    def generate_environment_services(
        self, paths: Dict[str, str], timestamp: str
    ) -> None:
        """Generate run script and Dockerfile for single container."""
        self.logger.info("Generating localhost single container configuration")

        # Generate run.sh script
        self.generate_from_template(
            template_name="run.sh.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_config_file_path),
            out_file=str(self.services_network_config_file_path),
            additional_param={
                "container_name": self.docker_name,
                "services": self.services_managers,
            },
        )

        # Make run script executable
        os.chmod(self.rendered_services_network_config_file_path, 0o755)

        # Generate Dockerfile
        self.generate_from_template(
            template_name="Dockerfile.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_docker_file_path),
            out_file=str(self.services_network_docker_file_path),
            additional_param={
                "base_image": "ubuntu:20.04",
                "services": self.services_managers,
            },
        )

        self.logger.info("Generated localhost configuration files")

    def launch_environment_services(self) -> None:
        """Launch single container with all services."""
        self.logger.info("Launching localhost single container")

        # Build Docker image if needed
        if self.global_config.docker.build_docker_image:
            self._build_container_image()

        # Get Docker container name
        self.get_docker_name()

        # Run container with services
        docker_run_cmd = [
            "docker",
            "run",
            "-d",  # Detached mode
            "--name",
            self.docker_name,
            "--network",
            "host",  # Use host network
            "-v",
            f"{self.output_dir}:/output",
            "-v",
            f"{self.log_dirs}:/logs",
            self.docker_name,
            "/output/run.sh",
        ]

        # Add port mappings for services
        for service in self.services_managers:
            if hasattr(service, "ports"):
                for port_mapping in service.ports:
                    docker_run_cmd.extend(["-p", port_mapping])

        result = self.execute_command(
            command=docker_run_cmd,
            timeout=60,
            log_prefix="docker_run",
        )

        self.logger.info(f"Container started: {self.docker_name}")

    def deploy_services(self) -> bool:
        """Deploy and monitor services in container with optional non-blocking monitoring."""

        # Access configuration to determine monitoring mode
        enable_background = getattr(
            self.env_config_to_test, "enable_background_monitoring", True
        )
        self.logger.info(
            f"Container deployment monitoring enabled: {enable_background}"
        )

        if not enable_background:
            # Use existing blocking monitoring for backward compatibility
            self.logger.info(
                "Using blocking container monitoring (backward compatibility mode)"
            )
            return self._deploy_services_blocking()
        else:
            # Use new non-blocking monitoring
            self.logger.info(
                "Using non-blocking container monitoring with background monitoring"
            )
            return self._deploy_services_non_blocking()

    def _deploy_services_blocking(self) -> bool:
        """Original blocking deployment - monitor container before returning"""
        self.logger.info("Deploying services in localhost container (blocking mode)")

        # Monitor container status
        if not self.monitor_docker_container(
            container_name=self.docker_name,
            timeout=self.timeout,
        ):
            self.logger.error("Container failed to start properly")
            return False

        # Check for early termination
        if self._check_early_termination():
            self.logger.warning("Services terminated early")
            self.notify_experiment_early_finish(
                reason="Services terminated unexpectedly",
                details={"container_name": self.docker_name},
            )
            return False

        self.logger.info("Services deployed successfully")
        return True

    def _deploy_services_non_blocking(self) -> bool:
        """Non-blocking deployment - start background monitoring and return quickly"""
        self.logger.info("Checking container status (non-blocking mode)")

        config = self.env_config_to_test

        # Quick initial check - wait briefly for container to start
        initial_wait = min(5, config.monitoring_interval_seconds)
        self.logger.info(
            f"Waiting {initial_wait} seconds for initial container startup..."
        )
        time.sleep(initial_wait)

        # Do a quick check to see if container started
        result = self.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name=^{self.docker_name}$"],
            check=False,
        )

        if not result.stdout.strip():
            self.logger.error("Container failed to start")
            return False

        # Start background monitoring for the container
        self.background_monitor = SingleContainerMonitor(self, self.docker_name, config)
        self.background_monitor.start_monitoring()

        self.logger.info(
            f"Started background monitoring for container: {self.docker_name}"
        )

        # Return True to allow experiment to proceed immediately
        return True

    def _teardown_environment(self) -> None:
        """Perform localhost specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down localhost container")

        # Stop background monitoring if active
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info("Stopping background container monitoring...")
            self.background_monitor.stop_monitoring()
            self.background_monitor = None

        # Stop and remove container
        self.safe_docker_cleanup(self.docker_name)

        # Clean up any remaining resources
        NetworkEnvironmentUtils.cleanup_docker_resources(
            prefix="localhost_",
            remove_images=False,  # Keep images for faster rebuilds
        )

    def _build_container_image(self) -> None:
        """Build Docker image for localhost container."""
        self.logger.info("Building localhost container image")

        build_cmd = [
            "docker",
            "build",
            "-t",
            f"{self.docker_name}:latest",
            "-f",
            str(self.rendered_services_network_docker_file_path),
            str(self.output_dir),
        ]

        self.execute_with_retry(
            command=build_cmd,
            max_retries=2,
            log_prefix="docker_build",
            timeout=300,
        )

    def _check_early_termination(self) -> bool:
        """Check if services terminated early."""
        # Check container status
        result = self.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name={self.docker_name}"],
            check=False,
        )

        # If container is not running, check exit status
        if not result.stdout.strip():
            exit_result = self.execute_docker_command(
                docker_args=[
                    "ps",
                    "-a",
                    "-f",
                    f"name={self.docker_name}",
                    "--format",
                    "{{.Status}}",
                ],
                check=False,
            )

            if "Exited" in exit_result.stdout:
                return True

        return False

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
        """Implementation of setup environment for localhost single container."""
        return self.setup_environment(
            services_managers,
            test_config,
            global_config,
            timestamp,
            plugin_manager,
            execution_environment,
        )

    def _do_deploy_services(self) -> None:
        """Implementation of service deployment for localhost single container."""
        if not self.deploy_services():
            raise RuntimeError("Failed to deploy localhost container services")

    def _do_teardown_environment(self) -> None:
        """Implementation of environment teardown for localhost single container."""
        self._teardown_environment()

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """Initialize the localhost single container environment."""
        if not hasattr(self, "test_config"):
            self.test_config = test_config
        if not hasattr(self, "global_config"):
            self.global_config = global_config

    def handle_event(self, event):
        """Handle events for localhost single container environment."""
        # Localhost container doesn't need special event handling beyond base class
        pass

    def is_network_environment(self):
        """Returns True since this is a network environment plugin."""
        return True
