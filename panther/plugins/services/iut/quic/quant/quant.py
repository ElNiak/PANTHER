"""Refactored Quant service manager using base classes."""

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
    name="quant",
    version="2.0.0",
    description="Quant - Minimal QUIC implementation ",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class QuantServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
):
    """Refactored Quant service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "quant"

    def _get_binary_name(self) -> str:
        # Quant uses different binaries
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Quant server specific arguments with plugin config support."""
        args = []

        # Document root - First try kwargs, then service config, then default
        if kwargs.get("root"):
            root = kwargs["root"]
        else:
            root = getattr(self.service_config_to_test, "server_root", "/var/www")
        args.extend(["-d", root])

        # Verbose logging - Check service config
        verbose = kwargs.get("verbose", False)
        if not verbose:
            verbose = getattr(self.service_config_to_test, "verbose", False)

        if verbose:
            args.append("-v")

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Quant client specific arguments with plugin config support."""
        args = []

        # Request URL path - First try kwargs, then service config, then default
        if kwargs.get("path"):
            path = kwargs["path"]
        else:
            path = getattr(self.service_config_to_test, "request_path", "/")
        args.extend(["-u", path])

        # Verbose logging - Check service config
        verbose = kwargs.get("verbose", False)
        if not verbose:
            verbose = getattr(self.service_config_to_test, "verbose", False)

        if verbose:
            args.append("-v")

        # Connection count - First try kwargs, then service config, then default
        if kwargs.get("connections"):
            connections = kwargs["connections"]
        else:
            connections = getattr(self.service_config_to_test, "connections", 1)

        if connections > 1:
            args.extend(["-n", str(connections)])

        return args

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for Quant service.

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
            ("quant_binaries", "artifacts/server"),
            ("quant_client", "artifacts/client"),
            ("debug_bins", "artifacts/Debug/bin/"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """Quant post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binaries to artifacts (not root logs)
            "cp /opt/quant/Debug/bin/* /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy any QUIC logs to artifacts
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -p 4443 -d /var/www"
        else:
            return f"{self._get_binary_name()} -u / localhost 4443"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the Quant service."""
        pass
