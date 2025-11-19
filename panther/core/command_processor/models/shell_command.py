"""
Merged ShellCommand implementation combining the best of both versions.

This implementation:
- Uses the cleaner structure from shell_command.py with CommandMetadata
- Includes all detection logic from command.py
- Fixes the dollar sign escaping issue for variable assignments
- Provides enhanced variable assignment detection
"""

import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

# Lazy import to avoid circular dependency - moved inside function
from panther.core.command_processor.models.constants import (
    SHELL_BUILTINS,
    SHELL_CONTROL_OPERATORS,
    SHELL_CONTROL_STRUCTURES,
)
from panther.core.command_processor.utils.shell_utils import (
    escape_shell_command,
    normalize_command_ending,
    parse_command_with_redirections,
    split_complex_command,
)
from panther.core.utils.logging_mixin import LoggerMixin


@dataclass
class CommandMetadata:
    """Metadata for shell commands."""

    is_critical: bool = True
    timeout: Optional[int] = None
    retry_count: int = 0
    environment: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Additional metadata from original implementation
    is_multiline: bool = False
    is_function_definition: bool = False
    is_function_call: bool = False
    has_control_operators: bool = False
    control_operators: List[str] = field(default_factory=list)
    is_variable_assignment: bool = False
    is_environment_variable_assignment: bool = False
    is_shell_builtin: bool = False
    is_control_structure: bool = False
    has_nested_quotes: bool = False
    has_comment: bool = False
    comment_text: str = ""
    is_empty: bool = False


