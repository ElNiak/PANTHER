from pathlib import Path
import os
import traceback
from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
    PicoquicShadowConfig,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin


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
class PicoquicShadowServiceManager(IImplementationManager):
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
        prepare(self, plugin_loader: Optional[PluginLoader] = None):
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
        self.logger.debug("Initializing Picoquic service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Picoquic configuration: %s", self.service_config_to_test)
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

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepares the Picoquic service manager by building the necessary Docker images.
        Args:
            plugin_loader (PluginLoader | None): An optional PluginLoader instance used to build Docker images.
        Raises:
            Any exceptions raised by the plugin_loader methods.
        """
        self.logger.debug("Preparing Picoquic service manager...")
        plugin_loader.build_docker_image_from_path(
            Path(
                os.path.join(
                    os.getcwd(),
                    "panther",
                    "plugins",
                    "services",
                    "Dockerfile",
                )
            ),
            "panther_base",
            "service",
        )
        plugin_loader.build_docker_image(
            self.get_implementation_name(),
            self.service_config_to_test.implementation.version,
        )

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

        # Build structured command arguments
        command_args = []

        # Add certificate parameters
        if "certificates" in params:
            command_args.append(params["certificates"]["cert_param"])
            command_args.append(params["certificates"]["cert_file"])
            command_args.append(params["certificates"]["key_param"])
            command_args.append(params["certificates"]["key_file"])

        # Add ticket file parameters for client
        if self.role == RoleEnum.client and "ticket_file" in params:
            command_args.append(params["ticket_file"]["param"])
            command_args.append(params["ticket_file"]["file"])

        # Add protocol parameters (ALPN)
        if "protocol" in params and "alpn" in params["protocol"]:
            command_args.append(params["protocol"]["alpn"]["param"])
            command_args.append(params["protocol"]["alpn"]["value"])

        # Add additional protocol parameters if available
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            command_args.append(params["protocol"]["additional_parameters"])

        # Add network interface if applicable
        if include_interface and "network" in params and "interface" in params["network"]:
            command_args.append(params["network"]["interface"]["param"])
            command_args.append(params["network"]["interface"]["value"])

        # Add initial version for client if specified
        if self.role == RoleEnum.client and "initial_version" in params:
            command_args.append("-v")
            command_args.append(params["initial_version"])

        # Add role-specific parameters
        if self.role == RoleEnum.server:
            # Add port for server
            if "network" in params and "port" in params["network"]:
                command_args.append("-p")
                command_args.append(str(params["network"]["port"]))
        elif self.role == RoleEnum.client:
            # Add target and port for client
            command_args.append(params["target"])
            command_args.append(str(params["network"]["port"]))

        # Add logging parameters
        if "logging" in params:
            command_args.append(">")
            command_args.append(params["logging"]["log_path"])
            command_args.append("2>")
            command_args.append(params["logging"]["err_path"])

        # Environment variables if needed
        env_vars = {}

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
