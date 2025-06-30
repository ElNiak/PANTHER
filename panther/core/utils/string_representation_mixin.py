"""
StringRepresentationMixin - Provides concise string representations for PANTHER classes.

This mixin standardizes string output across services and environments to reduce verbose
configuration printing while maintaining useful identifying information.
"""

from typing import Any, Dict, Optional


class StringRepresentationMixin:
    """
    Mixin providing concise string representations for services and environments.

    This mixin replaces verbose full-config printing with key identifying attributes,
    significantly reducing log noise and improving readability.

    Classes using this mixin should override _get_key_attributes() to specify
    which attributes to include in the string representation.
    """

    def _get_key_attributes(self) -> Dict[str, Any]:
        """
        Get key attributes for string representation.

        Override this method in subclasses to specify which attributes
        should be included in the string representation.

        Returns:
            Dict of attribute name to value for string representation
        """
        attrs = {}

        # Common attributes across many PANTHER classes
        if hasattr(self, "protocol"):
            protocol = getattr(self, "protocol", None)
            if protocol:
                attrs["protocol"] = getattr(protocol, "name", "unknown")
            else:
                attrs["protocol"] = "none"

        # Service-specific attributes
        if hasattr(self, "implementation_name"):
            attrs["impl"] = self.implementation_name
        elif hasattr(self, "name"):
            attrs["name"] = self.name

        if hasattr(self, "service_type"):
            attrs["type"] = self.service_type

        # Environment-specific attributes
        if hasattr(self, "env_type"):
            attrs["type"] = self.env_type

        if hasattr(self, "env_sub_type"):
            attrs["subtype"] = self.env_sub_type

        return attrs

    def __str__(self) -> str:
        """
        Concise string representation showing only key identifying information.

        Returns:
            String in format: ClassName(key1=value1, key2=value2, ...)
        """
        attrs = self._get_key_attributes()
        if attrs:
            attrs_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
            return f"{self.__class__.__name__}({attrs_str})"
        else:
            return f"{self.__class__.__name__}()"

    def __repr__(self) -> str:
        """
        Representation for debugging, same as __str__ for consistency.

        For more detailed output, use get_verbose_string() method.

        Returns:
            Same as __str__()
        """
        return self.__str__()

    def get_verbose_string(self) -> str:
        """
        Get verbose string representation with full configuration details.

        Use this method when you need complete configuration information
        for debugging purposes.

        Returns:
            Verbose string with all significant attributes
        """
        # Collect all potentially interesting attributes
        verbose_attrs = {}

        # Add all attributes from _get_key_attributes first
        verbose_attrs.update(self._get_key_attributes())

        # Add additional verbose attributes
        verbose_attributes = [
            "service_config_to_test",
            "env_config_to_test",
            "test_config",
            "output_dir",
            "event_manager",
            "services_managers",
            "command_builder",
            "docker_manager",
            "version",
            "parameters",
            "environment",
        ]

        for attr_name in verbose_attributes:
            if hasattr(self, attr_name):
                value = getattr(self, attr_name)
                if value is not None:
                    # For complex objects, try to get a string representation
                    if hasattr(value, "__dict__"):
                        verbose_attrs[attr_name] = f"<{type(value).__name__}>"
                    elif isinstance(value, list):
                        verbose_attrs[attr_name] = f"<list[{len(value)}]>"
                    elif isinstance(value, dict):
                        verbose_attrs[attr_name] = f"<dict[{len(value)}]>"
                    else:
                        verbose_attrs[attr_name] = str(value)

        attrs_str = ",\n    ".join(f"{k}={v}" for k, v in verbose_attrs.items())
        return f"{self.__class__.__name__}(\n    {attrs_str}\n)"
