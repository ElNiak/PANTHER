"""Refactored PicoQUIC Shadow service manager using base classes."""

from pathlib import Path
from typing import List

from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


@register_plugin(
    plugin_type="iut",
    name="picoquic_shadow",
    version="2.0.0",
    description="PicoQUIC for Shadow Network Simulator (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "shadow"],
)
class PicoquicShadowServiceManager(BaseQUICServiceManager):
    """Refactored PicoQUIC Shadow service manager for network simulation."""

    def _get_implementation_name(self) -> str:
        return "picoquic_shadow"

    def _get_binary_name(self) -> str:
        return "picoquicdemo"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC Shadow server arguments."""
        args = []

        # Shadow-specific network interface binding
        if kwargs.get("shadow_interface"):
            args.extend(["-i", kwargs["shadow_interface"]])

        # Shadow hostname binding
        if kwargs.get("shadow_hostname"):
            args.extend(["-n", kwargs["shadow_hostname"]])

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC Shadow client arguments."""
        args = []

        # Shadow-specific target resolution
        if kwargs.get("shadow_target"):
            # Replace localhost with shadow target
            return args

        # Multiple connection attempts for shadow timing
        if kwargs.get("connection_attempts"):
            args.extend(["-R", str(kwargs["connection_attempts"])])

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

    def generate_post_run_commands(self) -> List[str]:
        """Shadow-specific post-run cleanup."""
        return [
            "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;",
            "find /tmp -name 'shadow.*' -exec cp {} /app/logs/ \\; 2>/dev/null || true;",
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
