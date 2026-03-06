"""Result collection and handling via a chain-of-responsibility pattern.

Architecture::

    ResultCollector
    └── dispatches by result type to:
        ResultHandler (abstract)
        ├── LocalStorageHandler   ← file system persistence
        ├── ValidationHandler     ← data integrity checks
        ├── ParserHandler         ← parsing and normalisation
        └── StorageHandler        ← database persistence

Each handler creates ``output_dir`` and ``log_dir`` on init and
supports chaining via ``set_next_handler()`` / ``handle()``.

The ``ResultCollector`` maintains a registry mapping result-type
strings to lists of ``ResultHandler`` instances and fans results
out through ``collect()``.

See Also:
    `panther.core.reporting`
        Report generation from collected results.
    `panther.core.outputs`
        Output directory management.
"""

# Import key modules for easier access
from . import result_collector, result_handler
from .result_handlers import *

# Define the public API
__all__ = ["result_collector", "result_handler"]
