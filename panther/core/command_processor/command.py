"""
Shared utilities for handling shell commands across all PANTHER plugins.

This module provides the ShellCommand class and related functions for structured
command representation, proper shell escaping, and serialization to shell script format.
This utility is used across all PANTHER plugins to ensure consistent command handling.
"""

import re
import shlex
import logging
from typing import Any

# Shell control operators that could cause issues if they appear at the end of a command
SHELL_CONTROL_OPERATORS = ["&&", "||", ";", "&", "|", ">", ">>", "<<", "<"]

# Shell built-in commands that should not be quoted
SHELL_BUILTINS = [
    "set",
    "export",
    "source",
    "unset",
    ".",
    "alias",
    "bg",
    "bind",
    "builtin",
    "caller",
    "cd",
    "command",
    "compgen",
    "complete",
    "declare",
    "dirs",
    "disown",
    "echo",
    "enable",
    "eval",
    "exec",
    "exit",
    "fc",
    "fg",
    "getopts",
    "hash",
    "help",
    "history",
    "jobs",
    "kill",
    "let",
    "local",
    "logout",
    "mapfile",
    "popd",
    "printf",
    "pushd",
    "pwd",
    "read",
    "readarray",
    "readonly",
    "return",
    "shift",
    "shopt",
    "suspend",
    "test",
    "times",
    "trap",
    "type",
    "typeset",
    "ulimit",
    "umask",
    "unalias",
    "wait",
]

# Shell control structures that shouldn't be quoted
SHELL_CONTROL_STRUCTURES = [
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "case",
    "esac",
    "for",
    "while",
    "until",
    "do",
    "done",
    "select",
    "function",
]

# Additional redirection operators that should not be escaped
REDIRECTION_OPERATORS = [">", ">>", "<", "<<", "2>", "2>>", "&>", "&>>", "|&"]


