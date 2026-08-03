"""CoAP Protocol Plugin.

Registers CoAP-4 (RFC 7252) as a client-server protocol in PANTHER.
CoAP uses UDP port 5683 for session establishment between autonomous systems.
"""

from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.protocol_interface import IProtocolManager


@register_protocol(
    name="coap",
    type="client_server",
    versions=["rfc7252"],
    default_version="rfc7252",
    description="CoAP  (RFC 7252) is a specialized web transfer protocol for use with constrained nodes and constrained networks in the Internet of Things (IoT).",
    author="IETF IDR Working Group",
    license="IETF",
    homepage="https://datatracker.ietf.org/doc/html/rfc7252",
    capabilities=[
        "route-advertisement",
        "as-path",
        "communities",
        "fsm",
        "keepalive",
        "notification",
    ],
    tags=["udp", "tcp", "client-server", "coap"],
    config_schema={
        "hold_time": {
            "type": "integer",
            "default": 180,
            "description": "Hold timer in seconds (0 = no keepalives)",
        },
        "CoAP_version": {
            "type": "integer",
            "default": 4,
            "description": "CoAP protocol version",
        },
    },
    default_config={
        "hold_time": 180,
        "CoAP_version": 4,
    },
)
class CoAPProtocol(IProtocolManager):
    """CoAP-4 Protocol Manager."""

    def __init__(self):
        """Initialize CoAP protocol manager."""
        self._metadata = self.get_protocol_metadata()

    def validate_config(self):
        """Validate CoAP protocol configuration."""
        pass

    def load_config(self) -> dict:
        """Load CoAP protocol default configuration.

        Returns:
            dict: Default CoAP configuration parameters.
        """
        return self._metadata.get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """Get version-specific CoAP protocol parameters.

        Args:
            version: CoAP version identifier (e.g., 'rfc7252').

        Returns:
            dict: Version-specific parameters including port and timer values.
        """
        if version == "rfc7252":
            return {
                "port": 5683,
                "hold_time": 180,
                "keepalive_interval": 60,
                "CoAP_version": 4,
            }
        return {}

    @classmethod
    def get_default_server_port(cls) -> int:
        """Get the default CoAP server port.

        Returns:
            int: CoAP well-known UDP port (5683).
        """
        return 5683

    @classmethod
    def get_default_client_port(cls) -> int:
        """Get the default CoAP client port.

        Returns:
            int: Ephemeral port (0), assigned by the OS.
        """
        return 0


import logging  # noqa: E402

logging.getLogger(__name__)
