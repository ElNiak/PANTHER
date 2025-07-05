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
        """Initialize QUIC protocol manager.

        Sets up logging and skips parent YAML loading since configuration
        is handled through the decorator metadata system.
        """
        # Skip parent init since we don't need the old YAML loading
        self.logger = logging.getLogger("QUICProtocol")

    def validate_config(self):
        """Validate QUIC protocol configuration.

        Configuration validation is handled automatically through the schema
        defined in the register_protocol decorator. This method serves as
        a placeholder for any additional runtime validation.
        """
        # Configuration is validated through the schema
        pass

    def load_config(self) -> dict:
        """Load QUIC protocol configuration from decorator metadata.

        Returns:
            dict: Default QUIC configuration parameters including stream limits,
                  data limits, timeout values, and ALPN protocols.

        Examples:
            >>> config = self.load_config()
            >>> print(config['initial_max_data'])
            10485760
        """
        # Return the default config from decorator
        return self.get_protocol_metadata().get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """Get version-specific QUIC protocol parameters.

        Retrieves configuration parameters that are specific to a particular
        QUIC version, including version negotiation settings and vulnerability
        testing parameters.

        Args:
            version: QUIC version identifier (e.g., 'rfc9000', 'draft-27').

        Returns:
            dict: Version-specific parameters including initial version hex,
                  version negotiation flag, compatible versions list, and
                  optional vulnerability test settings.

        Examples:
            >>> params = self.get_version_parameters('rfc9000')
            >>> print(params['initial_version'])
            '00000001'
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
        """Get the default server port for QUIC connections.

        Returns:
            int: Default QUIC server port (4443).

        Note:
            Port 4443 is commonly used for QUIC as it's the HTTPS port (443)
            plus 4000, making it easy to remember and unlikely to conflict.
        """
        return 4443

    @classmethod
    def get_default_client_port(cls) -> int:
        """Get the default client port for QUIC connections.

        Returns:
            int: Ephemeral port (0), allowing the OS to assign an available port.

        Note:
            QUIC clients typically use ephemeral ports assigned by the operating
            system to avoid port conflicts and enable multiple concurrent connections.
        """
        return 0  # Ephemeral port


# Import logging after class definition to avoid circular imports
import logging
