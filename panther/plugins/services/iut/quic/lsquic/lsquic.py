"""Refactored LSQUIC service manager using base classes."""

from pathlib import Path
from typing import List, Tuple

from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)


@register_plugin(
    plugin_type=PluginType.IUT,
    name="lsquic",
    version="2.0.0",
    description="LSQUIC - LiteSpeed's QUIC and HTTP/3 implementation ",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "push"],
)
class LsquicServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
):
    """Refactored LSQUIC service manager with minimal code."""

    def __init__(self, service_config=None, global_config=None, **kwargs):
        """Initialize with service config for plugin config access."""
        super().__init__(
            service_config=service_config, global_config=global_config, **kwargs
        )
        self.service_config = service_config

    def _get_implementation_name(self) -> str:
        return "lsquic"

    def _get_binary_name(self) -> str:
        # LSQUIC uses different binaries for client and server
        return "http_server" if self.role == "server" else "http_client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """LSQUIC server specific arguments."""
        args = []

        # Get plugin config values with fallbacks
        doc_root = kwargs.get("doc_root")
        enable_push = kwargs.get("enable_push", True)
        max_conns = kwargs.get("max_conns")

        # Use direct attribute access on service_config_to_test as fallbacks
        doc_root = doc_root or getattr(
            self.service_config_to_test, "doc_root", "/var/www"
        )
        enable_push = (
            enable_push
            if kwargs.get("enable_push") is not None
            else getattr(self.service_config_to_test, "enable_push", True)
        )
        max_conns = max_conns or getattr(self.service_config_to_test, "max_conns", None)

        # Document root for serving files
        if doc_root:
            args.extend(["-s", doc_root])
        else:
            args.extend(["-s", "/var/www"])

        # Enable HTTP/3 PUSH if supported
        if enable_push:
            args.append("-p")

        # Connection limits
        if max_conns:
            args.extend(["-m", str(max_conns)])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """LSQUIC client specific arguments."""
        args = []

        # Get plugin config values with fallbacks
        request_path = kwargs.get("request_path", "/")
        method = kwargs.get("method", "GET")
        headers = kwargs.get("headers", {})
        output_file = kwargs.get("output_file")

        # Use direct attribute access on service_config_to_test as fallbacks
        request_path = (
            request_path
            if kwargs.get("request_path") is not None
            else getattr(self.service_config_to_test, "request_path", "/")
        )
        method = (
            method
            if kwargs.get("method") is not None
            else getattr(self.service_config_to_test, "method", "GET")
        )
        headers = headers or getattr(self.service_config_to_test, "headers", {})
        output_file = output_file or getattr(
            self.service_config_to_test, "output_file", None
        )

        # Request path
        path = request_path
        if not path.startswith("/"):
            path = "/" + path
        args.extend(["-p", path])

        # HTTP method
        args.extend(["-X", method])

        # Request headers
        if headers:
            for header, value in headers.items():
                args.extend(["-H", f"{header}: {value}"])

        # Output file
        if output_file:
            args.extend(["-o", output_file])

        return args

    def _extract_common_params(self, **kwargs):
        """Extract LSQUIC-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # Get plugin config values
        library_path = "/opt/lsquic/lib"
        logs_dir = "/app/logs/artifacts"

        # Use direct attribute access on service_config_to_test
        library_path = getattr(
            self.service_config_to_test, "library_path", library_path
        )
        logs_dir = getattr(self.service_config_to_test, "logs_dir", logs_dir)

        # LSQUIC uses different environment variables
        params["library_path"] = library_path
        params["logs_dir"] = logs_dir

        return params

    def generate_run_command(self, **kwargs):
        """Generate LSQUIC run command with environment setup."""
        # Extract parameters including plugin config
        params = self._extract_common_params(**kwargs)

        # Add LSQUIC-specific environment
        env_vars = {
            "LD_LIBRARY_PATH": params["library_path"],
            "LSQUIC_LOGS_DIR": params["logs_dir"],
        }

        # Call parent with environment
        command = super().generate_run_command(**kwargs)

        # Prepend environment variables to command
        env_prefix = " ".join([f"{k}={v}" for k, v in env_vars.items()])
        return f"{env_prefix} {command}"

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for LSQUIC service.

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
            ("lsquic_logs", "artifacts/lsquic/"),
            ("http_binaries", "artifacts/http_server"),
            ("http_client", "artifacts/http_client"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """LSQUIC post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binaries to artifacts (not root logs)
            "cp /opt/lsquic/bin/* /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy LSQUIC logs to artifacts
            "cp -r /app/logs/artifacts/* /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy any QUIC logs to artifacts
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
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

        # Default feature flags
        http3 = True
        push = True
        priority = True
        multipath = False  # Not yet supported

        # LSQUIC has excellent HTTP/3 support
        features.update(
            {
                "http3": http3,
                "push": push,
                "priority": priority,
                "multipath": multipath,
            }
        )
        return features
