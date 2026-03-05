"""Interfaces for command processing in PANTHER framework.

Defines the abstract contracts that all command processors and environment
adapters must satisfy.  Concrete implementations live in
`panther.core.command_processor.core.processor`.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ICommandProcessor(ABC):
    """Abstract base class defining the command processing contract.

    Implementations must handle a standard command dictionary structure::

        {
            "pre_run_cmds":  [list_of_commands],
            "run_cmd":       {"working_dir": ..., "command_binary": ..., ...},
            "post_run_cmds": [list_of_commands],
        }

    Example:
        ::

            processor = CommandProcessor()
            result = processor.process_commands({
                "pre_run_cmds": ["echo setup"],
                "run_cmd": {"command_args": "python script.py"},
                "post_run_cmds": ["echo cleanup"],
            })
    """

    @abstractmethod
    def process_commands(
        self, commands: Dict[str, Any], target_format: str = "generic"
    ) -> Dict[str, Any]:
        """Process a command structure into a target format.

        Args:
            commands: Dictionary containing command structure with keys such as
                ``pre_run_cmds``, ``run_cmd``, ``post_run_cmds``.
            target_format: Target format identifier. Defaults to ``"generic"``.

        Returns:
            Dictionary with processed commands.  ``run_cmd`` values are
            normalized dictionaries; list-type keys become lists of
            ``ShellCommand.to_dict()`` results.

        Raises:
            PantherException: If command structure is invalid.
        """

    @abstractmethod
    def process_command_list(
        self, commands: List[Any], detect_properties: bool = True
    ) -> List[Dict[str, Any]]:
        """Process a list of commands into structured format.

        Args:
            commands: List of commands (strings, ``ShellCommand`` objects, or
                dicts with a ``"command"`` key).
            detect_properties: Whether to detect properties like multiline,
                function definitions, etc. Defaults to ``True``.

        Returns:
            List of processed command dictionaries (each is a
            ``ShellCommand.to_dict()`` result).
        """

    @abstractmethod
    def detect_command_properties(self, command: str) -> Dict[str, bool]:
        """Detect properties of a command string.

        Detected properties include:
            - ``is_multiline``: Whether command spans multiple lines.
            - ``is_function_definition``: Whether command defines a shell function.
            - ``is_control_structure``: Whether command is an if/for/while/case block.

        Args:
            command: Command string to analyze.

        Returns:
            Dictionary mapping property names to boolean values.
        """


class IEnvironmentCommandAdapter(ABC):
    """Abstract interface for environment-specific command adaptations.

    Implement this to transform processed commands for a particular
    execution environment (Docker, Kubernetes, localhost, etc.).

    Example:
        ::

            class DockerAdapter(IEnvironmentCommandAdapter):
                def adapt_commands(self, commands):
                    # Wrap each shell command in ``docker exec ...``
                    ...
    """

    @abstractmethod
    def adapt_commands(self, commands: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt commands for a specific environment.

        Args:
            commands: Already-processed command dictionary from
                ``ICommandProcessor.process_commands``.

        Returns:
            Environment-adapted commands in the same dictionary shape.
        """
