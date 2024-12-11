from pathlib import Path
import subprocess
import os
from typing import Any, Dict, Optional
import traceback
from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import PicoquicShadowConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum

class PicoquicShadowServiceManager(IImplementationManager):
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
        return super().generate_post_run_commands() + ["cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;"]

    def prepare(self, plugin_loader: Optional[PluginLoader] = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing Picoquic service manager...")
        plugin_loader.build_docker_image_from_path(Path(os.path.join(
            os.getcwd(),
            "panther",
            "plugins",
            "services",
            "Dockerfile",
        )),"panther_base","service")
        plugin_loader.build_docker_image(self.get_implementation_name(), self.service_config_to_test.implementation.version)

    def generate_deployment_commands(self) -> str:
        """
        Generates deployment commands and collects volume mappings based on service parameters.

        :param service_params: Parameters specific to the service.
        :param environment: The environment in which the services are being deployed.
        :return: A dictionary with service name as key and a dictionary containing command and volumes.
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

        # Collect volume mappings
        # Only add certificate volumes if the user doesn't want to generate new certificates
        # TODO: manage that
        # if not self.service_config_to_test.generate_new_certificates:
        #     # Certificates
        #     self.volumes.append(
        #         {
        #             "local": os.path.abspath(params["certificates"]["cert_local_file"]),
        #             "container": params["certificates"]["cert_file"],
        #         }
        #     )
        #     self.volumes.append(
        #         {
        #             "local": os.path.abspath(params["certificates"]["key_local_file"]),
        #             "container": params["certificates"]["key_file"],
        #         }
        #     )

        # Ticket file (if applicable)
        if params["ticket_file"]["local_file"]:
            self.volumes.append(
                {
                    "local": os.path.abspath(params["ticket_file"]["local_file"]),
                    "container": params["ticket_file"]["file"],
                }
            )
        else:
            # TODO add that in the Dockerfile
            subprocess.run(["bash", "generate_certificates.sh"])

        # Render the appropriate template
        try:
            template_name = f"{str(self.role.name)}_command.jinja"
            self.logger.debug(
                f"Rendering command using template '{template_name}' with parameters: {params}"
            )
            template = self.jinja_env.get_template(template_name)
            command = template.render(**params)

            # Clean up the command string
            command_str = command.replace("\t", " ").replace("\n", " ").strip()

            service_name = self.service_config_to_test.name
            self.logger.debug(f"Generated command for '{service_name}': {command_str}")
            return command_str
        
        except Exception as e:
            self.logger.error(
                f"Failed to render command for service '{self.service_config_to_test.name}': {e}\n{traceback.format_exc()}"
            )
            raise e