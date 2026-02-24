"""Pydantic validator factory functions for PANTHER configuration models.

This module provides *factory functions* that return validator callables compatible
with Pydantic's ``@field_validator`` (v2) and ``@validator`` (v1) decorators. Use
these when you need to attach reusable validation logic to Pydantic model fields.

Contrast with ``panther.config.core.components.universal_validators``, which provides
standalone validation functions for imperative use outside of Pydantic models
(e.g., ``validate_integer_field(value, "port")``).

Factory functions (``create_*``)
    Return a ``Callable[[cls, Any], T]`` suitable for assignment to a Pydantic
    field validator. Each factory accepts configuration parameters (enum class,
    time units, valid values, etc.) and returns a closure that performs the
    actual validation.

Pre-configured validators
    Convenience functions (``protocol_role_validator``, ``implementation_type_validator``,
    ``logging_level_validator``, ``shadow_time_validator``) that wrap the factory
    functions with PANTHER-specific enum classes for immediate use.

Typical usage::

    from pydantic import BaseModel, field_validator
    from panther.config.core.validators.universal_validators import (
        create_enum_validator,
        create_time_string_validator,
        protocol_role_validator,
    )
    from panther.config.core.models.service import ProtocolRole

    class ServiceProtocolConfig(BaseModel):
        role: ProtocolRole
        stop_time: str = "30s"

        _validate_role = field_validator("role", mode="before")(
            protocol_role_validator
        )
        _validate_stop_time = field_validator("stop_time", mode="before")(
            create_time_string_validator(default_unit="s")
        )
"""

import logging
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar

from pydantic import ValidationError

# Set up logger
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Enum)


def create_enum_validator(
    enum_class: Type[T],
    transform: Callable[[str], str] = str.lower,
    logger_instance: Optional[logging.Logger] = None,
) -> Callable:
    """Create a reusable enum validator with error logging.

    Args:
        enum_class: The enum class to validate against
        transform: Function to transform string values before enum conversion
        logger_instance: Optional logger instance to use

    Returns:
        Validator function that can be used with Pydantic @field_validator

    Example:
        @field_validator('role', mode='before')
        role_validator = create_enum_validator(ProtocolRole, str.lower)
    """
    _logger = logger_instance or logger

    def validator(cls, v: Any) -> T:
        """Validate and convert value to enum."""
        if isinstance(v, str):
            try:
                return enum_class(transform(v))
            except ValueError as e:
                valid_values = [item.value for item in enum_class]
                error_msg = f"Invalid {enum_class.__name__} value '{v}'. Valid values are: {valid_values}"
                _logger.error(error_msg)
                raise ValueError(error_msg) from e
        return v

    return validator


def create_time_string_validator(
    default_unit: str = "s",
    valid_units: Optional[list] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> Callable:
    """Create a validator for time string conversion.

    Args:
        default_unit: Default time unit to append to numeric values
        valid_units: List of valid time units (defaults to common ones)
        logger_instance: Optional logger instance to use

    Returns:
        Validator function for time string conversion

    Example:
        @validator('stop_time', pre=True)
        time_validator = create_time_string_validator(default_unit="s")
    """
    if valid_units is None:
        valid_units = ["s", "ms", "m", "h", "d"]

    _logger = logger_instance or logger

    def validator(cls, v: Any) -> str:
        """Convert integer seconds to string format with time unit."""
        if isinstance(v, int):
            return f"{v}{default_unit}"
        elif isinstance(v, str):
            # If already a string, ensure it has a valid time unit
            if v.isdigit():
                return f"{v}{default_unit}"
            # Check if it already has a valid unit
            for unit in valid_units:
                if v.endswith(unit):
                    return v
            # If no valid unit found, log error
            error_msg = f"Invalid time format '{v}'. Expected integer (seconds) or string with time unit ({valid_units})"
            _logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            error_msg = f"Invalid time value '{v}' of type {type(v).__name__}. Expected integer (seconds) or string with time unit ({valid_units})"
            _logger.error(error_msg)
            raise ValueError(error_msg)

    return validator


def create_case_insensitive_string_validator(
    valid_values: list,
    transform: Callable[[str], str] = str.lower,
    logger_instance: Optional[logging.Logger] = None,
) -> Callable:
    """Create a validator for case-insensitive string values.

    Args:
        valid_values: List of valid string values
        transform: Function to transform input before validation
        logger_instance: Optional logger instance to use

    Returns:
        Validator function for case-insensitive string validation
    """
    _logger = logger_instance or logger

    def validator(cls, v: Any) -> str:
        """Validate string value case-insensitively."""
        if isinstance(v, str):
            transformed = transform(v)
            if transformed in [transform(val) for val in valid_values]:
                return transformed
            else:
                error_msg = f"Invalid value '{v}'. Valid values are: {valid_values}"
                _logger.error(error_msg)
                raise ValueError(error_msg)
        return v

    return validator


def create_type_conversion_validator(
    target_type: Type,
    conversion_func: Optional[Callable] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> Callable:
    """Create a validator for safe type conversion.

    Args:
        target_type: Target type to convert to
        conversion_func: Optional custom conversion function
        logger_instance: Optional logger instance to use

    Returns:
        Validator function for type conversion
    """
    _logger = logger_instance or logger

    if conversion_func is None:
        conversion_func = target_type

    def validator(cls, v: Any) -> Any:
        """Convert value to target type safely."""
        if isinstance(v, target_type):
            return v

        try:
            return conversion_func(v)
        except (ValueError, TypeError) as e:
            error_msg = f"Cannot convert '{v}' of type {type(v).__name__} to {target_type.__name__}: {e}"
            _logger.error(error_msg)
            raise ValueError(error_msg) from e

    return validator


# Pre-configured common validators for immediate use
def protocol_role_validator(cls, v: Any) -> Any:
    """Validator for ProtocolRole enum conversion."""
    from panther.config.core.models.service import ProtocolRole

    return create_enum_validator(ProtocolRole, str.lower)(cls, v)


def implementation_type_validator(cls, v: Any) -> Any:
    """Validator for ImplementationType enum conversion."""
    from panther.config.core.models.service import ImplementationType

    return create_enum_validator(ImplementationType, str.lower)(cls, v)


def logging_level_validator(cls, v: Any) -> Any:
    """Validator for LoggingLevel enum conversion."""
    from panther.config.core.models.global_config import LoggingLevel

    return create_enum_validator(LoggingLevel, str.upper)(cls, v)


def shadow_time_validator(cls, v: Any) -> str:
    """Validator for Shadow NS time format conversion."""
    return create_time_string_validator(default_unit="s")(cls, v)
