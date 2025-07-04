"""Shadow NS network environment plugin - version.

This module provides a Shadow network simulator environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.config.core.models import GlobalConfig, TestConfig
from panther.config.core.models.environment import EnvironmentConfig
from panther.config.core.models.network_resolution import NetworkResolutionContext
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
from panther.plugins.environments.network_environment.shadow_ns.shadow_network_resolver import (
    ShadowNetworkResolver,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_simulation_monitor import (
    ShadowSimulationMonitor,
    ShadowSimulationState,
)
from panther.plugins.environments.network_environment.utils import (
    NetworkEnvironmentUtils,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type=PluginType.NETWORK_ENVIRONMENT,
    name="shadow_ns",
    version="2.0.0",
    description="Shadow network simulator environment with reduced duplication",
    author="PANTHER Team",
    capabilities=["network_simulation", "deterministic_testing", "scalability_testing"],
    external_dependencies=["docker", "shadow>=2.0"],
)
class ShadowNsEnvironment(
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
            f"StandardOutputCollectorMixin initialized for shadow_ns, output_files exists: {hasattr(self, 'output_files')}"
        )

        # Shadow specific configuration
        self.name = f"shadow_ns_{env_sub_type}"
        self.env_name = self.name
        self.docker_version = "v1"
        self.docker_name = "shadow_ns"

        self.env_type = env_type
        self.env_sub_type = env_sub_type

        # Shadow specific attributes
        self.shadow_config = self._get_shadow_config()
        self.simulation_duration = self.shadow_config.get("duration", "300s")
        self.network_topology = self.shadow_config.get("topology", "simple")

        # Shadow process reference
        self.shadow_process = None

        # Initialize network resolver for placeholder resolution
        self.network_resolver = ShadowNetworkResolver()

        # Initialize plugin config cache
        self._plugin_config = None

    def _get_plugin_config(self):
        """Get plugin config with caching and fallback."""
        # Ensure _plugin_config attribute exists (defensive initialization)
        if not hasattr(self, "_plugin_config"):
            self._plugin_config = None

        if self._plugin_config is None:
            try:
                # Import here to avoid circular imports
                from panther.plugins.environments.network_environment.shadow_ns.config_schema import (
                    ShadowNSConfig,
                )

                self._plugin_config = self.env_config_to_test.get_plugin_config(
                    ShadowNSConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                from panther.plugins.environments.network_environment.shadow_ns.config_schema import (
                    ShadowNSConfig,
                )

                self._plugin_config = ShadowNSConfig()
        return self._plugin_config

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

            # Mark plugin as successfully set up if preparation succeeded
            self.plugin_setup = True
            self.logger.debug(
                "Shadow NS environment preparation completed successfully"
            )

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

        # Generate Shadow configuration
        self.generate_from_template(
            template_name="shadow-template.jinja",
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

        self.logger.info("Generated Shadow NS configuration files")

    def _get_shadow_user_args(self) -> List[str]:
        """Get user arguments for Shadow container."""
        user_config = self._get_user_mapping_config()
        if user_config:
            return ["--user", user_config]
        return []

    def launch_environment_services(self) -> None:
        """Launch Shadow network simulator."""
        self.logger.info("Launching Shadow NS environment")

        # Build Docker image if needed
        if self.global_config.docker.force_build_docker_image:
            self._build_shadow_image()

        # Docker container name is already set in __init__
        # self.docker_name = "shadow_ns"

        # Run Shadow container
        shadow_run_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self.docker_name,
            "--privileged",  # Required for Shadow NS
            "--cap-add=SYS_PTRACE",  # Required for ptrace
        ]

        # Add user mapping if configured
        shadow_run_cmd.extend(self._get_shadow_user_args())

        # Add volume mounts
        shadow_run_cmd.extend(
            [
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
        )

        result = self.execute_command(
            command=shadow_run_cmd,
            timeout=60,
            log_prefix="shadow_run",
        )

        user_info = self._get_user_mapping_config()
        user_desc = f" (user: {user_info})" if user_info else " (user: root)"
        self.logger.info(f"Shadow NS container started: {self.docker_name}{user_desc}")

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

        # Register service outputs now that simulation is ready
        if hasattr(self, "register_service_outputs"):
            self.logger.info("Registering service outputs...")
            self.register_service_outputs(
                self.services_managers,
                lambda service_name: self._get_service_log_directory(service_name),
            )
            self.logger.info(
                f"Registered outputs for {len(self.services_managers)} services"
            )

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

        # Register service outputs (even if simulation is still running)
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
        Shadow NS uses simulation-specific output directories.

        Check multiple possible locations in priority order.
        """
        # Priority order: service-specific > shadow-results > shared logs
        possible_dirs = [
            Path(self.output_dir) / "logs" / service_name,  # Service-specific
            Path(self.output_dir) / "shadow-results",  # Shadow results
            Path(self.output_dir) / "logs",  # Shared logs
        ]

        for log_dir in possible_dirs:
            if log_dir.exists():
                return log_dir

        # Return service-specific even if it doesn't exist (for creation)
        return possible_dirs[0]

    def _perform_final_output_registration(self) -> None:
        """Perform final output registration while simulation is still running."""
        self.logger.info(
            "Performing final output registration for Shadow NS simulation..."
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
        """Copy any remaining outputs from Shadow container to host directories."""
        if not hasattr(self, "services_managers"):
            return

        self.logger.debug("Copying final outputs from Shadow container to host...")

        # Copy Shadow simulation results
        shadow_copy_cmd = [
            "docker",
            "cp",
            f"{self.docker_name}:/root/shadow-results/.",
            f"{self.output_dir}/shadow-results/",
        ]

        try:
            result = self.execute_command(
                command=shadow_copy_cmd,
                timeout=30,
                log_prefix="copy_shadow_results",
                check=False,
            )

            if result.returncode == 0:
                self.logger.debug("Successfully copied Shadow simulation results")
            else:
                self.logger.debug("No additional Shadow results to copy")

        except Exception as e:
            self.logger.debug(f"Could not copy Shadow results: {e}")

        # Copy service-specific outputs
        for service_manager in self.services_managers:
            service_name = getattr(service_manager, "service_name", "unknown")

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
        self.logger.debug("=== Actual Output Files Analysis (Shadow NS) ===")

        # Check shadow-results directory
        shadow_results_dir = Path(self.output_dir) / "shadow-results"
        if shadow_results_dir.exists():
            self.logger.debug("Shadow results directory:")
            try:
                files = list(shadow_results_dir.iterdir())
                self.logger.debug(f"  Files: {[f.name for f in files if f.is_file()]}")
            except Exception as e:
                self.logger.debug(f"  Error listing Shadow results: {e}")
        else:
            self.logger.debug("Shadow results directory does not exist")

        # Check service logs
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
        """Perform Shadow NS specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down Shadow NS environment")

        # Wait for simulation to fully complete if needed
        self._wait_for_simulation_completion()

        # Perform final output registration before container teardown
        if hasattr(self, "services_managers"):
            self._perform_final_output_registration()

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
            prefix=self.network_name,
            remove_volumes=True,
            remove_networks=True,
        )

    def _wait_for_simulation_completion(self) -> None:
        """Wait for Shadow simulation to complete if still running."""
        if not hasattr(self, "docker_name"):
            return

        try:
            # Check if container is still running
            check_cmd = ["docker", "ps", "-q", "-f", f"name={self.docker_name}"]
            result = self.execute_command(check_cmd, timeout=10)

            if result and result.strip():
                self.logger.info("Waiting for Shadow simulation to complete...")
                # Wait for container to finish
                wait_cmd = ["docker", "wait", self.docker_name]
                self.execute_command(wait_cmd, timeout=300)  # 5 minute max wait
                self.logger.info("Shadow simulation completed")
            else:
                self.logger.debug("Shadow simulation already completed")

        except Exception as e:
            self.logger.warning(f"Could not wait for simulation completion: {e}")

    def _get_shadow_config(self) -> Dict[str, Any]:
        """Get Shadow-specific configuration using dual approach."""
        # Get plugin config
        plugin_config = self._get_plugin_config()

        # First try plugin_config dict for shadow sub-config
        shadow_config = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            shadow_config = self.env_config_to_test.plugin_config.get("shadow")

        # Second try typed config (ShadowNSConfig doesn't have a separate shadow field, return all relevant fields)
        if shadow_config is None:
            # Extract relevant shadow configuration from typed config
            shadow_config = {
                "duration": plugin_config.general.stop_time,
                "topology": "simple",  # Default value since not in config
                "general": plugin_config.general.model_dump()
                if hasattr(plugin_config.general, "model_dump")
                else plugin_config.general.dict(),
                "experimental": plugin_config.experimental.model_dump()
                if hasattr(plugin_config.experimental, "model_dump")
                else plugin_config.experimental.dict(),
                "network": plugin_config.network.model_dump()
                if hasattr(plugin_config.network, "model_dump")
                else plugin_config.network.dict(),
                "hosts": plugin_config.hosts.model_dump()
                if hasattr(plugin_config.hosts, "model_dump")
                else plugin_config.hosts.dict(),
            }

        return shadow_config if shadow_config else {}

    def _prepare_shadow_services(self) -> List[Dict[str, Any]]:
        """Prepare service configurations for Shadow."""
        shadow_services = []

        for service in self.services_managers:
            # Get service-specific output file paths
            output_file_paths = {}
            output_redirections = {}
            if hasattr(service, "get_output_file_paths"):
                output_file_paths = service.get_output_file_paths(log_base_path="/logs")
                self.logger.debug(
                    f"Service {service.service_name} output paths: {output_file_paths}"
                )

            # Get standard redirections
            if hasattr(service, "get_standard_redirections"):
                output_redirections = service.get_standard_redirections()
                self.logger.debug(
                    f"Service {service.service_name} redirections: {output_redirections}"
                )

            shadow_service = {
                "name": service.service_name,
                "type": getattr(service, "implementation_type", "unknown"),
                "protocol": getattr(service, "protocol_name", "unknown"),
                "role": service.role,
                "command": service.run_cmd if hasattr(service, "run_cmd") else {},
                "service": service,  # Include the service object
                "output_file_paths": output_file_paths,
                "output_redirections": output_redirections,
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

    def _build_shadow_image(self) -> None:
        """Build Shadow Docker image using the docker_builder approach."""
        self.logger.info("Building Shadow NS Docker image using docker_builder")

        # Import the docker builder
        from panther.core.docker_builder.docker_builder import DockerBuilder

        # Get the singleton docker builder instance
        # Respect global config for build_log_file setting
        build_log_file = (
            self.global_config.docker.log_docker_image_build
            if self.global_config and hasattr(self.global_config, "docker")
            else True  # fallback default
        )
        docker_builder = DockerBuilder.get_instance(
            build_log_file=build_log_file,
            enable_cache=True,
            global_config=self.global_config,
            experiment_context=getattr(self, "experiment_context", None),
        )

        # Check if image already exists
        image_tag = f"{self.docker_name}:latest"
        if docker_builder.image_exists(image_tag):
            self.logger.info(
                f"Shadow NS Docker image {image_tag} already exists, skipping build"
            )
            return

        # Build configuration for Shadow NS environment
        build_config = {
            "commit": "latest",
            "dependencies": {},
        }

        # Use docker_builder to build the image
        try:
            result = docker_builder.build_image(
                impl_name=self.docker_name,
                version="latest",
                dockerfile_path=self.services_network_docker_file_path,
                context_path=self.services_network_docker_file_path.parent,
                config=build_config,
                tag_version="latest",
                remove_dangling=True,
            )

            if result:
                self.logger.info(f"Successfully built Shadow NS Docker image: {result}")
            else:
                raise RuntimeError("Docker build returned None")

        except Exception as e:
            self.logger.error(f"Failed to build Shadow NS Docker image: {e}")
            raise RuntimeError(f"Shadow NS Docker image build failed: {e}") from e

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

    def _do_deploy_services(self) -> None:
        """Implementation of service deployment for Shadow NS."""
        if not self.deploy_services():
            raise RuntimeError("Failed to deploy Shadow NS services")

    def _do_teardown_environment(self) -> None:
        """Implementation of environment teardown for Shadow NS."""
        self._teardown_environment()

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """Initialize the Shadow NS environment."""
        self.output_dir = Path(output_dir)
        self.log_dirs = Path(output_dir) / "logs"
        self.event_manager = event_manager
        # Define Shadow specific paths
        # Both files should be in the output directory to avoid writing to project root
        self.services_network_config_file_path = (
            Path(self.output_dir).absolute() / "shadow.generated.yml"
        )
        self.rendered_services_network_config_file_path = (
            Path(self.output_dir).absolute() / "shadow.yml"
        )

        self.services_network_docker_file_path = Path(
            self._plugin_dir, self.env_type, self.env_sub_type, "Dockerfile"
        )
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

    def _get_service_ip(self, service_name: str) -> str:
        """
        Get IP address for a service in Shadow NS environment.

        Args:
            service_name: Name of the service

        Returns:
            IP address based on service role (11.0.0.1 for servers, 11.0.0.2 for clients)
        """
        return self.network_resolver.get_service_ip(
            service_name,
            self.network_resolver.create_resolution_context("shadow_ns", {}),
        )

    def _resolve_network_placeholders_in_commands(
        self, commands: Dict[str, List[str]], service: IServiceManager
    ) -> Dict[str, List[str]]:
        """
        Resolve network placeholders in service commands for Shadow NS environment.

        Args:
            commands: Dictionary of command lists by phase
            service: Service manager instance

        Returns:
            Commands with network placeholders resolved
        """
        try:
            # Register service roles with the network resolver for IP assignment
            service_roles = {}
            for s in self.services_managers:
                # Try to determine role from service manager
                role = "server"  # Default
                if hasattr(s, "role") and s.role:
                    role_name = getattr(s.role, "name", str(s.role)).lower()
                    role = "client" if "client" in role_name else "server"
                service_roles[s.service_name] = role

            self.network_resolver.register_service_roles(service_roles)

            # Create resolution context
            service_managers = {s.service_name: s for s in self.services_managers}
            context = self.network_resolver.create_resolution_context(
                "shadow_ns", service_managers
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
                f"Resolved network placeholders for Shadow NS service {service.service_name}"
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
                f"Resolved Shadow NS command: {command} -> {resolved_command}"
            )
            return resolved_command

        except Exception as e:
            self.logger.warning(
                f"Failed to resolve placeholders in command '{command}': {e}"
            )
            return command

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
