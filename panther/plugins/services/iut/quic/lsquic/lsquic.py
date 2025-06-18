"""Refactored LSQUIC service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="lsquic",
    version="2.0.0",
    description="LSQUIC - LiteSpeed's QUIC and HTTP/3 implementation (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3", "push"],
)
class LsquicServiceManager(BaseQUICServiceManager):
    """Refactored LSQUIC service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "lsquic"

    def _get_binary_name(self) -> str:
        # LSQUIC uses different binaries for client and server
        return "http_server" if self.role == "server" else "http_client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """LSQUIC server specific arguments."""
        args = []

        # Document root for serving files
        if kwargs.get("doc_root"):
            args.extend(["-s", kwargs["doc_root"]])
        else:
            args.extend(["-s", "/var/www"])

        # Enable HTTP/3 PUSH if supported
        if kwargs.get("enable_push", True):
            args.append("-p")

        # Connection limits
        if kwargs.get("max_conns"):
            args.extend(["-m", str(kwargs["max_conns"])])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """LSQUIC client specific arguments."""
        args = []

        # Request path
        path = kwargs.get("request_path", "/")
        if not path.startswith("/"):
            path = "/" + path
        args.extend(["-p", path])

        # HTTP method
        method = kwargs.get("method", "GET")
        args.extend(["-X", method])

        # Request headers
        if kwargs.get("headers"):
            for header, value in kwargs["headers"].items():
                args.extend(["-H", f"{header}: {value}"])

        # Output file
        if kwargs.get("output_file"):
            args.extend(["-o", kwargs["output_file"]])

        return args

    def _extract_common_params(self, **kwargs):
        """Extract LSQUIC-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # LSQUIC uses different environment variables
        params["library_path"] = "/opt/lsquic/lib"
        params["logs_dir"] = "/app/logs/lsquic"

        return params

    def generate_run_command(self, **kwargs):
        """Generate LSQUIC run command with environment setup."""
        # Add LSQUIC-specific environment
        env_vars = {
            "LD_LIBRARY_PATH": "/opt/lsquic/lib",
            "LSQUIC_LOGS_DIR": "/app/logs/lsquic",
        }

        # Call parent with environment
        command = super().generate_run_command(**kwargs)

        # Prepend environment variables to command
        env_prefix = " ".join([f"{k}={v}" for k, v in env_vars.items()])
        return f"{env_prefix} {command}"

    def generate_post_run_commands(self) -> List[str]:
        """LSQUIC post-run cleanup."""
        return [
            "cp /opt/lsquic/bin/* /app/logs/ 2>/dev/null || true;",
            "cp /app/logs/lsquic/* /app/logs/ 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -s /var/www -p 4443"
        else:
            return f"{self._get_binary_name()} localhost 4443 -p /"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the LSQUIC service."""
        pass

    def get_supported_features(self) -> dict:
        """Get LSQUIC-specific supported features."""
        features = super().get_supported_features()
        # LSQUIC has excellent HTTP/3 support
        features.update(
            {
                "http3": True,
                "push": True,
                "priority": True,
                "multipath": False,  # Not yet supported
            }
        )
        return features
