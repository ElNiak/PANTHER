"""PANTHER web application.

This package provides a web dashboard for PANTHER experiment management,
built on NiceGUI + NiceCRUD + FastAPI.

Install with: pip install panther-net[web]
Run with: panther web
"""

__all__ = ["create_app"]


def create_app(**kwargs):
    """Create and configure the NiceGUI web application.

    Lazy import to avoid requiring web dependencies when not using the webapp.
    """
    try:
        from panther.webapp.app import create_app as _create_app
    except ImportError as e:
        raise ImportError(
            "Web dependencies not installed. "
            "Install with: pip install panther-net[web]"
        ) from e
    return _create_app(**kwargs)
