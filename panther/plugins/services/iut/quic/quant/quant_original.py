# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

from pathlib import Path
from typing import TYPE_CHECKING

from panther.core.command_processor.command_builder import ServiceCommandBuilder
from panther.core.utils import ErrorHandlerMixin, ServiceManagerDockerMixin
from panther.core.utils.service_manager_utils import IUTServiceManagerMixin
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type="iut",
    name="quant",
    version="1.0.0",
    description="QUANT - A QUIC implementation with high-performance userspace UDP stack",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "spinbit"],
    external_dependencies=["docker"],
)
class QuantServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
    IImplementationManager,
):
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
        prepare(self, plugin_manager: "PluginManager | None" = None):
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

    def generate_run_command(self):
        """
        Generates the run command for the quant service.

        This method constructs a complete run command configuration using
        the structured approach for proper quoting and escaping of all
        command arguments and environment variables.

        Returns:
            dict: The run command configuration with all necessary components.
        """
        # Emit command generation started
        self.emit_command_generation_started("run")

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
                if self.service_config_to_test.implementation.version.parameters.get(
                    "debug", False
                )
                else "0"
            ),
        }

        # Try to render with structured template, fall back to original if needed
        try:
            cmd = self.template_renderer.render_structured_command(
                self.role.name, params, command_args, env_vars
            )
            # For structured templates, we'll use the rendered command as a string
            command_args = cmd.command
        except Exception as e:
            self.logger.warning(
                "Failed to use structured template for %s: %s. ", self.service_name, e
            )
            # Keep command_args as is if the structured template fails

        run_command = {
            "working_dir": self.working_dir,
            "command_binary": params["binary"]["name"],
            "command_args": command_args,
            "timeout": self.service_config_to_test.timeout,
            "command_env": env_vars,
        }

        # Notify service event
        self.notify_service_event(
            "run_command_generated",
            {
                "service_name": self.service_name,
                "role": self.role.name
                if hasattr(self.role, "name")
                else str(self.role),
            },
        )

        # Emit command generated
        self.emit_command_generated("run", str(run_command))

        return run_command

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return super().generate_post_run_commands() + [
            "cp -r /opt/quant/bin /app/logs/quant/;"
        ]

    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
        """
        Simplified prepare method - just delegate to the enhanced mixin.

        The ServiceManagerDockerMixin now handles:
        - Building base image only once per experiment
        - Building service-specific image
        - Proper event emission
        - Error handling
        - Command initialization (if initialize_commands exists)

        Args:
            plugin_manager: Optional plugin manager for Docker operations
        """
        super().prepare(plugin_manager)

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

        # Use ServiceCommandBuilder to build structured command arguments
        builder = ServiceCommandBuilder(self.role)

        # Add certificate parameters
        if "certificates" in params and params["certificates"]:
            certs = params["certificates"]
            if "cert_param" in certs and "cert_file" in certs:
                builder.add_flag_with_value(certs["cert_param"], certs["cert_file"])
            if "key_param" in certs and "key_file" in certs:
                builder.add_flag_with_value(certs["key_param"], certs["key_file"])

        # Add protocol parameters
        if "protocol" in params and params["protocol"]:
            proto = params["protocol"]
            if "additional_parameters" in proto and proto["additional_parameters"]:
                # Split additional parameters into separate arguments
                additional_params = self.build_command_args(
                    proto["additional_parameters"]
                )
                for param in additional_params:
                    builder.add_positional(param)

        # Add network interface if specified
        if "network" in params and params["network"]:
            network = params["network"]
            if "interface" in network and network["interface"]:
                builder.add_flag_with_value(
                    network["interface"]["param"], network["interface"]["value"]
                )

            # Add port for server or as part of URL for client
            if self.role == RoleEnum.server:
                builder.add_flag_with_value("-p", str(network["port"]))
                builder.add_flag_with_value("-v", "5")  # Verbose output

        # Add initial version if specified
        if "initial_version" in params and params["initial_version"]:
            builder.add_flag_with_value("-e", params["initial_version"])

        # Add target URL for client
        if self.role == RoleEnum.client:
            target = self.service_config_to_test.protocol.target
            port = params["network"]["port"]
            builder.add_positional(f"https://{target}:{port}/index.html")

        # Add logging redirection
        if "logging" in params and params["logging"]:
            builder.set_output_redirection(
                stdout=params["logging"]["log_path"],
                stderr=params["logging"]["err_path"],
            )

        cmd_args = builder.build()
        self.logger.debug("Generated command arguments: %s", cmd_args)
        return cmd_args

    def __str__(self) -> str:
        return f"QuantServiceManager({self.__dict__})"

    def __repr__(self):
        return f"QuantServiceManager({self.__dict__})"
