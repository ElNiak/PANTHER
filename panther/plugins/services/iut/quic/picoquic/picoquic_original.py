from pathlib import Path
from typing import TYPE_CHECKING

from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager
# PluginManager functionality now integrated into PluginManager
from typing import TYPE_CHECKING

from panther.core.command_processor.command_builder import ServiceCommandBuilder
from panther.core.utils import ErrorHandlerMixin, ServiceManagerDockerMixin
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.services.service_manager_utils import IUTServiceManagerMixin


@register_plugin(
    plugin_type="iut",
    name="picoquic",
    version="1.0.0",
    description="PicoQUIC - Lightweight QUIC implementation by Christian Huitema",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
    external_dependencies=["docker"],
)
class PicoquicServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
    IImplementationManager,
):
    """
    PicoquicServiceManager is a service manager for handling Picoquic services.
    This class is responsible for initializing the service manager, generating various commands required for the service lifecycle, and preparing the service manager for use.
    Methods:
        __init__(self, service_config_to_test: PicoquicConfig, service_type: str, protocol: ProtocolConfig, implementation_name: str):
            Initializes the PicoquicServiceManager with the given configuration, service type, protocol, and implementation name.
        get_service_name(self) -> str:
            Returns the name of the service.
        generate_pre_compile_commands(self):
        generate_compile_commands(self):
        generate_pre_run_commands(self):
        generate_run_command(self):
        generate_post_run_commands(self):
        prepare(self, plugin_manager: Optional["PluginManager"] = None):
            Prepares the service manager for use.
        generate_deployment_commands(self) -> str:
    """

    def __init__(
        self,
        service_config_to_test: PicoquicConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )
        # Use the new template method for standard initialization
        self.standard_iut_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            plugin_dir=Path(__file__).parent,
        )

    def _get_docker_image_name(self, implementation_name: str = None) -> str:
        """
        Override to extract version string from service configuration.
        """
        # Extract version string from version object
        version_str = "latest"
        if hasattr(self.service_config_to_test.implementation, "version"):
            version_obj = self.service_config_to_test.implementation.version
            if hasattr(version_obj, "version"):
                version_str = version_obj.version
            elif isinstance(version_obj, str):
                version_str = version_obj
            else:
                version_str = "latest"

        return f"picoquic:{version_str}"

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
            "environment": {},
        }

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return super().generate_post_run_commands() + [
            "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;"
        ]

    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
        """
        Simplified prepare method - just delegate to the enhanced mixin.

        The ServiceManagerDockerMixin now handles:
        - Building base image only once per experiment
        - Building service-specific image
        - Proper event emission
        - Error handling

        Args:
            plugin_manager: Optional plugin manager for Docker operations
        """
        super().prepare(plugin_manager)

    @ErrorHandlerMixin.with_error_handling("generate deployment commands")
    def generate_deployment_commands(self) -> str:
        """
        Generates deployment commands for the service based on its configuration and role.
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

        # Build parameters for the command template
        params = (
            self.service_config_to_test.implementation.version.server
            if self.role == RoleEnum.server
            else self.service_config_to_test.implementation.version.client
        )

        params["target"] = self.service_config_to_test.protocol.target
        self.working_dir = params["binary"]["dir"]

        # For regular picoquic (non-shadow), we don't need special network interface handling
        params["network"].pop("interface", None)

        # Build command using ServiceCommandBuilder
        builder = ServiceCommandBuilder(self.role)

        # Add standard parameters
        # TODO: we must make sure the cert are present - builder.add_certificates(params)
        builder.add_protocol_params(params)

        # Add picoquic-specific parameters
        if self.role == RoleEnum.client and "ticket_file" in params:
            builder.add_option(
                params["ticket_file"]["param"], params["ticket_file"]["file"]
            )

        # Add additional protocol parameters
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            builder.add_argument(params["protocol"]["additional_parameters"])

        # Add initial version for client
        if self.role == RoleEnum.client and "initial_version" in params:
            builder.add_option("-v", params["initial_version"])

        # Add role-specific parameters
        builder.add_role_specific_params(params, server_port_param="-p")

        # Get built arguments
        command_args = builder.build_args()
        env_vars = builder.build_env()

        # Render using template renderer
        try:
            cmd = self.template_renderer.render_structured_command(
                self.role.name, params, command_args, env_vars
            )
            return cmd.command
        except Exception as e:
            self.logger.warning(
                "Failed to render structured template for service '%s': %s",
                self.service_config_to_test.name,
                e,
            )
            # Fallback to original template
            template_name = f"{str(self.role.name)}_command.jinja"
            return self.render_commands(params, template_name)
