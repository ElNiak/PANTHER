"""Refactored Quinn service manager using base classes."""

from pathlib import Path
from typing import List, Tuple

from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin


@register_plugin(
    plugin_type=PluginType.IUT,
    name="quinn",
    version="2.0.0",
    description="Quinn - Async-friendly QUIC implementation in Rust (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "async"],
)
class QuinnServiceManager(IUTManagerEventMixin, RustQUICServiceManager):
    """Refactored Quinn service manager with minimal code."""

    def __init__(self, *args, global_config=None, **kwargs):
        """Initialize Quinn service manager with dual plugin config approach."""
        super().__init__(*args, global_config=global_config, **kwargs)

        # Store global configuration
        self.global_config = global_config

    def _get_implementation_name(self) -> str:
        return "quinn"

    def _get_cargo_bin_name(self) -> str:
        # Quinn uses different examples for client and server
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quinn server specific arguments with plugin config support."""
        args = []

        # Get server params from service config
        server_params = (
            self.service_config_to_test.version.server
            if hasattr(self.service_config_to_test, "version")
            and hasattr(self.service_config_to_test.version, "server")
            else None
        )

        # Listen address and port - Modern unified approach
        listen_addr = (
            kwargs.get("listen")
            or (getattr(server_params, "listen", None) if server_params else None)
            or "0.0.0.0:4443"
        )
        args.append(listen_addr)

        # Certificate and key files - Modern unified approach
        cert = kwargs.get("cert") or (
            getattr(server_params, "cert", None) if server_params else None
        )
        key = kwargs.get("key") or (
            getattr(server_params, "key", None) if server_params else None
        )

        if cert and key:
            args.extend(["--cert", cert])
            args.extend(["--key", key])

        # Enable keylog for debugging - Modern unified approach
        keylog = kwargs.get("keylog") or (
            getattr(server_params, "keylog", False) if server_params else False
        )

        if keylog:
            args.append("--keylog")

        # Connection limits - Check service config
        max_concurrent_streams = kwargs.get("max_concurrent_streams")
        if not max_concurrent_streams:
            max_concurrent_streams = getattr(
                self.service_config_to_test, "max_concurrent_streams", None
            )

        if max_concurrent_streams:
            args.extend(["--max-concurrent-streams", str(max_concurrent_streams)])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quinn client specific arguments with plugin config support."""
        args = []

        # Target URL (Quinn client expects full URL) - Check service config
        host = kwargs.get("host")
        port = kwargs.get("port")
        path = kwargs.get("path")

        if not host:
            host = getattr(self.service_config_to_test, "host", "localhost")
            port = port or getattr(self.service_config_to_test, "port", 4443)
            path = path or getattr(self.service_config_to_test, "path", None)

        if not host:
            host = "localhost"
        if not port:
            port = 4443

        # Construct URL
        url = f"https://{host}:{port}/"
        if path:
            path = path.lstrip("/")
            url = f"https://{host}:{port}/{path}"

        args.append(url)

        # Request count - Check service config
        requests = kwargs.get("requests")
        if not requests:
            requests = getattr(self.service_config_to_test, "requests", 1)

        args.extend(["--requests", str(requests)])

        # Concurrent requests - Check service config
        concurrent = kwargs.get("concurrent")
        if not concurrent:
            concurrent = getattr(self.service_config_to_test, "concurrent", None)

        if concurrent:
            args.extend(["--concurrent", str(concurrent)])

        # Request interval - Check service config
        interval = kwargs.get("interval")
        if not interval:
            interval = getattr(self.service_config_to_test, "interval", None)

        if interval:
            args.extend(["--interval", str(interval)])

        # Enable keylog for debugging
        if kwargs.get("keylog", False):
            args.append("--keylog")

        # Disable certificate verification for testing
        if kwargs.get("insecure", True):
            args.append("--insecure")

        return args

    def _extract_common_params(self, **kwargs):
        """Extract Quinn-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # Quinn-specific async runtime settings
        params["tokio_threads"] = kwargs.get("tokio_threads", "auto")
        params["async_runtime"] = kwargs.get("async_runtime", "tokio")

        return params

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for Quinn service.

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
            ("keylog", "artifacts/*.keylog"),
            ("sslkeylog", "artifacts/sslkeylogfile.txt"),
            ("keys", "artifacts/*keys.log"),
            ("pcap", "artifacts/{service_name}.pcap"),
            ("rust_binaries", "artifacts/examples/"),
            ("cargo_target", "artifacts/target/"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """Quinn post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy any QUIC logs to artifacts (not root logs)
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy key logs to artifacts
            'find /tmp -name "*.keylog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy Rust binaries to artifacts
            "cp -r /opt/quinn/target/release/examples /app/logs/artifacts/ 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_cargo_bin_name()} 0.0.0.0:4443"
        else:
            return f"{self._get_cargo_bin_name()} https://localhost:4443/ --insecure"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the Quinn service."""
        pass

    def get_supported_features(self) -> dict:
        """Get Quinn-specific supported features."""
        features = super().get_supported_features()
        # Quinn has excellent async support
        features.update(
            {
                "async": True,
                "tokio": True,
                "concurrent_streams": True,
                "connection_pooling": True,
                "performance": True,
            }
        )
        return features
