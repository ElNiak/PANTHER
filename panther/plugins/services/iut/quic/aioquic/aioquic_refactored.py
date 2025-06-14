"""Refactored aioquic service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="aioquic",
    version="2.0.0",
    description="aioquic - Python QUIC implementation with asyncio (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic", "http3"],
    capabilities=["rfc9000", "0rtt", "migration", "http3", "asyncio"],
)
class AioquicServiceManager(PythonQUICServiceManager):
    """Refactored aioquic service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "aioquic"

    def _get_python_module(self) -> str:
        # aioquic uses different examples for client and server
        return (
            "aioquic.http3.server" if self.role == "server" else "aioquic.http3.client"
        )

    def _get_binary_name(self) -> str:
        """aioquic uses example scripts."""
        if self.role == "server":
            return "python /opt/aioquic/examples/http3_server.py"
        else:
            return "python /opt/aioquic/examples/http3_client.py"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """aioquic server specific arguments."""
        args = []

        # Listen host and port
        host = kwargs.get("host", "0.0.0.0")
        port = kwargs.get("port", 4443)
        args.extend(["--host", host, "--port", str(port)])

        # Certificate and key
        if kwargs.get("certificate") and kwargs.get("private_key"):
            args.extend(["--certificate", kwargs["certificate"]])
            args.extend(["--private-key", kwargs["private_key"]])
        else:
            # Use default locations
            args.extend(["--certificate", "/certs/cert.pem"])
            args.extend(["--private-key", "/certs/key.pem"])

        # Document root for serving files
        if kwargs.get("root"):
            args.extend(["--root", kwargs["root"]])
        else:
            args.extend(["--root", "/var/www"])

        # Enable verbose logging
        if kwargs.get("verbose", False):
            args.append("--verbose")

        # Enable secrets log for debugging
        if kwargs.get("secrets_log"):
            args.extend(["--secrets-log", kwargs["secrets_log"]])

        # Session ticket store
        if kwargs.get("session_ticket_store"):
            args.extend(["--session-ticket-store", kwargs["session_ticket_store"]])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """aioquic client specific arguments."""
        args = []

        # Target URL
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        path = kwargs.get("path", "/")

        url = f"https://{host}:{port}{path}"
        args.append(url)

        # Output directory
        if kwargs.get("output_dir"):
            args.extend(["--output-dir", kwargs["output_dir"]])
        else:
            args.extend(["--output-dir", "/app/logs"])

        # Enable verbose logging
        if kwargs.get("verbose", False):
            args.append("--verbose")

        # Enable secrets log for debugging
        if kwargs.get("secrets_log"):
            args.extend(["--secrets-log", kwargs["secrets_log"]])

        # Session ticket file for 0-RTT
        if kwargs.get("session_ticket"):
            args.extend(["--session-ticket", kwargs["session_ticket"]])

        # Insecure mode (skip certificate verification)
        if kwargs.get("insecure", True):
            args.append("--insecure")

        # HTTP/3 specific options
        if kwargs.get("data"):
            args.extend(["--data", kwargs["data"]])

        # Include response headers
        if kwargs.get("include", False):
            args.append("--include")

        # Legacy HTTP (downgrade to HTTP/1.1 or HTTP/2)
        if kwargs.get("legacy_http"):
            args.append("--legacy-http")

        return args

    def _extract_common_params(self, **kwargs):
        """Extract aioquic-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # aioquic-specific paths
        params["python_path"] = "/opt/aioquic"
        params["examples_dir"] = "/opt/aioquic/examples"

        return params

    def generate_run_command(self, **kwargs):
        """Generate aioquic run command with Python environment."""
        # Add Python-specific environment
        env_vars = self._build_python_env_vars(self._extract_common_params(**kwargs))

        # Call parent to get base command
        command = super().generate_run_command(**kwargs)

        # Prepend environment variables
        env_prefix = " ".join([f"{k}={v}" for k, v in env_vars.items()])
        return f"{env_prefix} {command}"

    def generate_post_run_commands(self) -> List[str]:
        """aioquic post-run cleanup."""
        return [
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
            "find /tmp -name '*.log' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
            "cp -r /opt/aioquic/examples /app/logs/ 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} --host 0.0.0.0 --port 4443 --certificate /certs/cert.pem --private-key /certs/key.pem"
        else:
            return f"{self._get_binary_name()} https://localhost:4443/ --insecure --output-dir /app/logs"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the aioquic service."""
        pass

    def get_supported_features(self) -> dict:
        """Get aioquic-specific supported features."""
        features = super().get_supported_features()
        # aioquic has excellent Python async and HTTP/3 support
        features.update(
            {
                "http3": True,
                "asyncio": True,
                "websockets": True,
                "priority": True,
                "push": True,
                "datagram": True,
            }
        )
        return features
