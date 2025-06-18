from typing import Any, List

"""
Enhanced Jinja2 filters for secure command generation.

This module provides robust quoting and escaping filters for Jinja2 templates
to ensure all dynamic values are properly escaped in shell commands and YAML files.
"""

import json
import shlex

import yaml


def quote_shell(value: Any) -> str:
    """

    Safely quote a value for use in shell commands.

    Args:
        value: The value to quote (will be converted to string)

    Returns:
        str: The properly quoted value for shell use
    """
    if value is None:
        return ""
    return shlex.quote(str(value))


def quote_yaml(value: Any) -> str:
    """
    Safely quote a value for use in YAML.

    Args:
        value: The value to quote

    Returns:
        str: The properly quoted value for YAML use
    """
    if value is None:
        return "null"

    # For simple strings, use flow style dumping without the document markers
    dumped = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True)
    # Remove document start/end markers and trailing newlines
    result = dumped.strip()
    if result.startswith("---"):
        result = result[3:].strip()
    if result.endswith("..."):
        result = result[:-3].strip()
    return result


def quote_json(value: Any) -> str:
    """
    Safely quote a value for use in JSON.

    Args:
        value: The value to quote

    Returns:
        str: The properly quoted value for JSON use
    """
    return json.dumps(value)


def escape_docker_compose(value: Any) -> str:
    """
    Escape a value for use in Docker Compose YAML.

    Args:
        value: The value to escape

    Returns:
        str: The properly escaped value for Docker Compose
    """
    if value is None:
        return ""

    # Convert to string and handle special Docker Compose cases
    str_value = str(value)

    # If the value contains special characters, quote it
    if any(char in str_value for char in ['"', "'", "$", "\\", "\n", "\t"]):
        return quote_yaml(str_value)

    return str_value


def join_command_args(args: list) -> str:
    """
    Join command arguments with proper shell quoting.

    Args:
        args: List of command arguments

    Returns:
        str: Properly quoted and joined command string
    """
    if not args:
        return ""

    return " ".join(quote_shell(arg) for arg in args if arg is not None)


def create_env_export(env_vars: dict) -> str:
    """
    Create export statements for environment variables.

    Args:
        env_vars: Dictionary of environment variables

    Returns:
        str: Shell export statements
    """
    if not env_vars:
        return ""

    exports = []
    for key, value in env_vars.items():
        if value is not None:
            exports.append(f"export {quote_shell(key)}={quote_shell(value)}")

    return "\n".join(exports)


# Dictionary of all available filters for easy registration
TEMPLATE_FILTERS = {
    "quote_shell": quote_shell,
    "quote_yaml": quote_yaml,
    "quote_json": quote_json,
    "escape_docker_compose": escape_docker_compose,
    "join_command_args": join_command_args,
    "create_env_export": create_env_export,
}
