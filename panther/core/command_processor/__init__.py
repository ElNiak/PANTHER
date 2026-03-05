"""Command Processor Module - Safe Command Generation for PANTHER.

Provides structured command processing: parsing, validation, transformation,
and environment-specific adaptation for shell commands in protocol testing.

Architecture::

    ICommandProcessor (interface)
         |
    CommandProcessor (core impl + ErrorHandlerMixin)
         |
         +--> ShellCommand + CommandMetadata   (models)
         +--> CommandBuilder --> ServiceCommandBuilder   (builders)
         +--> CommandEventMixin / CommandModificationMixin   (mixins)
         +--> CommandUtils / ShellUtils / CommandSummarizer   (utils)

    5-layer design:
    1. Interfaces    -- ICommandProcessor, IEnvironmentCommandAdapter
    2. Models        -- ShellCommand, CommandMetadata, shell constants
    3. Builders      -- fluent command construction
    4. Utilities     -- escaping, parsing, combining, summarization
    5. Mixins        -- event emission, command modification

Key design principles:
    - Injection-safe command construction via ShellCommand validation
    - Multi-stage validation pipeline (structure, syntax, security)
    - Automatic detection of shell constructs
    - Shell-construct combining for split multiline commands
    - High-entropy summary logging instead of verbose command dumps

Example:
    Process a command dictionary::

        from panther.core.command_processor import CommandProcessor
        processor = CommandProcessor()
        processed = processor.process_commands(commands, target_format="generic")

    Build a command with the fluent builder::

        from panther.core.command_processor import CommandBuilder
        args = CommandBuilder().reset().add_argument("cmd").add_option("-p", "4433").build_args()
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
