"""Protocol plugins for the PANTHER network testing framework.

This package provides protocol-specific implementations for network protocol
testing and validation. Each protocol plugin defines metadata, configuration
schemas, and version-specific parameters for testing network services.

The package supports two main protocol categories:
    - client_server: Traditional client-server protocols (QUIC, HTTP, etc.)
    - peer_to_peer: Peer-to-peer protocols (BitTorrent, etc.)

Design Principles:
    1. **Protocol Agnostic** – core framework never hard-codes protocol logic.
    2. **Version Management** – multiple RFCs / drafts per protocol.
    3. **Configuration Driven** – all behaviour controlled via YAML + schemas.
    4. **Extensible** – new protocols added via ``@register_protocol()``.
    5. **Testing Focused** – built-in conformance, performance, and
       interoperability scenario categories.

Key Components:
    - IProtocolManager: Abstract base class for protocol implementations,
      providing ``validate_config()``, ``load_config()``,
      ``get_version_parameters(version)``, ``get_default_server_port()``,
      ``get_default_client_port()``.
    - Protocol decorators: Metadata registration system for protocol
      discovery (name, type, versions, capabilities, config_schema).
    - Configuration schemas: Validation and parameter management.
    - Version management: Support for multiple protocol versions and variants
      (e.g. QUIC rfc9000, draft29, draft27, draft27-vuln1, draft27-vuln2).

Test Scenario Categories:
    - **Conformance** – handshake, data transfer, error handling, termination
    - **Performance** – throughput, latency, setup time, resource usage
    - **Interoperability** – version negotiation, extension support, recovery

Examples:
    >>> from panther.plugins.protocols.client_server.quic import QUICProtocol
    >>> protocol = QUICProtocol()
    >>> config = protocol.load_config()
    >>> params = protocol.get_version_parameters('rfc9000')

See Also:
    :doc:`/protocol_plugins`
        Protocol plugins user guide.
"""
