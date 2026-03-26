"""Refactored quic-go service manager using base classes."""

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
    name="quic_go",
    version="2.0.0",
    description="quic-go - Go implementation of QUIC ",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class QuicGoServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
):
    """Refactored quic-go service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quic_go"

    def _get_binary_name(self) -> str:
        # quic-go uses example binaries
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """quic-go server specific arguments with plugin config support."""
        args = []

        # Document root for serving files - Check service config
        if kwargs.get("www"):
            www = kwargs["www"]
        else:
            www = getattr(self.service_config_to_test, "www", "/var/www")
        args.extend(["-www", www])

        # Certificate files - Check service config
        certfile = kwargs.get("certfile")
        keyfile = kwargs.get("keyfile")

        if not certfile:
            certfile = getattr(self.service_config_to_test, "certfile", None)
            keyfile = keyfile or getattr(self.service_config_to_test, "keyfile", None)

        if certfile and keyfile:
            args.extend(["-certfile", certfile])
            args.extend(["-keyfile", keyfile])

        # Enable qlog - Check service config
        qlog = kwargs.get("qlog", False)
        if not qlog:
            qlog = getattr(self.service_config_to_test, "qlog", False)

        if qlog:
            args.append("-qlog")

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """quic-go client specific arguments with plugin config support."""
        args = []

        # Target URL - Check service config
        host = kwargs.get("host")
        port = kwargs.get("port")
        path = kwargs.get("path")

        if not host:
            host = getattr(self.service_config_to_test, "host", "localhost")
            port = port or getattr(self.service_config_to_test, "port", 4443)
            path = path or getattr(self.service_config_to_test, "path", "/")

        if not host:
            host = "localhost"
        if not port:
            port = 4443
        if not path:
            path = "/"

        url = f"https://{host}:{port}{path}"
        args.append(url)

        # Insecure mode (skip cert verification) - Check service config
        insecure = kwargs.get("insecure")
        if insecure is None:
            insecure = getattr(self.service_config_to_test, "insecure", True)

        if insecure:
            args.append("-insecure")

        # Enable qlog - Check service config
        qlog = kwargs.get("qlog", False)
        if not qlog:
            qlog = getattr(self.service_config_to_test, "qlog", False)

        if qlog:
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

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for quic-go service.

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
            ("go_binaries", "artifacts/server"),
            ("go_client", "artifacts/client"),
            ("go_modules", "artifacts/go.mod"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """quic-go post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binaries to artifacts (not root logs)
            "cp /opt/quic-go/server /app/logs/artifacts/ 2>/dev/null || true;",
            "cp /opt/quic-go/client /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy Go module files to artifacts
            "cp /opt/quic-go/go.mod /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy any QUIC logs to artifacts
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
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
