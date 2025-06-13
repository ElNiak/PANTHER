# PANTHER-SCP/panther/plugins/services/implementations/aioquic_rfc9000/service_manager.py

from panther.plugins.services.iut.quic.aioquic.config_schema import AioquicConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

# PluginManager functionality now integrated into PluginManager
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.plugin_decorators import register_plugin
from panther.core.utils.service_manager_utils import IUTServiceManagerMixin
from panther.core.utils import (
    ServiceCommandBuilder,
    ServiceTemplateRenderer,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
)


@register_plugin(
    plugin_type="iut",
    name="aioquic",
    version="1.0.0",
    description="AioQUIC - Python asyncio implementation of QUIC and HTTP/3",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3", "datagrams", "webtransport"],
    external_dependencies=["docker"],
)
class AioquicServiceManager(
    IUTServiceManagerMixin, ServiceManagerDockerMixin, ErrorHandlerMixin, IImplementationManager
):
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
        # Use standardized initialization from mixin
        self.standardized_initialization(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        # Set up IUT-specific attributes
        self.setup_iut_specific_attributes(protocol, service_config_to_test)

        # Initialize template renderer
        plugin_dir = Path(__file__).parent
        self.template_renderer = ServiceTemplateRenderer(plugin_dir)

        # Set Docker attributes for ServiceManagerDockerMixin
        self.docker_image_name = "aioquic:latest"
        self.docker_file_path = plugin_dir / "Dockerfile"

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

    def generate_deployment_commands(self) -> list:
        """
        Generates a structured list of deployment command arguments for the QUIC service.

        This method constructs the command arguments using the ServiceCommandBuilder,
        ensuring proper escaping and handling of special characters.

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

        # Build command using ServiceCommandBuilder
        builder = ServiceCommandBuilder(self.role)

        # Add standard parameters
        builder.add_certificates(params, cert_param_key="cert_param", cert_file_key="cert_file")
        builder.add_protocol_params(params)

        # Add aioquic-specific parameters
        if self.role == RoleEnum.client and "ticket_file" in params:
            builder.add_option(params["ticket_file"]["param"], params["ticket_file"]["file"])

        # Add network interface if specified
        if "network" in params and "interface" in params["network"]:
            builder.add_option(
                params["network"]["interface"]["param"], params["network"]["interface"]["value"]
            )

        # Add initial version for client
        if self.role == RoleEnum.client and "initial_version" in params:
            builder.add_option("-v", params["initial_version"])

        # Add additional protocol parameters
        if "protocol" in params and "additional_parameters" in params["protocol"]:
            additional_params = self.build_command_args(params["protocol"]["additional_parameters"])
            builder.add_arguments(*additional_params)

        # Add role-specific parameters
        builder.add_role_specific_params(params, server_port_param="-p")

        # Get built arguments
        cmd_args = builder.build_args()

        # Add logging redirection (these need to be handled separately as they're shell constructs)
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
