import os
import traceback
from panther.plugins.services.iut.minip.ping_pong.config_schema import PingPongConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum


class PingPongServiceManager(IImplementationManager):
    def __init__(
        self,
        service_config_to_test: PingPongConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )
        self.logger.debug(
            f"Initializing PingPong service manager for '{implementation_name}'"
        )
        self.logger.debug(
            f"Loaded PingPong configuration: {self.service_config_to_test}"
        )
        self.initialize_commands()

    def generate_pre_compile_commands(self):
        """
        Generates pre-compile commands.
        """
        return super().generate_pre_compile_commands() + [
            "TARGET_IP=$(getent hosts "
            + self.service_targets
            + r' | awk "{ print \$1 }");',
            'echo "Resolved '
            + self.service_targets
            + ' IP - $$TARGET_IP" >> /app/logs/ivy_setup.log;',
            r'IVY_IP=$(hostname -I | awk "{ print \$1 }");',
            'echo "Resolved  '
            + self.service_name
            + ' IP - $$IVY_IP" >> /app/logs/ivy_setup.log;',
            " ",
            "ip_to_hex() {",
            '  echo $1 | awk -F"." "{ printf(\\"%02X%02X%02X%02X\\", \\$1, \\$2, \\$3, \\$4) }";',
            "}",
            " ",
            "ip_to_decimal() {",
            '  echo $1 | awk -F"." "{ printf(\\"%.0f\\", (\\$1 * 256 * 256 * 256) + (\\$2 * 256 * 256) + (\\$3 * 256) + \\$4) }";',
            "}",
            " ",
            "TARGET_IP_HEX=$(ip_to_decimal $$TARGET_IP);",
            "IVY_IP_HEX=$(ip_to_decimal $$IVY_IP);",
            'echo "Resolved '
            + self.service_targets
            + ' IP in hex - $$TARGET_IP_HEX" >> /app/logs/ivy_setup.log;',
            'echo "Resolved '
            + self.service_name
            + ' IP in hex - $$IVY_IP_HEX" >> /app/logs/ivy_setup.log;',
        ]

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
            "cp /opt/ping-pong/miniP_* /app/logs/miniP_*;"
        ]

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service manager for use.
        """
        self.logger.debug("Preparing PingPong service manager...")
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
        Generates deployment commands and collects volume mappings based on service parameters.

        :param service_params: Parameters specific to the service.
        :param environment: The environment in which the services are being deployed.
        :return: A dictionary with service name as key and a dictionary containing command and volumes.
        """
        self.logger.debug(
            f"Generating deployment commands for service: {self.service_name} with service parameters: {self.service_config_to_test}"
        )
        # Create the command list

        self.logger.debug(f"Role: {self.role.name}, Version: {self.service_version}")

        # Build parameters for the command template
        # TODO ensure that the parameters are correctly set
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        # For the client, include target and message if available
        elif self.role == RoleEnum.client:
            params = self.service_config_to_test.implementation.version.client

        params["target"] = "$$TARGET_IP_HEX"

        self.logger.debug(f"Parameters for command template: {params}")
        self.logger.debug(f"Role: {self.role.name}")
        self.working_dir = params["binary"]["dir"]

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
        return f"PingPongServiceManager({self.__dict__})"

    def __repr__(self):
        return f"PingPongServiceManager({self.__dict__})"
