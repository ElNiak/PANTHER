"""Docker Compose network environment plugin for PANTHER framework - version.

This module provides a Docker Compose-based network environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from panther.config.core.models import TestConfig, GlobalConfig
from panther.core.exceptions.fast_fail import (
    PortConflictException,
    ResourceExhaustionException,
)
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.core.utils import TemplateRenderer
from panther.config.core.models.environment import EnvironmentConfig
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

# Import after TYPE_CHECKING to avoid circular imports
from panther.plugins.environments.network_environment.docker_compose.background_service_monitor import (
    BackgroundServiceMonitor,
)


class DockerComposeState(Enum):
    """State management for Docker Compose deployment phases"""

    INITIALIZING = "initializing"
    STARTING_COMPOSE = "starting_compose"
    COMPOSE_UP = "compose_up"
    MONITORING_SERVICES = "monitoring_services"
    SERVICES_READY = "services_ready"
    FAILED = "failed"


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
    ConfigurationProcessorMixin,
    StatusMonitorMixin,
    ErrorHandlerMixin,
    StandardOutputCollectorMixin,
):
    """
    Docker Compose environment using base class and mixins.
    For this plugins, the docker images are build directly from the services
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
            f"Initializing Docker Compose environment: {env_type}/{env_sub_type} with output dir {output_dir}"
        )
        self.logger.debug(
            f"StandardOutputCollectorMixin initialized, output_files exists: {hasattr(self, 'output_files')}"
        )

        # Docker Compose specific configuration
        self.name = f"docker_compose_{env_sub_type}"
        self.env_name = self.name

        self.env_sub_type = env_sub_type
        self.env_type = env_type

        # Initialize template renderer
        self.template_renderer = TemplateRenderer(
            Path(self._plugin_dir) / env_type / env_sub_type / "templates"
        )

        self.output_registered = False

    def prepare_environment(self) -> bool:
        """Prepare Docker Compose environment with enhanced checks."""
        try:
            # Check disk space before any operations
            self._check_disk_space()

            # Check port availability before starting
            self._check_port_availability()

            # Use base implementation which handles common preparation
            result = super().prepare()

            if result:
                # Create certificate directories and generate certificates if needed
                self._setup_certificates()

                # Mark plugin as successfully set up if preparation succeeded
                self.plugin_setup = True
                self.logger.debug(
                    "Docker Compose environment preparation completed successfully"
                )

            return result

        except (PortConflictException, ResourceExhaustionException) as e:
            self.logger.error(f"Pre-deployment check failed: {e}")
            raise  # Re-raise for fast-fail handling

    def _setup_certificates(self) -> None:
        """Setup certificates for services that require them."""
        # Check if any service needs certificate generation
        needs_certificates = any(
            hasattr(service, "service_config_to_test")
            and service.service_config_to_test.generate_new_certificates
            for service in self.services_managers
        )

        if not needs_certificates:
            self.logger.debug("No services require certificate generation")
            return

        # Create certificate directory in output directory
        cert_dir = self.output_dir / "certs"
        cert_dir.mkdir(exist_ok=True)

        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "key.pem"

        # Generate certificates if they don't exist
        if not cert_file.exists() or not key_file.exists():
            self.logger.info("Generating self-signed certificates for services")

            # Use the certificate generation utility
            from panther.plugins.services.base.service_command_builder import (
                ServiceCommandBuilder,
            )

            cert_gen_cmd = ServiceCommandBuilder.create_certificate_generation_command(
                cert_dir=str(cert_dir),
                cert_name="cert",
                key_name="key",
                common_name="panther.local",
                days=365,
            )

            try:
                # Execute certificate generation command with safer approach
                import shlex
                import subprocess

                # Use shlex.split to safely parse the command and avoid shell=True
                cmd_parts = shlex.split(cert_gen_cmd)
                result = subprocess.run(
                    cmd_parts,
                    shell=False,  # Explicitly set shell=False for security
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,  # Handle errors explicitly
                )

                if result.returncode == 0:
                    self.logger.info(f"Generated certificates in {cert_dir}")
                    self.logger.debug(f"Certificate: {cert_file}")
                    self.logger.debug(f"Private key: {key_file}")
                else:
                    self.logger.error(
                        f"Failed to generate certificates: {result.stderr}"
                    )
                    raise RuntimeError(
                        f"Certificate generation failed: {result.stderr}"
                    )

            except subprocess.TimeoutExpired:
                self.logger.error("Certificate generation timed out")
                raise RuntimeError("Certificate generation timed out")
            except Exception as e:
                self.logger.error(f"Error generating certificates: {e}")
                raise RuntimeError(f"Certificate generation error: {e}")
        else:
            self.logger.info(f"Using existing certificates in {cert_dir}")

    def generate_environment_services(
        self, paths: Dict[str, str], timestamp: str
    ) -> None:
        """Generate Docker Compose configuration file."""
        self.logger.info("Generating Docker Compose configuration")

        # Prepare service data with corrected container names for template
        services_with_container_names = []
        for service in self.services_managers:
            # For docker-compose template, pass the full service manager object
            # The template expects attributes like service.role, service.service_targets, etc.
            services_with_container_names.append(service)
            entrypoint_script_path = Path(
                str(self.rendered_services_network_script_file_path).replace(
                    ".sh", f"_{service.service_name}.sh"
                )
            )

            template_script_path = Path(
                str(self.rendered_services_network_script_file_path).replace(
                    ".sh", f"_{service.service_name}.sh"
                )
            )

            self.logger.info(
                "Generating entrypoint script for service %s at %s",
                service.service_name,
                entrypoint_script_path,
            )

            # Generate entrypoint script
            self.generate_entrypoint_with_structured_args(
                service, paths, timestamp, entrypoint_script_path, template_script_path
            )

            # Verify entrypoint script was created
            if not os.path.exists(entrypoint_script_path):
                raise RuntimeError(
                    f"Failed to generate entrypoint script for service {service.service_name}"
                )

        # Generate docker-compose.yml from template
        user_mapping = self._get_user_mapping_config()
        self.generate_from_template(
            template_name="docker-compose.yml.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_services_network_config_file_path),
            out_file=str(self.services_network_config_file_path),
            additional_param={
                "network_name": self.network_name,
                "docker_network": f"{self.network_name}_network",
                "services": services_with_container_names,  # Template expects 'services' not 'services_with_container_names'
                "docker_user_mapping": user_mapping,
                "docker_config": (
                    self.global_config.docker
                    if hasattr(self, "global_config") and self.global_config
                    else None
                ),
            },
        )

        self.logger.info(
            f"Generated Docker Compose file: {self.rendered_services_network_config_file_path}"
        )

    def generate_entrypoint_with_structured_args(
        self,
        service: IServiceManager,
        paths: dict[str, str],
        timestamp: str,
        output_path: Path,
        template_path: Path,
    ):
        """
        Generates an entrypoint script with properly structured and quoted command arguments.

        This method uses a command processor to handle command arguments and environment variables,
        ensuring proper escaping of special characters in shell commands.

        Args:
            service: The service manager instance
            paths: Dictionary of path configurations
            timestamp: Timestamp string
            output_path: Path where the generated entrypoint script will be written
            template_path: Path to the template file (not used directly)
        """
        self.logger.debug(
            "Generating entrypoint script for %s with structured arguments",
            service.service_name,
        )

        # Use the command processor to process the commands
        from panther.core.command_processor import CommandProcessor
        from panther.plugins.environments.network_environment.docker_compose.command_adapter import (
            DockerComposeCommandAdapter,
        )

        # Create instances of the command processor and adapter
        command_processor = CommandProcessor()
        adapter = DockerComposeCommandAdapter()

        # Finalize commands to ensure latest implementation is used
        self.logger.debug(
            "Service %s run_cmd before finalization: %s",
            service.service_name,
            service.run_cmd,
        )
        finalized_commands = (
            service.finalize_commands()
            if hasattr(service, "finalize_commands")
            else service.run_cmd
        )
        self.logger.debug(
            "Service %s run_cmd after finalization: %s",
            service.service_name,
            finalized_commands,
        )

        # Process commands using the command processor
        processed_commands = command_processor.process_commands(finalized_commands)

        # Apply Docker Compose specific adaptations
        processed_commands = adapter.adapt_commands(processed_commands)

        # Get service-specific output file paths
        output_file_paths = {}
        output_redirections = {}
        if hasattr(service, "get_output_file_paths"):
            output_file_paths = service.get_output_file_paths()
            self.logger.debug(
                f"Service {service.service_name} output paths: {output_file_paths}"
            )

            # Get standard redirections
            if hasattr(service, "get_standard_redirections"):
                output_redirections = service.get_standard_redirections()
                self.logger.debug(
                    f"Service {service.service_name} redirections: {output_redirections}"
                )

        # Render entrypoint template with structured arguments
        self.logger.debug(
            "Rendering entrypoint template for service '%s' with structured commands",
            service,
        )
        self.generate_from_template(
            "entrypoint.sh.jinja",
            paths,
            timestamp,
            output_path,
            template_path,
            additional_param=service,
            structured_commands=processed_commands,
            output_file_paths=output_file_paths,
            output_redirections=output_redirections,
        )

    def _extract_service_environment_variables(self) -> dict:
        """Extract and resolve environment variables from all service managers."""
        import os
        import re

        # Start with system defaults
        service_env_vars = {
            "UID": str(os.getuid() if hasattr(os, "getuid") else 1000),
            "GID": str(os.getgid() if hasattr(os, "getgid") else 1000),
        }

        # Collect environment variables from all service managers
        for service in self.services_managers:
            if hasattr(service, "environments") and service.environments:
                self.logger.debug(
                    "Found environment variables in service %s: %s",
                    service.service_name,
                    service.environments,
                )
                service_env_vars.update(service.environments)

        # Resolve variable references (like $SOURCE_DIR in other variables)
        # Multiple passes to handle nested references
        for _ in range(3):  # Maximum 3 passes to resolve nested variables
            resolved_vars = {}
            for key, value in service_env_vars.items():
                if isinstance(value, str):
                    # Replace $VAR and ${VAR} references
                    resolved_value = value
                    for var_name, var_value in service_env_vars.items():
                        if isinstance(var_value, str):
                            resolved_value = re.sub(
                                rf"\$\{{{var_name}\}}|\${var_name}(?![a-zA-Z0-9_])",
                                var_value,
                                resolved_value,
                            )
                    resolved_vars[key] = resolved_value
                else:
                    resolved_vars[key] = str(value) if value is not None else ""

            service_env_vars = resolved_vars

        self.logger.debug(
            "Resolved service environment variables: %s", service_env_vars
        )
        return service_env_vars

    def launch_environment_services(self) -> None:
        """Launch Docker Compose services."""
        self.logger.info("Launching Docker Compose environment")

        # Set required environment variables for Docker Compose
        docker_env = os.environ.copy()

        # Extract environment variables from service configurations
        service_env_vars = self._extract_service_environment_variables()

        # Update with service-specific environment variables
        docker_env.update(service_env_vars)

        self.logger.debug(
            "Set Docker environment variables from services: %s",
            {k: v for k, v in service_env_vars.items()},
        )

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
            timeout=self.timeout,
            env=docker_env,
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

        # Register service outputs now that services are ready
        if hasattr(self, "register_service_outputs") and not self.output_registered:
            self.logger.info("Registering service outputs...")
            self.register_service_outputs(
                self.services_managers,
                lambda service_name: self._get_service_log_directory(service_name),
            )
            self.output_registered = True
            self.logger.info(
                f"Registered outputs for {len(self.services_managers)} services"
            )

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

        # Start background monitoring for all services (including ready ones for continued health checks)
        self.background_monitor = BackgroundServiceMonitor(self, service_names, config)
        self.background_monitor.start_monitoring()

        self.logger.info(
            f"Started background monitoring for {len(service_names)} services"
        )
        self.logger.info(f"Ready services: {ready_services}")
        self.logger.info(f"Pending services: {pending_services}")

        # Register service outputs (even if services are still starting)
        if hasattr(self, "register_service_outputs") and not self.output_registered:
            self.logger.info("Registering service outputs...")
            self.register_service_outputs(
                self.services_managers,
                lambda service_name: self._get_service_log_directory(service_name),
            )
            self.output_registered = True
            self.logger.info(
                f"Registered outputs for {len(self.services_managers)} services"
            )

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
        try:
            self.launch_environment_services()
        except Exception as e:
            self.logger.error(f"Error launching Docker Compose services: {e}")
            self.teardown_environment()

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
        self.output_dir = Path(output_dir)
        self.log_dirs = Path(output_dir) / "logs"
        self.event_manager = event_manager
        self.rendered_services_network_script_file_path = (
            Path(self.output_dir) / "entrypoint.sh"
        )

        self.services_network_config_file_path = (
            Path(self.output_dir) / f"{self.env_sub_type}.generated.yml"
        )
        self.rendered_services_network_config_file_path = (
            Path(self.output_dir) / f"{self.env_sub_type}.yml"
        )

        self.logger.debug(
            f"Initialized Docker Compose environment with config file: {self.services_network_config_file_path}"
        )

        if not hasattr(self, "test_config"):
            self.test_config = test_config
        if not hasattr(self, "global_config"):
            self.global_config = global_config

    def handle_event(self, event):
        """Handle events for Docker Compose environment."""
        # Docker Compose doesn't need special event handling beyond base class
        pass

    def _perform_final_output_registration(self) -> None:
        """
        Perform final output registration while containers are still running.

        This method ensures that all outputs generated during service execution
        are properly registered for collection before containers are stopped.
        """
        if not hasattr(self, "register_service_outputs") or not hasattr(
            self, "services_managers"
        ):
            self.logger.debug(
                "Cannot perform final output registration: missing required attributes"
            )
            return

        self.logger.info(
            "Performing final output registration before container teardown..."
        )
        self.logger.debug(
            f"Current output_files before final registration: {self.output_files}"
        )

        try:
            # Wait a moment for any final writes to complete
            import time

            time.sleep(2)

            # First, try to copy any additional files from running containers
            self._copy_container_outputs_to_host()

            # Clear existing registrations to start fresh
            self.output_files.clear()

            # Re-register all service outputs with the improved discovery
            self.register_service_outputs(
                self.services_managers,
                lambda service_name: self._get_service_log_directory(service_name),
            )

            self.logger.info(
                f"Final registration completed for {len(self.services_managers)} services"
            )
            self.logger.debug(
                f"Output_files after final registration: {self.output_files}"
            )

            # Log actual files found in directories for debugging
            self._log_actual_output_files()

        except Exception as e:
            self.logger.error(
                f"Failed to perform final output registration: {e}", exc_info=True
            )

    def _copy_container_outputs_to_host(self) -> None:
        """
        Copy any additional outputs from running containers to host volumes.

        This ensures that files written outside the mounted volumes are captured.
        """
        self.logger.debug("Checking for additional container outputs to copy...")

        for service in self.services_managers:
            service_name = service.service_name

            try:
                # Check if container exists (running or stopped)
                container_exists_result = self.execute_docker_command(
                    docker_args=["ps", "-a", "-q", "-f", f"name=^{service_name}$"],
                    check=False,
                )

                if not container_exists_result.stdout.strip():
                    self.logger.debug(f"Container {service_name} does not exist")
                    continue

                # Check if container is still running
                running_result = self.execute_docker_command(
                    docker_args=["ps", "-q", "-f", f"name=^{service_name}$"],
                    check=False,
                )
                
                is_running = bool(running_result.stdout.strip())
                self.logger.debug(f"Container {service_name} running: {is_running}")

                # For running containers, use exec to list files
                if is_running:
                    ls_result = self.execute_docker_command(
                        docker_args=[
                            "exec",
                            service_name,
                            "find",
                            "/app/logs",
                            "-type",
                            "f",
                            "-name",
                            "*",
                        ],
                        check=False,
                    )
                    
                    if ls_result.stdout.strip():
                        container_files = ls_result.stdout.strip().split("\n")
                        self.logger.debug(
                            f"Running container {service_name} contains files: {container_files}"
                        )
                else:
                    # For stopped containers, try to copy critical output files directly
                    self.logger.info(f"Container {service_name} is stopped, attempting to copy outputs...")
                    
                    # Try to copy essential log files that might contain compilation errors
                    essential_files = [
                        "/app/logs/stderr.log",
                        "/app/logs/stdout.log", 
                        "/app/logs/ivy_ivy_server.log",
                        "/app/logs/test_results.json"
                    ]
                    
                    host_logs_dir = Path(self.output_dir) / "logs" / service_name
                    host_logs_dir.mkdir(parents=True, exist_ok=True)
                    
                    for container_file in essential_files:
                        host_file = host_logs_dir / Path(container_file).name
                        try:
                            copy_result = self.execute_docker_command(
                                docker_args=[
                                    "cp",
                                    f"{service_name}:{container_file}",
                                    str(host_file)
                                ],
                                check=False,
                            )
                            if copy_result.returncode == 0:
                                self.logger.debug(f"Successfully copied {container_file} from stopped container {service_name}")
                            else:
                                self.logger.debug(f"File {container_file} not found in stopped container {service_name}")
                        except Exception as copy_error:
                            self.logger.debug(f"Could not copy {container_file} from {service_name}: {copy_error}")
                    
                    # Also try to copy any compilation output files
                    try:
                        # First get container info to see if we can access it
                        inspect_result = self.execute_docker_command(
                            docker_args=["inspect", service_name],
                            check=False,
                        )
                        if inspect_result.returncode == 0:
                            self.logger.debug(f"Stopped container {service_name} is accessible for file copying")
                    except Exception:
                        self.logger.debug(f"Cannot inspect stopped container {service_name}")

            except Exception as e:
                self.logger.warning(
                    f"Failed to copy outputs from container {service_name}: {e}"
                )

    def _log_actual_output_files(self) -> None:
        """Log actual files found in output directories for debugging."""
        if not hasattr(self, "output_dir"):
            return

        logs_dir = Path(self.output_dir) / "logs"
        if not logs_dir.exists():
            self.logger.warning(f"Logs directory does not exist: {logs_dir}")
            return

        self.logger.info("=== Actual Output Files Found ===")
        try:
            for service_dir in logs_dir.iterdir():
                if service_dir.is_dir():
                    service_name = service_dir.name
                    files = list(service_dir.glob("*"))
                    file_names = [f.name for f in files if f.is_file()]
                    file_sizes = {
                        f.name: f.stat().st_size for f in files if f.is_file()
                    }

                    self.logger.info(f"Service {service_name}: {len(file_names)} files")
                    for file_name in file_names:
                        size = file_sizes.get(file_name, 0)
                        self.logger.info(f"  - {file_name} ({size} bytes)")

        except Exception as e:
            self.logger.error(f"Failed to log actual output files: {e}")
        self.logger.info("=== End Actual Output Files ===")

    def _teardown_environment(self) -> None:
        """Perform Docker Compose specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down Docker Compose environment")

        # Perform final output registration while containers are still running
        self._perform_final_output_registration()

        # Stop background monitoring if active
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info("Stopping background service monitoring...")
            self.background_monitor.stop_monitoring()
            self.background_monitor = None

        if os.path.exists(self.rendered_services_network_config_file_path):
            # Set required environment variables for Docker Compose teardown
            docker_env = os.environ.copy()

            # Extract environment variables from service configurations
            service_env_vars = self._extract_service_environment_variables()

            # Update with service-specific environment variables
            docker_env.update(service_env_vars)

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
                    env=docker_env,
                )
                # Wait for containers to fully stop and ports to be released
                self._wait_for_containers_cleanup()
            except Exception as e:
                self.logger.error(f"Error during Docker Compose teardown: {e}")

        # Clean up any remaining Docker resources
        NetworkEnvironmentUtils.cleanup_docker_resources(
            prefix=self.network_name,
            remove_volumes=True,
            remove_networks=True,
        )

    def _wait_for_containers_cleanup(self, timeout: int = 30) -> None:
        """
        Wait for all containers to be fully stopped and ports released.

        This prevents race conditions between sequential tests where containers
        from previous tests might still be holding ports.
        """
        self.logger.info("Waiting for containers to fully cleanup...")
        import time

        # Get list of expected container names
        expected_containers = [
            service.service_name for service in self.services_managers
        ]

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if any of our containers are still running
            running_containers = []
            for container_name in expected_containers:
                result = self.execute_docker_command(
                    docker_args=["ps", "-q", "-f", f"name=^{container_name}$"],
                    check=False,
                )
                if result.stdout.strip():
                    running_containers.append(container_name)

            if not running_containers:
                # Also check legacy naming convention
                legacy_running = []
                for container_name in expected_containers:
                    legacy_name = f"{self.network_name}_{container_name}_1"
                    result = self.execute_docker_command(
                        docker_args=["ps", "-q", "-f", f"name={legacy_name}"],
                        check=False,
                    )
                    if result.stdout.strip():
                        legacy_running.append(legacy_name)

                if not legacy_running:
                    # Verify ports are actually released
                    if self._verify_ports_released():
                        self.logger.info(
                            "All containers and ports have been fully cleaned up"
                        )
                        return
                    else:
                        self.logger.debug(
                            "Containers stopped but some ports still in use"
                        )
                else:
                    self.logger.debug(
                        f"Legacy containers still running: {legacy_running}"
                    )
            else:
                self.logger.debug(f"Containers still running: {running_containers}")

            # Wait a bit before checking again
            time.sleep(1)

        self.logger.warning(
            f"Timeout waiting for container cleanup after {timeout} seconds"
        )

    def _verify_ports_released(self) -> bool:
        """
        Verify that all ports used by services are no longer in use.

        Returns:
            bool: True if all ports are released, False otherwise
        """
        import socket

        # Collect all ports used by services
        used_ports = set()
        for service in self.services_managers:
            if (
                hasattr(service, "service_config_to_test")
                and service.service_config_to_test.ports
            ):
                for port_mapping in service.service_config_to_test.ports:
                    # Port mappings are in format "host_port:container_port"
                    if ":" in port_mapping:
                        host_port = port_mapping.split(":")[0]
                        try:
                            used_ports.add(int(host_port))
                        except ValueError:
                            continue

        # Check if any ports are still in use using the improved method
        ports_in_use = []
        for port in used_ports:
            if not self._is_port_available(port, max_retries=1):
                ports_in_use.append(port)

        if ports_in_use:
            self.logger.debug(f"Ports still in use: {ports_in_use}")
            return False

        return True

    def _is_service_ready(self, service_name: str) -> bool:
        """Check if a specific service is ready."""
        # Check if container is running using the service name directly
        # Modern Docker Compose uses the service name as container name when container_name is specified

        # First try the service name directly (for modern Docker Compose with container_name)
        result = self.execute_docker_command(
            docker_args=["ps", "-q", "-f", f"name=^{service_name}$"],
            check=False,
        )

        self.logger.debug(
            f"Checking if service '{service_name}' is ready: {result.stdout.strip()}"
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

    def _get_service_log_directory(self, service_name: str) -> Path:
        """Docker Compose uses service-specific log directories."""
        return Path(self.output_dir) / "logs" / service_name

    def _check_port_availability(self) -> None:
        """Check if required ports are available before starting containers."""
        self.logger.info("Checking port availability for all services...")

        # First, clean up any stale containers that might be holding ports
        self._cleanup_stale_containers()

        conflicts = []
        for service in self.services_managers:
            if (
                hasattr(service, "service_config_to_test")
                and service.service_config_to_test.ports
            ):
                service_name = service.service_name
                for port_mapping in service.service_config_to_test.ports:
                    if ":" in port_mapping:
                        host_port = int(port_mapping.split(":")[0])

                        # Check if port is available using bind() for more accurate detection
                        if not self._is_port_available(host_port):
                            conflicts.append((host_port, service_name))
                            self.logger.error(
                                f"Port {host_port} is already in use (needed by {service_name})"
                            )
                        else:
                            self.logger.debug(
                                f"Port {host_port} is available for {service_name}"
                            )

        if conflicts:
            # Try to resolve conflicts with retry and cleanup
            resolved_conflicts = self._attempt_port_conflict_resolution(conflicts)

            if resolved_conflicts:
                # Try dynamic port allocation as last resort
                if self._attempt_dynamic_port_allocation(resolved_conflicts):
                    self.logger.info(
                        "All port conflicts resolved using dynamic allocation"
                    )
                else:
                    # Some conflicts remain unresolved
                    port, service = resolved_conflicts[0]
                    # Provide more detailed error information
                    self._log_port_usage_details(port)
                    raise PortConflictException(
                        f"Cannot start Docker Compose: port {port} is already in use",
                        port,
                        service,
                    )
            else:
                self.logger.info("All port conflicts resolved successfully")

    def _is_port_available(self, port: int, max_retries: int = 3) -> bool:
        """
        Check if a port is available using bind() method with retry logic.

        Args:
            port: Port number to check
            max_retries: Maximum number of retry attempts

        Returns:
            bool: True if port is available, False otherwise
        """
        import time

        for attempt in range(max_retries):
            try:
                # Use bind() which is more accurate than connect_ex()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(1)
                sock.bind(("localhost", port))
                sock.close()
                return True
            except OSError as e:
                if attempt < max_retries - 1:
                    # Port might be in TIME_WAIT state, wait briefly and retry
                    self.logger.debug(
                        f"Port {port} check attempt {attempt + 1} failed: {e}, retrying..."
                    )
                    time.sleep(0.5)
                else:
                    self.logger.debug(f"Port {port} is not available: {e}")
                    return False
            except Exception as e:
                self.logger.debug(f"Unexpected error checking port {port}: {e}")
                return False

        return False

    def _cleanup_stale_containers(self) -> None:
        """Remove any stale PANTHER containers that might be holding ports."""
        try:
            # Find containers with PANTHER-related names
            cmd = [
                "docker",
                "ps",
                "-a",
                "--format",
                "{{.Names}}",
                "--filter",
                "name=panther",
            ]
            result = self.execute_command(cmd, timeout=10, check=False)

            if result.returncode == 0 and result.stdout.strip():
                stale_containers = result.stdout.strip().split("\n")
                self.logger.info(
                    f"Found {len(stale_containers)} stale PANTHER containers"
                )

                for container in stale_containers:
                    if container.strip():
                        self.logger.debug(f"Removing stale container: {container}")
                        self.execute_command(
                            ["docker", "rm", "-f", container.strip()],
                            timeout=30,
                            check=False,
                        )

            # Also check for containers using specific service patterns
            service_patterns = [
                "picoquic",
                "ivy",
                "aioquic",
                "lsquic",
                "mvfst",
                "quiche",
                "quinn",
                "quic_go",
            ]
            for pattern in service_patterns:
                cmd = [
                    "docker",
                    "ps",
                    "-a",
                    "--format",
                    "{{.Names}}",
                    "--filter",
                    f"name={pattern}",
                ]
                result = self.execute_command(cmd, timeout=10, check=False)

                if result.returncode == 0 and result.stdout.strip():
                    containers = result.stdout.strip().split("\n")
                    for container in containers:
                        if container.strip():
                            self.logger.debug(
                                f"Removing stale service container: {container}"
                            )
                            self.execute_command(
                                ["docker", "rm", "-f", container.strip()],
                                timeout=30,
                                check=False,
                            )

        except Exception as e:
            self.logger.debug(f"Error during stale container cleanup: {e}")

    def _attempt_port_conflict_resolution(self, conflicts: List[tuple]) -> List[tuple]:
        """
        Attempt to resolve port conflicts through cleanup and waiting.

        Args:
            conflicts: List of (port, service_name) tuples

        Returns:
            List of remaining unresolved conflicts
        """
        self.logger.info(f"Attempting to resolve {len(conflicts)} port conflicts...")

        # Wait a moment for any TIME_WAIT states to clear
        import time

        time.sleep(2)

        # Force Docker network cleanup
        try:
            self.execute_command(
                ["docker", "network", "prune", "-f"], timeout=30, check=False
            )
        except Exception as e:
            self.logger.debug(f"Docker network cleanup failed: {e}")

        # Re-check each conflicted port
        remaining_conflicts = []
        for port, service_name in conflicts:
            if not self._is_port_available(port, max_retries=2):
                remaining_conflicts.append((port, service_name))
            else:
                self.logger.info(f"Port {port} conflict resolved for {service_name}")

        return remaining_conflicts

    def _log_port_usage_details(self, port: int) -> None:
        """Log detailed information about what is using a port."""
        try:
            # Try to find what's using the port
            import subprocess

            # On macOS/Linux, use lsof if available
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout:
                    self.logger.error(f"Port {port} is being used by:")
                    for line in result.stdout.split("\n")[1:]:  # Skip header
                        if line.strip():
                            self.logger.error(f"  {line}")
                else:
                    self.logger.debug(f"No lsof output for port {port}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # lsof not available or timed out
                self.logger.debug(f"Could not determine what is using port {port}")

            # Also check Docker containers
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--format",
                        "{{.Names}} {{.Ports}}",
                        "--filter",
                        f"publish={port}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.logger.error(f"Docker containers using port {port}:")
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            self.logger.error(f"  {line}")
            except subprocess.TimeoutExpired:
                pass

        except Exception as e:
            self.logger.debug(f"Error logging port usage details: {e}")

    def _attempt_dynamic_port_allocation(self, conflicts: List[tuple]) -> bool:
        """
        Attempt to resolve port conflicts by dynamically allocating alternative ports.

        Args:
            conflicts: List of (port, service_name) tuples with unresolved conflicts

        Returns:
            bool: True if all conflicts were resolved, False otherwise
        """
        self.logger.info(
            "Attempting dynamic port allocation for remaining conflicts..."
        )

        port_mappings = {}
        for original_port, service_name in conflicts:
            # Find an available alternative port
            alternative_port = self._find_available_port(original_port)
            if alternative_port:
                port_mappings[service_name] = (original_port, alternative_port)
                self.logger.info(
                    f"Assigned alternative port {alternative_port} to {service_name} (original: {original_port})"
                )
            else:
                self.logger.error(
                    f"Could not find alternative port for {service_name} (original: {original_port})"
                )
                return False

        # Apply the new port mappings to the service configurations
        if self._apply_dynamic_port_mappings(port_mappings):
            self.logger.info("Successfully applied dynamic port mappings")
            return True
        else:
            self.logger.error("Failed to apply dynamic port mappings")
            return False

    def _find_available_port(
        self, original_port: int, port_range: int = 1000
    ) -> Optional[int]:
        """
        Find an available port starting from original_port + 1000.

        Args:
            original_port: The original conflicted port
            port_range: Range of ports to search

        Returns:
            int: Available port number, or None if none found
        """
        # Start searching from original_port + 1000 to avoid common port ranges
        start_port = original_port + 1000
        end_port = start_port + port_range

        for port in range(start_port, end_port):
            if self._is_port_available(port, max_retries=1):
                return port

        # If no port found in that range, try a different range
        start_port = 50000  # Use high port numbers that are typically available
        end_port = 60000

        for port in range(start_port, end_port):
            if self._is_port_available(port, max_retries=1):
                return port

        return None

    def _apply_dynamic_port_mappings(self, port_mappings: Dict[str, tuple]) -> bool:
        """
        Apply dynamic port mappings to service configurations.

        Args:
            port_mappings: Dict mapping service_name to (original_port, new_port) tuples

        Returns:
            bool: True if successfully applied, False otherwise
        """
        try:
            for service in self.services_managers:
                service_name = service.service_name
                if service_name in port_mappings:
                    original_port, new_port = port_mappings[service_name]

                    # Update service configuration ports
                    if (
                        hasattr(service, "service_config_to_test")
                        and service.service_config_to_test.ports
                    ):
                        updated_ports = []
                        for port_mapping in service.service_config_to_test.ports:
                            if ":" in port_mapping:
                                host_port, container_port = port_mapping.split(":", 1)
                                if int(host_port) == original_port:
                                    updated_ports.append(f"{new_port}:{container_port}")
                                    self.logger.debug(
                                        f"Updated port mapping for {service_name}: {port_mapping} -> {new_port}:{container_port}"
                                    )
                                else:
                                    updated_ports.append(port_mapping)
                            else:
                                updated_ports.append(port_mapping)

                        service.service_config_to_test.ports = updated_ports

                    # Also update any direct port attributes
                    if hasattr(service, "ports"):
                        updated_ports = []
                        for port_mapping in service.ports:
                            if ":" in port_mapping:
                                host_port, container_port = port_mapping.split(":", 1)
                                if int(host_port) == original_port:
                                    updated_ports.append(f"{new_port}:{container_port}")
                                else:
                                    updated_ports.append(port_mapping)
                            else:
                                updated_ports.append(port_mapping)

                        service.ports = updated_ports

            return True

        except Exception as e:
            self.logger.error(f"Error applying dynamic port mappings: {e}")
            return False

    def _check_disk_space(self, required_gb: float = 2.0) -> None:
        """Check available disk space before building images."""
        import shutil

        stat = shutil.disk_usage("/")
        available_gb = stat.free / (1024**3)

        self.logger.info(f"Available disk space: {available_gb:.2f}GB")

        if available_gb < required_gb:
            raise ResourceExhaustionException(
                f"Insufficient disk space for Docker operations",
                "disk_space",
                available_gb,
                required_gb,
            )
