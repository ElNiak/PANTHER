# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

import subprocess
import os
import traceback
from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum

class QuinnServiceManager(IImplementationManager):
    """
    QuinnServiceManager is a class responsible for managing the Quinn service implementation.

    Attributes:
        service_config_to_test (QuinnConfig): Configuration for the Quinn service to be tested.
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
            Initializes the QuinnServiceManager with the given configuration, service type, protocol, and implementation name.
        generate_run_command():
            Generates the run command for the service.
        generate_post_run_commands():
            Generates post-run commands for the service.
        prepare(plugin_loader):
            Prepares the service manager for use by building Docker images.
        generate_deployment_commands():
        __str__():
            Returns a string representation of the QuinnServiceManager instance.
        __repr__():
            Returns a string representation of the QuinnServiceManager instance.
    """
    def __init__(
        self,
        service_config_to_test: QuinnConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )
        self.logger.debug(
            f"Initializing Quinn service manager for '{implementation_name}'"
        )
        self.logger.debug(
            f"Loaded Quinn configuration: {self.service_config_to_test}"
        )
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
        return super().generate_post_run_commands() + [
            "cp -r /opt/quinn/target/debug/examples/ /app/logs/quinn/;"
        ]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing Quinn service manager...")
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
        This method constructs the necessary deployment commands by rendering a template with the appropriate parameters.
        It includes network interface parameters conditionally based on the environment and role (server or client).
        Returns:
            str: The rendered deployment command string.
        Raises:
            Exception: If there is an error rendering the command template.
        Logs:
            Various debug information including service name, service parameters, role, version, and parameters for the command template.
        """
        
        self.logger.debug(
            f"Generating deployment commands for service: {self.service_name} with service parameters: {self.service_config_to_test}"
        )
        # Create the command list

        self.logger.debug(f"Role: {self.role}, Version: {self.service_version}")

        # Determine if network interface parameters should be included based on environment
        include_interface = True

        # Build parameters for the command template
        # TODO ensure that the parameters are correctly set
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        # For the client, include target and message if available
        elif self.role == RoleEnum.client:
            params = self.service_config_to_test.implementation.version.client

        params["target"] = self.service_config_to_test.protocol.target

        self.logger.debug(f"Parameters for command template: {params}")
        self.logger.debug(f"Role: {self.role}")
        self.working_dir = params["binary"]["dir"]
        # Conditionally include network interface parameters
        if not include_interface:
            params["network"].pop("interface", None)
        else:
            # TODO add that in the Dockerfile
            subprocess.run(["bash", "generate_certificates.sh"])

        # Render the appropriate template
        try:
            template_name = f"{str(self.role.name)}_command.jinja"
            return super().render_commands(params, template_name)
        except Exception as e:
            self.logger.error(
                f"Failed to render command for service '{self.service_config_to_test.name}': {e}\n{traceback.format_exc()}"
            )
            raise e

    def __str__(self) -> str:
        return f"QuinnServiceManager({self.__dict__})"

    def __repr__(self):
        return f"QuinnServiceManager({self.__dict__})"
