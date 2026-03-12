"""PANTHER CLI.

Modern CLI implementation with improved user experience,
better error handling, and enhanced maintainability.
"""

from panther import __version__

from .core.main import cli

__all__ = ["cli", "__version__"]
