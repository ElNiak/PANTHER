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

    def generate_pre_run_commands(self) -> List[str]:
        """Write configs with runtime IPs, start zebra before bgpd."""
        ctx = self._build_template_context()
        # Multiline command uses the heredoc path in the entrypoint template,
        # which prevents premature shell variable expansion.
        bgpd_conf_script = (
            f"SELF_IP=$(awk 'NR==1{{print $1; exit}}' /app/coordination/${{SERVICE_NAME}}_ip.txt 2>/dev/null || echo \"${{SERVICE_IP%% *}}\")\n"
            # Peer discovery must NOT hardcode the tester's service name.
            # entrypoint.sh.jinja:470 writes ${SERVICE_NAME}_ip.txt, so the old
            # hardcoded `ivy_tester_ip.txt` matched nothing whenever the tester
            # service was named anything else, and the `hostname -i` fallback
            # then returned our OWN address. FRR peered with itself and looped
            # on NOTIFICATION(2,2) Bad Peer AS -- silently, because the fallback
            # succeeds. Pick the one *_ip.txt that is not ours, and fail loudly
            # rather than self-peer. (SELF_IP is resolved just above.)
            f"PEER_FILE=$(ls /app/coordination/*_ip.txt 2>/dev/null"
            f' | grep -v "/${{SERVICE_NAME}}_ip.txt$" | head -n1)\n'
            f"WAIT=0\n"
            f'while [ -z "$PEER_FILE" ] && [ $WAIT -lt 30 ]; do\n'
            f"  sleep 1\n"
            f"  WAIT=$((WAIT + 1))\n"
            f"  PEER_FILE=$(ls /app/coordination/*_ip.txt 2>/dev/null"
            f' | grep -v "/${{SERVICE_NAME}}_ip.txt$" | head -n1)\n'
            f"done\n"
            f"NEIGHBOR_IP=$(awk 'NR==1{{print $1; exit}}' \"$PEER_FILE\" 2>/dev/null)\n"
            f'if [ -z "$NEIGHBOR_IP" ] || [ "$NEIGHBOR_IP" = "$SELF_IP" ]; then\n'
            f'  echo "ERROR: no distinct peer *_ip.txt in /app/coordination'
            f' (self=${{SERVICE_NAME}}, ip=$SELF_IP) - refusing to self-peer" >&2\n'
            f"  ls -la /app/coordination >&2\n"
            f"  exit 1\n"
            f"fi\n"
            f'printf "frr defaults traditional\\n'
            f"!\\n"
            f"router bgp {ctx['as_number']}\\n"
            f" bgp router-id %s\\n"
            f" neighbor %s remote-as {ctx['neighbor_as']}\\n"
            f" neighbor %s timers {ctx['hold_time']} {ctx['keepalive_time']}\\n"
            # ConnectRetryTime [rfc4271:8.2.1]. FRR's default is 120 s, but an
            # experiment window is typically 120-180 s, so a single missed
            # connect burns the whole run: measured 2026-09-09, bgpd opened one
            # SYN at t=0.9 s while the Ivy tester was still compiling, got RST,
            # and never tried again -- 0 BGP messages in a 180 s test.
            # 5 s keeps retrying until the tester's listener is actually up.
            # RFC 4271 sets no lower bound; §10 calls 120 s merely "suggested".
            f" neighbor %s timers connect 5\\n"
            f" !\\n"
            f" address-family ipv4 unicast\\n"
            f"  neighbor %s activate\\n"
            f" exit-address-family\\n"
            # Five placeholders above: router-id, remote-as, timers,
            # timers-connect, activate. Keep this argument list in step with
            # them -- printf silently reuses the format on a count mismatch.
            f'!\\n" "$SELF_IP" "$NEIGHBOR_IP" "$NEIGHBOR_IP" "$NEIGHBOR_IP" "$NEIGHBOR_IP" > /etc/frr/bgpd.conf\n'
            f'echo "Generated bgpd.conf: router-id=$SELF_IP neighbor=$NEIGHBOR_IP"'
        )
        return [
            "mkdir -p /tmp/frr",
            'printf "!\\nhostname zebra\\n!\\n" > /etc/frr/zebra.conf',
            bgpd_conf_script,
            "/usr/lib/frr/zebra -d -f /etc/frr/zebra.conf --log file:/tmp/frr/zebra.log",
            "sleep 1",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate the bgpd startup command string."""
        ctx = self._build_template_context()
        self.working_dir = "/etc/frr"
        return (
            f"/usr/lib/frr/bgpd -n -f /etc/frr/bgpd.conf "
            f"--log file:/tmp/frr/bgpd.log -p {ctx['listen_port']}"
        )

    def generate_run_command(self):
        """Build the run command dict for bgpd startup."""
        ctx = self._build_template_context()
        run_command = {
            "working_dir": "/etc/frr",
            "command_binary": "/usr/lib/frr/bgpd",
            "command_args": (
                f"-n -f /etc/frr/bgpd.conf "
                f"--log file:/tmp/frr/bgpd.log -p {ctx['listen_port']}"
            ),
            "timeout": getattr(self, "timeout", 60),
            "environment": {
                "PORT": str(ctx["listen_port"]),
                "ROLE": "server",
            },
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
