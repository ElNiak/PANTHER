"""Core command processing functionality.

Contains the main ``CommandProcessor`` implementation, abstract interfaces
(``ICommandProcessor``, ``IEnvironmentCommandAdapter``), and the
``CommandValidator`` / ``CommandValidationResult`` security-checking pipeline.

Processing flow::

    commands dict
        --> _validate_command_structure()   (fast-fail on bad types)
        --> process_command_list()          (per-list normalization)
        --> combine_shell_constructs()      (merge split multiline blocks)
        --> ShellCommand.to_dict()          (final structured output)
"""

from panther.core.command_processor.core.interfaces import (
    ICommandProcessor,
    IEnvironmentCommandAdapter,
)
from panther.core.command_processor.core.processor import CommandProcessor
from panther.core.command_processor.core.validator import (
    CommandValidationResult,
    CommandValidator,
)

__all__ = [
    "CommandProcessor",
    "ICommandProcessor",
    "IEnvironmentCommandAdapter",
    "CommandValidator",
    "CommandValidationResult",
]
