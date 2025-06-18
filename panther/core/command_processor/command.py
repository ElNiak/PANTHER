"""
Command processing - now uses the merged implementation.

This file maintains backward compatibility while delegating to the merged implementation.
The original implementation has been preserved in command_original.py for reference.
"""

# Import all necessary items from the merged implementation
from .shell_command import ShellCommand, CommandMetadata

# Import constants that were originally defined here
from .constants import (
    SHELL_CONTROL_OPERATORS,
    SHELL_BUILTINS,
    SHELL_CONTROL_STRUCTURES,
    REDIRECTION_OPERATORS,
)

# Import utility functions
from .shell_utils import (
    escape_shell_command,
    normalize_command_ending,
    parse_command_with_redirections,
    split_complex_command,
    combine_shell_constructs,
)

# Import other necessary components
from .command_summarizer import CommandSummarizer

# Export all for backward compatibility
__all__ = [
    "ShellCommand",
    "CommandMetadata",
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