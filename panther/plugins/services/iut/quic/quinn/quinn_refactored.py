"""Refactored Quinn service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="quinn",
    version="2.0.0",
    description="Quinn - Async-friendly QUIC implementation in Rust (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "async"],
)
class QuinnServiceManager(RustQUICServiceManager):
    """Refactored Quinn service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quinn"

    def _get_cargo_bin_name(self) -> str:
        # Quinn uses different examples for client and server
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quinn server specific arguments."""
        args = []

        # Listen address and port
        listen_addr = kwargs.get("listen", "0.0.0.0:4443")
        args.append(listen_addr)

        # Certificate and key files
        if kwargs.get("cert") and kwargs.get("key"):
            args.extend(["--cert", kwargs["cert"]])
            args.extend(["--key", kwargs["key"]])

        # Enable keylog for debugging
        if kwargs.get("keylog", False):
            args.append("--keylog")

        # Connection limits
        if kwargs.get("max_concurrent_streams"):
            args.extend(
                ["--max-concurrent-streams", str(kwargs["max_concurrent_streams"])]
            )

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quinn client specific arguments."""
        args = []

        # Target URL (Quinn client expects full URL)
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)

        # Construct URL
        url = f"https://{host}:{port}/"
        if kwargs.get("path"):
            path = kwargs["path"].lstrip("/")
            url = f"https://{host}:{port}/{path}"

        args.append(url)

        # Request count
        if kwargs.get("requests"):
            args.extend(["--requests", str(kwargs["requests"])])
        else:
            args.extend(["--requests", "1"])

        # Concurrent requests
        if kwargs.get("concurrent"):
            args.extend(["--concurrent", str(kwargs["concurrent"])])

        # Request interval
        if kwargs.get("interval"):
            args.extend(["--interval", str(kwargs["interval"])])

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

    def generate_post_run_commands(self) -> List[str]:
        """Quinn post-run cleanup."""
        return [
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
            "find /tmp -name '*.keylog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
            "cp /opt/quinn/target/release/examples/* /app/logs/ 2>/dev/null || true;",
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
