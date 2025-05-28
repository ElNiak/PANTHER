"""PANTHER web application.

This package contains the web interface for PANTHER.
"""

# Import key modules for easier access
from . import web_app
from . import experiment_setup

# Define the public API
__all__ = [
    "web_app",
    "experiment_setup"
]