# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

import os
import traceback
from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class PicoquicServiceManager(IImplementationManager):
    def __init__(
        self,
        service_config_to_test: PicoquicConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__(service_config_to_test, service_type, protocol, implementation_name)
        self.logger.debug("Initializing Picoquic service manager for '%s'", implementation_name)
        self.logger.debug("Loaded Picoquic configuration: %s", self.service_config_to_test)
        self.initialize_commands()

    def generate_run_command(self):
        """
        Generates the run command.
        """
        cmd_args = self.generate_deployment_commands()

        # Make sure working_dir is set - use binary dir as default if not already set
        working_dir = getattr(self, "working_dir", None)
        if working_dir is None:
            if self.role == RoleEnum.server:
                working_dir = self.service_config_to_test.implementation.version.server.binary.dir
            else:
                working_dir = self.service_config_to_test.implementation.version.client.binary.dir
            # Save it for reuse
            self.working_dir = working_dir

        # Make sure command_args is not None and is a valid type (list or str)
        if cmd_args is None:
            self.logger.warning("Command arguments are None, using empty list")
            cmd_args = []
        elif isinstance(cmd_args, str) and not cmd_args.strip():
            # If it's an empty string after stripping
            cmd_args = []

        return {
            "working_dir": working_dir,
            "command_binary": (
                self.service_config_to_test.implementation.version.server.binary.name
                if self.role == RoleEnum.server
                else self.service_config_to_test.implementation.version.client.binary.name
            ),
            "command_args": cmd_args,
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
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
        """

        self.logger.debug("Preparing Picoquic service manager...")
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

    def generate_deployment_commands(self) -> str:
        """
        Generates deployment commands for the service based on its configuration and role.
        This method constructs the necessary deployment commands using structured arguments
        for proper escaping. It includes network interface parameters based on the environment
        and role of the service (server or client).

        Returns:
            str: The rendered deployment command string.

        Raises:
            Exception: If there is an error rendering the command template.

        Logs:
            - Debug information about the service name, parameters, role, and version.
            - Error information if command rendering fails.
        """

        self.logger.debug(
            "Generating deployment commands for service: %s with service parameters: %s",
            self.service_name,
            self.service_config_to_test,
        )

        self.logger.debug("Role: %s, Version: %s", self.role, self.service_version)

        # Initialize params first
        params = {}

        # Build parameters for the command template
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        # For the client, include target and message if available
        elif self.role == RoleEnum.client:
            params = self.service_config_to_test.implementation.version.client
        else:
            self.logger.warning("Unknown role: %s, using empty params", self.role)

        params["target"] = self.service_config_to_test.protocol.target

        self.logger.debug("Parameters for command template: %s", params)
        self.logger.debug("Role: %s", self.role)
        self.working_dir = params["binary"]["dir"]

        # Build structured command arguments
        command_args = []

        # Add certificate parameters - with proper nested key checking
        if "certificates" in params:
            cert_fields = ["cert_param", "cert_file", "key_param", "key_file"]
            # Check if all required certificate fields exist
            if all(field in params["certificates"] for field in cert_fields):
                command_args.append(params["certificates"]["cert_param"])
                command_args.append(params["certificates"]["cert_file"])
                command_args.append(params["certificates"]["key_param"])
                command_args.append(params["certificates"]["key_file"])
            else:
                self.logger.debug(
                    "Some certificate parameters are missing, skipping certificate configuration"
                )
                # Optional: log which specific certificate fields are missing
                missing_fields = [
                    field for field in cert_fields if field not in params["certificates"]
                ]
                if missing_fields:
                    self.logger.debug("Missing certificate fields: %s", ", ".join(missing_fields))

        # Add ticket file parameters (client only)
        if self.role == RoleEnum.client and "ticket_file" in params:
            command_args.append(params["ticket_file"]["param"])
            command_args.append(params["ticket_file"]["file"])

        # Add ALPN parameters
        if "protocol" in params and "alpn" in params["protocol"]:
            command_args.append(params["protocol"]["alpn"]["param"])
            command_args.append(params["protocol"]["alpn"]["value"])

        # Add additional protocol parameters
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            command_args.append(params["protocol"]["additional_parameters"])

        # Add network interface if available
        if "network" in params and "interface" in params["network"]:
            command_args.append(params["network"]["interface"]["param"])
            command_args.append(params["network"]["interface"]["value"])

        # Add initial version (client only)
        if self.role == RoleEnum.client and "initial_version" in params:
            command_args.append("-v")
            command_args.append(params["initial_version"])

        # Add role-specific parameters
        if self.role == RoleEnum.server:
            command_args.append("-p")
            command_args.append(params["network"]["port"])
        elif self.role == RoleEnum.client:
            command_args.append(params["target"])
            command_args.append(params["network"]["port"])

        # Add logging parameters
        if "logging" in params:
            command_args.append(">")
            command_args.append(params["logging"]["log_path"])
            command_args.append("2>")
            command_args.append(params["logging"]["err_path"])

        # Environment variables if needed
        env_vars = {}  # Add any required environment variables here

        # Render the appropriate template with structured arguments
        try:
            # Try the structured template first
            template_name = f"{str(self.role.name)}_command_structured.jinja"

            # Use the render_template_with_structured_args method which handles proper escaping
            return super().render_template_with_structured_args(
                template_name, params=params, command_args=command_args, env_vars=env_vars
            )
        except (FileNotFoundError, ValueError, TypeError, KeyError) as e:
            self.logger.error(
                "Failed to render command for service '%s': %s\n%s",
                self.service_config_to_test.name,
                e,
                traceback.format_exc(),
            )
            # Fall back to original template if structured template fails
            try:
                template_name = f"{str(self.role.name)}_command.jinja"
                return super().render_template_with_structured_args(
                    template_name, params=params, command_args=command_args, env_vars=env_vars
                )
            except (FileNotFoundError, ValueError, TypeError, KeyError) as fallback_error:
                self.logger.error(
                    "Fallback template also failed: %s\n%s", fallback_error, traceback.format_exc()
                )
                raise e from fallback_error

    def __str__(self) -> str:
        return f"PicoquicServiceManager({self.__dict__})"

    def __repr__(self):
        return f"PicoquicServiceManager({self.__dict__})"

    def stop(self):
        """
        Stops the PicoquicServiceManager service.

        This method is called by the TestCase's teardown_services method to properly
        stop the service if it's running.
        """
        pass
