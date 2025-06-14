"""Refactored MVFST service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="mvfst",
    version="2.0.0",
    description="MVFST - Meta's implementation of QUIC transport protocol (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "congestion_control"],
)
class MvfstServiceManager(BaseQUICServiceManager):
    """Refactored MVFST service manager with minimal code."""

    def _get_implementation_name(self) -> str:
        return "mvfst"

    def _get_binary_name(self) -> str:
        # MVFST uses the same binary for both client and server
        return "quic_sample"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """MVFST server specific arguments."""
        args = []

        # Server mode flag
        args.append("--mode=server")

        # Congestion control algorithm
        cc_algo = kwargs.get("congestion_control", "cubic")
        args.extend(["--congestion", cc_algo])

        # Transport settings
        if kwargs.get("idle_timeout"):
            args.extend(["--idle_timeout", str(kwargs["idle_timeout"])])

        if kwargs.get("max_packet_size"):
            args.extend(["--max_packet_size", str(kwargs["max_packet_size"])])

        # Flow control settings
        if kwargs.get("flow_control_window"):
            args.extend(["--flow_control_window", str(kwargs["flow_control_window"])])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """MVFST client specific arguments."""
        args = []

        # Client mode flag
        args.append("--mode=client")

        # Connection parameters
        if kwargs.get("num_requests"):
            args.extend(["--num_requests", str(kwargs["num_requests"])])
        else:
            args.extend(["--num_requests", "1"])

        # Request body size
        if kwargs.get("body_size"):
            args.extend(["--body", str(kwargs["body_size"])])

        # Congestion control
        cc_algo = kwargs.get("congestion_control", "cubic")
        args.extend(["--congestion", cc_algo])

        # Happy Eyeballs
        if kwargs.get("happy_eyeballs", True):
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

    def generate_post_run_commands(self) -> List[str]:
        """MVFST post-run cleanup."""
        return [
            "cp /opt/mvfst/build/quic/samples/quic_sample /app/logs/ 2>/dev/null || true;",
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
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
