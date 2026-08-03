"""CoAP Protocol Plugin.

Registers CoAP (RFC 7252) as a client-server protocol in PANTHER.
CoAP runs over UDP on the registered port 5683 (5684 for coaps) and targets
constrained nodes and constrained networks.
"""

from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.protocol_interface import IProtocolManager


@register_protocol(
    name="coap",
    type="client_server",
    versions=["rfc7252"],
    default_version="rfc7252",
    description="CoAP (RFC 7252) is a specialized web transfer protocol for use with constrained nodes and constrained networks in the Internet of Things (IoT).",
    author="IETF CoRE Working Group",
    license="IETF",
    homepage="https://datatracker.ietf.org/doc/html/rfc7252",
    capabilities=[
        "confirmable-messages",
        "non-confirmable-messages",
        "retransmission",
        "message-deduplication",
        "token-matching",
        "content-negotiation",
        "proxying",
        "multicast",
    ],
    tags=["udp", "client-server", "coap", "constrained"],
    config_schema={
        "coap_version": {
            "type": "integer",
            "default": 1,
            "description": "CoAP version field; RFC 7252 section 3 requires 1",
        },
        "ack_timeout": {
            "type": "number",
            "default": 2.0,
            "description": "ACK_TIMEOUT, seconds (RFC 7252 section 4.8)",
        },
        "ack_random_factor": {
            "type": "number",
            "default": 1.5,
            "description": "ACK_RANDOM_FACTOR (RFC 7252 section 4.8)",
        },
        "max_retransmit": {
            "type": "integer",
            "default": 4,
            "description": "MAX_RETRANSMIT (RFC 7252 section 4.8)",
        },
        "nstart": {
            "type": "integer",
            "default": 1,
            "description": "NSTART, parallel interactions (RFC 7252 section 4.8)",
        },
        "default_leisure": {
            "type": "number",
            "default": 5.0,
            "description": "DEFAULT_LEISURE, seconds (RFC 7252 section 4.8)",
        },
        "probing_rate": {
            "type": "number",
            "default": 1.0,
            "description": "PROBING_RATE, bytes/second (RFC 7252 section 4.8)",
        },
    },
    default_config={
        "coap_version": 1,
        "ack_timeout": 2.0,
        "ack_random_factor": 1.5,
        "max_retransmit": 4,
        "nstart": 1,
        "default_leisure": 5.0,
        "probing_rate": 1.0,
    },
)
class CoAPProtocol(IProtocolManager):
    """CoAP Protocol Manager."""

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
                "coap_version": 1,
                "ack_timeout": 2.0,
                "ack_random_factor": 1.5,
                "max_retransmit": 4,
                "nstart": 1,
                "default_leisure": 5.0,
                "probing_rate": 1.0,
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
