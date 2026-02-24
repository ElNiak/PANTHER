"""quic package.

This package is part of the PANTHER framework.
"""

import contextlib

# Import the QUIC protocol plugin to ensure it's registered
with contextlib.suppress(ImportError):
    from .quic import QUICProtocol

__all__ = [
    "QUICProtocol",
]
