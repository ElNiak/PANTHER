# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

import os
from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class QuantServiceManager(IImplementationManager):
    """
    QuantServiceManager is a class responsible for managing the QUIC service implementation using the Quant library.
    It extends the IImplementationManager and provides methods to initialize, prepare, and generate commands for running and deploying the service.
    Attributes:
        service_config_to_test (QuantConfig): The configuration for the Quant service to be tested.
        service_type (str): The type of service being managed.
        protocol (ProtocolConfig): The protocol configuration.
        implementation_name (str): The name of the implementation.
    Methods:
        __init__(self, service_config_to_test: QuantConfig, service_type: str, protocol: ProtocolConfig, implementation_name: str):
            Initializes the QuantServiceManager with the provided configuration, service type, protocol, and implementation name.
        generate_run_command(self):
            Generates the run command for the service.
        generate_post_run_commands(self):
            Generates post-run commands for the service.
        prepare(self, plugin_loader: PluginLoader | None = None):
            Prepares the service manager for use, including building Docker images.
        generate_deployment_commands(self) -> list[str]:
            Generates a list of command arguments for deployment.
        __str__(self) -> str:
            Returns a string representation of the QuantServiceManager instance.
        __repr__(self):
            Returns a detailed string representation of the QuantServiceManager instance.
    """

    def __init__(
        self,
        service_config_to_test: QuantConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self.logger.debug("Initializing Quant service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Quant configuration: %s", self.service_config_to_test)
        self.initialize_commands()

    def generate_run_command(self):
        """
        Generates the run command for the quant service.

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

        self.working_dir = params["binary"]["dir"]

        # Build command arguments and environment variables
        command_args = self.generate_deployment_commands()

        # Environment variables
        env_vars = {
            "QUANT_LOG_LEVEL": "5",  # Default log level
            "QUANT_DEBUG": (
                "1"
                if self.service_config_to_test.implementation.version.parameters.get("debug", False)
                else "0"
            ),
        }

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
        return super().generate_post_run_commands() + ["cp -r /opt/quant/bin /app/logs/quant/;"]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing Quant service manager...")
        plugin_loader.build_docker_image_from_path(
            Path(
                os.path.join(
                    self._plugin_dir,
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

        # Add protocol parameters
        if "protocol" in params and params["protocol"]:
            proto = params["protocol"]
            if "additional_parameters" in proto and proto["additional_parameters"]:
                # Split additional parameters into separate arguments
                additional_params = self.build_command_args(proto["additional_parameters"])
                cmd_args.extend(additional_params)

        # Add network interface if specified
        if "network" in params and params["network"]:
            network = params["network"]
            if "interface" in network and network["interface"]:
                cmd_args.extend([network["interface"]["param"], network["interface"]["value"]])

            # Add port for server or as part of URL for client
            if self.role == RoleEnum.server:
                cmd_args.extend(["-p", str(network["port"])])
                cmd_args.extend(["-v", "5"])  # Verbose output

        # Add initial version if specified
        if "initial_version" in params and params["initial_version"]:
            cmd_args.extend(["-e", params["initial_version"]])

        # Add target URL for client
        if self.role == RoleEnum.client:
            target = self.service_config_to_test.protocol.target
            port = params["network"]["port"]
            cmd_args.append(f"https://{target}:{port}/index.html")

        # Add logging redirection
        if "logging" in params and params["logging"]:
            cmd_args.extend(
                [">", params["logging"]["log_path"], "2>", params["logging"]["err_path"]]
            )

        self.logger.debug("Generated command arguments: %s", cmd_args)
        return cmd_args

    def __str__(self) -> str:
        return f"QuantServiceManager({self.__dict__})"

    def __repr__(self):
        return f"QuantServiceManager({self.__dict__})"
