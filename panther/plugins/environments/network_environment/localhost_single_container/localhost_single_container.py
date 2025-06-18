from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.core.docker_builder.environment_manager_docker_mixing import (
    EnvironmentManagerDockerMixin,
)
from panther.plugins.environments.network_environment.localhost_single_container.single_container_monitor import (
    SingleContainerMonitor,
)

"""Localhost single container environment plugin - version.

This module provides a single container environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import os
import time
from enum import Enum
from pathlib import Path

from panther.config.core.models import TestConfig, GlobalConfig
from panther.core.events.experiment.events import ExperimentFinishedEarlyEvent
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.config.core.models.environment import EnvironmentConfig
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


# TODO: link these attributes to the environment config schema and the implementation
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
    EnvironmentManagerDockerMixin,  # Add this for Docker operations
    SubprocessExecutorMixin,
    ErrorHandlerMixin,
    ConfigurationProcessorMixin,
    StatusMonitorMixin,
    StandardOutputCollectorMixin,
    EnvironmentPluginEventMixin,
):
    """
    localhost single container environment using base class and mixins.

    This environment is designed to run a single container on localhost
    with minimal configuration and fast deployment capabilities.

    It first build the base image (services/Dockerfile) and tag it with the
    environment name and version. Then it generates a run script and a
    Dockerfile for the single container setup. The run script is responsible
    for starting the container with all necessary services and configurations.
    It also handles output collection and error management through mixins.
    The environment supports fast deployment and local testing, making it
    ideal for development workflows.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        # First initialize all parent classes including StandardOutputCollectorMixin
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        # Explicitly ensure StandardOutputCollectorMixin is initialized
        # This ensures output_files dictionary is created
        if not hasattr(self, "output_files"):
            self.output_files = {}

        self.logger.debug(
            f"StandardOutputCollectorMixin initialized for localhost, output_files exists: {hasattr(self, 'output_files')}"
        )

        # Localhost specific configuration
        self.name = f"localhost_single_container_{env_sub_type}"
        self.env_name = self.name
        self.docker_version = "v1"
        self.base_image_name = self.name + self.docker_version
        # docker_name will be set in initialize() when test_config is available
        self._final_docker_name = None  # Cache the final docker name

        self.env_sub_type = env_sub_type
        self.env_type = env_type

        # Container process reference
        self.container_process = None

    def _get_safe_test_name(self) -> str:
        """
        Get a Docker-safe test name for container naming.

        Returns:
            str: Sanitized test name suitable for Docker container names
        """
        # Try to get test name from test_config if available
        if (
            hasattr(self, "test_config")
            and self.test_config
            and hasattr(self.test_config, "name")
        ):
            test_name = self.test_config.name
        else:
            # Fallback to env_sub_type if test_config not available
            test_name = getattr(self, "env_sub_type", "test")

        # Sanitize the name for Docker compatibility
        # Replace spaces and special characters with underscores
        safe_name = test_name.lower()
        safe_name = "".join(c if c.isalnum() else "_" for c in safe_name)

        # Remove consecutive underscores and trailing underscores
        safe_name = "_".join(filter(None, safe_name.split("_")))

        # Truncate if too long (Docker container names have limits)
        if len(safe_name) > 50:
            safe_name = safe_name[:50].rstrip("_")

        # Ensure it's not empty
        if not safe_name:
            safe_name = "test"

        return safe_name

    def prepare_environment(self) -> bool:
        """Prepare localhost environment."""
        # Use base implementation
        success = super().prepare()

        # Mark plugin as successfully set up if preparation succeeded
        if success:
            self.plugin_setup = True
            self.logger.debug(
                "Localhost single container environment preparation completed successfully"
            )

        return success

    def generate_environment_services(
        self, paths: Dict[str, str], timestamp: str
    ) -> None:
        """Generate run script and Dockerfile for single container."""
        self.logger.info("Generating localhost single container configuration")
        
        # Ensure docker_name is set before building
        if not hasattr(self, 'docker_name') or not self.docker_name:
            safe_test_name = self._get_safe_test_name()
            self.docker_name = f"localhost_{safe_test_name}"
            self.logger.debug(f"Set docker_name during generate phase: {self.docker_name}")

        # Step 1: Build base service image using mixin
        base_image_tag = self.build_base_service_image(self.plugin_manager)
        self.logger.info(f"Base image tag: {base_image_tag}")

        # Step 2: Ensure all service images are available
        service_images = self.ensure_service_images_available(self.services_managers)
        self.logger.info(f"Service images available: {list(service_images.keys())}")

        # Collect service output patterns
        services_with_outputs = []
        for service in self.services_managers:
            service_data = {
                "service": service,
                "output_file_paths": {},
                "output_redirections": {},
            }

            # Get service-specific output file paths
            if hasattr(service, "get_output_file_paths"):
                service_data["output_file_paths"] = service.get_output_file_paths(
                    log_base_path="/app/logs/" + service.service_name
                )
                self.logger.debug(
                    f"Service {service.service_name} output paths: {service_data['output_file_paths']}"
                )

            # Get standard redirections
            if hasattr(service, "get_standard_redirections"):
                service_data["output_redirections"] = (
                    service.get_standard_redirections()
                )
                self.logger.debug(
                    f"Service {service.service_name} redirections: {service_data['output_redirections']}"
                )

            services_with_outputs.append(service_data)

        # Step 3: Generate run.sh script with proper parameters
        self.generate_from_template(
            template_name="run.sh.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_config_file_path),
            out_file=str(self.services_network_config_file_path),
            additional_param={
                "container_name": self.docker_name,
                "services": self.services_managers,
                "services_with_outputs": services_with_outputs,
            },
        )

        # Make run script executable
        os.chmod(self.rendered_services_network_config_file_path, 0o755)

        # Step 4: Generate Dockerfile with base_image properly set
        self.generate_from_template(
            template_name="Dockerfile.experience.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_docker_file_path),
            out_file=str(self.services_network_docker_file_path),
            additional_param={
                "base_image": base_image_tag,  # Now properly set from mixin!
                "services": self.services_managers,
                "service_images": service_images,  # Add mapping for FROM instructions
            },
        )

        # Step 5: Verify Dockerfile was generated correctly
        if not self.verify_dockerfile_ready(
            self.rendered_services_network_docker_file_path
        ):
            raise RuntimeError(
                "Generated Dockerfile is invalid (empty FROM instructions)"
            )

        # Step 6: Build final environment image using mixin
        if self.global_config.docker.build_docker_image:
            # Store the image name we're building
            self._final_docker_name = self.docker_name
            self.build_environment_image(
                dockerfile_path=self.rendered_services_network_docker_file_path,
                image_name=f"{self.docker_name}:latest",
            )
            self.logger.info(f"Built Docker image with name: {self.docker_name}:latest")

        self.logger.info("Generated localhost configuration files successfully")

    # Remove generate_base_image as it's now handled by the mixin's build_base_service_image

    def _get_docker_run_user_args(self) -> List[str]:
        """Get user arguments for docker run command."""
        user_config = self._get_user_mapping_config()
        if user_config:
            return ["--user", user_config]
        return []

    def launch_environment_services(self) -> None:
        """Launch single container with all services."""
        self.logger.info("Launching localhost single container")
        
        # Use the same docker name that was used during build
        if hasattr(self, '_final_docker_name') and self._final_docker_name:
            self.docker_name = self._final_docker_name
            self.logger.debug(f"Using cached docker name from build phase: {self.docker_name}")

        # Prepare volumes
        volumes = [
            f"{self.output_dir.absolute()}:/output",
            f"{self.log_dirs.absolute()}:/logs",
        ]

        # Collect all port mappings from services
        ports = []
        for service in self.services_managers:
            if hasattr(service, "ports"):
                ports.extend(service.ports)

        # Get user mapping configuration
        user_config = self._get_user_mapping_config()

        # Use the mixin's method to generate docker run command
        docker_run_cmd = self.get_environment_docker_run_command(
            image_name=f"{self.docker_name}:latest",
            container_name=self.docker_name,
            command="/output/run.sh",
            volumes=volumes,
            ports=ports,
            network="host",
            user=user_config,
            detach=True,
            remove=False,  # Don't auto-remove so we can collect logs
        )

        result = self.execute_command(
            command=docker_run_cmd,
            timeout=60,
            log_prefix="docker_run",
        )

        user_info = self._get_user_mapping_config()
        user_desc = f" (user: {user_info})" if user_info else " (user: root)"
        self.logger.info(f"Container started: {self.docker_name}{user_desc}")

    def deploy_services(self) -> bool:
        """Deploy and monitor services in container with optional non-blocking monitoring."""

        # Access configuration to determine monitoring mode
        # Handle case where env_config_to_test is None
        if self.env_config_to_test is None:
            from panther.config.core.models.environment import EnvironmentConfig
            self.env_config_to_test = EnvironmentConfig()
            self.logger.warning("env_config_to_test was None, initialized with default configuration")
        
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

        # Register service outputs now that services are ready
        if hasattr(self, "register_service_outputs"):
            self.logger.info("Registering service outputs...")
            self.register_service_outputs(
                self.services_managers,
                lambda service_name: self._get_service_log_directory(service_name),
            )
            self.logger.info(
                f"Registered outputs for {len(self.services_managers)} services"
            )

        self.logger.info("Services deployed successfully")
        return True

    def _deploy_services_non_blocking(self) -> bool:
        """Non-blocking deployment - start background monitoring and return quickly"""
        self.logger.info("Checking container status (non-blocking mode)")

        config = self.env_config_to_test
        
        # Handle case where env_config_to_test is None - create default config
        if config is None:
            from panther.config.core.models.environment import EnvironmentConfig
            config = EnvironmentConfig()
            self.logger.warning("env_config_to_test was None, using default environment configuration")

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

        # Register service outputs (even if services are still starting)
        if hasattr(self, "register_service_outputs"):
            self.logger.info("Registering service outputs...")
            self.register_service_outputs(
                self.services_managers,
                lambda service_name: self._get_service_log_directory(service_name),
            )
            self.logger.info(
                f"Registered outputs for {len(self.services_managers)} services"
            )

        # Return True to allow experiment to proceed immediately
        return True

    def _get_service_log_directory(self, service_name: str) -> Path:
        """
        Localhost container uses shared logs directory.

        Try service-specific directory first, fall back to shared logs.
        """
        # Try service-specific directory first
        service_dir = Path(self.output_dir) / "logs" / service_name
        return service_dir

    def _perform_final_output_registration(self) -> None:
        """Perform final output registration while container is still running."""
        self.logger.info(
            "Performing final output registration for localhost container..."
        )

        # Wait for final writes to complete
        time.sleep(2)

        # Copy any additional files from running container to host
        self._copy_container_outputs_to_host()

        # Clear and re-register all service outputs
        self.output_files.clear()
        self.register_service_outputs(
            self.services_managers,
            lambda service_name: self._get_service_log_directory(service_name),
        )

        self.logger.info(
            f"Final registration completed for {len(self.services_managers)} services"
        )
        self._log_actual_output_files()

    def _copy_container_outputs_to_host(self) -> None:
        """Copy any remaining outputs from container to host directories."""
        if not hasattr(self, "services_managers"):
            return

        self.logger.debug("Copying final outputs from localhost container to host...")

        for service_manager in self.services_managers:
            service_name = getattr(service_manager, "service_name", "unknown")

            # Copy any files that might not have been mounted correctly
            copy_cmd = [
                "docker",
                "cp",
                f"{self.docker_name}:/app/logs/.",
                f"{self.output_dir}/logs/{service_name}/",
            ]

            try:
                result = self.execute_command(
                    command=copy_cmd, timeout=30, log_prefix="copy_outputs", check=False
                )

                if result.returncode == 0:
                    self.logger.debug(f"Successfully copied outputs for {service_name}")
                else:
                    self.logger.debug(
                        f"No additional outputs to copy for {service_name}"
                    )

            except Exception as e:
                self.logger.debug(f"Could not copy outputs for {service_name}: {e}")

    def _log_actual_output_files(self) -> None:
        """Log what output files actually exist on the host."""
        self.logger.debug("=== Actual Output Files Analysis ===")

        logs_dir = Path(self.output_dir) / "logs"
        if logs_dir.exists():
            for item in logs_dir.iterdir():
                if item.is_dir():
                    self.logger.debug(f"Service directory: {item.name}")
                    try:
                        files = list(item.iterdir())
                        self.logger.debug(
                            f"  Files: {[f.name for f in files if f.is_file()]}"
                        )
                    except Exception as e:
                        self.logger.debug(f"  Error listing files: {e}")
                elif item.is_file():
                    self.logger.debug(f"Root log file: {item.name}")
        else:
            self.logger.debug("Logs directory does not exist")

    def _teardown_environment(self) -> None:
        """Perform localhost specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down localhost container")

        # Perform final output registration before container teardown
        if hasattr(self, "services_managers"):
            self._perform_final_output_registration()

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

    # Remove _build_container_image as it's now handled by the mixin's build_environment_image

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
        # Define localhost specific paths
        # Both files should be in the output directory to avoid writing to project root
        self.output_dir = Path(output_dir)
        self.log_dirs = Path(self.output_dir) / "logs"
        self.event_manager = event_manager
        self.services_network_config_file_path = (
            Path(self.output_dir).absolute() / "run.generated.sh"
        )
        self.rendered_services_network_config_file_path = (
            Path(self.output_dir).absolute() / "run.sh"
        )

        self.services_network_docker_file_path = (
            Path(self.output_dir).absolute() / "Dockerfile.generated"
        )
        self.rendered_services_network_docker_file_path = (
            Path(self.output_dir).absolute() / "Dockerfile"
        )
        # Always set test_config and global_config (override any existing values)
        self.test_config = test_config
        self.global_config = global_config

        # Set docker_name now that test_config is available
        # Generate Docker-safe name based on test name
        safe_test_name = self._get_safe_test_name()
        self.docker_name = f"localhost_{safe_test_name}"

    def handle_event(self, event):
        """Handle events for localhost single container environment."""
        # Localhost container doesn't need special event handling beyond base class
        pass

    def is_network_environment(self):
        """Returns True since this is a network environment plugin."""
        return True
