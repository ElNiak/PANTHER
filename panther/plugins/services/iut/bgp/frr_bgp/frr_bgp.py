"""FRRouting BGP service manager for PANTHER."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from panther.config.core.models import ProtocolConfig
from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.iut.bgp.frr_bgp.config_schema import FrrBgpConfig
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
    name="frr_bgp",
    version="1.0.0",
    description="FRRouting BGP-4 implementation",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["bgp"],
    capabilities=["rfc4271", "route-advertisement", "communities"],
    external_dependencies=["docker"],
)
class FrrBgpServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    ErrorHandlerMixin,
    IImplementationManager,
    StringRepresentationMixin,
):
    """Service manager for FRRouting BGP implementation."""

    def __init__(  # noqa: D107
        self,
        service_config_to_test: FrrBgpConfig,
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
        """Return empty list; FRR requires no pre-compile steps."""
        return []

    def generate_compile_commands(self) -> List[str]:
        """Return empty list; FRR ships as a pre-built Docker image."""
        return []

    def generate_runtime_commands(self) -> List[str]:
        """Return empty list; runtime setup is handled by the entrypoint."""
        return []

    def generate_deployment_commands(self) -> str:
        """Generate deployment command string for bgpd startup."""
        ctx = self._build_template_context()
        self.working_dir = "/etc/frr"
        return (
            f"mkdir -p /tmp/frr && /usr/lib/frr/zebra -d -f /etc/frr/zebra.conf "
            f"--log file:/tmp/frr/zebra.log && sleep 1 && "
            f"/usr/lib/frr/bgpd -n -f /etc/frr/bgpd.conf "
            f"--log file:/tmp/frr/bgpd.log -p {ctx['listen_port']}"
        )

    def generate_run_command(self):
        """Build the run command dict for bgpd startup."""
        cmd_args = self.generate_deployment_commands()
        run_command = {
            "working_dir": self.working_dir,
            "command_binary": "/bin/bash",
            "command_args": f"-c '{cmd_args}'",
            "timeout": getattr(self, "timeout", 60),
            "environment": {},
        }
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

    def _build_template_context(self) -> dict:
        server = {}
        if hasattr(self, "service_config_to_test") and hasattr(
            self.service_config_to_test, "version"
        ):
            version = self.service_config_to_test.version
            server = getattr(version, "server", None) or {}
        return {
            "as_number": server.get("as_number", 2),
            "router_id": server.get("router_id", "10.0.0.3"),
            "neighbor_ip": server.get("neighbor_ip", "10.0.0.1"),
            "neighbor_as": server.get("neighbor_as", 1),
            "hold_time": server.get("hold_time", 180),
            "keepalive_time": server.get("keepalive_time", 60),
            "listen_port": server.get("listen_port", 179),
        }

    def _do_prepare(self, plugin_manager: "Optional[PluginManager]" = None) -> None:
        """Delegate to the Docker mixin for image building."""
        self.prepare_docker_image()
