"""
QUIC Protocol Plugin

This plugin defines the QUIC protocol metadata including supported versions,
capabilities, and configuration schema. Service implementations will
automatically discover and use the versions defined here.
"""

from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.protocol_interface import IProtocolManager


@register_protocol(
    name="quic",
    type="client_server",
    versions=[
        "rfc9000",  # RFC 9000 - QUIC version 1
        "draft29",  # IETF QUIC draft 29
        "draft27",  # IETF QUIC draft 27
        "draft27-vuln1",  # Draft 27 with vulnerability test 1
        "draft27-vuln2",  # Draft 27 with vulnerability test 2
    ],
    default_version="rfc9000",
    description="QUIC transport protocol - A UDP-based multiplexed and secure transport",
    author="IETF QUIC Working Group",
    license="IETF",
    homepage="https://datatracker.ietf.org/doc/html/rfc9000",
    capabilities=[
        "0-rtt",  # Zero round-trip time connection establishment
        "connection-migration",  # Connection migration between network paths
        "multipath",  # Multipath support (experimental)
        "stream-multiplexing",  # Multiple streams per connection
        "flow-control",  # Per-stream and connection-level flow control
        "congestion-control",  # Pluggable congestion control
        "tls-1.3",  # TLS 1.3 for security
        "loss-recovery",  # Advanced loss recovery mechanisms
        "datagram",  # Unreliable datagram extension
        "grease",  # GREASE for protocol ossification prevention
    ],
    tags=["transport", "udp", "secure", "multiplexed", "ietf"],
    config_schema={
        "initial_max_data": {
            "type": "integer",
            "default": 10485760,
            "description": "Initial maximum data limit for the connection",
        },
        "initial_max_stream_data_bidi_local": {
            "type": "integer",
            "default": 1048576,
            "description": "Initial maximum data for locally-initiated bidirectional streams",
        },
        "initial_max_stream_data_bidi_remote": {
            "type": "integer",
            "default": 1048576,
            "description": "Initial maximum data for remotely-initiated bidirectional streams",
        },
        "initial_max_stream_data_uni": {
            "type": "integer",
            "default": 1048576,
            "description": "Initial maximum data for unidirectional streams",
        },
        "initial_max_streams_bidi": {
            "type": "integer",
            "default": 100,
            "description": "Initial maximum number of bidirectional streams",
        },
        "initial_max_streams_uni": {
            "type": "integer",
            "default": 100,
            "description": "Initial maximum number of unidirectional streams",
        },
        "max_idle_timeout": {
            "type": "integer",
            "default": 30000,
            "description": "Maximum idle timeout in milliseconds",
        },
        "alpn_protocols": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["h3", "hq-interop"],
            "description": "ALPN protocols to negotiate",
        },
    },
    default_config={
        "initial_max_data": 10485760,
        "initial_max_streams_bidi": 100,
        "max_idle_timeout": 30000,
        "alpn_protocols": ["h3", "hq-interop"],
    },
)
class QUICProtocol(IProtocolManager):
    """
    QUIC Protocol Manager

    This class manages QUIC protocol configurations and provides
    version-specific parameters for QUIC implementations.
    """

    def __init__(self):
        # Skip parent init since we don't need the old YAML loading
        self.logger = logging.getLogger("QUICProtocol")

    def validate_config(self):
        """Validate protocol configuration."""
        # Configuration is validated through the schema
        pass

    def load_config(self) -> dict:
        """Load protocol configuration."""
        # Return the default config from decorator
        return self.get_protocol_metadata().get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """
        Get version-specific parameters.

        Args:
            version: Protocol version identifier

        Returns:
            Version-specific parameters
        """
        # Version-specific parameters that might differ
        version_params = {
            "rfc9000": {
                "initial_version": "00000001",
                "version_negotiation": True,
                "compatible_versions": ["rfc9000"],
            },
            "draft-29": {
                "initial_version": "ff00001d",  # 0xFF00001D
                "version_negotiation": True,
                "compatible_versions": ["draft-29"],
            },
            "draft-27": {
                "initial_version": "ff00001b",  # 0xFF00001B
                "version_negotiation": True,
                "compatible_versions": ["draft-27"],
            },
            "draft-27-vuln1": {
                "initial_version": "ff00001b",
                "version_negotiation": True,
                "compatible_versions": ["draft-27"],
                # Specific parameters for vulnerability testing
                "enable_vuln_test": "vuln1",
            },
            "draft-27-vuln2": {
                "initial_version": "ff00001b",
                "version_negotiation": True,
                "compatible_versions": ["draft-27"],
                # Specific parameters for vulnerability testing
                "enable_vuln_test": "vuln2",
            },
        }

        return version_params.get(version, {})

    @classmethod
    def get_default_server_port(cls) -> int:
        """Get the default server port for QUIC."""
        return 4443

    @classmethod
    def get_default_client_port(cls) -> int:
        """Get the default client port for QUIC (usually ephemeral)."""
        return 0  # Ephemeral port


# Import logging after class definition to avoid circular imports
import logging
