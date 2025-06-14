"""Refactored quic-go service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="quic_go",
    version="2.0.0",
    description="quic-go - Go implementation of QUIC (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3"],
)
class QuicGoServiceManager(BaseQUICServiceManager):
    """Refactored quic-go service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quic_go"

    def _get_binary_name(self) -> str:
        # quic-go uses example binaries
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """quic-go server specific arguments."""
        args = []

        # Document root for serving files
        if kwargs.get("www"):
            args.extend(["-www", kwargs["www"]])
        else:
            args.extend(["-www", "/var/www"])

        # Certificate files
        if kwargs.get("certfile") and kwargs.get("keyfile"):
            args.extend(["-certfile", kwargs["certfile"]])
            args.extend(["-keyfile", kwargs["keyfile"]])

        # Enable qlog
        if kwargs.get("qlog", False):
            args.append("-qlog")

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """quic-go client specific arguments."""
        args = []

        # Target URL
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        path = kwargs.get("path", "/")

        url = f"https://{host}:{port}{path}"
        args.append(url)

        # Insecure mode (skip cert verification)
        if kwargs.get("insecure", True):
            args.append("-insecure")

        # Enable qlog
        if kwargs.get("qlog", False):
            args.append("-qlog")

        # Verbose output
        if kwargs.get("verbose", False):
            args.append("-v")

        return args

    def generate_compile_command(self, **kwargs) -> str:
        """Go-specific compile command."""
        return "go build -o server ./example/main.go && go build -o client ./example/client/main.go"

    def _extract_common_params(self, **kwargs):
        """Extract Go-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # Go-specific environment
        params["go_path"] = kwargs.get("go_path", "/opt/quic-go")
        params["go_env"] = kwargs.get("go_env", {})

        return params

    def generate_post_run_commands(self) -> List[str]:
        """quic-go post-run cleanup."""
        return [
            "cp /opt/quic-go/server /app/logs/ 2>/dev/null || true;",
            "cp /opt/quic-go/client /app/logs/ 2>/dev/null || true;",
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -www /var/www"
        else:
            return f"{self._get_binary_name()} https://localhost:4443/ -insecure"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the quic-go service."""
        pass

    def get_supported_features(self) -> dict:
        """Get quic-go specific supported features."""
        features = super().get_supported_features()
        # quic-go has excellent HTTP/3 and Go-specific features
        features.update(
            {
                "http3": True,
                "golang": True,
                "performance": True,
                "memory_efficient": True,
                "concurrent": True,
            }
        )
        return features
