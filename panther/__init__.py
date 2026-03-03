"""PANTHER package.

PANTHER (Protocol Analysis and Testing Harness for Extensible Research) is a
framework for network protocol testing and research.
"""

__version__ = "1.2.1"  # Keep this in sync with pyproject.toml

# When installed, try to get the version from the package metadata
try:
    import importlib.metadata

    __version__ = importlib.metadata.version("panther-net")
except (importlib.metadata.PackageNotFoundError, ImportError):
    # Package is not installed, use the hardcoded version
    pass

# Export public API
__all__ = ["__version__"]
