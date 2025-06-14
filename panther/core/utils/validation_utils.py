"""
Validation Utilities

This module provides utilities for common validation patterns,
reducing duplication of validation logic across the codebase.
"""

from __future__ import annotations
from typing import Any
from collections.abc import Callable
from pathlib import Path

from panther.core.utils.logging_mixin import LoggerMixin


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: ValidationResult) -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def raise_if_invalid(self) -> None:
        """Raise ValidationError if there are any errors."""
        if not self.is_valid:
            raise ValidationError(
                f"Validation failed with {len(self.errors)} errors:\n"
                + "\n".join(f"  - {error}" for error in self.errors)
            )


class ValidationUtils(LoggerMixin):
    """
    Utility class for common validation operations.

    Reduces duplication of validation logic across configuration and plugin validation.
    """

    @classmethod
    def validate_required_fields(
        cls, obj: Any, required_fields: list[str], result: ValidationResult | None = None
    ) -> ValidationResult:
        """
        Validate that an object has required fields.

        Args:
            obj: Object to validate
            required_fields: List of required field names
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        for field in required_fields:
            if not hasattr(obj, field):
                result.add_error(f"Missing required field: {field}")
            elif getattr(obj, field) is None:
                result.add_error(f"Required field '{field}' is None")
            elif isinstance(getattr(obj, field), str) and not getattr(obj, field).strip():
                result.add_error(f"Required field '{field}' is empty")

        return result

    @classmethod
    def validate_field_types(
        cls,
        obj: Any,
        field_types: dict[str, type | tuple[type, ...]],
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate field types on an object.

        Args:
            obj: Object to validate
            field_types: Dict mapping field names to expected types
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        for field, expected_type in field_types.items():
            if hasattr(obj, field):
                value = getattr(obj, field)
                if value is not None and not isinstance(value, expected_type):
                    if isinstance(expected_type, tuple):
                        type_names = " or ".join(t.__name__ for t in expected_type)
                    else:
                        type_names = expected_type.__name__
                    result.add_error(
                        f"Invalid type for field '{field}': "
                        f"expected {type_names}, got {type(value).__name__}"
                    )

        return result

    @classmethod
    def validate_string_choices(
        cls,
        value: str,
        field_name: str,
        choices: list[str],
        case_sensitive: bool = True,
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate that a string value is one of the allowed choices.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            choices: List of allowed values
            case_sensitive: Whether comparison is case-sensitive
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        if value is None:
            return result

        valid_choices = choices
        test_value = value

        if not case_sensitive:
            valid_choices = [c.lower() for c in choices]
            test_value = value.lower()

        if test_value not in valid_choices:
            result.add_error(
                f"Invalid value for '{field_name}': '{value}'. "
                f"Must be one of: {', '.join(choices)}"
            )

        return result

    @classmethod
    def validate_numeric_range(
        cls,
        value: int | float,
        field_name: str,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate that a numeric value is within a range.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        if value is None:
            return result

        if min_value is not None and value < min_value:
            result.add_error(f"Value for '{field_name}' ({value}) is below minimum ({min_value})")

        if max_value is not None and value > max_value:
            result.add_error(f"Value for '{field_name}' ({value}) is above maximum ({max_value})")

        return result

    @classmethod
    def validate_path_exists(
        cls,
        path: str | Path,
        field_name: str,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        create_if_missing: bool = False,
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate that a path exists and meets requirements.

        Args:
            path: Path to validate
            field_name: Name of the field for error messages
            must_be_file: Path must be a file
            must_be_dir: Path must be a directory
            create_if_missing: Create directory if it doesn't exist
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        if path is None:
            return result

        path_obj = Path(path)

        if not path_obj.exists():
            if create_if_missing and must_be_dir:
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    result.add_warning(f"Created missing directory: {path}")
                except Exception as e:
                    result.add_error(
                        f"Path '{field_name}' does not exist and could not be created: {e}"
                    )
            else:
                result.add_error(f"Path '{field_name}' does not exist: {path}")
        else:
            if must_be_file and not path_obj.is_file():
                result.add_error(f"Path '{field_name}' must be a file: {path}")
            elif must_be_dir and not path_obj.is_dir():
                result.add_error(f"Path '{field_name}' must be a directory: {path}")

        return result

    @classmethod
    def validate_list_not_empty(
        cls,
        lst: list[Any],
        field_name: str,
        min_length: int = 1,
        max_length: int | None = None,
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate that a list is not empty and meets length requirements.

        Args:
            lst: List to validate
            field_name: Name of the field for error messages
            min_length: Minimum required length
            max_length: Maximum allowed length
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        if lst is None:
            result.add_error(f"Field '{field_name}' is None but should be a list")
            return result

        if len(lst) < min_length:
            result.add_error(
                f"List '{field_name}' has {len(lst)} items, " f"minimum required is {min_length}"
            )

        if max_length is not None and len(lst) > max_length:
            result.add_error(
                f"List '{field_name}' has {len(lst)} items, " f"maximum allowed is {max_length}"
            )

        return result

    @classmethod
    def validate_dict_keys(
        cls,
        dct: dict[str, Any],
        field_name: str,
        required_keys: list[str] | None = None,
        allowed_keys: list[str] | None = None,
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate dictionary keys.

        Args:
            dct: Dictionary to validate
            field_name: Name of the field for error messages
            required_keys: Keys that must be present
            allowed_keys: Keys that are allowed (others generate warnings)
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        if dct is None:
            if required_keys:
                result.add_error(f"Field '{field_name}' is None but should be a dict")
            return result

        # Check required keys
        if required_keys:
            for key in required_keys:
                if key not in dct:
                    result.add_error(f"Dictionary '{field_name}' missing required key: '{key}'")

        # Check allowed keys
        if allowed_keys:
            for key in dct:
                if key not in allowed_keys:
                    result.add_warning(f"Dictionary '{field_name}' has unexpected key: '{key}'")

        return result

    @classmethod
    def validate_custom(
        cls,
        value: Any,
        field_name: str,
        validator: Callable[[Any], bool],
        error_message: str,
        result: ValidationResult | None = None,
    ) -> ValidationResult:
        """
        Validate using a custom validator function.

        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            validator: Function that returns True if valid
            error_message: Error message if validation fails
            result: Existing validation result to append to

        Returns:
            ValidationResult with any errors found
        """
        result = result or ValidationResult()

        try:
            if not validator(value):
                result.add_error(f"{field_name}: {error_message}")
        except Exception as e:
            result.add_error(f"Error validating '{field_name}': {type(e).__name__}: {str(e)}")

        return result

    @classmethod
    def create_validator(
        cls, validations: list[Callable[[Any, ValidationResult], ValidationResult]]
    ) -> Callable[[Any], ValidationResult]:
        """
        Create a composite validator from multiple validation functions.

        Args:
            validations: List of validation functions

        Returns:
            Composite validator function
        """

        def validator(obj: Any) -> ValidationResult:
            result = ValidationResult()
            for validation in validations:
                validation(obj, result)
            return result

        return validator
