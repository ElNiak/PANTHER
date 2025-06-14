"""Refactored Quant service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="quant",
    version="2.0.0",
    description="Quant - Minimal QUIC implementation (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class QuantServiceManager(BaseQUICServiceManager):
    """Refactored Quant service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quant"

    def _get_binary_name(self) -> str:
        # Quant uses different binaries
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quant server specific arguments."""
        args = []

        # Document root
        if kwargs.get("root"):
            args.extend(["-d", kwargs["root"]])
        else:
            args.extend(["-d", "/var/www"])

        # Verbose logging
        if kwargs.get("verbose", False):
            args.append("-v")

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quant client specific arguments."""
        args = []

        # Request URL path
        path = kwargs.get("path", "/")
        args.extend(["-u", path])

        # Verbose logging
        if kwargs.get("verbose", False):
            args.append("-v")

        # Connection count
        if kwargs.get("connections", 1) > 1:
            args.extend(["-n", str(kwargs["connections"])])

        return args

    def generate_post_run_commands(self) -> List[str]:
        """Quant post-run cleanup."""
        return [
            "cp /opt/quant/Debug/bin/* /app/logs/ 2>/dev/null || true;",
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -p 4443 -d /var/www"
        else:
            return f"{self._get_binary_name()} -u / localhost 4443"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the Quant service."""
        pass
