"""
Base classes for CLI subcommands.
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, _SubParsersAction
from typing import Any


class BaseCommand(ABC):
    """Base class for CLI subcommands."""

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
