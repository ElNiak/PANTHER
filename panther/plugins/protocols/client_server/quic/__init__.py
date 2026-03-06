"""QUIC transport protocol plugin.

Defines protocol metadata and configuration for QUIC testing across
multiple versions: RFC 9000, draft-29, draft-27, and vulnerability
variants (draft27-vuln1, draft27-vuln2).

Manages version-specific parameters, default ports, TLS configuration,
and test scenario categories for conformance, performance, and
interoperability testing.

See `QUICProtocol` for the protocol manager and
`QuicProtocolConfig` for configuration options.
"""

import contextlib

# Import the QUIC protocol plugin to ensure it's registered
with contextlib.suppress(ImportError):
    from .quic import QUICProtocol

__all__ = [
    "QUICProtocol",
]
