"""
Command Processor module for structured command processing across PANTHER framework.

This module provides utilities for processing command structures in a standardized way
across different environments and service managers.
"""

from .interfaces import ICommandProcessor, IEnvironmentCommandAdapter
from .command_processor import CommandProcessor

__all__ = ["ICommandProcessor", "IEnvironmentCommandAdapter", "CommandProcessor"]
