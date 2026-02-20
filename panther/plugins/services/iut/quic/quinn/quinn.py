"""Refactored Quinn service manager using base classes."""

from pathlib import Path
from typing import List, Optional, Tuple

from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig


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

        # Cache plugin config for easy access
        self._plugin_config = None

    def _get_plugin_config(self) -> Optional[QuinnConfig]:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.service_config_to_test.get_plugin_config(
                    QuinnConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                # Create default config
                self._plugin_config = QuinnConfig()
        return self._plugin_config

    def _get_implementation_name(self) -> str:
        return "quinn"

    def _get_cargo_bin_name(self) -> str:
        # Quinn uses different examples for client and server
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quinn server specific arguments with plugin config support."""
        args = []

        # Get plugin config values with fallbacks
        plugin_config = self._get_plugin_config()

        # Listen address and port - Modern unified approach
        listen_addr = (
            kwargs.get("listen")
            or getattr(  # Command line override
                plugin_config.version.server, "listen", None
            )
            if plugin_config.version.server
            else None or "0.0.0.0:4443"  # Plugin config  # Default
        )
        args.append(listen_addr)

        # Certificate and key files - Modern unified approach
        cert = (
            kwargs.get("cert")
            or getattr(  # Command line override
                plugin_config.version.server, "cert", None
            )
            if plugin_config.version.server
            else None  # Plugin config
        )
        key = (
            kwargs.get("key")
            or getattr(  # Command line override
                plugin_config.version.server, "key", None
            )
            if plugin_config.version.server
            else None  # Plugin config
        )

        if cert and key:
            args.extend(["--cert", cert])
            args.extend(["--key", key])

        # Enable keylog for debugging - Modern unified approach
        keylog = (
            kwargs.get("keylog")
            or getattr(  # Command line override
                plugin_config.version.server, "keylog", False
            )
            if plugin_config.version.server
            else False  # Plugin config
        )

        if keylog:
            args.append("--keylog")

        # Connection limits - Check plugin_config first
        max_concurrent_streams = kwargs.get("max_concurrent_streams")
        if (
            not max_concurrent_streams
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            max_concurrent_streams = self.service_config_to_test.plugin_config.get(
                "max_concurrent_streams"
            )
        elif (
            not max_concurrent_streams
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            max_concurrent_streams = (
                server_params.get("max_concurrent_streams") if server_params else None
            )

        if max_concurrent_streams:
            args.extend(["--max-concurrent-streams", str(max_concurrent_streams)])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quinn client specific arguments with plugin config support."""
        args = []

        # Get plugin config values with fallbacks
        plugin_config = self._get_plugin_config()

        # Target URL (Quinn client expects full URL) - Check plugin_config first
        host = kwargs.get("host")
        port = kwargs.get("port")
        path = kwargs.get("path")

        if (
            not host
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            host = self.service_config_to_test.plugin_config.get("host", "localhost")
            port = self.service_config_to_test.plugin_config.get("port", 4443)
            path = self.service_config_to_test.plugin_config.get("path")
        elif (
            not host
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            if client_params:
                host = client_params.get("host", "localhost")
                port = client_params.get("port", 4443)
                path = client_params.get("path")

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

        # Request count - Check plugin_config first
        requests = kwargs.get("requests")
        if (
            not requests
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            requests = self.service_config_to_test.plugin_config.get("requests", 1)
        elif (
            not requests
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            requests = client_params.get("requests", 1) if client_params else 1
        else:
            requests = 1

        args.extend(["--requests", str(requests)])

        # Concurrent requests - Check plugin_config first
        concurrent = kwargs.get("concurrent")
        if (
            not concurrent
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            concurrent = self.service_config_to_test.plugin_config.get("concurrent")
        elif (
            not concurrent
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            concurrent = client_params.get("concurrent") if client_params else None

        if concurrent:
            args.extend(["--concurrent", str(concurrent)])

        # Request interval - Check plugin_config first
        interval = kwargs.get("interval")
        if (
            not interval
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            interval = self.service_config_to_test.plugin_config.get("interval")
        elif (
            not interval
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            interval = client_params.get("interval") if client_params else None

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
        """
        Get phase-based output patterns for Quinn service.

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
            "find /tmp -name \"*.qlog\" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;",
            # Copy key logs to artifacts
            "find /tmp -name \"*.keylog\" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;",
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
