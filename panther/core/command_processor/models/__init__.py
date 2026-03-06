"""Command data models and structures.

Exports the core data models used throughout the command processing system:

- ``ShellCommand``     -- rich command representation with validation, safe
  escaping, serialization, and automatic type detection.
- ``CommandMetadata``  -- ``@dataclass`` holding execution context (criticality,
  timeout, environment) and detected properties (multiline, function, builtin,
  variable assignment, control structure, etc.).
- Shell constants      -- ``SHELL_BUILTINS``, ``SHELL_CONTROL_OPERATORS``,
  ``SHELL_CONTROL_STRUCTURES``, ``REDIRECTION_OPERATORS``.
"""

from panther.core.command_processor.models.constants import *
from panther.core.command_processor.models.shell_command import (
    CommandMetadata,
    ShellCommand,
)

__all__ = [
    "ShellCommand",
    "CommandMetadata",
    # Constants from constants.py
    "SHELL_CONTROL_OPERATORS",
    "SHELL_BUILTINS",
    "SHELL_CONTROL_STRUCTURES",
    "REDIRECTION_OPERATORS",
]
