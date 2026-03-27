"""Command Processor Module - Safe Command Generation for PANTHER.

Provides structured command processing: parsing, validation, transformation,
and environment-specific adaptation for shell commands in protocol testing.

Architecture::

    CommandProcessor (core impl + ErrorHandlerMixin)
         |
         +--> ShellCommand   (models)
         +--> ServiceCommandBuilder   (builders)
         +--> CommandEventMixin   (mixins)
         +--> CommandUtils / ShellUtils / CommandSummarizer   (utils)

    5-layer design:
    1. Interfaces    -- ICommandProcessor, IEnvironmentCommandAdapter
    2. Models        -- ShellCommand, CommandMetadata, shell constants
    3. Builders      -- fluent command construction
    4. Utilities     -- escaping, parsing, combining, summarization
    5. Mixins        -- event emission

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

        from panther.core.command_processor.builders import ServiceCommandBuilder
        from panther.config.core.models import ProtocolRole
        builder = ServiceCommandBuilder(role=ProtocolRole.SERVER)
"""

from panther.core.command_processor.builders import ServiceCommandBuilder
from panther.core.command_processor.core import (
    CommandProcessor,
    IEnvironmentCommandAdapter,
)
from panther.core.command_processor.mixins import CommandEventMixin
from panther.core.command_processor.models import ShellCommand
from panther.core.command_processor.utils import CommandUtils
from panther.core.command_processor.utils.summarizer import CommandSummarizer

__all__ = [
    "IEnvironmentCommandAdapter",
    "CommandProcessor",
    "CommandEventMixin",
    "CommandUtils",
    "ShellCommand",
    "ServiceCommandBuilder",
    "CommandSummarizer",
]
