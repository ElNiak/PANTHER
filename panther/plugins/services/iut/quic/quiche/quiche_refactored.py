"""Refactored Quiche service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="quiche",
    version="2.0.0",
    description="Quiche - Cloudflare's Rust implementation of QUIC (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3"],
)
class QuicheServiceManager(RustQUICServiceManager):
    """Refactored Quiche service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quiche"

    def _get_cargo_bin_name(self) -> str:
        # Quiche uses different binaries for client and server
        return "quiche-server" if self.role == "server" else "quiche-client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quiche server specific arguments."""
        args = []

        # Document root
        if kwargs.get("root"):
            args.extend(["--root", kwargs["root"]])
        else:
            args.extend(["--root", "/var/www"])

        # Listen address
        args.extend(["--listen", "0.0.0.0:4443"])

        # Enable early data (0-RTT)
        if kwargs.get("early_data", True):
            args.append("--early-data")

        # HTTP/3 SETTINGS
        if kwargs.get("max_field_section_size"):
            args.extend(
                ["--max-field-section-size", str(kwargs["max_field_section_size"])]
            )

        # Connection ID length
        if kwargs.get("cid_len"):
            args.extend(["--cid-len", str(kwargs["cid_len"])])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quiche client specific arguments."""
        args = []

        # HTTP/3 specific arguments
        if kwargs.get("http3", True):
            args.append("--http3")

        # Request body
        if kwargs.get("body"):
            args.extend(["--body", kwargs["body"]])

        # HTTP method
        method = kwargs.get("method", "GET")
        args.extend(["--method", method])

        # Additional headers
        if kwargs.get("headers"):
            for header, value in kwargs["headers"].items():
                args.extend(["--header", f"{header}: {value}"])

        # Output file for response
        if kwargs.get("output"):
            args.extend(["--output", kwargs["output"]])

        # Session cache for 0-RTT
        if kwargs.get("session_file"):
            args.extend(["--session-file", kwargs["session_file"]])

        # Connect timeout
        if kwargs.get("connect_timeout"):
            args.extend(["--connect-timeout", str(kwargs["connect_timeout"])])

        return args

    def _map_version(self, version: str) -> str:
        """Map QUIC version to Quiche format."""
        # Quiche uses hex format for draft versions
        version_map = {
            "rfc9000": "1",
            "draft29": "ff00001d",
            "draft28": "ff00001c",
            "draft27": "ff00001b",
        }
        return version_map.get(version, version)

    def generate_post_run_commands(self) -> List[str]:
        """Quiche post-run cleanup."""
        return [
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
            "cp /opt/quiche/target/release/quiche-* /app/logs/ 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_cargo_bin_name()} --listen 0.0.0.0:4443 --root /var/www"
        else:
            return f"{self._get_cargo_bin_name()} --http3 https://localhost:4443/"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the Quiche service."""
        pass

    def get_supported_features(self) -> dict:
        """Get Quiche-specific supported features."""
        features = super().get_supported_features()
        # Quiche has excellent HTTP/3 support
        features.update(
            {
                "http3": True,
                "priority": True,
                "datagram": True,
                "early_data": True,
                "cloudflare": True,
            }
        )
        return features
