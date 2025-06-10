"""
Environment Event Types Module

This module defines event types related to environment setup and management
to integrate the environment system with the event infrastructure.
"""

from typing import Any

from panther.core.observer.core.core_events import Event


class EnvironmentEvent(Event):
    """
    Environment-related events like initialization, setup failure, etc.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new EnvironmentEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"environment.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for EnvironmentEvents has the 'environment.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name

    def validate(self) -> bool:
        """
        Validate environment event data.

        Returns:
            bool: True if the event data is valid
        """
        return True


class EnvironmentInitializedEvent(EnvironmentEvent):
    """
    Event triggered when environment is successfully initialized.
    """

    def __init__(
        self,
        environment_type: str = None,
        plugin_name: str = None,
        plugin_type: str = None,
        environment_name: str = None,
        **kwargs,
    ):
        """
        Initialize an environment initialized event.

        Args:
            environment_type: Type of environment (e.g., 'network', 'execution')
            plugin_name: Name of the plugin
            plugin_type: Type of the plugin
            environment_name: Name of the environment
            **kwargs: Additional event data
        """
        event_data = kwargs or {}

        # Handle backward compatibility with both parameter patterns
        if environment_name:
            event_data["environment_name"] = environment_name
        elif plugin_name:
            event_data["environment_name"] = plugin_name

        if environment_type:
            event_data["environment_type"] = environment_type

        # Additional plugin information
        if plugin_name:
            event_data["plugin_name"] = plugin_name
        if plugin_type:
            event_data["plugin_type"] = plugin_type

        super().__init__("initialized", event_data)

    def validate(self) -> bool:
        """Validate that environment_name and environment_type are present."""
        return (
            "environment_name" in self.data
            and bool(self.data["environment_name"])
            and "environment_type" in self.data
            and bool(self.data["environment_type"])
        )


class EnvironmentSetupFailedEvent(EnvironmentEvent):
    """
    Event triggered when environment setup fails.
    """

    def __init__(
        self, environment_name: str, environment_type: str, error: str, data: dict[str, Any] = None
    ):
        """
        Initialize an environment setup failed event.

        Args:
            environment_name: Name of the environment that failed
            environment_type: Type of environment (e.g., 'network', 'execution')
            error: Error message or description
            data: Additional event data
        """
        event_data = data or {}
        event_data["environment_name"] = environment_name
        event_data["environment_type"] = environment_type
        event_data["error"] = error
        super().__init__("setup_failed", event_data)

    def validate(self) -> bool:
        """Validate that environment_name, environment_type, and error are present."""
        return (
            "environment_name" in self.data
            and bool(self.data["environment_name"])
            and "environment_type" in self.data
            and bool(self.data["environment_type"])
            and "error" in self.data
            and bool(self.data["error"])
        )
