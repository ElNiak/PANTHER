"""
Enhanced template utilities for plugin command generation.

This module provides helper classes and utilities to build structured template contexts
for secure command generation across all Panther plugins.
"""

import shlex
from typing import Any


class PluginTemplateContext:
    """
    Helper class to build structured template contexts for plugin command generation.

    This class provides a fluent interface for building command arguments, environment
    variables, and extra fields that will be safely rendered in Jinja2 templates.
    """

    def __init__(self):
        self.command_args: list[str] = []
        self.env_vars: dict[str, str] = {}
        self.extra_fields: str = ""

    def add_arg(self, arg: str | int | float | None) -> "PluginTemplateContext":
        """
        Add a single command argument.

        Args:
            arg: The argument to add (None values are skipped)

        Returns:
            self for method chaining
        """
        if arg is not None:
            self.command_args.append(str(arg))
        return self

    def add_args(self, *args: str | int | float | None) -> "PluginTemplateContext":
        """
        Add multiple command arguments.

        Args:
            *args: Arguments to add (None values are skipped)

        Returns:
            self for method chaining
        """
        for arg in args:
            if arg is not None:
                self.command_args.append(str(arg))
        return self

    def add_flag(
        self, flag: str, value: str | int | float | None = None
    ) -> "PluginTemplateContext":
        """
        Add a command flag with optional value.

        Args:
            flag: The flag (e.g., "-p", "--port")
            value: Optional value for the flag

        Returns:
            self for method chaining
        """
        self.command_args.append(str(flag))
        if value is not None:
            self.command_args.append(str(value))
        return self

    def add_conditional_flag(
        self, condition: bool, flag: str, value: str | int | float | None = None
    ) -> "PluginTemplateContext":
        """
        Add a flag only if condition is true.

        Args:
            condition: Whether to add the flag
            flag: The flag to add
            value: Optional value for the flag

        Returns:
            self for method chaining
        """
        if condition:
            self.add_flag(flag, value)
        return self

    def add_key_value_flag(
        self, flag: str, key: str, value: str | int | float
    ) -> "PluginTemplateContext":
        """
        Add a flag with key=value format.

        Args:
            flag: The flag (e.g., "--env")
            key: The key name
            value: The value

        Returns:
            self for method chaining
        """
        self.command_args.extend([str(flag), f"{key}={value}"])
        return self

    def add_env(self, key: str, value: str | int | float) -> "PluginTemplateContext":
        """
        Add an environment variable.

        Args:
            key: Environment variable name
            value: Environment variable value

        Returns:
            self for method chaining
        """
        self.env_vars[key] = str(value)
        return self

    def add_envs(
        self, env_dict: dict[str, str | int | float]
    ) -> "PluginTemplateContext":
        """
        Add multiple environment variables from a dictionary.

        Args:
            env_dict: Dictionary of environment variables

        Returns:
            self for method chaining
        """
        for key, value in env_dict.items():
            self.env_vars[key] = str(value)
        return self

    def set_extra_fields(self, fields: str) -> "PluginTemplateContext":
        """
        Set extra fields (for YAML fragments, etc.).

        Args:
            fields: Extra fields content

        Returns:
            self for method chaining
        """
        self.extra_fields = fields
        return self

    def add_output_redirection(
        self, stdout_path: str | None = None, stderr_path: str | None = None
    ) -> "PluginTemplateContext":
        """
        Add output redirection arguments.

        Args:
            stdout_path: Path for stdout redirection
            stderr_path: Path for stderr redirection

        Returns:
            self for method chaining
        """
        if stdout_path:
            self.add_args(">", stdout_path)
        if stderr_path:
            self.add_args("2>", stderr_path)
        return self

    def add_shell_command_args(self, shell_command: str) -> "PluginTemplateContext":
        """
        Parse and add arguments from a shell command string.

        Args:
            shell_command: Shell command string to parse

        Returns:
            self for method chaining
        """
        if shell_command and shell_command.strip():
            try:
                parsed_args = shlex.split(shell_command.strip())
                self.command_args.extend(parsed_args)
            except ValueError:
                # If parsing fails, add as single argument (safer)
                self.command_args.append(shell_command.strip())
        return self

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to template context dictionary.

        Returns:
            Dictionary suitable for Jinja2 template rendering
        """
        return {
            "command_args": self.command_args,
            "env_vars": self.env_vars,
            "extra_fields": self.extra_fields,
        }

    def get_command_string(self) -> str:
        """
        Get the command as a properly quoted shell command string.

        Returns:
            Properly quoted shell command string
        """
        return shlex.join(self.command_args)

    def clear(self) -> "PluginTemplateContext":
        """
        Clear all accumulated data.

        Returns:
            self for method chaining
        """
        self.command_args.clear()
        self.env_vars.clear()
        self.extra_fields = ""
        return self

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"PluginTemplateContext(args={self.command_args}, env={self.env_vars})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"PluginTemplateContext(command_args={self.command_args!r}, "
            f"env_vars={self.env_vars!r}, extra_fields={self.extra_fields!r})"
        )


def build_legacy_template_context(
    config_params: dict, service_name: str = "", role: str = "", target: str = ""
) -> dict:
    """
    Build a legacy template context for backward compatibility.

    This function helps maintain compatibility with existing templates that expect
    nested dictionary structures instead of the new structured approach.

    Args:
        config_params: Configuration parameters dictionary
        service_name: Name of the service
        role: Role (server/client)
        target: Target address/hostname

    Returns:
        Dictionary compatible with legacy template expectations
    """
    context = {"service_name": service_name, "role": role, "target": target}

    # Deep copy and ensure all nested values are accessible
    def safe_copy(obj):
        if isinstance(obj, dict):
            return {k: safe_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [safe_copy(item) for item in obj]
        else:
            return obj

    context.update(safe_copy(config_params))
    return context


def merge_template_contexts(
    enhanced_context: PluginTemplateContext, legacy_context: dict
) -> dict:
    """
    Merge enhanced and legacy template contexts.

    This allows templates to use either the new structured approach or
    the legacy approach, providing full backward compatibility.

    Args:
        enhanced_context: Enhanced context with command_args, env_vars, etc.
        legacy_context: Legacy context with nested dictionaries

    Returns:
        Merged context dictionary
    """
    merged = enhanced_context.to_dict()
    merged.update(legacy_context)
    return merged
