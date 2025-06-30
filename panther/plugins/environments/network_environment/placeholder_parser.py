"""
Placeholder parser for network-aware command resolution.

This module provides functionality to parse and validate network placeholders
in command templates using the format: @{service:attribute:format}
"""

import re
from typing import Dict, List, Set

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    PlaceholderInfo,
)
from panther.core.exceptions import PlaceholderParsingException


class PlaceholderParser:
    """Parser for network placeholders in command templates."""

    # Regex pattern for matching placeholders: @{service:attribute:format}
    PLACEHOLDER_PATTERN = re.compile(r"@\{([^:]+):([^:}]+)(?::([^}]+))?\}")

    def __init__(self):
        """Initialize the placeholder parser."""
        self._valid_attributes = {attr.value for attr in NetworkAttribute}
        self._valid_formats = {fmt.value for fmt in NetworkFormat}

    def parse_placeholders(self, command_template: str) -> List[PlaceholderInfo]:
        """
        Parse all placeholders from a command template.

        Args:
            command_template: Command template containing placeholders

        Returns:
            List of parsed placeholder information

        Raises:
            PlaceholderParsingException: If parsing fails
        """
        placeholders = []

        try:
            matches = self.PLACEHOLDER_PATTERN.finditer(command_template)

            for match in matches:
                service = match.group(1).strip()
                attribute = match.group(2).strip()
                format_type = match.group(3).strip() if match.group(3) else None
                raw_placeholder = match.group(0)

                placeholder_info = self._create_placeholder_info(
                    service, attribute, format_type, raw_placeholder, command_template
                )
                placeholders.append(placeholder_info)

        except Exception as e:
            raise PlaceholderParsingException(
                f"Failed to parse command template: {str(e)}",
                "unknown",
                command_template,
                str(e),
            )

        return placeholders

    def _create_placeholder_info(
        self,
        service: str,
        attribute: str,
        format_type: str | None,
        raw_placeholder: str,
        command_template: str,
    ) -> PlaceholderInfo:
        """
        Create PlaceholderInfo from parsed components.

        Args:
            service: Service name
            attribute: Network attribute
            format_type: Format type (optional)
            raw_placeholder: Original placeholder string
            command_template: Full command template

        Returns:
            PlaceholderInfo instance

        Raises:
            PlaceholderParsingException: If validation fails
        """
        try:
            # Validate attribute
            if attribute not in self._valid_attributes:
                raise PlaceholderParsingException(
                    f"Invalid attribute '{attribute}'. Valid attributes: {', '.join(self._valid_attributes)}",
                    raw_placeholder,
                    command_template,
                )

            # Validate format if provided
            if format_type and format_type not in self._valid_formats:
                raise PlaceholderParsingException(
                    f"Invalid format '{format_type}'. Valid formats: {', '.join(self._valid_formats)}",
                    raw_placeholder,
                    command_template,
                )

            # Create PlaceholderInfo (this will validate service name)
            return PlaceholderInfo(
                service=service,
                attribute=NetworkAttribute(attribute),
                format_type=NetworkFormat(format_type)
                if format_type
                else NetworkFormat.STRING,
                raw_placeholder=raw_placeholder,
            )

        except ValueError as e:
            raise PlaceholderParsingException(
                str(e), raw_placeholder, command_template, str(e)
            )

    def find_placeholder_strings(self, command_template: str) -> List[str]:
        """
        Find all placeholder strings in a command template.

        Args:
            command_template: Command template to search

        Returns:
            List of placeholder strings
        """
        matches = self.PLACEHOLDER_PATTERN.findall(command_template)
        return [
            f"@{{{service}:{attribute}{':' + fmt if fmt else ''}}}"
            for service, attribute, fmt in matches
        ]

    def validate_command_template(self, command_template: str) -> Dict[str, List[str]]:
        """
        Validate a command template and return validation results.

        Args:
            command_template: Command template to validate

        Returns:
            Dict with 'valid' and 'invalid' placeholder lists
        """
        result = {"valid": [], "invalid": []}

        try:
            placeholders = self.parse_placeholders(command_template)
            result["valid"] = [p.raw_placeholder for p in placeholders]
        except PlaceholderParsingException as e:
            result["invalid"].append(e.context["resolution_context"]["placeholder"])

        return result

    def get_required_services(self, command_template: str) -> Set[str]:
        """
        Get set of service names required by placeholders in template.

        Args:
            command_template: Command template to analyze

        Returns:
            Set of required service names
        """
        try:
            placeholders = self.parse_placeholders(command_template)
            return {p.service for p in placeholders}
        except PlaceholderParsingException:
            return set()

    def has_placeholders(self, command_template: str) -> bool:
        """
        Check if command template contains any placeholders.

        Args:
            command_template: Command template to check

        Returns:
            True if placeholders found, False otherwise
        """
        return bool(self.PLACEHOLDER_PATTERN.search(command_template))

    def replace_placeholders(
        self, command_template: str, substitutions: Dict[str, str]
    ) -> str:
        """
        Replace placeholders in template with provided substitutions.

        Args:
            command_template: Command template with placeholders
            substitutions: Dict mapping placeholder strings to values

        Returns:
            Command template with substitutions applied
        """
        result = command_template
        for placeholder, value in substitutions.items():
            result = result.replace(placeholder, value)
        return result
