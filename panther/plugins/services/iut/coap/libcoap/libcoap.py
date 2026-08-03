"""LibCoAP CoAP service manager for PANTHER."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from panther.config.core.models import ProtocolConfig, ProtocolRole
from panther.core.command_processor.builders import ServiceCommandBuilder
from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.iut.coap.libcoap.config_schema import LibcoapConfig
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


@register_plugin(
    plugin_type=PluginType.IUT,
    name="libcoap",
    version="1.0.0",
    description="LibCoAP CoAP implementation",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["coap"],
    capabilities=["rfc7252", "route-advertisement", "communities"],
    external_dependencies=["docker"],
)
class LibcoapServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    ErrorHandlerMixin,
    IImplementationManager,
    StringRepresentationMixin,
):
    """Service manager for LibCoAP CoAP implementation."""

    def __init__(  # noqa: D107
        self,
        service_config_to_test: LibcoapConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
        **kwargs,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            **kwargs,
        )
        self.standard_iut_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            plugin_dir=Path(__file__).parent,
        )

    def generate_pre_compile_commands(self) -> List[str]:
        """Return empty list; LibCoAP requires no pre-compile steps."""
        return []

    def generate_compile_commands(self) -> List[str]:
        """Return empty list; LibCoAP ships as a pre-built Docker image."""
        return []

    def generate_deployment_commands(self) -> str:
        """Generate the libcoap startup command string."""
        self.logger.debug(
            "Generating deployment commands for service: %s with service parameters: %s",
            self.service_name,
            self.service_config_to_test,
        )

        self.logger.debug(
            "Role: %s, Version: %s",
            self.role.name if hasattr(self.role, "name") else self.role,
            self.service_version,
        )

        # Build parameters based on role - check service config
        if hasattr(self.service_config_to_test, "version"):
            # Fall back to typed config on service_config_to_test directly
            if self.role == ProtocolRole.SERVER:
                params = (
                    self.service_config_to_test.version.server
                    if hasattr(self.service_config_to_test.version, "server")
                    else {}
                )
            else:
                params = (
                    self.service_config_to_test.version.client
                    if hasattr(self.service_config_to_test.version, "client")
                    else {}
                )
        else:
            # Final fallback to original approach
            if self.role == ProtocolRole.SERVER:
                params = self.service_config_to_test.implementation.version.server
            else:
                params = self.service_config_to_test.implementation.version.client

        params["target"] = "$TARGET_IP"
        self.working_dir = params["binary"]["dir"]

        # Use ServiceCommandBuilder with role
        builder = ServiceCommandBuilder(self.role)

        # Add seed parameter if available
        if "seed" in params:
            builder.add_positional(f"seed={params['seed']}")

        # Add server and client ports/addresses if available
        if "server_port" in params:
            builder.add_positional(f"server_port={params['server_port']}")
        if "server_addr" in params:
            builder.add_positional(f"server_addr={params['server_addr']}")

        # Add role-specific parameters
        if self.role == ProtocolRole.SERVER:
            if "client_port" in params:
                builder.add_positional(f"client_port={params['client_port']}")
            if "client_addr" in params:
                builder.add_positional(f"client_addr={params['client_addr']}")

        # Add logging parameters
        # if "logging" in params:
        # TODO -> dot not exist
        #     builder.set_output_redirection(
        #         stdout=params["logging"]["log_path"],
        #         stderr=params["logging"]["err_path"],
        #     )

        # Build command arguments and environment
        command_args = builder.build_args()
        env_vars = builder.build_env()

        # Try to render the template with structured arguments
        try:
            cmd = self.template_renderer.render_structured_command(
                self.role.name if hasattr(self.role, "name") else str(self.role),
                params,
                command_args,
                env_vars,
            )
            return cmd.command
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Failed to render structured template for service '%s': %s",
                self.service_config_to_test.name,
                e,
            )
            # Fallback to original template
            template_name = f"{self.role.name if hasattr(self.role, 'name') else self.role}_command.jinja"
            return self.render_commands(params, template_name)

    def generate_run_command(self):
        """Build the run command dict for libcoap startup."""
        self.emit_command_generation_started("run")

        cmd_args = self.generate_deployment_commands()

        # # Notify service event
        # self.notify_service_event(
        #     "run_command_generated",
        #     service_id=self.implementation_name,
        #     service_name=self.service_name,
        #     details={
        #         "role": (
        #             self.role.name if hasattr(self.role, "name") else str(self.role)
        #         ),
        #     },
        # )

        # Determine binary based on role
        # if self.role == ProtocolRole.SERVER:
        #     command_binary = (
        #         self.service_config_to_test.implementation.version.server.binary.name
        #     )
        # else:
        #     command_binary = (
        #         self.service_config_to_test.implementation.version.client.binary.name
        #     )
        # TODO: Use the binary path from the version config if available, otherwise fallback to default paths
        if self.role == ProtocolRole.SERVER:
            command_binary = "/opt/libcoap/libcoap-minimal/server"
        else:
            command_binary = "/opt/libcoap/libcoap-minimal/client"

        run_command = {
            "working_dir": self.working_dir,
            "command_binary": command_binary,
            "command_args": cmd_args,
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

        # Emit command generated
        self.emit_command_generated("run", str(run_command))

        return run_command

    def generate_post_run_commands(self) -> List[str]:
        """Copy FRR daemon logs to the shared log directory after the run."""
        return ["cp /tmp/frr/*.log /app/logs/ 2>/dev/null || true"]

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Return (output_type, filename_pattern) pairs for log collection."""
        return [
            ("test", "*.log"),
            ("test", "*.err.log"),
        ]

    def _do_prepare(self, plugin_manager: "Optional[PluginManager]" = None) -> None:
        """Delegate to the Docker mixin for image building."""
        self.prepare_docker_image()
