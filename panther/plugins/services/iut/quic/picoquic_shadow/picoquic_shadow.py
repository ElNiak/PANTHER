"""PicoQUIC Shadow service implementation for PANTHER framework.

This module provides a PicoQUIC implementation optimized for use with
the Shadow network simulator environment.
"""

import traceback
from typing import TYPE_CHECKING

from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import PicoquicShadowConfig
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin
from panther.core.utils.command_builder import ServiceCommandBuilder
from panther.core.utils.template_renderer import ServiceTemplateRenderer
from panther.core.utils.docker_operations_mixin import ServiceManagerDockerMixin
from panther.core.exceptions import ErrorHandlerMixin

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type="iut",
    name="picoquic_shadow",
    version="1.0.0",
    description="PicoQUIC Shadow - PicoQUIC implementation for Shadow network simulator",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "shadow_ns"],
    external_dependencies=["docker"],
)
class PicoquicShadowServiceManager(
    IImplementationManager, ServiceManagerDockerMixin, ErrorHandlerMixin
):
    """
    PicoquicShadowServiceManager is a service manager for handling Picoquic services.
    This class is responsible for initializing the service manager, generating various commands required for the service lifecycle, and preparing the service manager for use.
    Methods:
        __init__(self, service_config_to_test: PicoquicShadowConfig, service_type: str, protocol: ProtocolConfig, implementation_name: str):
            Initializes the PicoquicShadowServiceManager with the given configuration, service type, protocol, and implementation name.
        get_service_name(self) -> str:
            Returns the name of the service.
        generate_pre_compile_commands(self):
        generate_compile_commands(self):
        generate_pre_run_commands(self):
        generate_run_command(self):
        generate_post_run_commands(self):
        prepare(self, plugin_manager: Optional[PluginManager] = None):
            Prepares the service manager for use.
        generate_deployment_commands(self) -> str:
    """

    def __init__(
        self,
        service_config_to_test: PicoquicShadowConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        ServiceManagerDockerMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)

        self.logger.debug("Initializing Picoquic service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Picoquic configuration: %s", self.service_config_to_test)

        # Initialize command builder and template renderer
        self.command_builder = ServiceCommandBuilder()
        self.template_renderer = ServiceTemplateRenderer()

        self.initialize_commands()

    def get_service_name(self) -> str:
        return self.service_name

    def generate_pre_compile_commands(self):
        """
        Generates pre-compile commands.
        """
        return super().generate_pre_compile_commands() + []

    def generate_compile_commands(self):
        """
        Generates compile commands.
        """
        return super().generate_compile_commands() + []

    def generate_pre_run_commands(self):
        """
        Generates pre-run commands.
        """
        return super().generate_pre_run_commands() + []

    def generate_run_command(self):
        """
        Generates the run command.
        """
        cmd_args = self.generate_deployment_commands()
        return {
            "working_dir": self.working_dir,
            "command_binary": (
                self.service_config_to_test.implementation.version.server.binary.name
                if self.role == RoleEnum.server
                else self.service_config_to_test.implementation.version.client.binary.name
            ),
            "command_args": cmd_args,
            "timeout": self.service_config_to_test.timeout,
            "command_env": {},
        }

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return super().generate_post_run_commands() + [
            "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;"
        ]

    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
        """
        Prepares the Picoquic service manager by building the necessary Docker images.
        Args:
            plugin_manager (Any | None): An optional PluginManager instance used to build Docker images.
        Raises:
            Any exceptions raised by the plugin_manager methods.
        """
        self.logger.debug("Preparing Picoquic service manager...")
        try:
            # Use the mixin's prepare method for common initialization
            super().prepare(plugin_manager)

            # Build Docker images using the mixin methods
            self.build_docker_image_with_manager(plugin_manager, "panther_base", "service")

            # Extract simple version string from complex version object
            version_obj = self.service_config_to_test.implementation.version
            if hasattr(version_obj, "version"):
                version = version_obj.version
            elif hasattr(version_obj, "name"):
                version = version_obj.name
            elif isinstance(version_obj, str):
                version = version_obj
            else:
                version = "latest"

            self.build_docker_image_with_manager(
                plugin_manager,
                self.get_implementation_name(),
                version,
            )
        except Exception as e:
            self.handle_error(e, "preparing Picoquic service manager")

    def generate_deployment_commands(self) -> str:
        """
        Generates deployment commands for the service based on its configuration and role.
        This method constructs the necessary deployment commands using structured arguments
        for proper escaping and handling of special characters.

        Returns:
            str: The rendered deployment command string.

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

        # Build parameters for the command template - initialize with default empty dict
        params = {}
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        # For the client, include target and message if available
        elif self.role == RoleEnum.client:
            params = self.service_config_to_test.implementation.version.client
        else:
            # Default case - this should not happen but provides safety
            self.logger.warning("Unknown role: %s, using empty parameters", self.role)

        params["target"] = self.service_config_to_test.protocol.target

        self.logger.debug("Parameters for command template: %s", params)
        self.logger.debug("Role: %s", self.role)
        self.working_dir = params["binary"]["dir"]

        # Conditionally include network interface parameters
        if not include_interface:
            params["network"].pop("interface", None)

        # Use ServiceCommandBuilder to build structured command arguments
        builder = self.command_builder

        # Add certificate parameters
        if "certificates" in params:
            builder.add_flag_with_value(
                params["certificates"]["cert_param"], params["certificates"]["cert_file"]
            )
            builder.add_flag_with_value(
                params["certificates"]["key_param"], params["certificates"]["key_file"]
            )

        # Add ticket file parameters for client
        if self.role == RoleEnum.client and "ticket_file" in params:
            builder.add_flag_with_value(
                params["ticket_file"]["param"], params["ticket_file"]["file"]
            )

        # Add protocol parameters (ALPN)
        if "protocol" in params and "alpn" in params["protocol"]:
            builder.add_flag_with_value(
                params["protocol"]["alpn"]["param"], params["protocol"]["alpn"]["value"]
            )

        # Add additional protocol parameters if available
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            builder.add_positional(params["protocol"]["additional_parameters"])

        # Add network interface if applicable
        if include_interface and "network" in params and "interface" in params["network"]:
            builder.add_flag_with_value(
                params["network"]["interface"]["param"], params["network"]["interface"]["value"]
            )

        # Add initial version for client if specified
        if self.role == RoleEnum.client and "initial_version" in params:
            builder.add_flag_with_value("-v", params["initial_version"])

        # Add role-specific parameters
        if self.role == RoleEnum.server:
            # Add port for server
            if "network" in params and "port" in params["network"]:
                builder.add_flag_with_value("-p", str(params["network"]["port"]))
        elif self.role == RoleEnum.client:
            # Add target and port for client
            builder.add_positional(params["target"])
            builder.add_positional(str(params["network"]["port"]))

        # Add logging parameters
        if "logging" in params:
            builder.set_output_redirection(
                stdout=params["logging"]["log_path"], stderr=params["logging"]["err_path"]
            )

        # Environment variables if needed
        env_vars = {}

        # Build command arguments
        command_args = builder.build()

        # Try to render the template with structured arguments
        try:
            template_name = f"{str(self.role.name)}_command_structured.jinja"
            return self.render_template_with_structured_args(
                template_name, params, command_args, env_vars
            )
        except Exception as e:
            self.logger.warning(
                "Failed to render structured template for service '%s': %s",
                self.service_config_to_test.name,
                e,
            )
            try:
                # Fallback to original template
                template_name = f"{str(self.role.name)}_command.jinja"
                return self.render_commands(params, template_name)
            except Exception as e2:
                self.logger.error(
                    "Failed to render fallback command template for service '%s': %s\n%s",
                    self.service_config_to_test.name,
                    e2,
                    traceback.format_exc(),
                )
                raise e2
