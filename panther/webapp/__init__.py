"""PANTHER web application.

This package contains the web interface for PANTHER.
"""

# Import key modules for easier access
from . import experiment_setup, web_app

# Define the public API
__all__ = ["web_app", "experiment_setup"]
