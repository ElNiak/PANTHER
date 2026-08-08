"""Refactored Quiche service manager using base classes."""

from pathlib import Path
from typing import List, Tuple

from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager
from panther.plugins.services.service_event_mixin import ServiceManagerEventMixin


@register_plugin(
    plugin_type=PluginType.IUT,
    name="quiche",
    version="2.0.0",
    description="Quiche - Cloudflare's Rust implementation of QUIC ",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class QuicheServiceManager(ServiceManagerEventMixin, RustQUICServiceManager):
    """Refactored Quiche service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quiche"

    def _get_cargo_bin_name(self) -> str:
        # Quiche uses different binaries for client and server
        return "quiche-server" if self.role == "server" else "quiche-client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quiche server specific arguments with plugin config support."""
        args = []

        # Document root - Check service config
        if kwargs.get("root"):
            root = kwargs["root"]
        else:
            root = getattr(self.service_config_to_test, "root", "/var/www")
        args.extend(["--root", root])

        # Listen address - Check service config
        if kwargs.get("listen"):
            listen_addr = kwargs["listen"]
        else:
            listen_addr = getattr(self.service_config_to_test, "listen", "0.0.0.0:4443")
        args.extend(["--listen", listen_addr])

        # Enable early data (0-RTT) - Check service config
        early_data = kwargs.get("early_data")
        if early_data is None:
            early_data = getattr(self.service_config_to_test, "early_data", True)

        if early_data:
            args.append("--early-data")

        # HTTP/3 SETTINGS - Check service config
        max_field_section_size = kwargs.get("max_field_section_size")
        if not max_field_section_size:
            max_field_section_size = getattr(
                self.service_config_to_test, "max_field_section_size", None
            )

        if max_field_section_size:
            args.extend(["--max-field-section-size", str(max_field_section_size)])

        # Connection ID length - Check service config
        cid_len = kwargs.get("cid_len")
        if not cid_len:
            cid_len = getattr(self.service_config_to_test, "cid_len", None)

        if cid_len:
            args.extend(["--cid-len", str(cid_len)])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quiche client specific arguments with plugin config support."""
        args = []

        # HTTP/3 specific arguments - Check service config
        http3 = kwargs.get("http3")
        if http3 is None:
            http3 = getattr(self.service_config_to_test, "http3", True)

        if http3:
            args.append("--http3")

        # Request body - Check service config
        body = kwargs.get("body")
        if not body:
            body = getattr(self.service_config_to_test, "body", None)

        if body:
            args.extend(["--body", body])

        # HTTP method - Check service config
        method = kwargs.get("method")
        if not method:
            method = getattr(self.service_config_to_test, "method", "GET")
        args.extend(["--method", method])

        # Additional headers - Check service config
        headers = kwargs.get("headers")
        if not headers:
            headers = getattr(self.service_config_to_test, "headers", None)

        if headers:
            for header, value in headers.items():
                args.extend(["--header", f"{header}: {value}"])

        # Output file for response - Check service config
        output = kwargs.get("output")
        if not output:
            output = getattr(self.service_config_to_test, "output", None)

        if output:
            args.extend(["--output", output])

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

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for Quiche service.

        Returns:
            List of (output_type, filename_pattern) tuples organized by execution phases
        """
        return [
            # Pre-compile phase outputs
            ("pre_compile_stdout", "pre-compile/stdout.log"),
            ("pre_compile_stderr", "pre-compile/stderr.log"),
            # Compile phase outputs
            ("compile_stdout", "compile/stdout.log"),
            ("compile_stderr", "compile/stderr.log"),
            # Post-compile phase outputs
            ("post_compile_stdout", "post-compile/stdout.log"),
            ("post_compile_stderr", "post-compile/stderr.log"),
            # Pre-run phase outputs
            ("pre_run_stdout", "pre-run/stdout.log"),
            ("pre_run_stderr", "pre-run/stderr.log"),
            # Runtime phase outputs (main execution)
            ("runtime_stdout", "runtime/stdout.log"),
            ("runtime_stderr", "runtime/stderr.log"),
            # Post-run phase outputs
            ("post_run_stdout", "post-run/stdout.log"),
            ("post_run_stderr", "post-run/stderr.log"),
            # Test phase outputs
            ("test_stdout", "test/stdout.log"),
            ("test_stderr", "test/stderr.log"),
            # Artifacts - protocol-specific files organized by type
            ("qlog", "artifacts/*.qlog"),
            ("sslkeylog", "artifacts/sslkeylogfile.txt"),
            ("keys", "artifacts/*keys.log"),
            ("pcap", "artifacts/{service_name}.pcap"),
            ("quiche_binaries", "artifacts/quiche-server"),
            ("quiche_client", "artifacts/quiche-client"),
            ("session_files", "artifacts/*.session"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """Quiche post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy any QUIC logs to artifacts (not root logs)
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy Quiche binaries to artifacts
            "cp /opt/quiche/target/release/quiche-* /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy session files to artifacts
            'find /tmp -name "*.session" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
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
