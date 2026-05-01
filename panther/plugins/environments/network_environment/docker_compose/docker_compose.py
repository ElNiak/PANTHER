"""Docker Compose network environment plugin for PANTHER framework - version.

This module provides a Docker Compose-based network environment implementation
that uses the base class and mixins to eliminate code duplication.
"""

import os
import re
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from panther.config.core.models.environment import EnvironmentConfig
from panther.core.command_processor import CommandProcessor
from panther.core.events.base.event_base import BaseEvent
from panther.core.exceptions.fast_fail import (
    PortConflictException,
    ResourceExhaustionException,
)
from panther.core.observer.base.observer_interface import IObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.core.template.template_renderer import TemplateRenderer
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)
from panther.plugins.environments.network_environment.docker_compose.config_schema import (
    AuxiliaryNetworkConfig,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose_command_adapter import (
    DockerComposeCommandAdapter,
)
from panther.plugins.environments.network_environment.mixins import (
    ConfigurationProcessorMixin,
    ErrorHandlerMixin,
    StatusMonitorMixin,
    SubprocessExecutorMixin,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

# Import after TYPE_CHECKING to avoid circular imports
from panther.config.core.models.network_resolution import NetworkResolutionContext
from panther.plugins.environments.network_environment.docker_compose.background_service_monitor import (
    BackgroundServiceMonitor,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose_lifecycle_manager import (
    DockerComposeLifecycleManager,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose_output_manager import (
    DockerComposeOutputManager,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose_port_manager import (
    DockerComposePortManager,
)
from panther.plugins.environments.network_environment.docker_compose.docker_network_resolver import (
    DockerComposeNetworkResolver,
)


class DockerComposeState(Enum):
    """State management for Docker Compose deployment phases."""

    INITIALIZING = "initializing"
    STARTING_COMPOSE = "starting_compose"
    COMPOSE_UP = "compose_up"
    MONITORING_SERVICES = "monitoring_services"
    SERVICES_READY = "services_ready"
    FAILED = "failed"


@register_plugin(
    plugin_type=PluginType.NETWORK_ENVIRONMENT,
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
    IObserver,
):
    """Docker Compose network environment for container-based protocol testing.

    Orchestrates multi-service Docker Compose deployments with network isolation,
    template-driven configuration (Jinja2), background health monitoring, and
    execution environment integration (strace, Valgrind, etc.).

    Lifecycle: Docker setup -> network creation -> docker-compose.yml generation ->
    container startup -> deployment & analysis -> monitoring -> teardown.

    Combines ``BaseNetworkEnvironment`` for service coordination,
    ``SubprocessExecutorMixin`` for Docker CLI, ``ConfigurationProcessorMixin``
    for config processing, ``StatusMonitorMixin`` for health checks,
    ``ErrorHandlerMixin`` for recovery, ``StandardOutputCollectorMixin`` for
    output collection, and ``IObserver`` for event-driven monitoring.

    Attributes:
        name: Environment instance identifier.
        env_name: Environment name for template variable resolution.
        template_renderer: Jinja2 template processing engine.
        network_resolver: Docker network placeholder resolution.
        port_manager: Port conflict detection and resolution.
        output_manager: Output collection and organization.
        lifecycle_manager: Service lifecycle coordination.
        background_monitor: Real-time health monitoring.
        plugin_setup: Plugin initialization state tracking.
        output_registered: Output collection registration state.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
        target_platform: str = None,
    ):
        """Initialize DockerComposeEnvironment."""
        # First initialize all parent classes including StandardOutputCollectorMixin and IObserver
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        # Initialize IObserver explicitly (in case not properly called by super())
        IObserver.__init__(self)

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

        # Initialize network resolver for placeholder resolution
        self.network_resolver = DockerComposeNetworkResolver()

        # Initialize port manager for port conflict resolution
        self.port_manager = DockerComposePortManager(self.logger)

        # Initialize output manager for file operations and output collection
        self.output_manager = DockerComposeOutputManager(
            output_dir=self.output_dir,  # Already a Path object
            logger=self.logger,
            docker_executor=self,  # Pass self for Docker command execution
            output_collector=self,  # Pass self for output collection methods
        )

        self.output_registered = False

        # Register as observer for deployment events to enable background monitoring
        if event_manager:
            event_manager.register_observer(
                self, event_types=["environment.deployment_completed"]
            )
            self.logger.debug(
                "DockerComposeEnvironment registered as observer for deployment_completed events"
            )

    def prepare_environment(self) -> bool:
        """Prepare Docker Compose environment with enhanced checks."""
        try:
            # Check disk space before any operations using output manager
            self.output_manager.check_disk_space()

            # Check port availability before starting using port manager
            self.port_manager.check_port_availability(self.services_managers)

            # Use base implementation which handles common preparation
            result = super().prepare()

            if result:
                # Create certificate directories and generate certificates if needed using output manager
                self.output_manager.setup_certificates(self.services_managers)

                # Mark plugin as successfully set up if preparation succeeded
                self.plugin_setup = True
                self.logger.debug(
                    "Docker Compose environment preparation completed successfully"
                )
            else:
                self.logger.error("Docker Compose environment preparation failed")
                self.plugin_setup = False

            return result

        except (PortConflictException, ResourceExhaustionException) as e:
            self.logger.error(f"Pre-deployment check failed: {e}")
            raise  # Re-raise for fast-fail handling

    def generate_environment_services(
        self, paths: Dict[str, str], timestamp: str
    ) -> None:
        """Generate Docker Compose configuration file."""
        self.logger.info("Generating Docker Compose configuration")
        env_vars = []
        # Prepare service data with corrected container names for template
        services_with_container_names = []
        for service in self.services_managers:
            if not service.is_tester():
                # Add to TEST_IMPL environment variable if not a tester
                # Add implementation name to TEST_IMPL environment variable for all services
                env_vars = getattr(service, "environments", {}) or {}

                # Initialize TEST_IMPL if it doesn't exist
                if "TEST_IMPL" not in env_vars or env_vars["TEST_IMPL"] == "":
                    env_vars["TEST_IMPL"] = service.implementation_name
                else:
                    # If TEST_IMPL already exists, append with a separator
                    env_vars["TEST_IMPL"] += f",{service.implementation_name}"

        # Note: execution environment setup is handled per-service in generate_entrypoint_with_structured_args
        # This ensures proper command wrapping for each individual service

        # The template expects attributes like service.role, service.service_targets, etc.
        for service in self.services_managers:
            if service.is_tester():
                service.environments["TEST_IMPL"] = env_vars["TEST_IMPL"]

            # Update the service environment
            self.logger.debug(
                f"Updated TEST_IMPL for {service.service_name}: {env_vars['TEST_IMPL']}"
            )
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

            # Set up execution environment plugins BEFORE entrypoint generation
            # This ensures wrapper files are created before entrypoint script tries to read them
            if self.execution_environment:
                self.logger.debug(
                    f"Setting up execution environments for service {service.service_name} before entrypoint generation"
                )
                self.logger.debug(
                    f"Service {service.service_name} run_cmd before execution env setup: {service.run_cmd}"
                )
                self.setup_execution_plugins_for_service(service, timestamp)
                self.logger.debug(
                    f"Service {service.service_name} run_cmd after execution env setup: {service.run_cmd}"
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

        # Get computed target platform from DockerBuilder
        from panther.core.docker_builder import DockerBuilder

        docker_builder = DockerBuilder.get_instance(global_config=self.global_config)
        computed_target_platform = docker_builder.get_target_platform()

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
                "computed_target_platform": computed_target_platform,
                **self._auxiliary_network_render_context(services_with_container_names),
            },
        )

        self.logger.info(
            f"Generated Docker Compose file: {self.rendered_services_network_config_file_path}"
        )

    def _auxiliary_network_render_context(
        self, services_with_container_names: List[Any]
    ) -> Dict[str, Any]:
        """Build the auxiliary-network slice of the Jinja render context.

        Single source of truth for `aux_network_name` / `aux_network_subnet`:
        falls back to `AuxiliaryNetworkConfig()` defaults so any change to
        those defaults in `config_schema.py` propagates here automatically.

        Also enforces the Path α single-secondary-IP-per-service constraint:
        the Jinja template renders only the first secondary endpoint via
        `(values | list)[0]`, so a service declaring more than one would
        silently lose data. Multi-endpoint support is pending.
        """
        for svc in services_with_container_names:
            secondary = (
                getattr(svc.service_config_to_test, "secondary_endpoints", None) or {}
            )
            if len(secondary) > 1:
                raise ValueError(
                    f"Service {svc.service_name!r} declares "
                    f"{len(secondary)} secondary_endpoints "
                    f"({sorted(secondary.keys())}); the docker_compose plugin "
                    f"currently materializes at most one. Path α single-IP "
                    f"design choice; multi-endpoint support pending."
                )

        aux_cfg: AuxiliaryNetworkConfig = (
            getattr(self.env_config_to_test, "auxiliary_network", None)
            or AuxiliaryNetworkConfig()
        )
        return {
            "aux_network_name": aux_cfg.name,
            "aux_network_subnet": aux_cfg.subnet,
            "any_service_has_secondary_endpoints": any(
                bool(getattr(s.service_config_to_test, "secondary_endpoints", None))
                for s in services_with_container_names
            ),
        }

    def setup_execution_plugins_for_service(
        self, service: IServiceManager, timestamp: str
    ) -> None:
        """Set up execution environment plugins for a single service.

        This method applies execution environment modifications to one service at a time,
        allowing for per-service configuration and direct command wrapping.

        Args:
            service: The service manager to configure with execution environments
            timestamp: Timestamp for this execution (used for file naming)
        """
        if not self.execution_environment:
            self.logger.debug(
                f"No execution environments configured for service {service.service_name}"
            )
            return

        self.logger.info(
            f"Setting up execution environment plugins for service {service.service_name}"
        )

        for execution_env in self.execution_environment:
            try:
                self.logger.debug(
                    f"Setting up execution environment {execution_env} for service {service.service_name}"
                )
                # Call setup_environment with a single service instead of all services
                execution_env.setup_environment(
                    services_managers=[service],  # Pass single service as list
                    test_config=self.test_config,
                    global_config=self.global_config,
                    timestamp=timestamp,
                    plugin_manager=self.plugin_manager,
                )
                self.logger.debug(
                    f"Successfully set up execution environment {execution_env} for service {service.service_name}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to setup execution environment {execution_env} for service {service.service_name}: {e}"
                )

    def create_non_critical_command(self, command_lines: list) -> str:
        """Create a non-critical command block from a list of command lines.

        Non-critical commands are marked with a header comment so the entrypoint
        script can allow them to fail without aborting the entire execution.

        Args:
            command_lines: List of command line strings to combine.

        Returns:
            A single string with lines joined by newlines, prefixed by a
            non-critical marker comment. Trailing newlines are stripped.
        """
        # Strip trailing newlines from each line, then remove trailing empty entries
        stripped = [line.rstrip("\n") for line in command_lines]
        while stripped and not stripped[-1]:
            stripped.pop()
        body = "\n".join(stripped)
        return f"# PANTHER_NON_CRITICAL_COMMAND\n{body}"

    def generate_entrypoint_with_structured_args(
        self,
        service: IServiceManager,
        paths: dict[str, str],
        timestamp: str,
        output_path: Path,
        template_path: Path,
    ):
        """Generates an entrypoint script with properly structured and quoted command arguments.

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

        # Execution environment setup now happens BEFORE entrypoint generation
        # in generate_environment_services to ensure wrapper files exist when needed
        self.logger.debug(
            f"Execution environments were set up before entrypoint generation for service {service.service_name}"
        )

        # Apply network resolution to commands before processing
        finalized_commands = self._resolve_network_placeholders_in_commands(
            finalized_commands, service
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

        for phase, pcommand in processed_commands.items():
            if not isinstance(pcommand, list):
                self.logger.debug(
                    "Processing single command for service '%s' in phase '%s': %s",
                    service.service_name,
                    phase,
                    pcommand,
                )
            else:
                for command in pcommand:
                    self.logger.debug(
                        "Processing command for service '%s' in phase '%s': %s",
                        service.service_name,
                        phase,
                        command,
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

    def _do_teardown_environment(self) -> None:
        """Implementation of environment teardown for Docker Compose."""
        if hasattr(self, "lifecycle_manager") and self.lifecycle_manager:
            # Stop background monitoring if active
            self.remove_service_monitoring()
            self.lifecycle_manager.teardown_services()
        else:
            self.logger.warning(
                "Lifecycle manager not available for teardown, skipping service shutdown"
            )
            raise RuntimeError(
                "Lifecycle manager not available for teardown, cannot stop services"
            )

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """Initialize the Docker Compose environment."""
        # Only update output_dir if not already set or if it's different
        # This prevents path duplication when execution environments are present
        incoming_output_dir = Path(output_dir)

        if not hasattr(self, "output_dir") or self.output_dir != incoming_output_dir:
            self.output_dir = incoming_output_dir
            self.log_dirs = self.output_dir / "logs"

            # Reconstruct paths only if output_dir changed - use resolve() for absolute paths
            self.rendered_services_network_script_file_path = (
                self.output_dir / "entrypoint.sh"
            ).resolve()
            self.services_network_config_file_path = (
                self.output_dir / f"{self.env_sub_type}.generated.yml"
            ).resolve()
            self.rendered_services_network_config_file_path = (
                self.output_dir / f"{self.env_sub_type}.yml"
            ).resolve()

            self.logger.debug(
                f"Updated Docker Compose paths with output_dir: {self.output_dir}"
            )
            self.logger.debug(
                f"Resolved docker_compose.yml path: {self.rendered_services_network_config_file_path}"
            )

        # Always update these attributes
        self.event_manager = event_manager

        self.logger.debug(
            f"Initialized Docker Compose environment with config file: {self.services_network_config_file_path}"
        )

        if not hasattr(self, "test_config"):
            self.test_config = test_config
        if not hasattr(self, "global_config"):
            self.global_config = global_config

        # Override timeout from environment config
        self.timeout = self.env_config_to_test.deploy_timeout
        self.logger.debug(
            f"Deploy timeout set to {self.timeout}s from environment config"
        )

        # Auto-scale timeout when execution environments (strace, gdb, etc.)
        # are present, since debug images are significantly larger and slower
        # to start, especially under platform emulation (e.g. amd64 on ARM).
        if self.execution_environment:
            multiplier = getattr(
                self.env_config_to_test, "deploy_timeout_debug_multiplier", 2.0
            )
            if multiplier != 1.0:
                original_timeout = self.timeout
                self.timeout = int(self.timeout * multiplier)
                env_types = [
                    getattr(ee, "env_sub_type", type(ee).__name__)
                    for ee in self.execution_environment
                ]
                self.logger.info(
                    f"Execution environments detected ({env_types}): "
                    f"deploy timeout scaled {original_timeout}s -> {self.timeout}s "
                    f"(multiplier={multiplier})"
                )

        # Use a unique project name per test to prevent cross-test resource
        # conflicts.  The output directory basename is already unique per test
        # run, so we derive the project name from it and sanitize it for
        # Docker naming rules (lowercase alphanumeric + hyphens).
        experiment_name = str(self.output_dir).split("/")[-1]
        sanitized_name = re.sub(r"[^a-z0-9-]", "-", experiment_name.lower())
        sanitized_name = re.sub(r"^[^a-z0-9]+", "", sanitized_name)
        sanitized_name = re.sub(r"-+", "-", sanitized_name).rstrip("-")
        if sanitized_name:
            _reserved = {"default", "host", "bridge", "none"}
            if sanitized_name in _reserved:
                sanitized_name = f"panther-{sanitized_name}"
                self.logger.warning(
                    "Network name was Docker-reserved, prefixed: '%s'",
                    sanitized_name,
                )
            _max_len = 64
            if len(sanitized_name) > _max_len:
                sanitized_name = sanitized_name[:_max_len].rstrip("-")
                self.logger.warning(
                    "Network name truncated to %d chars: '%s'",
                    _max_len,
                    sanitized_name,
                )
            self.network_name = sanitized_name
            self.logger.debug(
                "Docker Compose project name set to '%s' (from output dir: %s)",
                self.network_name,
                experiment_name,
            )

        # Initialize lifecycle manager now that all required variables are set
        if hasattr(self, "services_managers") and self.services_managers:
            self.lifecycle_manager = DockerComposeLifecycleManager(
                services_managers=self.services_managers,
                network_name=self.network_name,
                config_file_path=self.rendered_services_network_config_file_path,
                output_dir=self.output_dir,  # Already a Path object
                timeout=self.timeout,
                docker_executor=self,  # Pass self for Docker command execution
                status_monitor=self,  # Pass self for status monitoring
                port_manager=self.port_manager,
                output_manager=self.output_manager,
                logger=self.logger,
            )
            self.logger.debug("Lifecycle manager initialized")
        else:
            self.logger.debug(
                "Lifecycle manager initialization deferred - services not yet available"
            )

    def handle_event(self, event):
        """Handle events for Docker Compose environment."""
        self.logger.debug(
            f"DockerCompose handle_event called with event: {getattr(event, 'name', 'unknown')} (type: {type(event).__name__})"
        )

        # Check for deployment completed event to start background monitoring
        if (
            hasattr(event, "get_full_name")
            and event.get_full_name() == "environment.deployment_completed"
        ):
            self.logger.info(f"Received deployment_completed event: {event}")
            self._start_background_monitoring_after_deployment()
        # Check for experiment completion events to stop background monitoring
        elif hasattr(event, "get_full_name") and event.get_full_name() in [
            "experiment.completed",
            "experiment.failed",
            "experiment.finished_early",
        ]:
            self.logger.info(
                f"Received experiment end event: {event.get_full_name()} - stopping background monitoring"
            )
            self._stop_background_monitoring_on_experiment_end()
        # Also check by event type name for broader compatibility
        elif (
            hasattr(event, "event_type")
            and hasattr(event.event_type, "value")
            and event.event_type.value in ["completed", "failed", "finished_early"]
        ):
            self.logger.info(
                f"Received experiment end event type: {event.event_type.value} - stopping background monitoring"
            )
            self._stop_background_monitoring_on_experiment_end()
        else:
            # Log all events to see what we're getting
            event_name = getattr(
                event, "get_full_name", lambda: getattr(event, "name", "unknown")
            )()
            self.logger.debug(f"Ignoring event: {event_name}")
        # No other special event handling needed beyond base class

    def on_event(self, event: BaseEvent):
        """IObserver interface method - delegates to handle_event."""
        self.handle_event(event)

    def _teardown_environment(self) -> None:
        """Perform Docker Compose specific teardown with background monitor cleanup."""
        self.logger.info("Tearing down Docker Compose environment")

        # Perform final output registration while containers are still running using output manager
        self.output_manager.perform_final_output_registration(self.services_managers)

        # Stop background monitoring if active
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info("Stopping background service monitoring...")
            self.background_monitor.stop_monitoring()

        if os.path.exists(self.rendered_services_network_config_file_path):
            try:
                self.lifecycle_manager.teardown_services()
            except Exception as e:
                self.logger.error(f"Error during Docker Compose teardown: {e}")

    def _get_service_log_directory(self, service_name: str) -> Path:
        """Get the log directory path for a specific service.

        This method delegates to the output manager for consistent path handling.
        """
        if hasattr(self, "output_manager") and self.output_manager:
            return self.output_manager.get_service_log_directory(service_name)
        else:
            # Fallback for cases where output manager isn't available
            return self.output_dir / "logs" / service_name

    def launch_environment_services(self) -> None:
        """Launch Docker Compose services using lifecycle manager.

        This method delegates to the lifecycle manager for service launch operations.
        """
        self.logger.info("Launching Docker Compose services")
        # Ensure lifecycle manager is initialized before use
        if not hasattr(self, "lifecycle_manager") or not self.lifecycle_manager:
            self._ensure_lifecycle_manager_initialized()

        if hasattr(self, "lifecycle_manager") and self.lifecycle_manager:
            self.deploy_services_monitoring()  # Deploy services first
            self.lifecycle_manager.launch_services()
        else:
            raise RuntimeError("Lifecycle manager not available for service launch")

    def deploy_services_monitoring(self) -> bool:
        """Deploy services in Docker Compose environment.

        For Docker Compose, services are already deployed when launched.
        This method handles any post-launch deployment tasks.

        Note: Background monitoring is now started after deployment completion
        via event handler to avoid race conditions.

        Returns:
            bool: True if services are successfully deployed and running
        """
        # Background monitoring will be started via deployment_completed event
        # to ensure containers are fully ready before health checks begin
        return True

    def remove_service_monitoring(self) -> None:
        """Remove service monitoring for Docker Compose environment.

        This method stops the background service monitor if it exists.
        """
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info(
                "Stopping background service monitoring for Docker Compose services"
            )
            self.background_monitor.stop_monitoring()
            self.background_monitor = None
        else:
            self.logger.debug(
                "No background service monitor to stop for Docker Compose services"
            )

    def _stop_background_monitoring_on_experiment_end(self) -> None:
        """Stop background monitoring when experiment ends.

        This method ensures monitoring threads are cleaned up when experiments
        complete, preventing hanging background monitoring loops.
        """
        if hasattr(self, "background_monitor") and self.background_monitor:
            self.logger.info(
                "Experiment ended - proactively stopping background monitoring"
            )
            try:
                self.background_monitor.stop_monitoring()
                self.background_monitor = None
                self.logger.info(
                    "Background monitoring stopped due to experiment completion"
                )
            except Exception as e:
                self.logger.warning(
                    f"Error stopping background monitoring on experiment end: {e}"
                )
        else:
            self.logger.debug("No background monitor active to stop on experiment end")

    def _start_background_monitoring_after_deployment(self) -> None:
        """Start background monitoring after deployment is completed.

        This method is called when deployment_completed event is received
        to ensure containers are fully ready before health checks begin.
        """
        enable_background = self.env_config_to_test.enable_background_monitoring

        if (
            enable_background
            and hasattr(self, "background_monitor")
            and self.background_monitor
        ):
            self.logger.info(
                "Background monitoring is already active for Docker Compose services"
            )
        elif enable_background:
            # Initialize background service monitor now that deployment is complete
            self.logger.info(
                "Starting background service monitoring for Docker Compose services after deployment completion"
            )
            self.background_monitor = BackgroundServiceMonitor(
                docker_compose_env=self,
                services=[sm.service_name for sm in self.services_managers],
                config=self.config.network_environment,
            )
            self.background_monitor.start_monitoring()
        else:
            self.logger.debug(
                "Background monitoring is disabled, skipping monitor startup"
            )

    def _ensure_lifecycle_manager_initialized(self) -> None:
        """Ensure lifecycle manager is initialized when needed.

        This method initializes the lifecycle manager if it hasn't been created yet
        and all required dependencies are available.
        """
        # Check if we have all required attributes for lifecycle manager initialization
        required_attrs = [
            "services_managers",
            "network_name",
            "rendered_services_network_config_file_path",
            "output_dir",
            "timeout",
            "port_manager",
            "output_manager",
            "logger",
        ]

        if missing_attrs := [
            attr for attr in required_attrs if not hasattr(self, attr)
        ]:
            self.logger.error(
                f"Cannot initialize lifecycle manager - missing attributes: {missing_attrs}"
            )
            raise RuntimeError(
                f"Missing required attributes for lifecycle manager: {missing_attrs}"
            )

        if not self.services_managers:
            raise RuntimeError(
                "Cannot initialize lifecycle manager - no services managers available"
            )

        # Initialize lifecycle manager
        self.logger.debug(
            f"Initializing lifecycle manager with config_file_path: {self.rendered_services_network_config_file_path}"
        )
        self.logger.debug(
            f"Initializing lifecycle manager with output_dir: {self.output_dir}"
        )

        self.lifecycle_manager = DockerComposeLifecycleManager(
            services_managers=self.services_managers,
            network_name=self.network_name,
            config_file_path=self.rendered_services_network_config_file_path,
            output_dir=self.output_dir,  # Already a Path object
            timeout=self.timeout,
            docker_executor=self,  # Pass self for Docker command execution
            status_monitor=self,  # Pass self for status monitoring
            port_manager=self.port_manager,
            output_manager=self.output_manager,
            logger=self.logger,
        )
        self.logger.debug("Lifecycle manager initialized on-demand")

    def _extract_service_environment_variables(self) -> dict:
        """Extract service environment variables using lifecycle manager.

        This method delegates to the lifecycle manager for environment variable extraction.
        """
        # Ensure lifecycle manager is initialized before use
        if not hasattr(self, "lifecycle_manager") or not self.lifecycle_manager:
            try:
                self._ensure_lifecycle_manager_initialized()
            except RuntimeError as e:
                # If initialization fails, use fallback
                self.logger.warning(
                    f"Failed to initialize lifecycle manager for environment variable extraction: {e}"
                )
                return {}

        if hasattr(self, "lifecycle_manager") and self.lifecycle_manager:
            return self.lifecycle_manager.extract_service_environment_variables()
        else:
            # Fallback for cases where lifecycle manager isn't available
            self.logger.warning(
                "Lifecycle manager not available for environment variable extraction"
            )
            return {}

    def _get_service_ip(self, service_name: str) -> str:
        """Get IP address for a service in Docker Compose environment.

        Docker Compose uses service names for internal DNS resolution,
        so we return the service name which Docker will resolve to the
        appropriate container IP.

        Args:
            service_name: Name of the service

        Returns:
            Service name (Docker DNS will resolve this)
        """
        # In Docker Compose, services can reach each other by service name
        # Docker's internal DNS handles the resolution
        return service_name

    def _resolve_network_placeholders_in_commands(
        self, commands: Dict[str, List[str]], service: IServiceManager
    ) -> Dict[str, List[str]]:
        """Resolve network placeholders in service commands.

        Args:
            commands: Dictionary of command lists by phase
            service: Service manager instance

        Returns:
            Commands with network placeholders resolved
        """
        try:
            # Create resolution context
            service_managers = {s.service_name: s for s in self.services_managers}
            context = self.network_resolver.create_resolution_context(
                "docker_compose", service_managers
            )

            # Populate service network information
            self.network_resolver.populate_service_network_info(context)

            # Resolve placeholders in each command phase
            resolved_commands = {}
            for phase, command_data in commands.items():
                if phase == "run_cmd" and isinstance(command_data, dict):
                    # Special handling for run_cmd dict structure
                    resolved_commands[phase] = {}
                    for key, value in command_data.items():
                        if key == "command_args" and isinstance(value, str):
                            # Resolve placeholders in command args
                            resolved_commands[phase][key] = (
                                self._resolve_placeholders_in_command(value, context)
                            )
                        elif key == "command_binary" and isinstance(value, str):
                            # Also resolve placeholders in command binary if present
                            resolved_commands[phase][key] = (
                                self._resolve_placeholders_in_command(value, context)
                            )
                        elif key == "working_dir" and isinstance(value, str):
                            # Resolve placeholders in working directory
                            resolved_commands[phase][key] = (
                                self._resolve_placeholders_in_command(value, context)
                            )
                        elif key == "environment" and isinstance(value, dict):
                            # Resolve placeholders in environment variables
                            resolved_env = {}
                            for env_key, env_value in value.items():
                                if isinstance(env_value, str):
                                    resolved_env[env_key] = (
                                        self._resolve_placeholders_in_command(
                                            env_value, context
                                        )
                                    )
                                else:
                                    resolved_env[env_key] = env_value
                            resolved_commands[phase][key] = resolved_env
                        else:
                            # Keep other fields as-is
                            resolved_commands[phase][key] = value
                else:
                    # Normal list processing for other phases
                    resolved_commands[phase] = []
                    if isinstance(command_data, list):
                        for command in command_data:
                            if isinstance(command, str):
                                resolved_command = (
                                    self._resolve_placeholders_in_command(
                                        command, context
                                    )
                                )
                                resolved_commands[phase].append(resolved_command)
                            else:
                                # Non-string commands pass through unchanged
                                resolved_commands[phase].append(command)
                    else:
                        # If it's not a list, log warning and keep as-is
                        self.logger.warning(
                            f"Unexpected command data type for phase {phase}: {type(command_data)}"
                        )
                        resolved_commands[phase] = command_data

            self.logger.debug(
                f"Resolved network placeholders for service {service.service_name}"
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
        """Resolve network placeholders in a single command string.

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

            self.logger.debug(f"Resolved command: {command} -> {resolved_command}")
            return resolved_command

        except Exception as e:
            self.logger.warning(
                f"Failed to resolve placeholders in command '{command}': {e}"
            )
            return command
