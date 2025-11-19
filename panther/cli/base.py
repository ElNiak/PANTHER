"""
Base classes for CLI subcommands.
"""

import logging
from abc import ABC, abstractmethod
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, Dict
from panther.core.utils.logging_mixin import LoggerMixin


class BaseCommand(LoggerMixin, ABC):
    """Base class for CLI subcommands - singleton pattern."""
    _instance = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    @abstractmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the subcommand parser."""
        pass

    @classmethod
    @abstractmethod
    def handle(cls, args: Any) -> int:
        """Handle the subcommand execution."""
        pass
    
    @classmethod
    def get_instance(cls) -> "BaseCommand":
        """Get or create the singleton instance of the command."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class CLIActionDispatchMixin:
    """Mixin providing standardized action dispatch for CLI commands."""

    @classmethod
    def dispatch_action(
        cls,
        args: Any,
        action_attr: str,
        action_handlers: Dict[str, Any],
        command_name: str,
    ) -> int:
        """
        Standardized action dispatch logic.

        Args:
            args: Parsed arguments
            action_attr: Attribute name for the action (e.g., 'plugins_action')
            action_handlers: Dictionary mapping action names to handler methods
            command_name: Name of the command for error messages

        Returns:
            Exit code (0 for success, 1 for error)
        """
        if not hasattr(args, action_attr) or getattr(args, action_attr) is None:
            cls.get_instance().logger.info(
                f"❌ No {command_name} action specified. Use 'panther {command_name} --help' for options."
            )
            return 1

        action = getattr(args, action_attr)
        handler = action_handlers.get(action)
        if handler:
            return handler(args)
        else:
            cls.get_instance().logger.info(f"❌ Unknown {command_name} action: {action}")
            return 1

    @classmethod
    def get_instance(cls) -> "BaseCommand":
        """Get or create the singleton instance of the command."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
