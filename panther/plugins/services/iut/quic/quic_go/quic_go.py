import subprocess
import os
import traceback
from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class QuicGoServiceManager(IImplementationManager):
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
        return super().generate_post_run_commands() + ["cp -r /opt/quic-go/ /app/logs/;"]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepares the QuicGo service manager by building the necessary Docker images.
        Args:
            plugin_loader (PluginLoader | None): An optional PluginLoader instance used to build Docker images.
        Raises:
            Any exceptions raised by the plugin_loader methods.
        """

        self.logger.debug("Preparing QuicGo service manager...")
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
        Generates deployment commands for the QUIC service based on the role and service configuration.
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
        else:
            # TODO add that in the Dockerfile
            subprocess.run(["bash", "generate_certificates.sh"])

        # Build structured command arguments
        command_args = []

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

    def __str__(self) -> str:
        return f"QuicGoServiceManager({self.__dict__})"

    def __repr__(self):
        return f"QuicGoServiceManager({self.__dict__})"
