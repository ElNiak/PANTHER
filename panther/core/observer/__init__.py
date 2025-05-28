"""PANTHER observer package.

This package implements the observer pattern for event handling in the PANTHER framework.
"""

# Import key modules for easier access
from . import event
from . import event_manager
from . import experiment_observer
from . import gui_observer
from . import logger_observer
from . import observer_interface
from . import result_observer

# Define the public API
__all__ = [
    "event",
    "event_manager",
    "experiment_observer",
    "gui_observer",
    "logger_observer",
    "observer_interface",
    "result_observer"
]