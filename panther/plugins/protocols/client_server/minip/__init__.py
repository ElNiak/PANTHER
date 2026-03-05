"""MiniP (Minimal Interoperability Protocol) plugin.

A simplified protocol designed for testing the PANTHER infrastructure
itself. MiniP provides a minimal client-server handshake suitable for
validating framework functionality without full protocol complexity.

See `MiniPProtocol` for the protocol manager implementation.
"""

import contextlib

# Import the QUIC protocol plugin to ensure it's registered
with contextlib.suppress(ImportError):
    from .minip import MiniPProtocol

__all__ = [
    "MiniPProtocol",
]
