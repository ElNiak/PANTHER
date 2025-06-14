# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

from pathlib import Path
from typing import TYPE_CHECKING

from panther.core.command_processor.command_builder import ServiceCommandBuilder
from panther.core.utils import ErrorHandlerMixin, ServiceManagerDockerMixin
from panther.core.utils.service_manager_utils import IUTServiceManagerMixin
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.services.iut.quic.mvfst.config_schema import MvfstConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type="iut",
    name="mvfst",
    version="1.0.0",
    description="MVFST - Facebook's implementation of QUIC transport protocol",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "congestion_control"],
    external_dependencies=["docker"],
)
class MvfstServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
    IImplementationManager,
):
    def __init__(
        self,
        service_config_to_test: MvfstConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )
        # Use the new template method for standard initialization
        self.standard_iut_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            plugin_dir=Path(__file__).parent,
        )

    def generate_run_command(self):
        """
        Generates the run command for the MVFST service.

        This method constructs a complete run command configuration using
        the structured approach for proper quoting and escaping of all
        command arguments and environment variables.

        Returns:
            dict: The run command configuration with all necessary components.
        """
        # Emit command generation started
        self.emit_command_generation_started("run")

        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        else:  # client
            params = self.service_config_to_test.implementation.version.client

        # Set working directory from params
        self.working_dir = params["binary"]["dir"]

        # Build command arguments as list
        command_args = self.generate_deployment_commands()

        # Environment variables
        env_vars = {
            "LD_LIBRARY_PATH": "/opt/mvfst/lib",
            "MVFST_LOG_DIR": "/app/logs/mvfst",
        }

        # Add any protocol-specific environment variables
        if "environment" in params:
            for key, value in params["environment"].items():
                env_vars[key] = value

        # Try to render with structured template, fall back to original if needed
        try:
            cmd = self.template_renderer.render_structured_command(
                self.role.name, params, command_args, env_vars
            )
            # For structured templates, we'll use the rendered command as a string
            command_args = cmd.command
        except Exception as e:
            self.logger.warning(
                "Failed to render structured template for service '%s': %s",
                self.service_config_to_test.name,
                e,
            )
            # Use fallback template if structured fails
            try:
                template_name = f"{str(self.role.name)}_command.jinja"
                command_args = self.render_commands(params, template_name)
            except Exception as e2:
                self.logger.error(
                    "Failed to render command template for service '%s': %s",
                    self.service_config_to_test.name,
                    e2,
                )
                # Use the command arguments as list if template rendering fails
                pass

        run_command = {
            "working_dir": self.working_dir,
            "command_binary": (
                self.service_config_to_test.implementation.version.server.binary.name
                if self.role == RoleEnum.server
                else self.service_config_to_test.implementation.version.client.binary.name
            ),
            "command_args": command_args,
            "timeout": self.service_config_to_test.timeout,
            "command_env": env_vars,
        }

        # Notify service event
        self.notify_service_event(
            "run_command_generated",
            {
                "service_name": self.service_name,
                "role": self.role.name
                if hasattr(self.role, "name")
                else str(self.role),
            },
        )

        # Emit command generated
        self.emit_command_generated("run", str(run_command))

        return run_command

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return super().generate_post_run_commands() + [
            "cp /opt/mvfst/picoquicdemo /app/logs/picoquicdemo;"
        ]

    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
        """
        Prepare the service manager for use.

        The ServiceManagerDockerMixin handles all Docker-related preparation including:
        - Building base images
        - Building service-specific images
        - Setting up Docker environments
        - Initializing commands
        """
        super().prepare(plugin_manager)

    def generate_deployment_commands(self) -> list:
        """
        Generates deployment commands for the MVFST service based on its configuration and role.
        This method constructs the necessary deployment commands using structured arguments
        for proper escaping and handling of special characters.

        Returns:
            list: The command arguments as a list for proper handling.

        Raises:
            Exception: If there is an error rendering the command template.
        """
        self.logger.debug(
            "Generating deployment commands for service: %s with service parameters: %s",
            self.service_name,
            self.service_config_to_test,
        )

        self.logger.debug("Role: %s, Version: %s", self.role, self.service_version)

        # Determine if network interface parameters should be included based on environment
        include_interface = True

        # Build parameters for the command template
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        # For the client, include target and message if available
        elif self.role == RoleEnum.client:
            params = self.service_config_to_test.implementation.version.client

        params["target"] = self.service_config_to_test.protocol.target

        self.logger.debug("Parameters for command template: %s", params)
        self.logger.debug("Role: %s", self.role)
        self.working_dir = params["binary"]["dir"]

        # Conditionally include network interface parameters
        if not include_interface:
            params["network"].pop("interface", None)
        else:
            # Certificate generation handled via Docker build process
            # TODO: move certificate generation to Dockerfile for better consistency
            pass

        # Use ServiceCommandBuilder to build structured command arguments
        builder = ServiceCommandBuilder(self.role)

        # Add certificate parameters if available
        if "certificates" in params:
            builder.add_flag_with_value(
                params["certificates"]["cert_param"],
                params["certificates"]["cert_file"],
            )
            builder.add_flag_with_value(
                params["certificates"]["key_param"], params["certificates"]["key_file"]
            )

        # Add protocol parameters
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            builder.add_positional(params["protocol"]["additional_parameters"])

        # Add network interface if applicable
        if (
            include_interface
            and "network" in params
            and "interface" in params["network"]
        ):
            builder.add_flag_with_value(
                params["network"]["interface"]["param"],
                params["network"]["interface"]["value"],
            )

        # Add role-specific parameters
        if self.role == RoleEnum.server:
            # Add server-specific parameters
            if "network" in params and "port" in params["network"]:
                builder.add_flag_with_value("-p", str(params["network"]["port"]))
        elif self.role == RoleEnum.client:
            # Add client-specific parameters including target and port
            if params["target"] and "network" in params and "port" in params["network"]:
                builder.add_positional(
                    f"https://{params['target']}:{params['network']['port']}/index.html"
                )

        # Add logging parameters using output redirection
        if "logging" in params:
            builder.set_output_redirection(
                stdout=params["logging"]["log_path"],
                stderr=params["logging"]["err_path"],
            )

        # Return the command arguments as a list for consistent handling
        # Environment variables are handled separately in generate_run_command
        return builder.build()

    def __str__(self) -> str:
        return f"MvfstServiceManager({self.__dict__})"

    def __repr__(self):
        return f"MvfstServiceManager({self.__dict__})"
