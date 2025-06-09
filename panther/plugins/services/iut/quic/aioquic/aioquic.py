# PANTHER-SCP/panther/plugins/services/implementations/aioquic_rfc9000/service_manager.py

import os
from panther.plugins.services.iut.quic.aioquic.config_schema import AioquicConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class AioquicServiceManager(IImplementationManager):
    """
    Manages the Aioquic service implementation for QUIC protocol testing.

    This manager handles initialization, deployment, and execution of Aioquic
    services in both client and server roles. It provides capabilities for
    generating properly structured run commands, preparing Docker environments,
    and handling post-run operations.

    The manager supports:
    - Dynamic command generation based on client/server roles
    - Structured command argument handling for proper escaping
    - Docker environment preparation and image building
    - Environment variable configuration
    - Certificate and security parameter management
    - Network interface and protocol configuration

    Attributes:
        working_dir (str): The working directory for the service
        service_config_to_test (AioquicConfig): Configuration for the Aioquic service
        service_type (str): Type of service being managed
        protocol (ProtocolConfig): Protocol configuration
        implementation_name (str): Name identifier for this implementation
        logger: Logger for the service manager

    Inherits:
        IImplementationManager: Base class for all implementation managers
    """

    def __init__(
        self,
        service_config_to_test: AioquicConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self.logger.debug("Initializing Aioquic service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Aioquic configuration: %s", self.service_config_to_test)
        self.initialize_commands()

    def generate_run_command(self):
        """
        Generates the run command for the aioquic service.

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
            "PYTHONPATH": "/opt/aioquic",
            "PYTHONUNBUFFERED": "1",  # Ensure python output is unbuffered
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
                "Failed to use structured template for %s: %s. ", self.service_name, e
            )
            # Keep command_args as is if the structured template fails

        return {
            "working_dir": self.working_dir,
            "command_binary": params["binary"]["name"],
            "command_args": command_args,
            "timeout": self.service_config_to_test.timeout,
            "command_env": env_vars,
        }

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return super().generate_post_run_commands() + [
            "cp /opt/aioquic/aioquicdemo /app/logs/aioquicdemo;"
        ]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing Aioquic service manager...")
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
        Generates a structured list of deployment command arguments for the QUIC service.

        This method constructs the command arguments using the structured approach,
        creating a list of arguments rather than concatenating strings, which
        ensures proper escaping and handling of special characters.

        Returns:
            list: The list of command arguments.
        """
        self.logger.debug(
            "Generating deployment commands for service: %s with service parameters: %s",
            self.service_name,
            self.service_config_to_test,
        )

        # Get appropriate parameters based on role
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        else:  # client
            params = self.service_config_to_test.implementation.version.client

        # Initialize the command argument list
        cmd_args = []

        # Add certificate parameters
        if "certificates" in params and params["certificates"]:
            certs = params["certificates"]
            if "cert_param" in certs and "cert_file" in certs:
                cmd_args.extend([certs["cert_param"], certs["cert_file"]])
            if "key_param" in certs and "key_file" in certs:
                cmd_args.extend([certs["key_param"], certs["key_file"]])

        # Add ticket file parameters for client
        if self.role == RoleEnum.client and "ticket_file" in params:
            ticket = params["ticket_file"]
            if "param" in ticket and "file" in ticket:
                cmd_args.extend([ticket["param"], ticket["file"]])

        # Add protocol parameters (ALPN)
        if "protocol" in params and params["protocol"]:
            proto = params["protocol"]
            if "alpn" in proto and proto["alpn"]:
                cmd_args.extend([proto["alpn"]["param"], proto["alpn"]["value"]])

            # Add additional parameters
            if "additional_parameters" in proto and proto["additional_parameters"]:
                # Split additional parameters into separate arguments
                additional_params = self.build_command_args(proto["additional_parameters"])
                cmd_args.extend(additional_params)

        # Add network interface if specified
        if "network" in params and params["network"]:
            network = params["network"]
            if "interface" in network and network["interface"]:
                cmd_args.extend([network["interface"]["param"], network["interface"]["value"]])

        # Add initial version for client if specified
        if self.role == RoleEnum.client and "initial_version" in params:
            cmd_args.extend(["-v", params["initial_version"]])

        # Add target and port
        if self.role == RoleEnum.client:
            target = self.service_config_to_test.protocol.target
            port = params["network"]["port"]
            cmd_args.extend([target, str(port)])
        else:  # server
            cmd_args.extend(["-p", str(params["network"]["port"])])

        # Add logging redirection
        if "logging" in params and params["logging"]:
            cmd_args.extend(
                [">", params["logging"]["log_path"], "2>", params["logging"]["err_path"]]
            )

        self.logger.debug("Generated command arguments: %s", cmd_args)
        return cmd_args

    def __str__(self) -> str:
        return f"AioquicServiceManager({self.__dict__})"

    def __repr__(self):
        return f"AioquicServiceManager({self.__dict__})"
