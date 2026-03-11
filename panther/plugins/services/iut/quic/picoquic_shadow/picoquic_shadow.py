"""Refactored PicoQUIC Shadow service manager using base classes."""

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
    name="picoquic_shadow",
    version="2.0.0",
    description="PicoQUIC for Shadow Network Simulator ",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "shadow"],
)
class PicoquicShadowServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
):
    """Refactored PicoQUIC Shadow service manager for network simulation."""

    def __init__(self, *args, global_config=None, **kwargs):
        """Initialize PicoQUIC Shadow service manager with dual plugin config approach."""
        super().__init__(*args, global_config=global_config, **kwargs)

    def _get_implementation_name(self) -> str:
        return "picoquic_shadow"

    def _get_binary_name(self) -> str:
        return "picoquicdemo"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC Shadow server arguments with plugin config support."""
        args = []

        # Shadow-specific network interface binding - Check service config
        shadow_interface = kwargs.get("shadow_interface")
        if not shadow_interface:
            shadow_interface = getattr(
                self.service_config_to_test, "shadow_interface", None
            )

        if shadow_interface:
            args.extend(["-i", shadow_interface])

        # Shadow hostname binding - Check service config
        shadow_hostname = kwargs.get("shadow_hostname")
        if not shadow_hostname:
            shadow_hostname = getattr(
                self.service_config_to_test, "shadow_hostname", None
            )

        if shadow_hostname:
            args.extend(["-n", shadow_hostname])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC Shadow client arguments with plugin config support."""
        args = []

        # Shadow-specific target resolution - Check service config
        shadow_target = kwargs.get("shadow_target")
        if not shadow_target:
            shadow_target = getattr(self.service_config_to_test, "shadow_target", None)

        if shadow_target:
            # Replace localhost with shadow target
            return args

        # Multiple connection attempts for shadow timing - Check service config
        connection_attempts = kwargs.get("connection_attempts")
        if not connection_attempts:
            connection_attempts = getattr(
                self.service_config_to_test, "connection_attempts", None
            )

        if connection_attempts:
            args.extend(["-R", str(connection_attempts)])

        return args

    def _extract_common_params(self, **kwargs):
        """Extract Shadow-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # Shadow network simulation parameters
        params["shadow_interface"] = kwargs.get("shadow_interface")
        params["shadow_hostname"] = kwargs.get("shadow_hostname")
        params["shadow_target"] = kwargs.get("shadow_target")

        # Replace localhost with shadow hostname if specified
        if params.get("shadow_hostname") and params["host"] == "localhost":
            params["host"] = params["shadow_hostname"]

        return params

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get phase-based output patterns for PicoQUIC Shadow service.

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
            ("picoquic_binary", "artifacts/picoquicdemo"),
            ("shadow_logs", "artifacts/shadow.*"),
            ("shadow_config", "artifacts/shadow.config.xml"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """Shadow-specific post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binary to artifacts (not root logs)
            "cp /opt/picoquic/picoquicdemo /app/logs/artifacts/picoquicdemo 2>/dev/null || true;",
            # Copy Shadow simulation files to artifacts
            'find /tmp -name "shadow.*" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
            # Copy any QUIC logs to artifacts
            'find /tmp -name "*.qlog" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;',
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for Shadow compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -p 4443"
        else:
            return f"{self._get_binary_name()} localhost 4443"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the PicoQUIC Shadow service."""
        pass

    def get_supported_features(self) -> dict:
        """Get Shadow-specific supported features."""
        features = super().get_supported_features()
        # Shadow simulation features
        features.update(
            {
                "shadow": True,
                "network_simulation": True,
                "deterministic": True,
                "scalable": True,
            }
        )
        return features
