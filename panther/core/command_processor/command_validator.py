"""Command validation functionality."""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of command validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)


class CommandValidator:
    """Validates shell commands for security and correctness."""

    # Dangerous commands that should be avoided
    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "dd if=/dev/zero",
        "mkfs",
        "format",
        ":(){ :|:& };:",  # Fork bomb
    ]

    # Commands that require careful handling
    SENSITIVE_COMMANDS = [
        "sudo",
        "su",
        "chmod",
        "chown",
        "mount",
        "umount",
    ]

    # Shell metacharacters that need escaping
    SHELL_METACHARACTERS = [
        "$",
        "`",
        "\\",
        '"',
        "'",
        "|",
        "&",
        ";",
        "(",
        ")",
        "<",
        ">",
        "{",
        "}",
        "[",
        "]",
        "*",
        "?",
        "~",
        "!",
        "^",
        "#",
    ]

    def validate_command(self, command: str) -> ValidationResult:
        """
        Validate a shell command for security and correctness.

        Args:
            command: The command to validate

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # Check for empty command
        if not command or not command.strip():
            result.add_error("Command is empty")
            return result

        # Check for dangerous commands
        self._check_dangerous_commands(command, result)

        # Check for sensitive commands
        self._check_sensitive_commands(command, result)

        # Check for unbalanced quotes
        self._check_quotes_balance(command, result)

        # Check for injection attempts
        self._check_injection_attempts(command, result)

        # Check for malformed redirections
        self._check_redirections(command, result)

        # Check for environment variable usage
        self._check_environment_variables(command, result)

        return result

    def _check_dangerous_commands(self, command: str, result: ValidationResult) -> None:
        """Check for dangerous command patterns."""
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                result.add_error(f"Dangerous command pattern detected: {dangerous}")

    def _check_sensitive_commands(self, command: str, result: ValidationResult) -> None:
        """Check for sensitive commands that need careful handling."""
        for sensitive in self.SENSITIVE_COMMANDS:
            if re.search(rf"\b{sensitive}\b", command):
                result.add_warning(f"Sensitive command detected: {sensitive}")

    def _check_quotes_balance(self, command: str, result: ValidationResult) -> None:
        """Check if quotes are properly balanced."""
        single_quotes = command.count("'")
        double_quotes = command.count('"')

        if single_quotes % 2 != 0:
            result.add_error("Unbalanced single quotes")

        if double_quotes % 2 != 0:
            result.add_error("Unbalanced double quotes")

    def _check_injection_attempts(self, command: str, result: ValidationResult) -> None:
        """Check for potential command injection attempts."""
        # Check for multiple command separators
        separators = [";", "&&", "||", "|"]
        separator_count = sum(command.count(sep) for sep in separators)

        if separator_count > 3:
            result.add_warning(
                "Many command separators detected - possible injection attempt"
            )

        # Check for backticks (command substitution)
        if "`" in command:
            result.add_warning(
                "Backticks detected - use $() for command substitution instead"
            )

        # Check for eval usage
        if re.search(r"\beval\b", command):
            result.add_error("Use of 'eval' detected - this is a security risk")

    def _check_redirections(self, command: str, result: ValidationResult) -> None:
        """Check for malformed or dangerous redirections."""
        # Check for redirections to /dev/null without reason
        if "> /dev/null 2>&1" in command:
            result.add_warning("Output is being discarded - ensure this is intentional")

        # Check for overwriting important files
        important_files = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/hosts",
            ".bashrc",
            ".profile",
        ]
        for file in important_files:
            if f"> {file}" in command or f">> {file}" in command:
                result.add_error(f"Attempting to write to system file: {file}")

    def _check_environment_variables(
        self, command: str, result: ValidationResult
    ) -> None:
        """Check for environment variable usage."""
        # Check for unexpanded variables
        if re.search(r"\$[A-Za-z_][A-Za-z0-9_]*", command):
            # Check if the variable is properly quoted
            unquoted_vars = re.findall(
                r"(?<![\"\'])(\$[A-Za-z_][A-Za-z0-9_]*)(?![\"\'])", command
            )
            if unquoted_vars:
                result.add_warning(
                    f"Unquoted variables detected: {', '.join(unquoted_vars)}"
                )

        # Check for PATH manipulation
        if "PATH=" in command:
            result.add_warning("PATH environment variable is being modified")

    def sanitize_command(self, command: str) -> str:
        """
        Sanitize a command by escaping dangerous characters.

        Args:
            command: The command to sanitize

        Returns:
            Sanitized command
        """
        # This is a basic sanitization - in practice, use shell_utils.escape_shell_command
        sanitized = command

        # Remove dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/",  # rm -rf /
            r":\(\)\{.*\};:",  # Fork bomb
        ]

        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "", sanitized)

        return sanitized.strip()

    def validate_command_structure(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validate the syntactic structure of a command.

        Args:
            command: The command to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for basic syntax errors
        if command.endswith("\\"):
            return False, "Command ends with escape character"

        # Check for unclosed parentheses
        if command.count("(") != command.count(")"):
            return False, "Unbalanced parentheses"

        # Check for unclosed braces
        if command.count("{") != command.count("}"):
            return False, "Unbalanced braces"

        # Check for unclosed brackets
        if command.count("[") != command.count("]"):
            return False, "Unbalanced brackets"

        return True, None