class ShellCommand:
    """
    Structured representation of a shell command with metadata.

    This class provides a standardized way to represent shell commands across
    all PANTHER plugins, with support for:
    - Proper shell escaping
    - Multiline commands and function definitions
    - Environment variables and working directories
    - Command criticality and timeout handling
    - Variable assignments and shell built-ins
    - Control structures and commands with nested quotes
    - Comments within commands
    - Empty command detection and handling

    Attributes:
        command (str): The shell command to be executed
        description (str): Description of what the command does
        is_critical (bool): Whether failure of this command should halt execution
        is_multiline (bool): Whether the command contains multiple lines
        is_function_definition (bool): Whether the command defines a shell function
        is_function_call (bool): Whether the command is a simple function call
        has_control_operators (bool): Whether the command contains control operators like &&, ||, etc.
        control_operators (list): List of control operators found in the command
        working_dir (str): Working directory for the command execution
        environment (dict): Environment variables for the command
        timeout (int): Command timeout in seconds
        is_variable_assignment (bool): Whether this is a variable assignment (e.g., VAR=value)
        is_shell_builtin (bool): Whether this command starts with a shell builtin (e.g., set -x)
        is_control_structure (bool): Whether this is a shell control structure (e.g., if/while/for)
        has_nested_quotes (bool): Whether this command contains nested quotes that need special handling
        has_comment (bool): Whether this command contains a comment
        comment_text (str): Text of the comment if present
        is_empty (bool): Whether this command is empty (just whitespace or comment)
    """

    def __init__(
        self,
        command: str,
        description: str = "",
        is_critical: bool = True,
        is_multiline: bool = False,
        is_function_definition: bool = False,
        is_function_call: bool = False,
        has_control_operators: bool = False,
        control_operators: list[str] | None = None,
        working_dir: str | None = None,
        environment: dict[str, str] | None = None,
        timeout: int | None = None,
        is_variable_assignment: bool = False,
        is_shell_builtin: bool = False,
        is_control_structure: bool = False,
        has_nested_quotes: bool = False,
        has_comment: bool = False,
        comment_text: str = "",
        is_empty: bool = False,
    ):
        """
        Initialize a ShellCommand instance.

        Args:
            command: The shell command to be executed
            description: Human-readable description of the command
            is_critical: Whether command failure should halt execution
            is_multiline: Whether the command spans multiple lines
            is_function_definition: Whether this defines a shell function
            is_function_call: Whether this is a simple function call
            has_control_operators: Whether the command contains control operators like &&, ||, etc.
            control_operators: List of control operators found in the command
            working_dir: Working directory for command execution
            environment: Environment variables for the command
            timeout: Command timeout in seconds
            is_variable_assignment: Whether this is a variable assignment (e.g., VAR=value)
            is_shell_builtin: Whether this command starts with a shell builtin (e.g., set -x)
            is_control_structure: Whether this is a shell control structure (e.g., if/while/for)
            has_nested_quotes: Whether this command contains nested quotes that need special handling
            has_comment: Whether this command contains a comment
            comment_text: Text of the comment if present
            is_empty: Whether this command is empty (just whitespace or comment)
        """
        self.command = command
        self.description = description
        self.is_critical = is_critical
        self.is_multiline = is_multiline
        self.is_function_definition = is_function_definition
        self.is_function_call = is_function_call
        self.has_control_operators = has_control_operators
        self.control_operators = control_operators or []
        self.working_dir = working_dir
        self.environment = environment or {}
        self.timeout = timeout
        self.is_variable_assignment = is_variable_assignment
        self.is_shell_builtin = is_shell_builtin
        self.is_control_structure = is_control_structure
        self.has_nested_quotes = has_nested_quotes
        self.has_comment = has_comment
        self.comment_text = comment_text
        self.is_empty = is_empty

    def __repr__(self):
        return (
            f"ShellCommand(command={self.command!r}, description={self.description!r}, "
            f"is_critical={self.is_critical}, is_multiline={self.is_multiline}, "
            f"is_function_definition={self.is_function_definition}, is_function_call={self.is_function_call}, "
            f"has_control_operators={self.has_control_operators}, control_operators={self.control_operators!r}, "
            f"working_dir={self.working_dir!r}, environment={self.environment!r}, "
            f"timeout={self.timeout}, is_variable_assignment={self.is_variable_assignment}, "
            f"is_shell_builtin={self.is_shell_builtin}, is_control_structure={self.is_control_structure}, "
            f"has_nested_quotes={self.has_nested_quotes}, has_comment={self.has_comment}, "
            f"comment_text={self.comment_text!r}, is_empty={self.is_empty})"
        )

    def __str__(self):
        return (
            f"ShellCommand(command={self.command!r}, description={self.description!r}, "
            f"is_critical={self.is_critical}, is_multiline={self.is_multiline}, "
            f"is_function_definition={self.is_function_definition}, is_function_call={self.is_function_call}, "
            f"has_control_operators={self.has_control_operators}, control_operators={self.control_operators!r}, "
            f"working_dir={self.working_dir!r}, environment={self.environment!r}, "
            f"timeout={self.timeout}, is_variable_assignment={self.is_variable_assignment}, "
            f"is_shell_builtin={self.is_shell_builtin}, is_control_structure={self.is_control_structure}, "
            f"has_nested_quotes={self.has_nested_quotes}, has_comment={self.has_comment}, "
            f"comment_text={self.comment_text!r}, is_empty={self.is_empty})"
        )

    def get_shell_safe_command(self) -> str:
        """
        Get shell-safe version of the command with proper escaping.

        This method escapes special characters that could cause issues
        when the command is passed as a quoted string in shell scripts.

        Returns:
            Shell-safe version of the command
        """
        if not self.command:
            return ""

        safe_cmd = self.command
        # Escape backslashes first to avoid double-escaping
        safe_cmd = safe_cmd.replace("\\", "\\\\")
        # Escape double quotes
        safe_cmd = safe_cmd.replace('"', '\\"')
        # Escape dollar signs to prevent variable expansion
        safe_cmd = safe_cmd.replace("$", "\\$")
        # Escape backticks to prevent command substitution
        safe_cmd = safe_cmd.replace("`", "\\`")

        return safe_cmd

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the command to a dictionary representation.

        Returns:
            Dictionary containing all command attributes
        """
        return {
            "command": self.command,
            "shell_safe_command": self.get_shell_safe_command(),
            "description": self.description,
            "is_critical": self.is_critical,
            "is_multiline": self.is_multiline,
            "is_function_definition": self.is_function_definition,
            "is_function_call": self.is_function_call,
            "has_control_operators": self.has_control_operators,
            "control_operators": self.control_operators,
            "working_dir": self.working_dir,
            "environment": self.environment,
            "timeout": self.timeout,
            "is_variable_assignment": getattr(self, "is_variable_assignment", False),
            "is_shell_builtin": getattr(self, "is_shell_builtin", False),
            "is_control_structure": getattr(self, "is_control_structure", False),
            "has_nested_quotes": getattr(self, "has_nested_quotes", False),
            "has_comment": getattr(self, "has_comment", False),
            "comment_text": getattr(self, "comment_text", ""),
            "is_empty": getattr(self, "is_empty", False),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShellCommand":
        """
        Create a ShellCommand instance from a dictionary.

        Args:
            data: Dictionary containing command attributes

        Returns:
            ShellCommand instance
        """
        return cls(
            command=data["command"],
            description=data.get("description", ""),
            is_critical=data.get("is_critical", True),
            is_multiline=data.get("is_multiline", False),
            is_function_definition=data.get("is_function_definition", False),
            is_function_call=data.get("is_function_call", False),
            has_control_operators=data.get("has_control_operators", False),
            control_operators=data.get("control_operators", []),
            working_dir=data.get("working_dir"),
            environment=data.get("environment", {}),
            timeout=data.get("timeout"),
            is_variable_assignment=data.get("is_variable_assignment", False),
            is_shell_builtin=data.get("is_shell_builtin", False),
            is_control_structure=data.get("is_control_structure", False),
            has_nested_quotes=data.get("has_nested_quotes", False),
            has_comment=data.get("has_comment", False),
            comment_text=data.get("comment_text", ""),
            is_empty=data.get("is_empty", False),
        )

    @classmethod
    def from_string(cls, command_str: str, is_critical: bool = True) -> "ShellCommand":
        """
        Create a ShellCommand from a plain string command.
        This is useful for plugin developers who need to create commands from strings.

        Args:
            command_str: The command string
            is_critical: Whether the command is critical

        Returns:
            A ShellCommand instance
        """
        # First normalize any problematic command endings
        # command_str = normalize_command_ending(command_str)

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

        # Check for control operators
        has_control_operators = False
        control_operators = []
        for op in SHELL_CONTROL_OPERATORS:
            if op in command_str:
                has_control_operators = True
                control_operators.append(op)

        # Detect if it's a simple function call (single word)
        is_function_call = False
        if not is_function_def and not has_control_operators:
            cmd_stripped = command_str.strip()
            if cmd_stripped and " " not in cmd_stripped and "(" not in cmd_stripped:
                is_function_call = True

        # Also consider multiline if there are multiple commands chained together
        if not is_multiline:
            for op in ["&&", "||", ";"]:
                if op in command_str and command_str.count(op) > 1:
                    is_multiline = True
                    break

        # Detect if this is a variable assignment (e.g., VAR=value)
        is_variable_assignment = False
        cmd_parts = command_str.strip().split()
        if not is_function_def and "=" in command_str:
            # Check if it's a simple variable assignment with no spaces around =
            if "=" in command_str.strip() and " = " not in command_str:
                # For multiline variable assignments, check just the first line
                first_line = command_str.strip().split("\n")[0].strip()
                var_assign_pattern = r"^[a-zA-Z0-9_]+=.*$"
                if re.match(var_assign_pattern, first_line):
                    is_variable_assignment = True

        # Detect if this is a shell built-in command
        is_shell_builtin = False
        if cmd_parts and cmd_parts[0] in SHELL_BUILTINS:
            is_shell_builtin = True

        # Detect if this is a shell control structure
        is_control_structure = False
        if cmd_parts:
            # Check if first word is a control structure keyword
            if cmd_parts[0] in SHELL_CONTROL_STRUCTURES:
                is_control_structure = True
                # Consider shell control structures as multiline commands
                is_multiline = True
            # Also check for typical patterns of control structures in the first line
            elif any(
                command_str.strip().startswith(f"{keyword} ")
                for keyword in ["while", "for", "if", "case", "function"]
            ):
                is_control_structure = True
                is_multiline = True

        # Additional check for incomplete control structures or function definitions
        if not is_control_structure and not is_function_def:
            # Look for typical control structure patterns in the command
            cmd_lower = command_str.lower()
            if (
                (" while " in cmd_lower or cmd_lower.startswith("while "))
                or (" for " in cmd_lower or cmd_lower.startswith("for "))
                or (" if " in cmd_lower or cmd_lower.startswith("if "))
                or (" case " in cmd_lower or cmd_lower.startswith("case "))
            ):
                is_control_structure = True
                is_multiline = True
            # Also check for typical patterns of control structures in the first line
            elif any(
                command_str.strip().startswith(f"{keyword} ")
                for keyword in ["while", "for", "if", "case"]
            ):
                is_control_structure = True
                is_multiline = True

        # Additional check for incomplete control structures or function definitions
        if not is_control_structure and not is_function_def:
            # Look for typical control structure patterns in the command
            cmd_lower = command_str.lower()
            if (
                (" while " in cmd_lower or cmd_lower.startswith("while "))
                or (" for " in cmd_lower or cmd_lower.startswith("for "))
                or (" if " in cmd_lower or cmd_lower.startswith("if "))
                or (" case " in cmd_lower or cmd_lower.startswith("case "))
            ):
                is_control_structure = True
                is_multiline = True

        # Detect if this has nested quotes
        has_nested_quotes = False
        if (
            ('"' in command_str and "'" in command_str)
            or (command_str.count('"') > 2)
            or (command_str.count("'") > 2)
        ):
            has_nested_quotes = True

        # Special case for export commands with nested quotes
        if (
            cmd_parts
            and cmd_parts[0] == "export"
            and "=" in command_str
            and ('"' in command_str or "'" in command_str)
        ):
            has_nested_quotes = True

        # Detect if this command contains a comment
        has_comment = False
        comment_text = ""
        if "#" in command_str:
            # Extract the comment part
            comment_parts = command_str.split("#", 1)
            command_body = comment_parts[0].strip()
            comment_text = comment_parts[1].strip() if len(comment_parts) > 1 else ""

            if command_body:
                # If there's a command body before the comment, it's not an empty command
                is_empty = False
            else:
                # If the comment is the only thing present, mark as empty
                is_empty = True

            has_comment = True
        else:
            is_empty = command_str.strip() == ""

        return cls(
            command=command_str,
            description=f"Command: {command_str[:40]}{'...' if len(command_str) > 40 else ''}",
            is_critical=is_critical,
            is_multiline=is_multiline,
            is_function_definition=is_function_def,
            is_function_call=is_function_call,
            has_control_operators=has_control_operators,
            control_operators=control_operators,
            is_variable_assignment=is_variable_assignment,
            is_shell_builtin=is_shell_builtin,
            is_control_structure=is_control_structure,
            has_nested_quotes=has_nested_quotes,
            has_comment=has_comment,
            comment_text=comment_text,
            is_empty=is_empty,
        )

    def extract_redirections(self) -> tuple:
        """
        Extract redirections from the command.

        Returns:
            tuple: (command_without_redirections, stdout_redirect, stderr_redirect)
        """
        cmd, redirections = parse_command_with_redirections(self.command)

        stdout_redirect = None
        stderr_redirect = None

        for op, target in redirections:
            if op in [">", ">>"]:
                stdout_redirect = target
            elif op in ["2>", "2>>"]:
                stderr_redirect = target
            elif op in ["&>", "&>>"]:
                stdout_redirect = target
                stderr_redirect = target

        return (cmd, stdout_redirect, stderr_redirect)


def escape_shell_command(cmd: str) -> str:
    """
    Properly escape a shell command using Python's built-in tools.

    This function handles escaping for different contexts:
    - For single-line commands, it properly quotes the entire command
    - For multiline commands, it preserves the structure while escaping quotes
    - For chained commands with semicolons, each command is properly escaped
    - For commands ending with control operators (&&, ;, &), they are normalized
    - For shell built-in commands like set, export, etc., special handling is applied
    - For commands with complex quoting and variable assignments, special handling is applied
    - For variable assignments (e.g. VAR=value), they are not quoted
    - For shell control structures (if, while, for, until), they are not quoted
    - For commands with redirection operators, redirection parts are preserved

    Args:
        cmd: The shell command to escape

    Returns:
        Escaped shell command safe for inclusion in shell scripts
    """
    # First normalize any problematic command endings
    # cmd = normalize_command_ending(cmd)

    # Remove surrounding quotes if they exist
    if (cmd.startswith("'") and cmd.endswith("'")) or (cmd.startswith('"') and cmd.endswith('"')):
        cmd = cmd[1:-1]

    # Special handling for variable assignments and export commands with nested quotes
    if cmd.startswith("export ") and ("=" in cmd) and ('"' in cmd or "'" in cmd):
        return cmd

    # Handle commands with redirection operators
    for op in REDIRECTION_OPERATORS:
        if op in cmd:
            # Parse and preserve redirection parts
            cmd_parts, redirections = parse_command_with_redirections(cmd)
            if redirections:
                # Escape the command part only, preserving redirections
                escaped_cmd = escape_shell_command_without_redirections(cmd_parts)
                # Reconstruct the command with unescaped redirections
                return reconstruct_command_with_redirections(escaped_cmd, redirections)
            break

    # Check if this is a simple variable assignment (VAR=value with no spaces around =)
    if "=" in cmd and not cmd.strip().startswith("-") and " = " not in cmd:
        var_assign_pattern = r"^[a-zA-Z0-9_]+=.*$"
        if re.match(var_assign_pattern, cmd.strip()):
            return cmd.strip()

    cmd_parts = cmd.strip().split()
    # Handle shell builtins
    if cmd_parts and cmd_parts[0] in SHELL_BUILTINS:
        return cmd

    # Handle shell control structures
    if cmd_parts and cmd_parts[0] in SHELL_CONTROL_STRUCTURES:
        return cmd

    # For multiline commands, we'll handle them differently
    if "\n" in cmd:
        # For multiline commands, preserve the structure
        # but escape any double quotes that might interfere with outer quoting
        return cmd.replace('"', '\\"')

    # For commands with semicolons, escape each part separately
    if ";" in cmd:
        parts = []
        for part in cmd.split(";"):
            # Skip empty parts (handles cases like "ls;;ls" or "ls;  ;ls")
            stripped = part.strip()
            if stripped:
                # Check for redirections in this part
                if any(op in stripped for op in REDIRECTION_OPERATORS):
                    cmd_part, redirections = parse_command_with_redirections(stripped)
                    if redirections:
                        escaped_cmd = escape_shell_command_without_redirections(cmd_part)
                        parts.append(
                            reconstruct_command_with_redirections(escaped_cmd, redirections)
                        )
                        continue

                # Check if this is a variable assignment
                if "=" in stripped and not stripped.startswith("-") and " = " not in stripped:
                    if re.match(r"^[a-zA-Z0-9_]+=.*$", stripped):
                        parts.append(stripped)
                        continue

                # Check if this part starts with a shell builtin or control structure
                part_cmd = stripped.split()[0] if stripped.split() else ""
                if part_cmd in SHELL_BUILTINS or part_cmd in SHELL_CONTROL_STRUCTURES:
                    parts.append(stripped)
                else:
                    parts.append(shlex.quote(stripped))
            else:
                # Keep empty commands (they do nothing but preserve chain structure)
                parts.append("")
        return "; ".join(parts)

    # Check for other control operators that might be within the command (&&, ||, etc.)
    for op in ["&&", "||"]:
        if op in cmd:
            parts = []
            for part in cmd.split(op):
                stripped = part.strip()
                if stripped:
                    # Check for redirections in this part
                    if any(redirection_op in stripped for redirection_op in REDIRECTION_OPERATORS):
                        cmd_part, redirections = parse_command_with_redirections(stripped)
                        if redirections:
                            escaped_cmd = escape_shell_command_without_redirections(cmd_part)
                            parts.append(
                                reconstruct_command_with_redirections(escaped_cmd, redirections)
                            )
                            continue

                    # Check if this is a variable assignment
                    if "=" in stripped and not stripped.startswith("-") and " = " not in stripped:
                        if re.match(r"^[a-zA-Z0-9_]+=.*$", stripped):
                            parts.append(stripped)
                            continue

                    # Check if this part starts with a shell builtin or control structure
                    part_cmd = stripped.split()[0] if stripped.split() else ""
                    if part_cmd in SHELL_BUILTINS or part_cmd in SHELL_CONTROL_STRUCTURES:
                        parts.append(stripped)
                    else:
                        parts.append(shlex.quote(stripped))
            return f" {op} ".join(parts)

    # For single line commands, full quoting is appropriate (except for special cases)
    return shlex.quote(cmd)


def escape_shell_command_without_redirections(cmd: str) -> str:
    """
    Escape a shell command without considering redirections.

    Args:
        cmd: The command part without redirections

    Returns:
        Escaped command
    """
    cmd = cmd.strip()

    # Skip escaping for special cases
    cmd_parts = cmd.split()
    if not cmd_parts:
        return cmd

    # Handle shell builtins and control structures
    if cmd_parts[0] in SHELL_BUILTINS or cmd_parts[0] in SHELL_CONTROL_STRUCTURES:
        return cmd

    # Handle variable assignments
    if "=" in cmd and not cmd.strip().startswith("-") and " = " not in cmd:
        var_assign_pattern = r"^[a-zA-Z0-9_]+=.*$"
        if re.match(var_assign_pattern, cmd.strip()):
            return cmd.strip()

    # Normal escaping for other commands
    return shlex.quote(cmd)


def parse_command_with_redirections(cmd: str) -> tuple:
    """
    Parse a command to separate the command part from redirection parts.

    Args:
        cmd: The command string potentially containing redirections

    Returns:
        tuple: (command_part, list_of_redirections)
    """
    redirections = []
    command_part = cmd

    # Define redirection patterns
    redirect_patterns = [
        # stdout to file (>)
        (r"(?<![&2])>\s*(\S+)", ">"),
        # stdout append to file (>>)
        (r"(?<![&2])>>\s*(\S+)", ">>"),
        # stderr to file (2>)
        (r"2>\s*(\S+)", "2>"),
        # stderr append to file (2>>)
        (r"2>>\s*(\S+)", "2>>"),
        # both stdout and stderr to file (&>)
        (r"&>\s*(\S+)", "&>"),
        # both stdout and stderr append to file (&>>)
        (r"&>>\s*(\S+)", "&>>"),
        # stdin from file (<)
        (r"<\s*(\S+)", "<"),
        # here document (<<)
        (r"<<\s*(\S+)", "<<"),
    ]

    # Extract all redirections
    for pattern, op in redirect_patterns:
        matches = re.finditer(pattern, cmd)
        for match in matches:
            target = match.group(1)
            redirections.append((op, target, match.span()))

    # Sort redirections by position (to remove from right to left)
    redirections.sort(key=lambda x: x[2][0], reverse=True)

    # Remove redirections from the command
    modified_cmd = cmd
    for op, target, span in redirections:
        modified_cmd = modified_cmd[: span[0]] + modified_cmd[span[1] :]

    return modified_cmd.strip(), [(op, target) for op, target, _ in redirections]


def reconstruct_command_with_redirections(cmd: str, redirections: list) -> str:
    """
    Reconstruct a command by adding back the unescaped redirections.

    Args:
        cmd: The escaped command part
        redirections: List of (operator, target) tuples

    Returns:
        Complete command with unescaped redirections
    """
    result = cmd

    # Add redirections back (in original order)
    for op, target in reversed(redirections):
        result = f"{result} {op} {target}"

    return result.strip()


def normalize_command_ending(cmd: str) -> str:
    """
    Normalize a shell command by handling trailing control operators.

    This function removes or adjusts trailing shell control operators like &&, ;, &
    that could cause the shell to wait for additional input.

    Args:
        cmd: The shell command to normalize

    Returns:
        Command with trailing control operators handled appropriately
    """
    if not cmd or not cmd.strip():
        return ""

    cmd = cmd.rstrip()

    # Check for trailing control operators
    for op in sorted(SHELL_CONTROL_OPERATORS, key=len, reverse=True):
        if cmd.endswith(op):
            # For && and ||, we need to be careful not to break command chains
            if op in ["&&", "||"]:
                cmd = cmd[: -len(op)].rstrip()
            # For simple redirections at the end, just remove them
            elif op in [">", ">>", "<", "<<"]:
                cmd = cmd[: -len(op)].rstrip()
            # For semicolons, just remove them
            elif op == ";":
                cmd = cmd[:-1].rstrip()
            # For ampersands, handle background processes
            elif op == "&":
                cmd = cmd[:-1].rstrip()

    return cmd


def combine_shell_constructs(command_list):
    """
    Combine consecutive elements in a command list that form a single shell construct.

    This function detects shell constructs like loops, functions, and conditional blocks
    that are split across multiple list elements and combines them into a single
    multiline command string. This is necessary because shell constructs that span
    multiple lines need to be treated as a single command unit rather than individual
    commands.

    Supported shell constructs:
    - while/done loops
    - for/done loops
    - if/fi conditionals
    - case/esac statements
    - function definitions

    Example:
        Input: ['for i in 1 2 3; do', 'echo $i', 'done']
        Output: ['for i in 1 2 3; do\necho $i\ndone']

    Args:
        command_list: List of command strings or ShellCommand objects to process

    Returns:
        A new list with combined shell constructs as multiline strings or ShellCommand objects.
        Returns an empty list if the input is empty or invalid.
    """
    logger = logging.getLogger(__name__)

    # Input validation
    if not command_list:
        logger.debug("Empty command list provided to combine_shell_constructs")
        return []

    if not isinstance(command_list, list):
        logger.warning(
            "Invalid command_list type provided to combine_shell_constructs: %s",
            type(command_list),
        )
        return []

    # Filter out empty entries and process both string and ShellCommand objects
    filtered_commands = []
    original_objects = []  # Keep track of original objects

    for cmd in command_list:
        if not cmd:
            continue

        if isinstance(cmd, str):
            if cmd.strip():
                filtered_commands.append(cmd)
                original_objects.append(None)  # No original object for strings
        elif isinstance(cmd, ShellCommand):
            # Handle ShellCommand objects by extracting their command string
            if cmd.command and cmd.command.strip():
                filtered_commands.append(cmd.command)
                original_objects.append(cmd)  # Store the original ShellCommand

    if not filtered_commands:
        logger.debug("No valid commands found in command_list after filtering")
        return []

    # Use filtered commands for processing
    logger.debug("Processing %d commands in shell construct combination", len(filtered_commands))

    # Track shell constructs we're looking for
    construct_patterns = {
        "while": {
            "start": ["while"],
            "end": ["done"],
            "patterns": [
                # while condition; do
                lambda s: s.strip()
                .lower()
                .startswith("while "),
            ],
        },
        "for": {
            "start": ["for"],
            "end": ["done"],
            "patterns": [
                # for var in list; do
                lambda s: s.strip()
                .lower()
                .startswith("for "),
            ],
        },
        "if": {
            "start": ["if"],
            "end": ["fi"],
            "patterns": [
                # if condition; then
                lambda s: s.strip()
                .lower()
                .startswith("if "),
            ],
        },
        "case": {
            "start": ["case"],
            "end": ["esac"],
            "patterns": [
                # case var in
                lambda s: s.strip()
                .lower()
                .startswith("case "),
            ],
        },
        "function": {
            "start": ["function", "() {", "(){"],
            "end": ["}"],
            # Additional patterns to identify function definitions
            "patterns": [
                # function name() { ... }
                lambda s: s.strip().lower().startswith("function ") and ("() {" in s or "(){" in s),
                # name() { ... }
                lambda s: ("() {" in s or "(){" in s)
                and not s.strip().lower().startswith("function "),
                # function name { ... }
                lambda s: s.strip().lower().startswith("function ") and "{" in s,
            ],
        },
    }

    result = []
    construct_buffer = []
    construct_buffer_originals = []  # Track original objects for buffered commands
    active_constructs = []

    for i, cmd in enumerate(filtered_commands):
        # Skip empty commands (should not happen after filtering)
        if not cmd or not cmd.strip():
            continue

        cmd_lower = cmd.lower().strip()
        first_word = cmd_lower.split()[0] if cmd_lower.split() else ""

        # Check if this line starts a new construct
        starts_construct = False
        for construct, patterns in construct_patterns.items():
            # First check for explicit patterns if defined
            if "patterns" in patterns:
                for pattern_func in patterns["patterns"]:
                    if pattern_func(cmd):
                        starts_construct = True
                        active_constructs.append(construct)
                        logger.debug(
                            "Starting %s construct (pattern match): %s",
                            construct,
                            cmd.strip()[:40],
                        )
                        break
                if starts_construct:
                    break

            # Then check for start keywords
            if not starts_construct and any(p in cmd_lower for p in patterns["start"]):
                # For function definitions
                if construct == "function":
                    # Check for the two common function definition styles:
                    # 1. function name() { ... }
                    # 2. name() { ... }
                    if (
                        "function " in cmd_lower
                        or (
                            any(
                                cmd_lower.find(f"{c}") > -1
                                for c in ["() {", "(){", "()\n{", "() \n{"]
                            )
                        )
                        or (
                            cmd_lower.rstrip().endswith("{")
                            and "(" in cmd_lower
                            and ")" in cmd_lower
                        )
                    ):
                        starts_construct = True
                        active_constructs.append(construct)
                        logger.debug(
                            "Starting %s construct (keyword match): %s",
                            construct,
                            cmd.strip()[:40],
                        )
                        break
                # For other constructs, check if it's the first word
                elif first_word in patterns["start"]:
                    starts_construct = True
                    active_constructs.append(construct)
                    logger.debug(
                        "Starting %s construct (first word match): %s",
                        construct,
                        cmd.strip()[:40],
                    )
                    break

        # Check if this line ends an active construct
        ends_construct = False
        if active_constructs:
            current_construct = active_constructs[-1]
            end_patterns = construct_patterns[current_construct]["end"]

            # Check for end patterns in the command
            if any(p in cmd_lower for p in end_patterns):
                # For closing braces of functions, ensure it's not part of another construct
                if current_construct == "function" and "}" in cmd_lower:
                    # Make sure it's a standalone "}" or at the end of a line
                    if cmd_lower == "}" or cmd_lower.endswith("}") or cmd_lower.endswith("};"):
                        ends_construct = True
                        active_constructs.pop()
                        logger.debug("Ending %s construct: %s", current_construct, cmd.strip()[:40])
                # For other end patterns
                else:
                    # Make sure the end pattern appears as a complete word
                    for pattern in end_patterns:
                        if pattern in cmd_lower.split() or cmd_lower.endswith(pattern + ";"):
                            ends_construct = True
                            active_constructs.pop()
                            logger.debug(
                                "Ending %s construct: %s", current_construct, cmd.strip()[:40]
                            )
                            break

        # Buffer the current command and its original object
        construct_buffer.append(cmd)
        construct_buffer_originals.append(original_objects[i])

        # If we've ended all active constructs or encountered a standalone command
        if (ends_construct and not active_constructs) or (
            not starts_construct and not active_constructs
        ):
            # If we have only one command in buffer and it's not part of a construct, add it as is
            if len(construct_buffer) == 1 and not starts_construct and not ends_construct:
                # If the original command was a ShellCommand, return the original object
                original_obj = construct_buffer_originals[0]
                if original_obj is not None:
                    result.append(original_obj)
                else:
                    result.append(construct_buffer[0])
            else:
                # Join the buffered commands into a single multiline command
                multiline_cmd = "\n".join(construct_buffer)

                # Check if any of the original commands were ShellCommand objects
                has_shell_command = any(obj is not None for obj in construct_buffer_originals)

                if has_shell_command:
                    # Find the first ShellCommand object to use as a template
                    shell_cmd_template = None
                    for obj in construct_buffer_originals:
                        if obj is not None:
                            shell_cmd_template = obj
                            break

                    if shell_cmd_template:
                        # Create a new ShellCommand object based on the template
                        # Check if this is a function definition and adjust the description accordingly
                        description = shell_cmd_template.description
                        if "\n" in multiline_cmd and (
                            "() {" in multiline_cmd.split("\n")[0]
                            or "(){" in multiline_cmd.split("\n")[0]
                            or "function " in multiline_cmd.lower().split("\n")[0]
                        ):
                            # Extract function name for better description
                            first_line = multiline_cmd.split("\n")[0].strip().lower()
                            if "function " in first_line:
                                fn_name = first_line.replace("function ", "").split("{")[0].strip()
                                if "(" in fn_name:
                                    fn_name = fn_name.split("(")[0].strip()
                            else:  # name() { syntax
                                fn_name = first_line.split("(")[0].strip()

                            # Use plain function name without special characters in description
                            description = f"Function: {fn_name}"
                            logger.debug(
                                f"Setting safer function description for combined construct: {fn_name}"
                            )

                        new_shell_cmd = ShellCommand(
                            command=multiline_cmd,
                            description=description,
                            is_critical=shell_cmd_template.is_critical,
                            is_multiline=True,
                            is_function_definition=shell_cmd_template.is_function_definition,
                            is_function_call=shell_cmd_template.is_function_call,
                        )
                        result.append(new_shell_cmd)
                    else:
                        result.append(multiline_cmd)
                else:
                    result.append(multiline_cmd)

                # Identify the type of construct for better logging
                construct_type = "unknown"
                if construct_buffer and construct_buffer[0]:
                    first_line = construct_buffer[0].strip().lower()
                    if "function " in first_line or "() {" in first_line or "(){" in first_line:
                        construct_type = "function definition"
                    elif first_line.startswith("if "):
                        construct_type = "if block"
                    elif first_line.startswith("for "):
                        construct_type = "for loop"
                    elif first_line.startswith("while "):
                        construct_type = "while loop"
                    elif first_line.startswith("case "):
                        construct_type = "case statement"

                logger.debug(
                    "Combined %s into multiline command: %s",
                    construct_type,
                    multiline_cmd.split("\n")[0].strip()[:40] + "...",
                )
            construct_buffer = []
            construct_buffer_originals = []

    # Handle any remaining commands in the buffer
    if construct_buffer:
        # If we have incomplete constructs (active_constructs not empty), log a warning
        if active_constructs:
            logger.warning(
                "Incomplete shell construct detected: %s. Commands: %s",
                active_constructs,
                [cmd.strip()[:40] + "..." if len(cmd) > 40 else cmd for cmd in construct_buffer],
            )

        # Still combine the remaining commands to avoid losing them
        multiline_cmd = "\n".join(construct_buffer)

        # Check if any of the original commands were ShellCommand objects
        has_shell_command = any(obj is not None for obj in construct_buffer_originals)

        if has_shell_command:
            # Find the first ShellCommand object to use as a template
            shell_cmd_template = None
            for obj in construct_buffer_originals:
                if obj is not None:
                    shell_cmd_template = obj
                    break

            if shell_cmd_template:
                # Create a new ShellCommand object from the template
                new_shell_cmd = ShellCommand(
                    command=multiline_cmd,
                    description=shell_cmd_template.description,
                    is_critical=shell_cmd_template.is_critical,
                    is_multiline=True,
                    is_function_definition=shell_cmd_template.is_function_definition,
                    is_function_call=shell_cmd_template.is_function_call,
                )
                result.append(new_shell_cmd)
            else:
                result.append(multiline_cmd)
        else:
            result.append(multiline_cmd)

        logger.debug(
            "Combined remaining commands into multiline command: %s",
            multiline_cmd.split("\n")[0].strip()[:40] + "...",
        )

    # Final validation - make sure we don't return empty result
    if not result:
        logger.warning(
            "Shell construct combination resulted in empty list. Original commands: %s",
            [str(cmd)[:40] + "..." if len(str(cmd)) > 40 else str(cmd) for cmd in command_list[:5]],
        )

        # If we have original ShellCommand objects, return those
        if any(obj is not None for obj in original_objects):
            return [
                obj if obj is not None else cmd
                for cmd, obj in zip(filtered_commands, original_objects)
            ]

        # Otherwise return filtered string commands
        return filtered_commands

    return result
