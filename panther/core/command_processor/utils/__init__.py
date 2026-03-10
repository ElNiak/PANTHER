"""Command processing utilities.

Aggregates utility functions and helper classes:

- ``CommandUtils``       -- static helpers for creating, merging, and validating
  command structures; working-directory extraction from ``cd ... &&`` prefixes;
  and smart log summarization.
- ``CommandGenerationError`` -- exception for command generation failures.
- ``CommandSummarizer``  -- pattern-based classification, sensitive-info masking,
  and compact summarization for log output.
- Shell utilities        -- ``escape_shell_command``, ``normalize_command_ending``,
  ``parse_command_with_redirections``, ``split_complex_command``,
  ``combine_shell_constructs``, and related helpers.
"""

from panther.core.command_processor.utils.command_utils import (
    CommandGenerationError,
    CommandUtils,
)
from panther.core.command_processor.utils.shell_utils import *
from panther.core.command_processor.utils.summarizer import CommandSummarizer

__all__ = [
    "CommandUtils",
    "CommandGenerationError",
    "CommandSummarizer",
    # Shell utilities - exported from shell_utils
    "escape_shell_command",
    "escape_shell_command_without_redirections",
    "parse_command_with_redirections",
    "reconstruct_command_with_redirections",
    "normalize_command_ending",
    "split_complex_command",
    "combine_shell_constructs",
]
