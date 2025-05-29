"""PANTHER results package.

This package handles collecting and processing test results in the PANTHER framework.
"""

# Import key modules for easier access
from . import result_collector
from . import result_handler
from .result_handlers import *

# Define the public API
__all__ = ["result_collector", "result_handler"]
