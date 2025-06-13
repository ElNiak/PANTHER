from pathlib import Path
from typing import TYPE_CHECKING

from panther.plugins.services.iut.minip.ping_pong.config_schema import PingPongConfig
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin
from panther.core.utils.service_manager_utils import IUTServiceManagerMixin
from panther.core.utils import (
    ServiceCommandBuilder,
    ServiceTemplateRenderer,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
)

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type="iut",
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
    IUTServiceManagerMixin, ServiceManagerDockerMixin, ErrorHandlerMixin, IImplementationManager
):
    def __init__(
        self,
        service_config_to_test: PingPongConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )

        # Use standardized initialization from mixin
        self.standardized_initialization(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )

        # Set up IUT-specific attributes
        self.setup_iut_specific_attributes(protocol, service_config_to_test)

        # Initialize template renderer with plugin directory
        plugin_dir = Path(__file__).parent
        self.template_renderer = ServiceTemplateRenderer(plugin_dir)

        # Set Docker attributes for ServiceManagerDockerMixin
        self.docker_image_name = "ping_pong:latest"
        self.docker_file_path = plugin_dir / "Dockerfile"

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
            {
                "service_name": self.service_name,
                "role": self.role.name if hasattr(self.role, "name") else str(self.role),
            },
        )

        # Determine binary based on role
        if self.role == RoleEnum.server:
            command_binary = self.service_config_to_test.implementation.version.server.binary.name
        else:
            command_binary = self.service_config_to_test.implementation.version.client.binary.name

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

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        commands = super().generate_post_run_commands()
        commands.append("cp /opt/ping-pong/miniP_* /app/logs/miniP_* 2>/dev/null || true")
        return commands

    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
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

        # Build parameters based on role
        if self.role == RoleEnum.server:
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
        if self.role == RoleEnum.server:
            if "client_port" in params:
                builder.add_positional(f"client_port={params['client_port']}")
            if "client_addr" in params:
                builder.add_positional(f"client_addr={params['client_addr']}")

        # Add logging parameters
        if "logging" in params:
            builder.set_output_redirection(
                stdout=params["logging"]["log_path"], stderr=params["logging"]["err_path"]
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
        except Exception as e:
            self.logger.warning(
                "Failed to render structured template for service '%s': %s",
                self.service_config_to_test.name,
                e,
            )
            # Fallback to original template
            template_name = (
                f"{self.role.name if hasattr(self.role, 'name') else self.role}_command.jinja"
            )
            return self.render_commands(params, template_name)

    def __str__(self) -> str:
        return f"PingPongServiceManager({self.service_config_to_test})"

    def __repr__(self):
        return f"PingPongServiceManager({self.service_config_to_test})"
