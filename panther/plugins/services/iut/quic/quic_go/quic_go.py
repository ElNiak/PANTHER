import os
from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="iut",
    name="quic_go",
    version="1.0.0",
    description="quic-go - A QUIC implementation in pure Go",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3", "datagrams"],
    external_dependencies=["docker"],
)
class QuicGoServiceManager(IImplementationManager):
    """
    QuicGoServiceManager is a class responsible for managing the quic-go service implementation.

    Attributes:
        service_config_to_test (QuicGoConfig): Configuration for the quic-go service to be tested.
        service_type (str): Type of the service.
        protocol (ProtocolConfig): Protocol configuration.
        implementation_name (str): Name of the implementation.
        logger (Logger): Logger instance for logging debug information.
        working_dir (str): Working directory for the service.
        role (RoleEnum): Role of the service (server or client).
        service_version (str): Version of the service.
        service_name (str): Name of the service.

    Methods:
        __init__(service_config_to_test, service_type, protocol, implementation_name, event_manager):
            Initializes the QuicGoServiceManager with the given configuration.
        generate_run_command():
            Generates the run command for the service.
        generate_post_run_commands():
            Generates post-run commands for the service.
        prepare(plugin_loader):
            Prepares the service manager for use by building Docker images.
        generate_deployment_commands():
            Generates deployment commands as a list for the service.
        __str__():
            Returns a string representation of the QuicGoServiceManager instance.
        __repr__():
            Returns a string representation of the QuicGoServiceManager instance.
    """

    def __init__(
        self,
        service_config_to_test: QuicGoConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self.logger.debug("Initializing QuicGo service manager for '%s'", implementation_name)
        self.logger.debug("Loaded QuicGo configuration: %s", self.service_config_to_test)
        self.initialize_commands()

    def generate_run_command(self):
        """
        Generates the run command for the quic-go service.

        This method constructs a complete run command configuration using
        the structured approach for proper quoting and escaping of all
        command arguments and environment variables.

        Returns:
            dict: The run command configuration with all necessary components.
        """
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        else:  # client
            params = self.service_config_to_test.implementation.version.client

        # Set working directory from params
        self.working_dir = params["binary"]["dir"]

        # Build command arguments as list
        command_args = self.generate_deployment_commands()

        # Environment variables for Go-specific settings
        env_vars = {
            "GODEBUG": "gctrace=1",
            "GOLOG": "INFO",
            "QUIC_GO_LOG_DIR": "/app/logs/quic_go",
        }

        # Add any protocol-specific environment variables
        if "environment" in params:
            for key, value in params["environment"].items():
                env_vars[key] = value

        # Try to render with structured template, fall back to original if needed
        try:
            template_name = f"{str(self.role.name)}_command_structured.jinja"
            rendered_command = self.render_template_with_structured_args(
                template_name, params, command_args, env_vars
            )
            # For structured templates, we'll use the rendered command as a string
            command_args = rendered_command
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

        return {
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

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return super().generate_post_run_commands() + ["cp -r /opt/quic-go/ /app/logs/quic_go/;"]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing quic-go service manager...")
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

    def generate_deployment_commands(self) -> list:
        """
        Generates deployment commands for the quic-go service based on its configuration and role.
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

        # Build structured command arguments
        command_args = []

        # Add certificate parameters if available
        if "certificates" in params:
            command_args.append(params["certificates"]["cert_param"])
            command_args.append(params["certificates"]["cert_file"])
            command_args.append(params["certificates"]["key_param"])
            command_args.append(params["certificates"]["key_file"])

        # Add protocol parameters
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            command_args.append(params["protocol"]["additional_parameters"])

        # Add network interface if applicable
        if include_interface and "network" in params and "interface" in params["network"]:
            command_args.append(params["network"]["interface"]["param"])
            command_args.append(params["network"]["interface"]["value"])

        # Add role-specific parameters
        if self.role == RoleEnum.server:
            # Add port for server
            if "network" in params and "port" in params["network"]:
                command_args.append("-p")
                command_args.append(str(params["network"]["port"]))
        elif self.role == RoleEnum.client:
            # Add target and port for client
            if params["target"] and "network" in params and "port" in params["network"]:
                command_args.append(
                    f"https://{params['target']}:{params['network']['port']}/index.html"
                )

        # Add logging parameters
        if "logging" in params:
            command_args.append(">")
            command_args.append(params["logging"]["log_path"])
            command_args.append("2>")
            command_args.append(params["logging"]["err_path"])

        # Environment variables if needed
        env_vars = {}

        # Return the command arguments as a list for consistent handling
        # Environment variables are handled separately in generate_run_command
        return command_args

    def __str__(self) -> str:
        return f"QuicGoServiceManager({self.__dict__})"

    def __repr__(self):
        return f"QuicGoServiceManager({self.__dict__})"
