"""Standalone field coercion functions for direct use in PANTHER configuration code.

This module provides pure validation/coercion functions that accept a value and field name,
then return the validated/converted result or raise ``ValueError``. They are intended
for imperative call-sites where you need to validate a single value outside of a
Pydantic model context.

Contrast with ``panther.config.core.validators.pydantic_factories``, which provides
*factory functions* that return Pydantic-compatible validator callables.

Typical usage::

    from panther.config.core.components.field_coercion import validate_integer_field

    port = validate_integer_field(raw_value, "port")
"""

import logging
from typing import Any


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
