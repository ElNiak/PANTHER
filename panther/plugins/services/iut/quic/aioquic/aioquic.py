"""Refactored aioquic service manager using base classes."""

from pathlib import Path
from typing import List, Tuple

from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager
from panther.plugins.services.service_event_mixin import ServiceManagerEventMixin


@register_plugin(
    plugin_type=PluginType.IUT,
    name="aioquic",
    version="2.0.0",
    description="aioquic - Python QUIC implementation with asyncio ",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "asyncio"],
)
class AioquicServiceManager(ServiceManagerEventMixin, PythonQUICServiceManager):
    """Refactored aioquic service manager with minimal code."""

    def __init__(self, service_config=None, global_config=None, **kwargs):
        """Initialize with service config for plugin config access."""
        super().__init__(
            service_config=service_config, global_config=global_config, **kwargs
        )

        # Store global configuration
        self.global_config = global_config
        self.service_config = service_config

    def _get_implementation_name(self) -> str:
        return "aioquic"

    def _get_python_module(self) -> str:
        # aioquic uses different examples for client and server
        return (
            "aioquic.http3.server" if self.role == "server" else "aioquic.http3.client"
        )

    def _get_binary_name(self) -> str:
        """Aioquic uses example scripts."""
        if self.role == "server":
            return "python /opt/aioquic/examples/http3_server.py"
        else:
            return "python /opt/aioquic/examples/http3_client.py"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Aioquic server specific arguments."""
        args = []

        # Listen host and port
        host = kwargs.get("host", "0.0.0.0")
        port = kwargs.get("port", 4443)
        args.extend(["--host", host, "--port", str(port)])

        # Get plugin config values with fallbacks
        certificate = kwargs.get("certificate")
        private_key = kwargs.get("private_key")
        root = kwargs.get("root")
        verbose = kwargs.get("verbose", False)
        secrets_log = kwargs.get("secrets_log")
        session_ticket_store = kwargs.get("session_ticket_store")

        # Use direct attribute access on service_config_to_test as fallbacks
        certificate = certificate or getattr(
            self.service_config_to_test, "server_certificate", "/certs/cert.pem"
        )
        private_key = private_key or getattr(
            self.service_config_to_test, "server_private_key", "/certs/key.pem"
        )
        root = root or getattr(self.service_config_to_test, "server_root", "/var/www")
        verbose = verbose or getattr(self.service_config_to_test, "verbose", False)
        secrets_log = secrets_log or getattr(
            self.service_config_to_test, "secrets_log", None
        )
        session_ticket_store = session_ticket_store or getattr(
            self.service_config_to_test, "session_ticket_store", None
        )

        # Certificate and key
        if certificate and private_key:
            args.extend(["--certificate", certificate])
            args.extend(["--private-key", private_key])
        else:
            # Use default locations
            args.extend(["--certificate", "/certs/cert.pem"])
            args.extend(["--private-key", "/certs/key.pem"])

        # Document root for serving files
        if root:
            args.extend(["--root", root])
        else:
            args.extend(["--root", "/var/www"])

        # Enable verbose logging
        if verbose:
            args.append("--verbose")

        # Enable secrets log for debugging
        if secrets_log:
            args.extend(["--secrets-log", secrets_log])

        # Session ticket store
        if session_ticket_store:
            args.extend(["--session-ticket-store", session_ticket_store])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Aioquic client specific arguments."""
        args = []

        # Target URL
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        path = kwargs.get("path", "/")

        url = f"https://{host}:{port}{path}"
        args.append(url)

        # Get plugin config values with fallbacks
        output_dir = kwargs.get("output_dir")
        verbose = kwargs.get("verbose", False)
        secrets_log = kwargs.get("secrets_log")
        session_ticket = kwargs.get("session_ticket")
        insecure = kwargs.get("insecure", True)
        data = kwargs.get("data")
        include = kwargs.get("include", False)
        legacy_http = kwargs.get("legacy_http")

        # Use direct attribute access on service_config_to_test as fallbacks
        output_dir = output_dir or getattr(
            self.service_config_to_test, "client_output_dir", "/app/logs/artifacts"
        )
        verbose = verbose or getattr(self.service_config_to_test, "verbose", False)
        secrets_log = secrets_log or getattr(
            self.service_config_to_test, "secrets_log", None
        )
        insecure = (
            insecure
            if kwargs.get("insecure") is not None
            else getattr(self.service_config_to_test, "client_insecure", True)
        )
        legacy_http = legacy_http or getattr(
            self.service_config_to_test, "client_legacy_http", False
        )

        # Output directory
        if output_dir:
            args.extend(["--output-dir", output_dir])
        else:
            args.extend(["--output-dir", "/app/logs/artifacts"])

        # Enable verbose logging
        if verbose:
            args.append("--verbose")

        # Enable secrets log for debugging
        if secrets_log:
            args.extend(["--secrets-log", secrets_log])

        # Session ticket file for 0-RTT
        if session_ticket:
            args.extend(["--session-ticket", session_ticket])

        # Insecure mode (skip certificate verification)
        if insecure:
            args.append("--insecure")

        # HTTP/3 specific options
        if data:
            args.extend(["--data", data])

        # Include response headers
        if include:
            args.append("--include")

        # Legacy HTTP (downgrade to HTTP/1.1 or HTTP/2)
        if legacy_http:
            args.append("--legacy-http")

        return args

    def _extract_common_params(self, **kwargs):
        """Extract aioquic-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # Get plugin config values
        python_path = "/opt/aioquic"
        examples_dir = "/opt/aioquic/examples"

        # Use direct attribute access on service_config_to_test
        python_path = getattr(self.service_config_to_test, "python_path", python_path)
        examples_dir = getattr(
            self.service_config_to_test, "examples_dir", examples_dir
        )

        # aioquic-specific paths
        params["python_path"] = python_path
        params["examples_dir"] = examples_dir

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

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for aioquic service.

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
            ("http3_logs", "artifacts/*http3*.log"),
            ("examples", "artifacts/examples/"),
            ("python_logs", "artifacts/*.log"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """Aioquic post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy any QUIC logs to artifacts (not root logs)
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy general logs to artifacts
            'find /tmp -name "*.log" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy examples directory to artifacts
            "cp -r /opt/aioquic/examples /app/logs/artifacts/ 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} --host 0.0.0.0 --port 4443 --certificate /certs/cert.pem --private-key /certs/key.pem"
        else:
            return f"{self._get_binary_name()} https://localhost:4443/ --insecure --output-dir /app/logs/artifacts"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the aioquic service."""
        pass

    def get_supported_features(self) -> dict:
        """Get aioquic-specific supported features."""
        features = super().get_supported_features()

        # Default feature flags
        http3 = True
        asyncio = True
        websockets = True
        priority = True
        push = True
        datagram = True

        # Use direct attribute access on service_config_to_test
        http3 = getattr(self.service_config_to_test, "enable_http3", http3)
        websockets = getattr(
            self.service_config_to_test, "enable_websockets", websockets
        )
        priority = getattr(self.service_config_to_test, "enable_priority", priority)
        push = getattr(self.service_config_to_test, "enable_push", push)
        datagram = getattr(self.service_config_to_test, "enable_datagram", datagram)

        # aioquic has excellent Python async and HTTP/3 support
        features.update(
            {
                "http3": http3,
                "asyncio": asyncio,
                "websockets": websockets,
                "priority": priority,
                "push": push,
                "datagram": datagram,
            }
        )
        return features
