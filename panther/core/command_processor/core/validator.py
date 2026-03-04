"""Command validation functionality.

Provides ``CommandValidator`` for security and correctness checks on raw
shell command strings, and ``ValidationResult`` for structured error/warning
accumulation.

Checks performed:
    - Dangerous command patterns (``rm -rf /``, fork bombs, etc.)
    - Sensitive commands requiring careful handling (``sudo``, ``chmod``, ...)
    - Quote balance (single and double)
    - Potential injection attempts (excessive separators, backticks, ``eval``)
    - Malformed or risky redirections
    - Unquoted environment variable expansion
    - Syntactic structure (balanced parens, braces, brackets)
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ValidationResult:
    """Accumulator for command validation errors and warnings.

    Attributes:
        is_valid: ``True`` until ``add_error`` is called.
        errors: List of error description strings (validation failures).
        warnings: List of advisory warning strings (non-blocking).
    """

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def add_error(self, error: str) -> None:
        """Add an error and mark the result as invalid.

        Args:
            error: Human-readable error description.
        """
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add an advisory warning (does not affect ``is_valid``).

        Args:
            warning: Human-readable warning description.
        """
        self.warnings.append(warning)


class CommandValidator:
    """Validate shell commands for security and correctness.

    Performs multi-pass analysis: dangerous patterns, sensitive commands,
    quote balance, injection indicators, redirection safety, and environment
    variable hygiene.  Also offers ``sanitize_command`` for removing known
    dangerous patterns and ``validate_command_structure`` for syntactic
    bracket/brace/parenthesis balance checks.

    Example:
        ::

            validator = CommandValidator()
            result = validator.validate_command("rm -rf /")
            assert not result.is_valid
            assert any("Dangerous" in e for e in result.errors)
    """

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
            if dangerous == "format":
                # Special handling for 'format' - only dangerous as a standalone command
                # or when used as a disk formatting command, not in printf format strings
                if re.search(r"\bformat\s+[A-Za-z]:", command) or re.search(
                    r"^format\s", command
                ):
                    result.add_error(f"Dangerous command pattern detected: {dangerous}")
            elif dangerous in command:
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
