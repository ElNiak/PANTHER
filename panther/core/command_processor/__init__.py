"""
Command Processor module for structured command processing across PANTHER framework.

This module provides utilities for processing command structures in a standardized way
across different environments and service managers.
"""

from .command_builder import CommandBuilder, ServiceCommandBuilder
from .command_event_mixin import CommandEventMixin
from .command_processor import CommandProcessor
from .command_utils import CommandGenerationError, CommandUtils
from .interfaces import ICommandProcessor, IEnvironmentCommandAdapter
from .command import ShellCommand, CommandMetadata

__all__ = [
    "ICommandProcessor",
    "IEnvironmentCommandAdapter",
    "CommandProcessor",
    "CommandEventMixin",
    "CommandBuilder",
    "ServiceCommandBuilder",
    "CommandUtils",
    "CommandGenerationError",
    "ShellCommand",
    "CommandMetadata",
]
