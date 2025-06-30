"""
Command Processor module for structured command processing across PANTHER framework.

This module provides utilities for processing command structures in a standardized way
across different environments and service managers.
"""

from panther.core.command_processor.builders import (
    CommandBuilder,
    ServiceCommandBuilder,
)

# Import from sub-modules for backward compatibility
from panther.core.command_processor.core import (
    CommandProcessor,
    ICommandProcessor,
    IEnvironmentCommandAdapter,
)
from panther.core.command_processor.mixins import (
    CommandEventMixin,
    CommandModificationMixin,
)
from panther.core.command_processor.models import CommandMetadata, ShellCommand

# Import constants that were originally defined in command.py
from panther.core.command_processor.models.constants import (
    REDIRECTION_OPERATORS,
    SHELL_BUILTINS,
    SHELL_CONTROL_OPERATORS,
    SHELL_CONTROL_STRUCTURES,
)
from panther.core.command_processor.utils import CommandGenerationError, CommandUtils

# Import utility functions that were in command.py
from panther.core.command_processor.utils.shell_utils import (
    combine_shell_constructs,
    escape_shell_command,
    normalize_command_ending,
    parse_command_with_redirections,
    split_complex_command,
)

# Import other necessary components that were in command.py
from panther.core.command_processor.utils.summarizer import CommandSummarizer

__all__ = [
    "ICommandProcessor",
    "IEnvironmentCommandAdapter",
    "CommandProcessor",
    "CommandEventMixin",
    "CommandUtils",
    "CommandGenerationError",
    "ShellCommand",
    "CommandMetadata",
    "CommandModificationMixin",
    "CommandBuilder",
    "ServiceCommandBuilder",
    # From command.py
    "SHELL_CONTROL_OPERATORS",
    "SHELL_BUILTINS",
    "SHELL_CONTROL_STRUCTURES",
    "REDIRECTION_OPERATORS",
    "escape_shell_command",
    "normalize_command_ending",
    "parse_command_with_redirections",
    "split_complex_command",
    "combine_shell_constructs",
    "CommandSummarizer",
]