class ShellCommand(LoggerMixin):
    """
    Represents a shell command with validation and safe execution support.

    This merged implementation provides:
    - Command validation and sanitization
    - Safe string representation for shell execution
    - Serialization/deserialization support
    - Metadata for execution control
    - Detection of command types (variable assignments, builtins, etc.)
    - Smart escaping based on command type
    """

    def __init__(
        self,
        command: str,
        metadata: Optional[CommandMetadata] = None,
        validate: bool = True,
        **kwargs,
    ):
        """
        Initialize a ShellCommand.

        Args:
            command: The shell command string
            metadata: Optional metadata for the command
            validate: Whether to validate the command on creation
            **kwargs: Additional keyword arguments that will be set as metadata attributes
                     (e.g., is_critical, description, timeout, etc.)

        Raises:
            ValueError: If validation is enabled and command is invalid
        """
        self.raw_command = command.strip()
        self.metadata = metadata or CommandMetadata()

        # Elegantly apply all kwargs to metadata attributes if they exist
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                self.logger.debug(f"Setting ShellCommand metadata '{key}' to '{value}'")
                setattr(self.metadata, key, value)
            else:
                self.logger.debug(
                    f"ShellCommand metadata has no attribute '{key}', ignoring."
                )
            # Silently ignore unknown attributes for backward compatibility

        # Normalize the command
        self.command = normalize_command_ending(self.raw_command)

        # Parse command structure
        self._parse_command_structure()

        # Detect command type if not already set
        if not any(
            [
                self.metadata.is_variable_assignment,
                self.metadata.is_shell_builtin,
                self.metadata.is_control_structure,
                self.metadata.is_function_definition,
            ]
        ):
            self._detect_command_type()

        self.logger.debug(
            "Parsed command: %s, Executable: %s, Arguments: %s, Redirections: %s",
            self.command,
            self.executable,
            self.arguments,
            self.redirections,
        )
        # Validate if requested
        if validate:
            self._validate()
            

    def _parse_command_structure(self) -> None:
        """Parse the command to extract its components."""
        # Extract base command and redirections
        self.base_command, self.redirections = parse_command_with_redirections(
            self.command
        )

        # Split into individual commands if complex
        self.command_parts = split_complex_command(self.command)

        # Identify the primary executable
        if self.base_command:
            try:
                parts = shlex.split(self.base_command)
            except ValueError:
                # If shlex fails, do simple split
                parts = self.base_command.split()

            self.executable = parts[0] if parts else None
            self.arguments = parts[1:] if len(parts) > 1 else []
        else:
            self.executable = None
            self.arguments = []

    def _detect_command_type(self) -> None:
        """Detect the type of command and set appropriate metadata."""
        command_str = self.command

        # Check for empty command
        if not command_str.strip() and len(self.command_parts) == 0:
            self.metadata.is_empty = True
            return

        # Check for comments
        if "#" in command_str:
            comment_parts = command_str.split("#", 1)
            command_body = comment_parts[0].strip()
            self.metadata.comment_text = (
                comment_parts[1].strip() if len(comment_parts) > 1 else ""
            )
            self.metadata.has_comment = True

            if not command_body and len(self.command_parts) == 0:
                self.metadata.is_empty = True
                return

        # Check for multiline
        if "\n" in command_str:
            self.metadata.is_multiline = True

        # Check for control operators
        for op in SHELL_CONTROL_OPERATORS:
            if op in command_str:
                self.metadata.has_control_operators = True
                self.metadata.control_operators.append(op)

        # Get command parts
        try:
            cmd_parts = shlex.split(command_str.strip())
        except ValueError:
            cmd_parts = command_str.strip().split()

        if not cmd_parts and len(self.command_parts) == 0:
            self.metadata.is_empty = True
            return

        first_word = cmd_parts[0]

        # Check for function definition
        if "() {" in command_str and "}" in command_str:
            self.metadata.is_function_definition = True
            self.metadata.is_multiline = True
        elif command_str.strip().startswith("function ") and "{" in command_str:
            self.metadata.is_function_definition = True
            self.metadata.is_multiline = True

        # Check for shell builtin
        if first_word in SHELL_BUILTINS:
            self.metadata.is_shell_builtin = True

        # Check for control structure
        if first_word in SHELL_CONTROL_STRUCTURES:
            self.metadata.is_control_structure = True
            self.metadata.is_multiline = True

        # Enhanced variable assignment detection
        if self._is_variable_assignment(command_str, cmd_parts) and not self.metadata.is_environment_variable_assignment:
            self.metadata.is_variable_assignment = True

        # Check for simple function call
        if (
            not self.metadata.is_function_definition
            and not self.metadata.has_control_operators
            and len(cmd_parts) == 1
            and "(" not in command_str
        ):
            self.metadata.is_function_call = True

        # Check for nested quotes
        if (
            ('"' in command_str and "'" in command_str)
            or (command_str.count('"') > 2)
            or (command_str.count("'") > 2)
        ):
            self.metadata.has_nested_quotes = True

    def _is_variable_assignment(self, command_str: str, cmd_parts: List[str]) -> bool:
        """
        Enhanced variable assignment detection.

        Detects:
        - Simple assignments: VAR=value
        - Export statements: export VAR=value or export VAR
        - Command substitution: VAR=$(command) or VAR=`command`
        - Multiple assignments: VAR1=val1 VAR2=val2
        - Quoted values: VAR='value' or VAR="value"
        """
        if not cmd_parts:
            return False

        # Check for export command
        if cmd_parts[0] == "export":
            # export VAR or export VAR=value
            return False

        # Check for variable assignment pattern
        # This regex matches: VARNAME=anything including $(cmd) or `cmd`
        # Variable names must start with letter or underscore
        var_pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*="

        # Check first line for multiline commands
        first_line = command_str.strip().split("\n")[0].strip()

        # Check if the command or first word matches variable assignment
        if re.match(var_pattern, first_line):
            return True

        # Check for multiple assignments (VAR1=val1 VAR2=val2 command)
        # All words before a non-assignment word
        for part in cmd_parts:
            if not re.match(var_pattern, part):
                break
            return True  # At least one assignment found

        return False

    def _validate(self) -> None:
        """Validate the command for security and correctness."""
        # Lazy import to avoid circular dependency
        from panther.core.command_processor.core.validator import CommandValidator

        validator = CommandValidator()
        result = validator.validate_command(self.command)

        if not result.is_valid:
            error_msg = "Command validation failed:\n"
            error_msg += "\n".join(f"  - {error}" for error in result.errors)
            raise ValueError(error_msg)

        # Store warnings for later reference
        self.validation_warnings = result.warnings

    @property
    def shell_safe_command(self) -> str:
        """Property access to shell-safe command."""
        return self.get_shell_safe_command()

    def get_shell_safe_command(self, escape_variables: bool = True) -> str:
        """
        Get a shell-safe version of the command.

        Args:
            escape_variables: Whether to escape shell variables ($).
                             Should be False for variable assignments and command substitutions.

        Returns:
            Escaped command safe for shell execution
        """
        # For variable assignments and command substitutions, don't escape $
        if (
            self.metadata.is_variable_assignment
            or self.metadata.is_shell_builtin
            or (self.metadata.is_shell_builtin and self.executable == "export")
        ):
            escape_variables = False

        # Also check for shell variable patterns in complex commands
        # This handles cases where variables are used in pipelines or compound commands
        if escape_variables:
            import re

            shell_variable_patterns = [
                r"\$\?",  # Exit status variable
                r"\$\w+",  # Shell variables like $HOME, $PWD
                r"\$\{\w+\}",  # Shell variables in braces like ${HOME}
                r"\$\(\s*\w+.*?\)",  # Command substitution like $(command)
                r"\$\d+",  # Positional parameters like $1, $2
                r"\$\*",  # All positional parameters
                r"\$@",  # All positional parameters quoted
                r"[a-zA-Z_][a-zA-Z0-9_]*=\$",  # Variable assignments with $ values
            ]

            # If the command contains shell variable patterns, don't escape variables
            has_shell_constructs = any(
                re.search(pattern, self.command) for pattern in shell_variable_patterns
            )
            if has_shell_constructs:
                escape_variables = False

        # Use custom escaping logic
        if not escape_variables:
            # Don't escape $ for these command types
            safe_cmd = self.command
            # Escape backslashes first to avoid double-escaping
            safe_cmd = safe_cmd.replace("\\", "\\\\")
            # Escape double quotes
            safe_cmd = safe_cmd.replace('"', '\\"')
            # Don't escape dollar signs
            # Escape backticks to prevent command substitution
            safe_cmd = safe_cmd.replace("`", "\\`")
            return safe_cmd
        else:
            # Use standard escaping
            return escape_shell_command(self.command)

    def get_executable_path(self) -> Optional[str]:
        """
        Get the path to the main executable.

        Returns:
            Path to executable or None if not applicable
        """
        return self.executable

    def get_arguments(self) -> List[str]:
        """
        Get command arguments.

        Returns:
            List of command arguments
        """
        return self.arguments.copy()

    def get_redirections(self) -> List[Tuple[str, str]]:
        """
        Get command redirections.

        Returns:
            List of (operator, target) tuples
        """
        return self.redirections.copy()

    def has_redirections(self) -> bool:
        """Check if command has redirections."""
        return bool(self.redirections)

    def is_complex(self) -> bool:
        """Check if this is a complex command with multiple parts."""
        return len(self.command_parts) > 1

    def is_critical(self) -> bool:
        """Check if this command is critical for execution."""
        return self.metadata.is_critical

    def with_timeout(self, timeout: int) -> "ShellCommand":
        """
        Create a new command with a timeout.

        Args:
            timeout: Timeout in seconds

        Returns:
            New ShellCommand instance with timeout
        """
        new_metadata = CommandMetadata(**self.metadata.__dict__)
        new_metadata.timeout = timeout
        return ShellCommand(self.raw_command, new_metadata, validate=False)

    def with_environment(self, env: Dict[str, str]) -> "ShellCommand":
        """
        Create a new command with additional environment variables.

        Args:
            env: Environment variables to add/override

        Returns:
            New ShellCommand instance with updated environment
        """
        new_env = self.metadata.environment.copy()
        new_env.update(env)

        new_metadata = CommandMetadata(**self.metadata.__dict__)
        new_metadata.environment = new_env
        return ShellCommand(self.raw_command, new_metadata, validate=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert command to dictionary representation.
        # TODO: improve maintenance by using asdict from dataclasses

        Returns:
            Dictionary with command data
        """
        return {
            "command": self.command,
            "raw_command": self.raw_command,
            "shell_safe_command": self.get_shell_safe_command(),
            "executable": self.executable,
            "arguments": self.arguments,
            "redirections": self.redirections,
            "metadata": {
                "is_critical": self.metadata.is_critical,
                "timeout": self.metadata.timeout,
                "retry_count": self.metadata.retry_count,
                "environment": self.metadata.environment,
                "working_directory": self.metadata.working_directory,
                "description": self.metadata.description,
                "tags": self.metadata.tags,
                "is_multiline": self.metadata.is_multiline,
                "is_function_definition": self.metadata.is_function_definition,
                "is_function_call": self.metadata.is_function_call,
                "has_control_operators": self.metadata.has_control_operators,
                "control_operators": self.metadata.control_operators,
                "is_variable_assignment": self.metadata.is_variable_assignment,
                "is_environment_variable_assignment": self.metadata.is_environment_variable_assignment,
                "is_shell_builtin": self.metadata.is_shell_builtin,
                "is_control_structure": self.metadata.is_control_structure,
                "has_nested_quotes": self.metadata.has_nested_quotes,
                "has_comment": self.metadata.has_comment,
                "comment_text": self.metadata.comment_text,
                "is_empty": self.metadata.is_empty,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShellCommand":
        """
        Create ShellCommand from dictionary.

        Args:
            data: Dictionary with command data

        Returns:
            New ShellCommand instance
        """
        metadata_data = data.get("metadata", {})
        metadata = CommandMetadata(**metadata_data)

        # Use raw_command if available, otherwise use command
        command_str = data.get("raw_command", data.get("command", ""))

        return cls(command_str, metadata, validate=False)

    @classmethod
    def from_string(
        cls, command_str: str, is_critical: bool = True, **kwargs
    ) -> "ShellCommand":
        """
        Create ShellCommand from a simple string.
        Automatically extracts working directory from commands starting with 'cd && '.

        Args:
            command_str: Command string
            is_critical: Whether the command is critical
            **kwargs: Additional metadata attributes (e.g., description, timeout)

        Returns:
            New ShellCommand instance
        """
        # Import here to avoid circular dependency
        from panther.core.command_processor.utils.command_utils import CommandUtils

        # Extract working directory if present
        working_dir, cleaned_cmd = CommandUtils.extract_working_directory_from_command(
            command_str
        )

        # Set working_directory in kwargs if extracted and not already specified
        if working_dir and "working_directory" not in kwargs:
            kwargs["working_directory"] = working_dir

        # Use cleaned command
        command_to_use = cleaned_cmd

        # Pass is_critical through kwargs for consistency
        kwargs["is_critical"] = is_critical
        return cls(command_to_use, **kwargs)

    # Alias for backward compatibility
    @classmethod
    def create_from_string(
        cls, command_str: str, is_critical: bool = True
    ) -> "ShellCommand":
        """Alias for from_string() for backward compatibility."""
        return cls.from_string(command_str, is_critical)

    def __str__(self) -> str:
        """String representation of the command."""
        if self.metadata.description:
            return f"{self.metadata.description}: {self.command}"
        return self.command

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"ShellCommand("
            f"command={self.command!r}, "
            f"critical={self.metadata.is_critical}, "
            f"variable_assignment={self.metadata.is_variable_assignment}, "
            f"timeout={self.metadata.timeout}"
            f")"
        )
