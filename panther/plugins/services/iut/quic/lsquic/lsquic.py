# PANTHER-SCP/panther/plugins/services/implementations/lsquic_rfc9000/service_manager.py

import os
from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="iut",
    name="lsquic",
    version="1.0.0",
    description="LSQUIC - LiteSpeed's QUIC and HTTP/3 implementation",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3", "push"],
    external_dependencies=["docker"],
)
class LsquicServiceManager(IImplementationManager):
    def __init__(
        self,
        service_config_to_test: LsquicConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self.logger.debug("Initializing Lsquic service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Lsquic configuration: %s", self.service_config_to_test)
        self.initialize_commands()

    def generate_run_command(self):
        """
        Generates the run command for the LSQUIC service.

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

        # Build command arguments as list
        command_args = self.generate_deployment_commands()

        # Environment variables
        env_vars = {
            "LD_LIBRARY_PATH": "/opt/lsquic/lib",
            "LSQUIC_LOGS_DIR": "/app/logs/lsquic",
        }

        # Add any additional environment variables from config
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
        return super().generate_post_run_commands() + ["cp /opt/lsquic/bin /app/logs/;"]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing Lsquic service manager...")
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
        Generates a structured list of deployment command arguments for the LSQUIC service.

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

        target = self.service_config_to_test.protocol.target

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
        if "network" in params and params["network"] and "interface" in params["network"]:
            network = params["network"]
            cmd_args.extend([network["interface"]["param"], network["interface"]["value"]])

        # Add server address parameter
        if "network" in params and "port" in params["network"]:
            cmd_args.extend(["-s", f"{target}:{params['network']['port']}"])

        # Add logging redirection
        if "logging" in params and params["logging"]:
            cmd_args.extend(
                [">", params["logging"]["log_path"], "2>", params["logging"]["err_path"]]
            )

        self.logger.debug("Generated command arguments: %s", cmd_args)
        return cmd_args

    def __str__(self) -> str:
        return f"LsquicServiceManager({self.__dict__})"

    def __repr__(self):
        return f"LsquicServiceManager({self.__dict__})"
