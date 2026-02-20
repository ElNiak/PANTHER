"""
PANTHER Click-based CLI

Modern CLI implementation using Click framework for improved user experience,
better error handling, and enhanced maintainability.
"""

from panther import __version__

from .core.main import cli
__all__ = ["cli", "__version__"]