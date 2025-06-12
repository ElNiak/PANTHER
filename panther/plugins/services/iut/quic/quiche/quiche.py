# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

import os
from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="iut",
    name="quiche",
    version="1.0.0",
    description="Quiche - Cloudflare's implementation of QUIC and HTTP/3 in Rust",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3", "qlog"],
    external_dependencies=["docker"],
)
class QuicheServiceManager(IImplementationManager):
    """
    QuicheServiceManager is a class responsible for managing the Quiche service implementation.

    Attributes:
        service_config_to_test (QuicheConfig): Configuration for the Quiche service to be tested.
        service_type (str): Type of the service.
        protocol (ProtocolConfig): Protocol configuration.
        implementation_name (str): Name of the implementation.
        logger (Logger): Logger instance for logging debug information.
        working_dir (str): Working directory for the service.
        role (RoleEnum): Role of the service (server or client).
        service_version (str): Version of the service.
        service_name (str): Name of the service.

    Methods:
        __init__(service_config_to_test, service_type, protocol, implementation_name):
            Initializes the QuicheServiceManager with the given configuration, service type, protocol, and implementation name.
        generate_run_command():
            Generates the run command for the service.
        generate_post_run_commands():
            Generates post-run commands for the service.
        prepare(plugin_loader):
            Prepares the service manager for use by building Docker images.
        generate_deployment_commands():
        __str__():
            Returns a string representation of the QuicheServiceManager instance.
        __repr__():
            Returns a string representation of the QuicheServiceManager instance.
    """

    def __init__(
        self,
        service_config_to_test: QuicheConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self.logger.debug("Initializing Quiche service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Quiche configuration: %s", self.service_config_to_test)
        self.initialize_commands()

    def generate_run_command(self):
        """
        Generates the run command for the Quiche service.

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

        # Environment variables
        env_vars = {
            "RUST_LOG": "quiche=trace",
            "QUICHE_LOG_DIR": "/app/logs/quiche",
            "RUST_BACKTRACE": "1",
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
        return super().generate_post_run_commands() + ["cp -r /opt/quiche/ /app/logs/quiche/;"]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing Quiche service manager...")
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
        Generates deployment commands for the QUIC service based on the role and service configuration.
        This method constructs the necessary deployment commands using structured arguments for proper escaping.
        It includes network interface parameters conditionally based on the environment and role (server or client).

        Returns:
            list: The command arguments as a list for proper handling.

        Raises:
            Exception: If there is an error rendering the command template.

        Logs:
            Various debug information including service name, service parameters, role, version,
            and parameters for the command template.
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

        # Add certificate parameters
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

        # Add version if specified
        if "initial_version" in params:
            command_args.append("--wire-version")
            command_args.append(params["initial_version"])

        # Add role-specific parameters
        if self.role == RoleEnum.server:
            if "network" in params and "destination" in params["network"]:
                command_args.append(params["network"]["destination"]["param"])
                command_args.append(
                    f"{params['network']['destination']['value']}:{params['network']['port']}"
                )
        elif self.role == RoleEnum.client:
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
        env_vars = {}  # Add any required environment variables here

        # Return the command arguments as a list for consistent handling
        # Environment variables are handled separately in generate_run_command
        return command_args

    def __str__(self) -> str:
        return f"QuicheServiceManager({self.__dict__})"

    def __repr__(self):
        return f"QuicheServiceManager({self.__dict__})"
