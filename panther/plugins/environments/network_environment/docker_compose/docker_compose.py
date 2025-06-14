"""Docker Compose network environment plugin for PANTHER framework - version.

This module provides a Docker Compose-based network environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import asyncio
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.execution_environment_mixins import (
    StandardOutputCollectorMixin,
)
from panther.core.utils import TemplateRenderer
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


class DockerComposeState(Enum):
    """State management for Docker Compose deployment phases"""

    INITIALIZING = "initializing"
    STARTING_COMPOSE = "starting_compose"
    COMPOSE_UP = "compose_up"
    MONITORING_SERVICES = "monitoring_services"
    SERVICES_READY = "services_ready"
    FAILED = "failed"


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
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.info("Stopping background service monitoring...")
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                self.logger.warning("Background monitoring thread did not stop cleanly")
        self.monitor_thread = None

    def _monitor_loop(self):
        """Main monitoring loop running in background thread"""
        self.logger.debug(
            f"Background monitoring loop started for services: {self.services}"
        )

        while self.monitoring_active:
            try:
                self._check_all_services()
                time.sleep(self.config.monitoring_interval_seconds)
            except Exception as e:
                self.logger.error(f"Error in background monitoring: {e}")
                time.sleep(self.config.monitoring_interval_seconds)

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


@register_plugin(
    plugin_type="environment",
    name="docker_compose",
    version="2.0.0",
    description="Docker Compose network environment with reduced duplication",
    author="PANTHER Team",
    capabilities=["container_orchestration", "network_isolation", "service_discovery"],
    external_dependencies=["docker", "docker-compose>=2.0"],
)
class DockerComposeEnvironment(
    BaseNetworkEnvironment,
    SubprocessExecutorMixin,
    ErrorHandlerMixin,
    ConfigurationProcessorMixin,
    StatusMonitorMixin,
    StandardOutputCollectorMixin,
    EnvironmentPluginEventMixin,
):
    """
    Docker Compose environment using base class and mixins.

    This implementation reduces code duplication from 257 lines to ~80 lines
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

        # Docker Compose specific configuration
        self.name = f"docker_compose_{env_sub_type}"
        self.env_name = self.name

        # Define Docker Compose specific paths
        self.services_network_config_file_path = Path(
            self._plugin_dir, env_type, env_sub_type, f"{env_sub_type}.generated.yml"
        )
        self.rendered_services_network_config_file_path = (
            self.output_dir / f"{env_sub_type}.yml"
        )

        # Initialize template renderer
        self.template_renderer = TemplateRenderer(
            Path(self._plugin_dir) / env_type / env_sub_type / "templates"
        )

    def prepare_environment(self) -> bool:
        """Prepare Docker Compose environment."""
        # Use base implementation which handles common preparation
        result = super().prepare()

        # Mark plugin as successfully set up if preparation succeeded
        if result:
            self.plugin_setup = True
            self.logger.debug(
                "Docker Compose environment preparation completed successfully"
            )

        return result

    def generate_environment_services(
        self, paths: Dict[str, str], timestamp: str
    ) -> None:
        """Generate Docker Compose configuration file."""
        self.logger.info("Generating Docker Compose configuration")

        # Prepare service data with corrected container names for template
        services_with_container_names = []
        for service in self.services_managers:
            service_data = {
                "service_name": service.service_name,
                "container_name": self._get_container_name_for_service(
                    service.service_name
                ),
                # Add other service attributes as needed by template
            }
            services_with_container_names.append(service_data)

        # Generate docker-compose.yml from template
        self.generate_from_template(
            template_name="docker-compose.yml.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_config_file_path),
            out_file=str(self.services_network_config_file_path),
            additional_param={
                "network_name": self.network_name,
                "docker_network": f"{self.network_name}_network",
                "services_with_container_names": services_with_container_names,
            },
        )

        self.logger.info(
            f"Generated Docker Compose file: {self.rendered_services_network_config_file_path}"
        )

    def launch_environment_services(self) -> None:
        """Launch Docker Compose services."""
        self.logger.info("Launching Docker Compose environment")

        # Start Docker Compose
        compose_up_cmd = [
            "docker-compose",
            "-f",
            str(self.rendered_services_network_config_file_path),
            "up",
            "-d",
        ]

        self.execute_with_logging(
            command=compose_up_cmd,
            stdout_file=str(self.output_dir / "logs" / "docker_compose_up.log"),
            stderr_file=str(self.output_dir / "logs" / "docker_compose_up.err.log"),
            timeout=300,
        )

        self.logger.info("Docker Compose services launched")

    def deploy_services(self) -> bool:
        """Check service readiness with optional non-blocking monitoring."""

        # Access configuration to determine monitoring mode
        # The configuration fields are directly on env_config_to_test, not in a nested config
        enable_background = getattr(
            self.env_config_to_test, "enable_background_monitoring", True
        )
        self.logger.info(f"Service deployment monitoring enabled: {enable_background}")

        if not enable_background:
            # Use existing blocking monitoring for backward compatibility
            self.logger.info(
                "Using blocking service monitoring (backward compatibility mode)"
            )
            return self._deploy_services_blocking()
        else:
            # Use new non-blocking monitoring
            self.logger.info(
                "Using non-blocking service monitoring with background monitoring"
            )
            return self._deploy_services_non_blocking()

    def _deploy_services_blocking(self) -> bool:
        """Original blocking deployment - check all services before returning"""
        self.logger.info("Checking Docker Compose service readiness (blocking mode)")

        # Get all service names
        service_names = [
            service_manager.service_name for service_manager in self.services_managers
        ]

        if not service_names:
            self.logger.warning("No services to monitor")
            return True

        self.logger.info(
            f"Starting blocking monitoring for {len(service_names)} services: {service_names}"
        )

        # Use ThreadPoolExecutor for concurrent monitoring
        failed_services = []
        successful_services = []

        with ThreadPoolExecutor(
            max_workers=len(service_names), thread_name_prefix="service_monitor"
        ) as executor:
            # Submit all monitoring tasks
            future_to_service = {
                executor.submit(
                    self._monitor_single_service, service_name
                ): service_name
                for service_name in service_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_service, timeout=self.timeout + 10):
                service_name = future_to_service[future]
                try:
                    is_healthy = future.result(
                        timeout=5
                    )  # Short timeout for getting result
                    if is_healthy:
                        successful_services.append(service_name)
                        self.logger.info(f"✓ Service {service_name} is ready")
                    else:
                        failed_services.append(service_name)
                        self.logger.error(
                            f"✗ Service {service_name} failed to become ready"
                        )
                except Exception as e:
                    failed_services.append(service_name)
                    self.logger.error(
                        f"✗ Exception monitoring service {service_name}: {e}"
                    )

        # Check results
        if failed_services:
            self.logger.error(f"Failed services: {failed_services}")
            self.logger.info(f"Successful services: {successful_services}")
            return False

        self.logger.info(
            f"All {len(successful_services)} services are ready: {successful_services}"
        )

        # Register service outputs for collection after successful deployment
        self._register_all_service_outputs()

        self.logger.info("All Docker Compose services are ready and outputs registered")
        return True

    def _deploy_services_non_blocking(self) -> bool:
        """Non-blocking deployment - start background monitoring and return quickly"""
        self.logger.info(
            "Checking Docker Compose service readiness (non-blocking mode)"
        )

        service_names = [
            service_manager.service_name for service_manager in self.services_managers
        ]

        if not service_names:
            self.logger.warning("No services to monitor")
            return True

        config = self.env_config_to_test

        # Quick initial check - wait briefly for services to start
        initial_wait = min(5, config.monitoring_interval_seconds)
        self.logger.info(
            f"Waiting {initial_wait} seconds for initial service startup..."
        )
        time.sleep(initial_wait)

        # Do a quick check to see which services are already ready
        ready_services = []
        pending_services = []

        for service_name in service_names:
            if self._is_service_ready(service_name):
                ready_services.append(service_name)
                self.logger.info(f"✓ Service {service_name} is ready")
            else:
                pending_services.append(service_name)
                self.logger.info(f"⏳ Service {service_name} is starting...")

        # If all services are ready, register outputs and return immediately
        if not pending_services:
            self._register_all_service_outputs()
            self.logger.info(
                f"All {len(ready_services)} services are ready immediately"
            )
            return True

        # Start background monitoring for all services (including ready ones for continued health checks)
        self.background_monitor = BackgroundServiceMonitor(self, service_names, config)
        self.background_monitor.start_monitoring()

        self.logger.info(
            f"Started background monitoring for {len(service_names)} services"
        )
        self.logger.info(f"Ready services: {ready_services}")
        self.logger.info(f"Pending services: {pending_services}")

        # Register outputs for all services (ready and pending)
        self._register_all_service_outputs()

        # Return True to allow experiment to proceed immediately
        return True

    def _monitor_single_service(self, service_name: str) -> bool:
        """
        Monitor a single service in a separate thread.

        Args:
            service_name: Name of the service to monitor

        Returns:
            bool: True if service became ready, False otherwise
        """
        thread_name = threading.current_thread().name
        self.logger.debug(
            f"[{thread_name}] Starting monitoring for service: {service_name}"
        )

        try:
            # Use status monitor mixin to check service health
            health_check = self.monitor_service_status(
                service_name=service_name,
                timeout=self.timeout,
                ready_check=lambda: self._is_service_ready(service_name),
            )

            result = health_check.is_healthy
            self.logger.debug(
                f"[{thread_name}] Service {service_name} monitoring result: {result}"
            )
            return result

        except Exception as e:
            self.logger.error(
                f"[{thread_name}] Error monitoring service {service_name}: {e}"
            )
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
        """Implementation of setup environment for Docker Compose."""
        return self.setup_environment(
            services_managers,
            test_config,
            global_config,
            timestamp,
            plugin_manager,
            execution_environment,
        )

    def _do_deploy_services(self) -> None:
        """Implementation of service deployment for Docker Compose."""
        # Follow the correct workflow: first launch services, then check readiness
        self.logger.info("Starting Docker Compose service deployment")

        # Step 1: Launch the Docker Compose services (containers)
        self.launch_environment_services()

        # Step 2: Give containers a moment to start up
        startup_delay = 3  # seconds
        self.logger.info(
            f"Waiting {startup_delay} seconds for containers to start up..."
        )
        time.sleep(startup_delay)

        # Step 3: Check service readiness and register outputs
        if not self.deploy_services():
            raise RuntimeError("Failed to deploy Docker Compose services")

    def _do_teardown_environment(self) -> None:
        """Implementation of environment teardown for Docker Compose."""
        self._teardown_environment()

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """Initialize the Docker Compose environment."""
        # Already initialized in __init__, but ensure key attributes are set
        if not hasattr(self, "test_config"):
            self.test_config = test_config
        if not hasattr(self, "global_config"):
            self.global_config = global_config

    def handle_event(self, event):
        """Handle events for Docker Compose environment."""
        # Docker Compose doesn't need special event handling beyond base class
        pass

    def is_network_environment(self):
        """Returns True since this is a network environment plugin."""
        return True

    def _teardown_environment(self) -> None:
        """Perform Docker Compose specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down Docker Compose environment")

        # Stop background monitoring if active
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info("Stopping background service monitoring...")
            self.background_monitor.stop_monitoring()
            self.background_monitor = None

        # Register all service outputs before teardown
        self._register_all_service_outputs()

        # Collect outputs after registration
        outputs = self.collect_outputs()
        if outputs:
            self.logger.info(
                f"Collected {len(outputs)} outputs from Docker Compose environment"
            )
            for output_type, path in outputs.items():
                self.logger.debug(f"  {output_type}: {path}")

        if os.path.exists(self.rendered_services_network_config_file_path):
            # Stop and remove containers
            compose_down_cmd = [
                "docker-compose",
                "-f",
                str(self.rendered_services_network_config_file_path),
                "down",
                "-v",
                "--remove-orphans",
            ]

            try:
                self.execute_command(
                    command=compose_down_cmd,
                    timeout=60,
                    check=False,  # Don't fail on error during cleanup
                )
            except Exception as e:
                self.logger.error(f"Error during Docker Compose teardown: {e}")

        # Clean up any remaining Docker resources
        NetworkEnvironmentUtils.cleanup_docker_resources(
            prefix=self.network_name,
            remove_volumes=True,
            remove_networks=True,
        )

    def _build_docker_images(self) -> None:
        """Build Docker images for services."""
        self.logger.info("Building Docker images")

        build_cmd = [
            "docker-compose",
            "-f",
            str(self.rendered_services_network_config_file_path),
            "build",
            "--parallel",
        ]

        self.execute_with_retry(
            command=build_cmd,
            max_retries=2,
            log_prefix="docker_compose_build",
            timeout=600,
        )

    def _is_service_ready(self, service_name: str) -> bool:
        """Check if a specific service is ready."""
        # Check if container is running using the service name directly
        # Modern Docker Compose uses the service name as container name when container_name is specified

        # First try the service name directly (for modern Docker Compose with container_name)
        result = self.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name=^{service_name}$"],
            check=False,
        )

        if result.stdout.strip():
            return True

        # Fallback to legacy naming convention for backward compatibility
        container_name = f"{self.network_name}_{service_name}_1"
        result = self.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name={container_name}"],
            check=False,
        )

        return bool(result.stdout.strip())

    def _get_container_name_for_service(self, service_name: str) -> str:
        """Get the actual container name that should be used for a service.

        This handles the mismatch between YAML config service names and
        the actual container names used in Docker Compose.
        """
        # Map service names to their actual container names
        # This is needed because some services have different names in config vs containers
        service_to_container_mapping = {
            "ivy_server": "ivy_client",  # ivy_server config -> ivy_client container
            "picoquic_client": "picoquic_server",  # picoquic_client config -> picoquic_server container
        }

        container_name = service_to_container_mapping.get(service_name, service_name)
        self.logger.debug(
            f"Mapped service '{service_name}' to container '{container_name}'"
        )
        return container_name

    def _register_service_outputs(self, service_manager: IServiceManager) -> None:
        """Register service outputs for collection."""
        service_name = service_manager.service_name
        container_name = self._get_container_name_for_service(service_name)

        # Use the log_dirs attribute that gets passed to the template
        # The template uses: {{ log_dir | realpath }}/{{ service.service_name }}:/app/logs/
        # So we need to match that path structure
        if hasattr(self, "log_dirs") and self.log_dirs:
            base_log_dir = Path(self.log_dirs).resolve()  # Same as | realpath filter
        else:
            # Fallback to a default log directory if not set
            base_log_dir = Path(self.output_dir) / "logs"

        # The volume mapping in template uses service_name, but we want to read from container_name directory
        log_dir = base_log_dir / container_name

        self.logger.info(
            f"Registering outputs for service '{service_name}' (container: '{container_name}') from: {log_dir}"
        )

        # Check if log directory exists and create if needed
        if not log_dir.exists():
            self.logger.warning(f"Log directory does not exist: {log_dir}")
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created log directory: {log_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create log directory {log_dir}: {e}")
                return

        # Register expected outputs
        outputs_to_register = [
            ("stdout", "stdout.log"),
            ("stderr", "stderr.log"),
            ("sslkeylog", "sslkeylogfile.txt"),
            ("pcap", f"{container_name}.pcap"),
        ]

        for output_type, filename in outputs_to_register:
            file_path = log_dir / filename
            self.register_output_file(output_type, str(file_path), service_name)
            self.logger.debug(
                f"Registered {output_type} output for {service_name}: {file_path}"
            )

        # Register any additional logs that exist in the directory
        if log_dir.exists():
            self.logger.debug(f"Scanning for additional logs in: {log_dir}")
            for log_file in log_dir.glob("*.log"):
                if log_file.name not in ["stdout.log", "stderr.log"]:
                    output_type = f"{log_file.stem}_additional"
                    self.register_output_file(output_type, str(log_file), service_name)
                    self.logger.debug(
                        f"Registered additional {output_type} log for {service_name}: {log_file}"
                    )

            # Check for any pcap files
            for pcap_file in log_dir.glob("*.pcap"):
                output_type = f"{pcap_file.stem}_pcap"
                self.register_output_file(output_type, str(pcap_file), service_name)
                self.logger.debug(
                    f"Registered pcap file for {service_name}: {pcap_file}"
                )

        # Debug: List what's actually in the directory
        if log_dir.exists():
            files = list(log_dir.iterdir())
            self.logger.info(
                f"Contents of {log_dir}: {[f.name for f in files] if files else 'empty'}"
            )
        else:
            self.logger.warning(f"Directory does not exist: {log_dir}")

    def _register_all_service_outputs(self) -> None:
        """Register outputs from all services before teardown."""
        if not hasattr(self, "services_managers") or not self.services_managers:
            self.logger.warning("No service managers available for output registration")
            return

        self.logger.info("Registering outputs from all Docker Compose services")

        for service_manager in self.services_managers:
            self._register_service_outputs(service_manager)
