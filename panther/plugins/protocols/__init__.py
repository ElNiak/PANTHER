"""Protocol plugins for the PANTHER network testing framework.

This package provides protocol-specific implementations for network protocol
testing and validation. Each protocol plugin defines metadata, configuration
schemas, and version-specific parameters for testing network services.

The package supports two main protocol categories:
    - client_server: Traditional client-server protocols (QUIC, HTTP, etc.)
    - peer_to_peer: Peer-to-peer protocols (BitTorrent, etc.)

Key Components:
    - IProtocolManager: Abstract base class for protocol implementations
    - Protocol decorators: Metadata registration system for protocol discovery
    - Configuration schemas: Validation and parameter management
    - Version management: Support for multiple protocol versions and variants

Examples:
    >>> from panther.plugins.protocols.client_server.quic import QUICProtocol
    >>> protocol = QUICProtocol()
    >>> config = protocol.load_config()
    >>> params = protocol.get_version_parameters('rfc9000')
"""
