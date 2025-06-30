from typing import Any, Dict, List, Optional, Union

"""
Interfaces for command processing in PANTHER framework.

This module defines the interfaces for command processors and environment command adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ICommandProcessor(ABC):
    """Interface for command processing operations."""

    @abstractmethod
    def process_commands(
        self, commands: Dict[str, Any], target_format: str = "generic"
    ) -> Dict[str, Any]:
        """
        Process a command structure into a target format.

        Args:
            commands: Dictionary containing command structure
            target_format: Target format identifier

        Returns:
            Dictionary with processed commands
        """

    @abstractmethod
    def process_command_list(
        self, commands: List[Any], detect_properties: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process a list of commands into structured format.

        Args:
            commands: List of commands (strings, ShellCommand objects, etc.)
            detect_properties: Whether to detect properties like multiline, function definitions, etc.

        Returns:
            List of processed command dictionaries
        """

    @abstractmethod
    def detect_command_properties(self, command: str) -> Dict[str, bool]:
        """
        Detect properties of a command string.

        Args:
            command: Command string to analyze

        Returns:
            Dictionary of detected properties
        """


class IEnvironmentCommandAdapter(ABC):
    """Interface for environment-specific command adaptations."""

    @abstractmethod
    def adapt_commands(self, commands: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt commands for a specific environment.

        Args:
            commands: Processed commands

        Returns:
            Environment-adapted commands
        """
