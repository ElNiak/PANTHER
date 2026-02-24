"""
PANTHER Results Package

Provides result collection and handling via a chain-of-responsibility pattern.

Components:
- ResultCollector: Type-based handler registry. Maps result type strings to lists
  of ResultHandler instances and dispatches results to them via collect().
- ResultHandler: Abstract base class for chain-of-responsibility handlers.
  Creates output_dir and log_dir on init. Provides set_next_handler() and handle().
- result_handlers/: Specialized handler implementations:
  - LocalStorageHandler: File system result storage
  - ValidationHandler: Result data validation
  - ParserHandler: Result parsing and normalization
  - StorageHandler: Database/persistent storage
"""

# Import key modules for easier access
from . import result_collector, result_handler
from .result_handlers import *

# Define the public API
__all__ = ["result_collector", "result_handler"]
