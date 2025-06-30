"""Universal validation functions for consistent type conversion across PANTHER configurations."""

import logging
from typing import Any, List, Union


def validate_integer_field(value: Any, field_name: str) -> int:
    """Convert various input types to integer with clear error messages.

    Args:
        value: Input value to convert
        field_name: Name of the field for error messages

    Returns:
        Integer value

    Raises:
        ValueError: If conversion is not possible
    """
    logger = logging.getLogger(__name__)

    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        try:
            # Handle decimal strings by converting to float first
            if "." in value:
                float_val = float(value)
                logger.warning(
                    f"Converting decimal string '{value}' to integer {int(float_val)} for field '{field_name}'"
                )
                return int(float_val)
            else:
                return int(value)
        except ValueError:
            logger.error(
                f"Invalid integer value '{value}' for field '{field_name}'. Expected integer or numeric string"
            )
            raise ValueError(
                f"Invalid integer value '{value}' for field '{field_name}'. Expected integer or numeric string"
            )
    elif isinstance(value, float):
        if value.is_integer():
            logger.warning(
                f"Converting float {value} to integer {int(value)} for field '{field_name}'"
            )
            return int(value)
        else:
            logger.error(
                f"Cannot convert float {value} with fractional part to integer for field '{field_name}'"
            )
            raise ValueError(
                f"Cannot convert float {value} with fractional part to integer for field '{field_name}'"
            )
    else:
        logger.error(
            f"Invalid type {type(value)} for field '{field_name}'. Expected integer, string, or float"
        )
        raise ValueError(
            f"Invalid type {type(value)} for field '{field_name}'. Expected integer, string, or float"
        )


def validate_time_field(
    value: Any, field_name: str, valid_units: List[str] = None
) -> str:
    """Convert time values to string format with units.

    Args:
        value: Input value (int seconds or string with units)
        field_name: Name of the field for error messages
        valid_units: List of valid time units (default: ['s', 'ms', 'm', 'h', 'd'])

    Returns:
        String with time unit

    Raises:
        ValueError: If conversion is not possible
    """
    logger = logging.getLogger(__name__)

    if valid_units is None:
        valid_units = ["s", "ms", "m", "h", "d"]

    if isinstance(value, int):
        return f"{value}s"
    elif isinstance(value, str):
        # If already a string, validate format
        if value.isdigit():
            return f"{value}s"
        # Check if it has a valid unit
        for unit in valid_units:
            if value.endswith(unit):
                try:
                    # Validate the numeric part
                    numeric_part = value[: -len(unit)]
                    int(numeric_part)
                    return value
                except ValueError:
                    break
        logger.error(
            f"Invalid time value '{value}' for field '{field_name}'. Expected integer (seconds) or string with time unit {valid_units}"
        )
        raise ValueError(
            f"Invalid time value '{value}' for field '{field_name}'. Expected integer (seconds) or string with time unit {valid_units}"
        )
    else:
        logger.error(
            f"Invalid time value '{value}' of type {type(value).__name__} for field '{field_name}'. Expected integer (seconds) or string with time unit {valid_units}"
        )
        raise ValueError(
            f"Invalid time value '{value}' of type {type(value).__name__} for field '{field_name}'. Expected integer (seconds) or string with time unit {valid_units}"
        )


def validate_enum_field(
    value: Any, field_name: str, valid_values: List[str], case_sensitive: bool = False
) -> str:
    """Convert string values to valid enum options.

    Args:
        value: Input value to validate
        field_name: Name of the field for error messages
        valid_values: List of valid enum values
        case_sensitive: Whether validation is case sensitive

    Returns:
        Valid enum value

    Raises:
        ValueError: If value is not valid
    """
    logger = logging.getLogger(__name__)

    if not isinstance(value, str):
        logger.error(
            f"Invalid type {type(value)} for enum field '{field_name}'. Expected string"
        )
        raise ValueError(
            f"Invalid type {type(value)} for enum field '{field_name}'. Expected string"
        )

    # Handle case insensitive matching
    if not case_sensitive:
        value_lower = value.lower()
        for valid_val in valid_values:
            if valid_val.lower() == value_lower:
                if value != valid_val:
                    logger.warning(
                        f"Converting '{value}' to '{valid_val}' for field '{field_name}'"
                    )
                return valid_val
    else:
        if value in valid_values:
            return value

    logger.error(
        f"Invalid value '{value}' for field '{field_name}'. Valid options: {valid_values}"
    )
    raise ValueError(
        f"Invalid value '{value}' for field '{field_name}'. Valid options: {valid_values}"
    )


def validate_boolean_field(value: Any, field_name: str) -> bool:
    """Convert various input types to boolean.

    Args:
        value: Input value to convert
        field_name: Name of the field for error messages

    Returns:
        Boolean value

    Raises:
        ValueError: If conversion is not possible
    """
    logger = logging.getLogger(__name__)

    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        lower_val = value.lower()
        if lower_val in ("true", "1", "yes", "on", "enabled"):
            if value != "true":
                logger.warning(f"Converting '{value}' to True for field '{field_name}'")
            return True
        elif lower_val in ("false", "0", "no", "off", "disabled"):
            if value != "false":
                logger.warning(
                    f"Converting '{value}' to False for field '{field_name}'"
                )
            return False
        else:
            logger.error(
                f"Invalid boolean value '{value}' for field '{field_name}'. Expected true/false, yes/no, 1/0, etc."
            )
            raise ValueError(
                f"Invalid boolean value '{value}' for field '{field_name}'. Expected true/false, yes/no, 1/0, etc."
            )
    elif isinstance(value, (int, float)):
        bool_val = bool(value)
        logger.warning(
            f"Converting numeric {value} to {bool_val} for field '{field_name}'"
        )
        return bool_val
    else:
        logger.error(
            f"Invalid type {type(value)} for boolean field '{field_name}'. Expected boolean, string, or number"
        )
        raise ValueError(
            f"Invalid type {type(value)} for boolean field '{field_name}'. Expected boolean, string, or number"
        )
