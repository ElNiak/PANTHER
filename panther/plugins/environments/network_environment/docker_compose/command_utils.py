"""
Utilities for handling shell commands in Docker Compose environments.

This module provides classes and functions for structured command representation,
proper shell escaping, and serialization to shell script format.
"""

import shlex
import json
from typing import Any


class ShellCommand:
    """
    Structured representation of a shell command with metadata.

    Attributes:
        command (str): The shell command to be executed
        description (str): Description of what the command does
        is_critical (bool): Whether failure of this command should halt execution
        is_multiline (bool): Whether the command contains multiple lines
        is_function_definition (bool): Whether the command defines a shell function
        working_dir (str): Working directory for the command execution
        environment (dict): Environment variables for the command
        timeout (int): Command timeout in seconds
    """

    def __init__(
        self,
        command: str,
        description: str = "",
        is_critical: bool = True,
        is_multiline: bool = False,
        is_function_definition: bool = False,
        working_dir: str | None = None,
        environment: dict[str, str] | None = None,
        timeout: int | None = None,
    ):
        self.command = command
        self.description = description
        self.is_critical = is_critical
        self.is_multiline = is_multiline
        self.is_function_definition = is_function_definition
        self.working_dir = working_dir
        self.environment = environment or {}
        self.timeout = timeout

    def to_dict(self) -> dict[str, Any]:
        """Convert the command to a dictionary representation."""
        return {
            "command": self.command,
            "description": self.description,
            "is_critical": self.is_critical,
            "is_multiline": self.is_multiline,
            "is_function_definition": self.is_function_definition,
            "working_dir": self.working_dir,
            "environment": self.environment,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShellCommand":
        """Create a ShellCommand instance from a dictionary."""
        return cls(
            command=data["command"],
            description=data.get("description", ""),
            is_critical=data.get("is_critical", True),
            is_multiline=data.get("is_multiline", False),
            is_function_definition=data.get("is_function_definition", False),
            working_dir=data.get("working_dir"),
            environment=data.get("environment", {}),
            timeout=data.get("timeout"),
        )

    @classmethod
    def from_string(cls, command_str: str, is_critical: bool = True) -> "ShellCommand":
        """
        Create a ShellCommand from a plain string command.
        This is useful for backward compatibility with existing code.

        Args:
            command_str: The command string
            is_critical: Whether the command is critical

        Returns:
            A ShellCommand instance
        """
        # Detect function definitions by pattern
        is_function_def = False
        if "() {" in command_str and "}" in command_str:
            is_function_def = True
        elif (
            command_str.strip().startswith("function ")
            and "{" in command_str
            and "}" in command_str
        ):
            is_function_def = True

        # Detect if it's multiline
        is_multiline = "\n" in command_str

        return cls(
            command=command_str,
            description=f"Command: {command_str[:40]}{'...' if len(command_str) > 40 else ''}",
            is_critical=is_critical,
            is_multiline=is_multiline,
            is_function_definition=is_function_def,
        )


def escape_shell_command(cmd: str) -> str:
    """
    Properly escape a shell command using Python's built-in tools.

    This function handles escaping for different contexts:
    - For single-line commands, it properly quotes the entire command
    - For multiline commands, it preserves the structure while escaping quotes

    Args:
        cmd: The shell command to escape

    Returns:
        Escaped shell command safe for inclusion in shell scripts
    """
    # For multiline commands, we'll handle them differently
    if "\n" in cmd:
        # For multiline commands, we need to preserve the structure
        # but escape any double quotes that might interfere with outer quoting
        return cmd.replace('"', '\\"')

    # For single line commands, full quoting is appropriate
    return shlex.quote(cmd)


def format_multiline_command(cmd: str) -> str:
    """
    Format a multiline command using heredoc syntax for consistent execution.

    Args:
        cmd: The multiline shell command

    Returns:
        Command wrapped in a heredoc
    """
    # Generate a unique token with a random suffix to avoid potential conflicts
    # Even if the token appears in the command, the odds of an exact match are extremely low
    import uuid

    heredoc_token = f"PANTHER_EOF_{str(uuid.uuid4()).replace('-', '')[:8]}"

    # Ensure the command doesn't end with a newline
    cmd = cmd.rstrip("\n")

    # Use <<'TOKEN' syntax to prevent variable and command expansion within the heredoc
    # This preserves the command exactly as written
    return f"""cat <<'{heredoc_token}' | bash
{cmd}
{heredoc_token}"""


def format_function_definition(cmd: str) -> str:
    """
    Format a function definition for inclusion in a shell script.

    Args:
        cmd: The function definition

    Returns:
        Formatted function definition
    """
    # Ensure the function definition doesn't have leading/trailing whitespace
    cmd = cmd.strip()

    # Make sure the function is properly defined with complete syntax
    if not cmd.endswith("}"):
        cmd += "\n}"

    return cmd


def convert_legacy_commands(commands: list[str]) -> list[ShellCommand]:
    """
    Convert a list of legacy command strings to ShellCommand objects.

    Args:
        commands: List of command strings from the old format

    Returns:
        List of ShellCommand objects
    """
    result = []

    for cmd in commands:
        # Check if this is a non-critical command (marked with special comment)
        if isinstance(cmd, str) and cmd.startswith("# PANTHER_NON_CRITICAL_COMMAND"):
            # Extract the actual command without the marker
            actual_cmd = cmd.replace("# PANTHER_NON_CRITICAL_COMMAND\n", "")
            result.append(
                ShellCommand(
                    command=actual_cmd,
                    description=f"Non-critical: {actual_cmd[:40]}...",
                    is_critical=False,
                    is_multiline="\n" in actual_cmd,
                )
            )
        # Check if this is a function definition command
        elif isinstance(cmd, str) and "# PANTHER_FUNCTION_DEFINITION" in cmd:
            # Extract the function definition without the marker
            actual_cmd = cmd.replace("# PANTHER_FUNCTION_DEFINITION", "").strip()
            result.append(
                ShellCommand(
                    command=actual_cmd,
                    description=f"Function: {actual_cmd.split('(')[0] if '(' in actual_cmd else actual_cmd[:20]}",
                    is_function_definition=True,
                    is_multiline="\n" in actual_cmd,
                )
            )
        else:
            # Regular command
            result.append(ShellCommand.from_string(cmd))

    return result


# Custom Jinja2 filters for template usage
def add_template_filters(env):
    """
    Add custom filters to a Jinja2 Environment for shell command handling.

    Args:
        env: The Jinja2 Environment to augment with filters
    """
    env.filters["escape_shell"] = escape_shell_command

    def to_json(val):
        return json.dumps(val)

    env.filters["to_json"] = to_json
