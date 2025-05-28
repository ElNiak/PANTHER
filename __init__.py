"""module package.

This package is part of the PANTHER framework.
"""

# Re-export package version from the main package
try:
    from panther import __version__
except ImportError:
    __version__ = "1.1.0"  # Fallback if panther package isn't importable yet

# Define the public API
__all__ = ["__version__"]