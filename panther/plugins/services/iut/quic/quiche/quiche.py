"""Refactored Quiche service manager using base classes."""

from pathlib import Path
from typing import List, Optional, Tuple

from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig


@register_plugin(
    plugin_type=PluginType.IUT,
    name="quiche",
    version="2.0.0",
    description="Quiche - Cloudflare's Rust implementation of QUIC (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class QuicheServiceManager(IUTManagerEventMixin, RustQUICServiceManager):
    """Refactored Quiche service manager with minimal code."""

    def __init__(self, *args, global_config=None, **kwargs):
        """Initialize Quiche service manager with dual plugin config approach."""
        super().__init__(*args, global_config=global_config, **kwargs)

        # Store global configuration
        self.global_config = global_config

        # Cache plugin config for easy access
        self._plugin_config = None

    def _get_plugin_config(self) -> Optional[QuicheConfig]:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.service_config_to_test.get_plugin_config(
                    QuicheConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                # Create default config
                self._plugin_config = QuicheConfig()
        return self._plugin_config

    def _get_implementation_name(self) -> str:
        return "quiche"

    def _get_cargo_bin_name(self) -> str:
        # Quiche uses different binaries for client and server
        return "quiche-server" if self.role == "server" else "quiche-client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quiche server specific arguments with plugin config support."""
        args = []

        # Get plugin config values with fallbacks
        plugin_config = self._get_plugin_config()

        # Document root - Check plugin_config first
        if kwargs.get("root"):
            root = kwargs["root"]
        elif (
            hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            root = self.service_config_to_test.plugin_config.get("root", "/var/www")
        elif (
            plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            root = (
                server_params.get("root", "/var/www") if server_params else "/var/www"
            )
        else:
            root = "/var/www"
        args.extend(["--root", root])

        # Listen address - Check plugin_config first
        if kwargs.get("listen"):
            listen_addr = kwargs["listen"]
        elif (
            hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            listen_addr = self.service_config_to_test.plugin_config.get(
                "listen", "0.0.0.0:4443"
            )
        elif (
            plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            listen_addr = (
                server_params.get("listen", "0.0.0.0:4443")
                if server_params
                else "0.0.0.0:4443"
            )
        else:
            listen_addr = "0.0.0.0:4443"
        args.extend(["--listen", listen_addr])

        # Enable early data (0-RTT) - Check plugin_config first
        early_data = kwargs.get("early_data")
        if (
            early_data is None
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            early_data = self.service_config_to_test.plugin_config.get(
                "early_data", True
            )
        elif (
            early_data is None
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            early_data = (
                server_params.get("early_data", True) if server_params else True
            )
        else:
            early_data = True if early_data is None else early_data

        if early_data:
            args.append("--early-data")

        # HTTP/3 SETTINGS - Check plugin_config first
        max_field_section_size = kwargs.get("max_field_section_size")
        if (
            not max_field_section_size
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            max_field_section_size = self.service_config_to_test.plugin_config.get(
                "max_field_section_size"
            )
        elif (
            not max_field_section_size
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            max_field_section_size = (
                server_params.get("max_field_section_size") if server_params else None
            )

        if max_field_section_size:
            args.extend(["--max-field-section-size", str(max_field_section_size)])

        # Connection ID length - Check plugin_config first
        cid_len = kwargs.get("cid_len")
        if (
            not cid_len
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            cid_len = self.service_config_to_test.plugin_config.get("cid_len")
        elif (
            not cid_len
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            cid_len = server_params.get("cid_len") if server_params else None

        if cid_len:
            args.extend(["--cid-len", str(cid_len)])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quiche client specific arguments with plugin config support."""
        args = []

        # Get plugin config values with fallbacks
        plugin_config = self._get_plugin_config()

        # HTTP/3 specific arguments - Check plugin_config first
        http3 = kwargs.get("http3")
        if (
            http3 is None
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            http3 = self.service_config_to_test.plugin_config.get("http3", True)
        elif (
            http3 is None
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            http3 = client_params.get("http3", True) if client_params else True
        else:
            http3 = True if http3 is None else http3

        if http3:
            args.append("--http3")

        # Request body - Check plugin_config first
        body = kwargs.get("body")
        if (
            not body
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            body = self.service_config_to_test.plugin_config.get("body")
        elif (
            not body
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            body = client_params.get("body") if client_params else None

        if body:
            args.extend(["--body", body])

        # HTTP method - Check plugin_config first
        method = kwargs.get("method")
        if (
            not method
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            method = self.service_config_to_test.plugin_config.get("method", "GET")
        elif (
            not method
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            method = client_params.get("method", "GET") if client_params else "GET"
        else:
            method = method or "GET"
        args.extend(["--method", method])

        # Additional headers - Check plugin_config first
        headers = kwargs.get("headers")
        if (
            not headers
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            headers = self.service_config_to_test.plugin_config.get("headers")
        elif (
            not headers
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            headers = client_params.get("headers") if client_params else None

        if headers:
            for header, value in headers.items():
                args.extend(["--header", f"{header}: {value}"])

        # Output file for response - Check plugin_config first
        output = kwargs.get("output")
        if (
            not output
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            output = self.service_config_to_test.plugin_config.get("output")
        elif (
            not output
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            output = client_params.get("output") if client_params else None

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
        """
        Get phase-based output patterns for Quiche service.

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
