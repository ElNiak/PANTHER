"""Clean refactored PicoQUIC service manager using base classes."""

from pathlib import Path
from typing import List, Optional

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="picoquic",
    version="2.0.0",
    description="PicoQUIC - Lightweight QUIC implementation (Clean refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class PicoquicServiceManager(BaseQUICServiceManager):
    """Clean PicoQUIC service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "picoquic"

    def _get_binary_name(self) -> str:
        return "picoquicdemo"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC server doesn't need extra args beyond common ones."""
        return []

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC client specific arguments."""
        args = []

        # 0-RTT ticket file
        if kwargs.get("ticket_file"):
            args.extend(["-t", kwargs["ticket_file"]])

        # Request specific file
        if kwargs.get("request_file"):
            args.extend(["-o", kwargs["request_file"]])

        return args

    def generate_post_run_commands(self) -> List[str]:
        """Copy binary to logs for debugging."""
        return ["cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;"]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        # For the clean implementation, just return the basic command
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -p 4443"
        else:
            return f"{self._get_binary_name()} localhost 4443"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the service (no-op for clean implementation)."""
        pass
