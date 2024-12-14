from pathlib import Path
import os
import traceback
from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
    PicoquicShadowConfig,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


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
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )
        self.logger.debug(
            f"Initializing Picoquic service manager for '{implementation_name}'"
        )
        self.logger.debug(
            f"Loaded Picoquic configuration: {self.service_config_to_test}"
        )
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
        This method constructs the necessary deployment commands by rendering a template
        with the service parameters. It logs the process of generating these commands,
        including the service name, service parameters, role, and version. Depending on
        the environment, it may include network interface parameters.
        Returns:
            str: The rendered deployment command string.
        Raises:
            Exception: If there is an error rendering the command template.
        """
        
        self.logger.debug(
            f"Generating deployment commands for service: {self.service_name} with service parameters: {self.service_config_to_test}"
        )
        # Create the command list

        self.logger.debug(f"Role: {self.role}, Version: {self.service_version}")

        # Determine if network interface parameters should be included based on environment
        # TODO
        # include_interface = environment not in ["docker_compose"]
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

        # Render the appropriate template
        try:
            template_name = f"{str(self.role.name)}_command.jinja"
            return super().render_commands(params, template_name)

        except Exception as e:
            self.logger.error(
                f"Failed to render command for service '{self.service_config_to_test.name}': {e}\n{traceback.format_exc()}"
            )
            raise e
