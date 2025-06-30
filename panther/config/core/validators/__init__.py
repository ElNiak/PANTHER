"""
Universal validators for PANTHER configuration validation.

This package provides reusable validators that handle common type conversion
patterns with proper error logging and user-friendly error messages.
"""

# pylint: disable-next=undefined-variable  # Variables defined dynamically via __getattr__
__all__ = [
    "create_enum_validator",
    "create_time_string_validator",
    "create_case_insensitive_string_validator",
    "create_type_conversion_validator",
    "protocol_role_validator",
    "implementation_type_validator",
    "logging_level_validator",
    "shadow_time_validator",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    if name == "create_enum_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            create_enum_validator,
        )

        return create_enum_validator
    elif name == "create_time_string_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            create_time_string_validator,
        )

        return create_time_string_validator
    elif name == "create_case_insensitive_string_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            create_case_insensitive_string_validator,
        )

        return create_case_insensitive_string_validator
    elif name == "create_type_conversion_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            create_type_conversion_validator,
        )

        return create_type_conversion_validator
    elif name == "protocol_role_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            protocol_role_validator,
        )

        return protocol_role_validator
    elif name == "implementation_type_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            implementation_type_validator,
        )

        return implementation_type_validator
    elif name == "logging_level_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            logging_level_validator,
        )

        return logging_level_validator
    elif name == "shadow_time_validator":
        from .universal_validators import (  # pylint: disable=import-outside-toplevel
            shadow_time_validator,
        )

        return shadow_time_validator
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
