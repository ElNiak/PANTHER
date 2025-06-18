"""
Command Summarizer

This module provides smart command summarization for logging purposes,
reducing verbosity while maintaining useful information about command generation.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple


class CommandSummarizer:
    """Smart command summarization for logging."""

    # Common command patterns to recognize
    COMMAND_PATTERNS = {
        "setup": ["export", "mkdir", "cd", "cp", "mv", "chmod", "chown"],
        "build": ["make", "cmake", "gcc", "g++", "cargo", "npm", "python setup.py"],
        "install": ["apt-get", "yum", "pip", "npm install", "cargo install"],
        "network": ["wget", "curl", "git clone", "rsync", "scp"],
        "cleanup": ["rm", "rmdir", "clean", "purge", "uninstall"],
        "test": ["test", "pytest", "unittest", "check", "verify"],
        "docker": ["docker", "docker-compose"],
        "ivy": ["ivy_check", "ivy", "ivy compile"],
    }

    # Sensitive patterns to mask
    SENSITIVE_PATTERNS = [
        (r"password[=\s]+[^\s]+", "password=<MASKED>"),
        (r"token[=\s]+[^\s]+", "token=<MASKED>"),
        (r"key[=\s]+[^\s]+", "key=<MASKED>"),
        (r"secret[=\s]+[^\s]+", "secret=<MASKED>"),
        (r"--password\s+[^\s]+", "--password <MASKED>"),
        (r"--token\s+[^\s]+", "--token <MASKED>"),
    ]

    @staticmethod
    def summarize_command_list(commands: List[str], max_commands: int = 3) -> str:
        """
        Summarize a list of commands for logging.

        Args:
            commands: List of command strings
            max_commands: Maximum number of commands to show in detail

        Returns:
            Summary string suitable for logging
        """
        if not commands:
            return "No commands"

        total_count = len(commands)

        # Classify commands by type
        command_types = CommandSummarizer._classify_commands(commands)

        # Build summary
        if total_count <= max_commands:
            # Show all commands (masked for security)
            masked_commands = [
                CommandSummarizer._mask_sensitive(cmd) for cmd in commands
            ]
            commands_str = "; ".join(masked_commands)
            return f"{total_count} commands: {commands_str}"
        else:
            # Show summary with types and sample
            type_summary = CommandSummarizer._format_command_types(command_types)
            sample_commands = commands[:max_commands]
            masked_sample = [
                CommandSummarizer._mask_sensitive(cmd) for cmd in sample_commands
            ]
            sample_str = "; ".join(masked_sample)

            return f"{total_count} commands ({type_summary}). Sample: {sample_str}..."

    @staticmethod
    def summarize_template_context(context: Dict[str, Any], max_keys: int = 5) -> str:
        """
        Summarize template rendering context.

        Args:
            context: Template context dictionary
            max_keys: Maximum number of keys to show

        Returns:
            Summary string suitable for logging
        """
        if not context:
            return "Empty context"

        total_keys = len(context)

        # Identify important vs. verbose keys
        important_keys = []
        verbose_keys = []

        for key, value in context.items():
            if CommandSummarizer._is_important_context_key(key, value):
                important_keys.append(key)
            else:
                verbose_keys.append(key)

        # Build summary
        summary_parts = [f"{total_keys} parameters"]

        if important_keys:
            if len(important_keys) <= max_keys:
                key_summary = CommandSummarizer._format_context_keys(
                    context, important_keys
                )
                summary_parts.append(f"key params: {key_summary}")
            else:
                sample_keys = important_keys[:max_keys]
                key_summary = CommandSummarizer._format_context_keys(
                    context, sample_keys
                )
                summary_parts.append(
                    f"key params: {key_summary}... (+{len(important_keys) - max_keys} more)"
                )

        if verbose_keys:
            summary_parts.append(f"{len(verbose_keys)} verbose params")

        return " | ".join(summary_parts)

    @staticmethod
    def get_command_stats(commands: List[str]) -> Dict[str, Any]:
        """
        Get command statistics for logging.

        Args:
            commands: List of command strings

        Returns:
            Dictionary with command statistics
        """
        if not commands:
            return {"total": 0, "types": {}, "patterns": []}

        command_types = CommandSummarizer._classify_commands(commands)

        # Analyze command patterns
        patterns = []
        for cmd in commands:
            first_word = cmd.strip().split()[0] if cmd.strip() else ""
            if first_word:
                patterns.append(first_word)

        pattern_counts = Counter(patterns)
        top_patterns = [
            f"{cmd}({count})" for cmd, count in pattern_counts.most_common(3)
        ]

        return {
            "total": len(commands),
            "types": dict(command_types),
            "top_patterns": top_patterns,
            "avg_length": (
                sum(len(cmd) for cmd in commands) // len(commands) if commands else 0
            ),
        }

    @staticmethod
    def summarize_single_command(command: str, max_length: int = 100) -> str:
        """
        Summarize a single command for logging.

        Args:
            command: Command string
            max_length: Maximum length for summary

        Returns:
            Summarized command string
        """
        if not command:
            return "Empty command"

        # Mask sensitive information
        masked_cmd = CommandSummarizer._mask_sensitive(command)

        # Truncate if too long
        if len(masked_cmd) <= max_length:
            return masked_cmd
        else:
            return masked_cmd[: max_length - 3] + "..."

    @staticmethod
    def _classify_commands(commands: List[str]) -> Counter:
        """Classify commands by type based on patterns."""
        types = Counter()

        for cmd in commands:
            cmd_lower = cmd.lower().strip()
            classified = False

            for cmd_type, patterns in CommandSummarizer.COMMAND_PATTERNS.items():
                for pattern in patterns:
                    if pattern in cmd_lower:
                        types[cmd_type] += 1
                        classified = True
                        break
                if classified:
                    break

            if not classified:
                types["other"] += 1

        return types

    @staticmethod
    def _format_command_types(command_types: Counter) -> str:
        """Format command type summary."""
        if not command_types:
            return "no types"

        # Sort by count, show top 3
        sorted_types = command_types.most_common(3)
        type_strs = [f"{cmd_type}: {count}" for cmd_type, count in sorted_types]

        total_types = len(command_types)
        if total_types > 3:
            type_strs.append(f"+{total_types - 3} more")

        return ", ".join(type_strs)

    @staticmethod
    def _is_important_context_key(key: str, value: Any) -> bool:
        """Determine if a context key is important for logging."""
        # Important keys are typically short, non-verbose values
        key_lower = key.lower()

        # Always important
        important_keys = {
            "name",
            "type",
            "role",
            "protocol",
            "implementation",
            "port",
            "host",
            "timeout",
            "version",
            "env",
            "mode",
        }

        if key_lower in important_keys:
            return True

        # Verbose keys to skip
        verbose_indicators = {
            "config",
            "template",
            "content",
            "data",
            "params",
            "arguments",
            "full_",
            "detailed_",
            "raw_",
        }

        if any(indicator in key_lower for indicator in verbose_indicators):
            return False

        # Check value type and size
        if isinstance(value, (dict, list)) and len(str(value)) > 50:
            return False

        if isinstance(value, str) and len(value) > 100:
            return False

        return True

    @staticmethod
    def _format_context_keys(context: Dict[str, Any], keys: List[str]) -> str:
        """Format context keys for summary."""
        key_strs = []

        for key in keys:
            value = context[key]

            if isinstance(value, (dict, list)):
                value_str = f"{type(value).__name__}({len(value)})"
            elif isinstance(value, str) and len(value) > 20:
                value_str = f'"{value[:17]}..."'
            else:
                value_str = str(value)

            key_strs.append(f"{key}={value_str}")

        return ", ".join(key_strs)

    @staticmethod
    def _mask_sensitive(command: str) -> str:
        """Mask sensitive information in commands."""
        masked = command

        for pattern, replacement in CommandSummarizer.SENSITIVE_PATTERNS:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)

        return masked
