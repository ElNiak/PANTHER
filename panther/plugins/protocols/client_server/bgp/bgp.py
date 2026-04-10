"""BGP Protocol Plugin.

Registers BGP-4 (RFC 4271) as a client-server protocol in PANTHER.
BGP uses TCP port 179 for session establishment between autonomous systems.
"""

from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.protocol_interface import IProtocolManager


@register_protocol(
    name="bgp",
    type="client_server",
    versions=["rfc4271"],
    default_version="rfc4271",
    description="BGP-4 path-vector routing protocol (RFC 4271)",
    author="IETF IDR Working Group",
    license="IETF",
    homepage="https://datatracker.ietf.org/doc/html/rfc4271",
    capabilities=[
        "route-advertisement",
        "as-path",
        "communities",
        "fsm",
        "keepalive",
        "notification",
    ],
    tags=["routing", "tcp", "inter-domain"],
    config_schema={
        "hold_time": {
            "type": "integer",
            "default": 180,
            "description": "Hold timer in seconds (0 = no keepalives)",
        },
        "bgp_version": {
            "type": "integer",
            "default": 4,
            "description": "BGP protocol version",
        },
    },
    default_config={
        "hold_time": 180,
        "bgp_version": 4,
    },
)
class BGPProtocol(IProtocolManager):
    """BGP-4 Protocol Manager."""

    def __init__(self):
        """Initialize BGP protocol manager."""
        self._metadata = self.get_protocol_metadata()

    def validate_config(self):
        """Validate BGP protocol configuration."""
        pass

    def load_config(self) -> dict:
        """Load BGP protocol default configuration.

        Returns:
            dict: Default BGP configuration parameters.
        """
        return self._metadata.get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """Get version-specific BGP protocol parameters.

        Args:
            version: BGP version identifier (e.g., 'rfc4271').

        Returns:
            dict: Version-specific parameters including port and timer values.
        """
        if version == "rfc4271":
            return {
                "port": 179,
                "hold_time": 180,
                "keepalive_interval": 60,
                "bgp_version": 4,
            }
        return {}

    @classmethod
    def get_default_server_port(cls) -> int:
        """Get the default BGP server port.

        Returns:
            int: BGP well-known TCP port (179).
        """
        return 179

    @classmethod
    def get_default_client_port(cls) -> int:
        """Get the default BGP client port.

        Returns:
            int: Ephemeral port (0), assigned by the OS.
        """
        return 0


import logging  # noqa: E402

logging.getLogger(__name__)
