"""Ping-Pong service implementation for MiniP protocol testing.

This module provides a ping-pong service implementation for testing
MiniP protocol functionality within the PANTHER framework.
"""

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from panther.config.core.models import ProtocolConfig, ProtocolRole
from panther.core.command_processor.builders import ServiceCommandBuilder
from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)
from panther.plugins.services.iut.minip.ping_pong.config_schema import PingPongConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type=PluginType.IUT,
    name="ping_pong",
    version="1.0.0",
    description="Ping-Pong implementation for MiniP protocol testing",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["minip"],
    capabilities=["ping_pong", "basic_networking"],
    external_dependencies=["docker"],
)
class PingPongServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    ErrorHandlerMixin,
    IImplementationManager,
    StringRepresentationMixin,
):
    """
    Service manager for Ping-Pong protocol implementation.
    """

    def __init__(
        self,
        service_config_to_test: PingPongConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
        global_config=None,
        **kwargs,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            global_config=global_config,
        )

        # Store global configuration
        self.global_config = global_config
        # Use the new template method for standard initialization
        self.standard_iut_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            plugin_dir=Path(__file__).parent,
        )

        # Cache plugin config for dual plugin config approach
        self._plugin_config = None

    def _get_plugin_config(self) -> Optional[PingPongConfig]:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.service_config_to_test.get_plugin_config(
                    PingPongConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                # Create default config
                self._plugin_config = PingPongConfig()
        return self._plugin_config

    def generate_pre_compile_commands(self):
        """
        Generates pre-compile commands using structured command building.
        """
        # Get base commands from parent
        base_commands = super().generate_pre_compile_commands()

        # Build commands using ServiceCommandBuilder
        builder = ServiceCommandBuilder(self.role)

        # Add IP resolution commands
        builder.add_command(
            f"TARGET_IP=$(getent hosts {self.service_targets} | awk '{{print $1}}')"
        )
        builder.add_command(
            f'echo "Resolved {self.service_targets} IP - $TARGET_IP" >> /app/logs/ivy_setup.log'
        )
        builder.add_command("IVY_IP=$(hostname -I | awk '{print $1}')")
        builder.add_command(
            f'echo "Resolved {self.service_name} IP - $IVY_IP" >> /app/logs/ivy_setup.log'
        )

        # Add function definitions
        # TODO: check from panther_ivy -> Wrong here
        builder.add_command("")
        builder.add_command("ip_to_hex() {")
        builder.add_command(
            '  echo "$1" | awk -F"." "{printf(\\"%02X%02X%02X%02X\\", $1, $2, $3, $4)}";'
        )
        builder.add_command("}")
        builder.add_command("")
        builder.add_command("ip_to_decimal() {")
        builder.add_command(
            '  echo "$1" | awk -F"." "{printf(\\"%.0f\\", ($1 * 256 * 256 * 256) + ($2 * 256 * 256) + ($3 * 256) + $4)}";'
        )
        builder.add_command("}")
        builder.add_command("")

        # Add IP conversion commands
        builder.add_command("TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP)")
        builder.add_command("IVY_IP_HEX=$(ip_to_decimal $IVY_IP)")
        builder.add_command(
            f'echo "Resolved {self.service_targets} IP in hex - $TARGET_IP_HEX" >> /app/logs/ivy_setup.log'
        )
        builder.add_command(
            f'echo "Resolved {self.service_name} IP in hex - $IVY_IP_HEX" >> /app/logs/ivy_setup.log'
        )

        return base_commands + builder.build()

    def generate_run_command(self):
        """
        Generates the run command using structured command building.
        """
        # Emit command generation started
        self.emit_command_generation_started("run")

        cmd_args = self.generate_deployment_commands()

        # Notify service event
        self.notify_service_event(
            "run_command_generated",
            service_id=self.implementation_name,
            service_name=self.service_name,
            details={
                "role": (
                    self.role.name if hasattr(self.role, "name") else str(self.role)
                ),
            },
        )

        # Determine binary based on role
        if self.role == ProtocolRole.SERVER:
            command_binary = (
                self.service_config_to_test.implementation.version.server.binary.name
            )
        else:
            command_binary = (
                self.service_config_to_test.implementation.version.client.binary.name
            )

        run_command = {
            "working_dir": self.working_dir,
            "command_binary": command_binary,
            "command_args": cmd_args,
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

        # Emit command generated
        self.emit_command_generated("run", str(run_command))

        return run_command

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get phase-based output patterns for Ping-Pong service.

        Returns:
            List of (output_type, filename_pattern) tuples organized by execution phases
        """
        return [
            # Pre-compile phase outputs
            ("pre_compile_stdout", "pre-compile/stdout.log"),
            ("pre_compile_stderr", "pre-compile/stderr.log"),
            # Compile phase outputs
            ("compile_stdout", "compile/stdout.log"),
            ("compile_stderr", "compile/stderr.log"),
            # Post-compile phase outputs
            ("post_compile_stdout", "post-compile/stdout.log"),
            ("post_compile_stderr", "post-compile/stderr.log"),
            # Pre-run phase outputs
            ("pre_run_stdout", "pre-run/stdout.log"),
            ("pre_run_stderr", "pre-run/stderr.log"),
            # Runtime phase outputs (main execution)
            ("runtime_stdout", "runtime/stdout.log"),
            ("runtime_stderr", "runtime/stderr.log"),
            # Post-run phase outputs
            ("post_run_stdout", "post-run/stdout.log"),
            ("post_run_stderr", "post-run/stderr.log"),
            # Test phase outputs
            ("test_stdout", "test/stdout.log"),
            ("test_stderr", "test/stderr.log"),
            # Artifacts - protocol-specific files organized by type
            ("minip_logs", "artifacts/miniP_*.log"),
            ("ping_pong_data", "artifacts/ping_pong_*.dat"),
            ("network_trace", "artifacts/{service_name}_trace.pcap"),
            ("ivy_setup", "artifacts/ivy_setup.log"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self):
        """
        Generates post-run commands with phase-based output organization.
        """
        commands = super().generate_post_run_commands()
        # Create artifacts directory
        commands.append("mkdir -p /app/logs/artifacts;")
        # Copy MiniP logs to artifacts (not root logs)
        commands.append(
            "cp /opt/ping-pong/miniP_* /app/logs/artifacts/ 2>/dev/null || true"
        )
        # Copy any ping-pong specific data files
        commands.append(
            "find /tmp -name 'ping_pong_*.dat' -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;"
        )
        # Copy ivy setup logs to artifacts
        commands.append(
            "cp /app/logs/ivy_setup.log /app/logs/artifacts/ 2>/dev/null || true"
        )
        return commands

    def _do_prepare(self, plugin_manager: "Optional[PluginManager]" = None):
        """
        Simplified prepare method - just delegate to the enhanced mixin.

        The ServiceManagerDockerMixin now handles:
        - Building base image only once per experiment
        - Building service-specific image
        - Proper event emission
        - Error handling
        - Command initialization (if initialize_commands exists)

        Args:
            plugin_manager: Optional plugin manager for Docker operations
        """
        super().prepare(plugin_manager)

    def generate_deployment_commands(self) -> str:
        """
        Generates deployment commands using ServiceCommandBuilder and ServiceTemplateRenderer.
        """
        self.logger.debug(
            "Generating deployment commands for service: %s with service parameters: %s",
            self.service_name,
            self.service_config_to_test,
        )

        self.logger.debug(
            "Role: %s, Version: %s",
            self.role.name if hasattr(self.role, "name") else self.role,
            self.service_version,
        )

        # Get plugin config
        plugin_config = self._get_plugin_config()

        # Build parameters based on role - check plugin_config first
        if (
            hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            # Use dictionary access for plugin_config
            plugin_dict = self.service_config_to_test.plugin_config
            if self.role == ProtocolRole.SERVER:
                params = plugin_dict.get("server", {})
            else:
                params = plugin_dict.get("client", {})
        elif plugin_config and hasattr(plugin_config, "version"):
            # Fall back to typed config
            if self.role == ProtocolRole.SERVER:
                params = (
                    plugin_config.version.server
                    if hasattr(plugin_config.version, "server")
                    else {}
                )
            else:
                params = (
                    plugin_config.version.client
                    if hasattr(plugin_config.version, "client")
                    else {}
                )
        else:
            # Final fallback to original approach
            if self.role == ProtocolRole.SERVER:
                params = self.service_config_to_test.implementation.version.server
            else:
                params = self.service_config_to_test.implementation.version.client

        params["target"] = "$TARGET_IP"
        self.working_dir = params["binary"]["dir"]

        # Use ServiceCommandBuilder with role
        builder = ServiceCommandBuilder(self.role)

        # Add seed parameter if available
        if "seed" in params:
            builder.add_positional(f"seed={params['seed']}")

        # Add server and client ports/addresses if available
        if "server_port" in params:
            builder.add_positional(f"server_port={params['server_port']}")
        if "server_addr" in params:
            builder.add_positional(f"server_addr={params['server_addr']}")

        # Add role-specific parameters
        if self.role == ProtocolRole.SERVER:
            if "client_port" in params:
                builder.add_positional(f"client_port={params['client_port']}")
            if "client_addr" in params:
                builder.add_positional(f"client_addr={params['client_addr']}")

        # Add logging parameters
        if "logging" in params:
            builder.set_output_redirection(
                stdout=params["logging"]["log_path"],
                stderr=params["logging"]["err_path"],
            )

        # Build command arguments and environment
        command_args = builder.build_args()
        env_vars = builder.build_env()

        # Try to render the template with structured arguments
        try:
            cmd = self.template_renderer.render_structured_command(
                self.role.name if hasattr(self.role, "name") else str(self.role),
                params,
                command_args,
                env_vars,
            )
            return cmd.command
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Failed to render structured template for service '%s': %s",
                self.service_config_to_test.name,
                e,
            )
            # Fallback to original template
            template_name = f"{self.role.name if hasattr(self.role, 'name') else self.role}_command.jinja"
            return self.render_commands(params, template_name)
