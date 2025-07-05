from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.config.core.models.network_resolution import NetworkResolutionContext
from panther.core.docker_builder.plugin_mixin.environment_manager_docker_mixing import (
    StagedDockerMixin,
)
from panther.plugins.environments.network_environment.localhost_single_container.localhost_network_resolver import (
    LocalhostNetworkResolver,
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

from panther.config.core.models import GlobalConfig, TestConfig
from panther.config.core.models.environment import EnvironmentConfig
from panther.core.events.experiment.events import ExperimentFinishedEarlyEvent
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
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
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


# TODO: link these attributes to the environment config schema and the implementation
@register_plugin(
    plugin_type=PluginType.NETWORK_ENVIRONMENT,
    name="localhost_single_container",
    version="2.0.0",
    description="single container environment with reduced duplication",
    author="PANTHER Team",
    capabilities=["single_container", "fast_deployment", "local_testing"],
    external_dependencies=["docker"],
)
class LocalhostSingleContainerEnvironment(
    BaseNetworkEnvironment,
    StagedDockerMixin,  # Add this for Docker operations
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
        target_platform: Optional[str] = None,
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

        # Initialize network resolver for placeholder resolution
        self.network_resolver = LocalhostNetworkResolver()

        # Initialize plugin config cache
        self._plugin_config = None

    def _get_plugin_config(self):
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                # Import here to avoid circular imports
                from panther.plugins.environments.network_environment.localhost_single_container.config_schema import (
                    LocalhostSingleContainerConfig,
                )

                self._plugin_config = self.env_config_to_test.get_plugin_config(
                    LocalhostSingleContainerConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                from panther.plugins.environments.network_environment.localhost_single_container.config_schema import (
                    LocalhostSingleContainerConfig,
                )

                self._plugin_config = LocalhostSingleContainerConfig()
        return self._plugin_config

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
        if not hasattr(self, "docker_name") or not self.docker_name:
            safe_test_name = self._get_safe_test_name()
            self.docker_name = f"localhost_{safe_test_name}"
            self.logger.debug(
                f"Set docker_name during generate phase: {self.docker_name}"
            )

        # Step 1: Build base service image using mixin
        base_image_tag = self.build_base_service_image(self.plugin_manager)
        self.logger.info(f"Base image tag: {base_image_tag}")

        # Step 2: Ensure all service images are available
        service_images = self.ensure_service_images_available(self.services_managers)
        self.logger.info(f"Service images available: {list(service_images.keys())}")

        # Apply environment path adaptation and network resolution to all services before template generation
        services_with_resolved_commands = []
        for service in self.services_managers:
            # CRITICAL: Call adapt_environment_paths before network resolution
            # This ensures template variables like IS_APT_PATH are properly set
            if hasattr(service, "adapt_environment_paths"):
                # Determine architecture mode from service configuration
                use_system_models = self._determine_architecture_mode(service)
                self.logger.debug(
                    f"Calling adapt_environment_paths for {service.service_name} with use_system_models={use_system_models}"
                )

                # Get current environment variables to pass to adaptation
                service_env_vars = {}
                if hasattr(service, "environments") and service.environments:
                    service_env_vars.update(service.environments)
                elif (
                    hasattr(service, "environment_variables")
                    and service.environment_variables
                ):
                    service_env_vars.update(service.environment_variables)

                # Call the service's path adaptation method
                try:
                    service.adapt_environment_paths(service_env_vars, use_system_models)
                    self.logger.debug(
                        f"Successfully adapted environment paths for {service.service_name}"
                    )

                    # Update the service's environment variables with adapted values
                    if hasattr(service, "environments"):
                        service.environments.update(service_env_vars)
                    elif hasattr(service, "environment_variables"):
                        service.environment_variables.update(service_env_vars)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to adapt environment paths for {service.service_name}: {e}"
                    )
            # Finalize commands to ensure latest implementation is used
            finalized_commands = (
                service.finalize_commands()
                if hasattr(service, "finalize_commands")
                else service.run_cmd
            )
            self.logger.debug(
                f"Service {service.service_name} commands before network resolution: {finalized_commands}"
            )

            # Apply network resolution to commands
            if isinstance(finalized_commands, dict):
                resolved_commands = self._resolve_network_placeholders_in_commands(
                    finalized_commands, service
                )
                # Update service with resolved commands
                service.run_cmd = resolved_commands
            elif isinstance(finalized_commands, (list, str)):
                # Handle simple command formats by wrapping in dict
                wrapped_commands = {
                    "main": finalized_commands
                    if isinstance(finalized_commands, list)
                    else [finalized_commands]
                }
                resolved_commands = self._resolve_network_placeholders_in_commands(
                    wrapped_commands, service
                )
                # Extract resolved commands back
                service.run_cmd = resolved_commands.get("main", finalized_commands)

            services_with_resolved_commands.append(service)
            self.logger.debug(
                f"Service {service.service_name} commands after network resolution: {service.run_cmd}"
            )

        # Collect service output patterns
        services_with_outputs = []
        for service in services_with_resolved_commands:
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
                service_data[
                    "output_redirections"
                ] = service.get_standard_redirections()
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
                "services": services_with_resolved_commands,
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
                "services": services_with_resolved_commands,
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
        if self.global_config.docker.force_build_docker_image:
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
        if hasattr(self, "_final_docker_name") and self._final_docker_name:
            self.docker_name = self._final_docker_name
            self.logger.debug(
                f"Using cached docker name from build phase: {self.docker_name}"
            )

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
            self.logger.warning(
                "env_config_to_test was None, initialized with default configuration"
            )

        # Get enable_background_monitoring using dual approach
        plugin_config = self._get_plugin_config()

        # First try plugin_config dict
        enable_background = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            enable_background = self.env_config_to_test.plugin_config.get(
                "enable_background_monitoring"
            )

        # Second try typed config
        if enable_background is None:
            enable_background = plugin_config.enable_background_monitoring
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
            self.logger.warning(
                "env_config_to_test was None, using default environment configuration"
            )

        # Quick initial check - wait briefly for container to start
        # Get monitoring_interval_seconds using dual approach
        plugin_config = self._get_plugin_config()

        # First try plugin_config dict
        monitoring_interval = None
        if hasattr(config, "plugin_config") and config.plugin_config:
            monitoring_interval = config.plugin_config.get(
                "monitoring_interval_seconds"
            )

        # Second try typed config
        if monitoring_interval is None:
            monitoring_interval = plugin_config.monitoring_interval_seconds

        initial_wait = min(5, monitoring_interval)
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
            prefix=self.network_name,
            remove_volumes=True,
            remove_networks=True,
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

    def _determine_architecture_mode(self, service) -> bool:
        """
        Determine whether to use system models (APT architecture) based on service configuration.

        Args:
            service: Service manager instance

        Returns:
            bool: True for APT architecture, False for individual protocol architecture
        """
        # Check if service has explicit configuration for architecture mode
        if hasattr(service, "use_system_models"):
            return service.use_system_models

        # Check service configuration for APT indicators
        if hasattr(service, "service_config_to_test"):
            config = service.service_config_to_test

            # Look for APT-related configuration keys
            if hasattr(config, "use_apt_protocols") and config.use_apt_protocols:
                return True
            if hasattr(config, "protocol_path") and "apt/apt_protocols" in str(
                config.protocol_path
            ):
                return True

        # Check environment variables for APT indicators
        env_vars = {}
        if hasattr(service, "environments") and service.environments:
            env_vars = service.environments
        elif (
            hasattr(service, "environment_variables") and service.environment_variables
        ):
            env_vars = service.environment_variables

        # Look for APT path indicators in environment
        for key, value in env_vars.items():
            if isinstance(value, str):
                if "apt/apt_protocols" in value or "apt_protocols" in value:
                    return True

        # Default to individual protocol architecture (non-APT)
        self.logger.debug(
            f"No APT indicators found for {service.service_name}, using individual protocol architecture"
        )
        return False

    def _resolve_network_placeholders_in_commands(
        self, commands: Dict[str, List[str]], service: IServiceManager
    ) -> Dict[str, List[str]]:
        """
        Resolve network placeholders in service commands for localhost environment.

        Args:
            commands: Dictionary of command lists by phase
            service: Service manager instance

        Returns:
            Commands with network placeholders resolved
        """
        try:
            # Register all services with the network resolver for consistent indexing
            service_names = [s.service_name for s in self.services_managers]
            self.network_resolver.register_services(service_names)

            # Create resolution context
            service_managers = {s.service_name: s for s in self.services_managers}
            context = self.network_resolver.create_resolution_context(
                "localhost_single_container", service_managers
            )

            # Populate service network information
            self.network_resolver.populate_service_network_info(context)

            # Resolve placeholders in each command phase
            resolved_commands = {}
            for phase, command_list in commands.items():
                resolved_commands[phase] = []

                for command in command_list:
                    if isinstance(command, str):
                        resolved_command = self._resolve_placeholders_in_command(
                            command, context
                        )
                        resolved_commands[phase].append(resolved_command)
                    else:
                        # Non-string commands pass through unchanged
                        resolved_commands[phase].append(command)

            self.logger.debug(
                f"Resolved network placeholders for localhost service {service.service_name}"
            )

            return resolved_commands

        except Exception as e:
            self.logger.warning(
                f"Failed to resolve network placeholders for {service.service_name}: {e}"
            )
            # Return original commands if resolution fails
            return commands

    def _resolve_placeholders_in_command(
        self, command: str, context: NetworkResolutionContext
    ) -> str:
        """
        Resolve network placeholders in a single command string.

        Args:
            command: Command string with potential placeholders
            context: Network resolution context

        Returns:
            Command string with placeholders resolved
        """
        if not self.network_resolver.parser.has_placeholders(command):
            return command

        try:
            # Get resolution results
            results = self.network_resolver.resolve_network_placeholders(
                command, context
            )

            # Apply substitutions
            resolved_command = command
            for result in results:
                placeholder, value = result.to_substitution_pair()
                resolved_command = resolved_command.replace(placeholder, value)

            self.logger.debug(
                f"Resolved localhost command: {command} -> {resolved_command}"
            )
            return resolved_command

        except Exception as e:
            self.logger.warning(
                f"Failed to resolve placeholders in command '{command}': {e}"
            )
            return command

    def _get_service_ip(self, service_name: str) -> str:
        """
        Get the IP address for a service in localhost single container environment.

        In a localhost single container environment, all services run in the same container
        and communicate via the loopback interface.

        Args:
            service_name: Name of the service to get IP address for

        Returns:
            str: Always returns "127.0.0.1" for localhost environment
        """
        return "127.0.0.1"
