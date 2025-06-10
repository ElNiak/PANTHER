"""
Methods for IEnvironmentPlugin to emit standardized events.
"""

from typing import Any


class EnvironmentPluginEventMixin:
    """
    Mixin providing standardized event emission methods for environment plugins.

    This class extends IEnvironmentPlugin with helper methods to emit standard events.
    """

    def notify_environment_setup_started(self, details: dict[str, Any] = None):
        """
        Notify that environment setup has started using the event emitter.

        Args:
            details: Additional details about the setup
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            environment_type = getattr(self, "env_sub_type", "unknown")
            self.event_emitter.emit_environment_setup_started(environment_type, details)
            env_type = "network" if self.is_network_environment else "execution"
            env_subtype = (
                self.__class__.__name__.lower() if hasattr(self, "__class__") else "unknown"
            )

            self.event_emitter.emit_environment_setup_started(
                environment_type=f"{env_type}_{env_subtype}".rstrip("_"), details=details or {}
            )

    def notify_environment_initialized(self, details: dict[str, Any] = None):
        """
        Notify that environment has been initialized using the event emitter.

        Args:
            details: Additional details about the initialization
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get environment type information
            env_type = "network" if self.is_network_environment() else "execution"
            env_subtype = getattr(self, "env_sub_type", "")
            plugin_name = self.__class__.__name__

            # Store details in environment object for reference if needed
            if hasattr(self, "initialization_details"):
                self.initialization_details.update(details or {})
            else:
                self.initialization_details = details or {}

            # Emit environment initialized event
            self.event_emitter.emit_environment_initialized(
                environment_type=env_type,
                plugin_name=plugin_name,
                plugin_type=env_subtype,
            )

    def notify_environment_setup_completed(self, success: bool, details: dict[str, Any] = None):
        """
        Notify that environment setup has completed using the event emitter.

        Args:
            success: Whether the setup was successful
            details: Additional details about the setup
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Use a single, consistent environment_type value
            env_type = getattr(self, "env_type", "unknown")
            env_subtype = getattr(self, "env_sub_type", "")
            environment_type = f"{env_type}_{env_subtype}".rstrip("_")

            # Ensure details is not None
            details_dict = details or {}

            # Add environment name to details if not present
            if "environment_name" not in details_dict:
                env_name = getattr(self, "env_name", self.__class__.__name__)
                details_dict["environment_name"] = env_name

            # Emit a single event with complete information
            self.event_emitter.emit_environment_setup_completed(
                environment_type=environment_type,
                success=success,
                details=details_dict,
            )

    def notify_environment_teardown(self, success: bool, details: dict[str, Any] = None):
        """
        Notify that environment teardown has completed using the event emitter.

        Args:
            success: Whether the teardown was successful
            details: Additional details about the teardown
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            environment_type = getattr(self, "env_sub_type", "unknown")
            self.event_emitter.emit_environment_teardown(environment_type, success, details)
            env_type = getattr(self, "env_type", "unknown")
            env_subtype = getattr(self, "env_sub_type", "")

            self.event_emitter.emit_environment_teardown(
                environment_type=f"{env_type}_{env_subtype}".rstrip("_"),
                success=success,
                details=details or {},
            )

    def notify_experiment_early_finish(self, reason: str, details: dict[str, Any] = None):
        """
        Notify that the experiment should finish early using the event emitter.

        Args:
            reason: Why the experiment should finish early
            details: Additional details about the early finish
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            experiment_id = getattr(self, "experiment_id", "unknown")
            self.event_emitter.emit_experiment_finished_early(experiment_id, reason, details)
        if hasattr(self, "event_emitter"):
            env_name = getattr(self, "env_name", "unknown")

            if hasattr(self, "env_config_to_test") and hasattr(self.env_config_to_test, "name"):
                env_name = self.env_config_to_test.name

            self.event_emitter.emit_experiment_finished_early(
                experiment_id=env_name, reason=reason, details=details or {}
            )
