"""Protocol plugins for the PANTHER network testing framework.

Provides protocol-specific implementations for network protocol testing
and validation. Each protocol plugin defines metadata, configuration
schemas, and version-specific parameters.

Protocol Categories:
    - **client_server** – QUIC, HTTP, MiniP (traditional client-server)
    - **peer_to_peer** – BitTorrent (peer-to-peer)

Design Principles:
    1. **Protocol Agnostic** – core framework never hard-codes protocol logic.
    2. **Version Management** – multiple RFCs / drafts per protocol.
    3. **Configuration Driven** – all behaviour controlled via YAML + schemas.
    4. **Extensible** – new protocols added via `@register_protocol()`.
    5. **Testing Focused** – conformance, performance, and interoperability
       scenario categories.

Key Components:
    - `IProtocolManager` – abstract base providing `validate_config()`,
      `load_config()`, `get_version_parameters(version)`,
      `get_default_server_port()`, `get_default_client_port()`.
    - Protocol decorators – metadata registration for discovery
      (name, type, versions, capabilities, config_schema).
    - Version management – e.g. QUIC rfc9000, draft29, draft27,
      draft27-vuln1, draft27-vuln2.

Test Scenario Categories:
    - **Conformance** – handshake, data transfer, error handling, termination
    - **Performance** – throughput, latency, setup time, resource usage
    - **Interoperability** – version negotiation, extension support, recovery

Example:
    ```python
    from panther.plugins.protocols.client_server.quic import QUICProtocol
    protocol = QUICProtocol()
    config = protocol.load_config()
    params = protocol.get_version_parameters('rfc9000')
    ```
"""
