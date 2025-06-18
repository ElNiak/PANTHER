"""quic package.

This package is part of the PANTHER framework.
"""

# Import the QUIC protocol plugin to ensure it's registered
try:
    from .quic_protocol import QUICProtocol
except ImportError:
    pass  # Protocol plugin may not be needed in all contexts
