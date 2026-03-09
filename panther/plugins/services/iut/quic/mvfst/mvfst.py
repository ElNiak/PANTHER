"""Refactored MVFST service manager using base classes."""

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
    name="mvfst",
    version="2.0.0",
    description="MVFST - Meta's implementation of QUIC transport protocol (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "congestion_control"],
)
class MvfstServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
):
    """Refactored MVFST service manager with minimal code."""

    def __init__(self, *args, global_config=None, **kwargs):
        """Initialize MVfst service manager with dual plugin config approach."""
        super().__init__(*args, global_config=global_config, **kwargs)

    def _get_implementation_name(self) -> str:
        return "mvfst"

    def _get_binary_name(self) -> str:
        # MVFST uses the same binary for both client and server
        return "quic_sample"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """MVFST server specific arguments with plugin config support."""
        args = []

        # Server mode flag
        args.append("--mode=server")

        # Congestion control algorithm - Check service config
        cc_algo = kwargs.get("congestion_control")
        if not cc_algo:
            cc_algo = getattr(
                self.service_config_to_test, "congestion_control", "cubic"
            )
        args.extend(["--congestion", cc_algo])

        # Transport settings - Check service config
        idle_timeout = kwargs.get("idle_timeout")
        if not idle_timeout:
            idle_timeout = getattr(self.service_config_to_test, "idle_timeout", None)

        if idle_timeout:
            args.extend(["--idle_timeout", str(idle_timeout)])

        # Max packet size - Check service config
        max_packet_size = kwargs.get("max_packet_size")
        if not max_packet_size:
            max_packet_size = getattr(
                self.service_config_to_test, "max_packet_size", None
            )

        if max_packet_size:
            args.extend(["--max_packet_size", str(max_packet_size)])

        # Flow control settings - Check service config
        flow_control_window = kwargs.get("flow_control_window")
        if not flow_control_window:
            flow_control_window = getattr(
                self.service_config_to_test, "flow_control_window", None
            )

        if flow_control_window:
            args.extend(["--flow_control_window", str(flow_control_window)])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """MVFST client specific arguments with plugin config support."""
        args = []

        # Client mode flag
        args.append("--mode=client")

        # Connection parameters - Check service config
        num_requests = kwargs.get("num_requests")
        if not num_requests:
            num_requests = getattr(self.service_config_to_test, "num_requests", 1)
        args.extend(["--num_requests", str(num_requests)])

        # Request body size - Check service config
        body_size = kwargs.get("body_size")
        if not body_size:
            body_size = getattr(self.service_config_to_test, "body_size", None)

        if body_size:
            args.extend(["--body", str(body_size)])

        # Congestion control - Check service config
        cc_algo = kwargs.get("congestion_control")
        if not cc_algo:
            cc_algo = getattr(
                self.service_config_to_test, "congestion_control", "cubic"
            )
        args.extend(["--congestion", cc_algo])

        # Happy Eyeballs - Check service config
        happy_eyeballs = kwargs.get("happy_eyeballs")
        if happy_eyeballs is None:
            happy_eyeballs = getattr(
                self.service_config_to_test, "happy_eyeballs", True
            )

        if happy_eyeballs:
            args.append("--happy_eyeballs")

        # Early data (0-RTT)
        if kwargs.get("early_data", False):
            args.append("--early_data")

        return args

    def _map_version(self, version: str) -> str:
        """Map QUIC version to MVFST format."""
        # MVFST uses numeric version codes
        version_map = {
            "rfc9000": "1",
            "draft29": "ff00001d",
            "draft28": "ff00001c",
            "draft27": "ff00001b",
        }
        return version_map.get(version, version)

    def _extract_common_params(self, **kwargs):
        """Extract MVFST-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # MVFST specific defaults
        params["congestion_control"] = kwargs.get("congestion_control", "cubic")
        params["transport_params"] = kwargs.get("transport_params", {})

        return params

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for MVFST service.

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
            ("congestion", "artifacts/*congestion*.log"),
            ("binary", "artifacts/quic_sample"),
            ("mvfst_logs", "artifacts/*mvfst*.log"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """MVFST post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binary to artifacts (not root logs)
            "cp /opt/mvfst/build/quic/samples/quic_sample /app/logs/artifacts/quic_sample 2>/dev/null || true;",
            # Copy any QUIC logs to artifacts
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy MVFST-specific logs to artifacts
            'find /tmp -name "*mvfst*.log" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy SSL key logs to artifacts
            'find /tmp -name "*keys.log" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} --mode=server --host=0.0.0.0 --port=4443"
        else:
            return (
                f"{self._get_binary_name()} --mode=client --host=localhost --port=4443"
            )

    def _do_prepare(self, plugin_manager=None):
        """Prepare the MVFST service."""
        pass

    def get_supported_features(self) -> dict:
        """Get MVFST-specific supported features."""
        features = super().get_supported_features()
        # MVFST has advanced congestion control
        features.update(
            {
                "congestion_control": True,
                "bbr": True,
                "cubic": True,
                "copa": True,
                "flow_control": True,
                "happy_eyeballs": True,
            }
        )
        return features
