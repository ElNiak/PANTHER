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
            # Generate environment ID and name
            env_type = getattr(self, "env_type", "unknown")
            env_subtype = getattr(self, "env_sub_type", "")
            environment_type = f"{env_type}_{env_subtype}".rstrip("_")
            environment_name = getattr(self, "env_name", self.__class__.__name__)
            environment_id = f"{environment_type}_{environment_name}"

            self.event_emitter.emit_environment_setup_started(
                environment_id=environment_id,
                environment_name=environment_name,
                environment_type=environment_type,
                setup_config=details,
            )

    def notify_environment_initialized(self, details: dict[str, Any] = None):
        """
        Notify that environment has been initialized using the event emitter.

        Args:
            details: Additional details about the initialization
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Generate environment ID and name
            env_type = "network" if self.is_network_environment() else "execution"
            env_subtype = getattr(self, "env_sub_type", "")
            environment_type = f"{env_type}_{env_subtype}".rstrip("_")
            environment_name = getattr(self, "env_name", self.__class__.__name__)
            environment_id = f"{environment_type}_{environment_name}"

            # Store details in environment object for reference if needed
            if hasattr(self, "initialization_details"):
                self.initialization_details.update(details or {})
            else:
                self.initialization_details = details or {}

            # Emit environment initialization completed event
            self.event_emitter.emit_environment_initialization_completed(
                environment_id=environment_id,
                environment_name=environment_name,
                environment_type=environment_type,
                duration_seconds=0.0,  # Duration not tracked in this method
                initialization_details=details,
            )

    def notify_environment_setup_completed(self, success: bool, details: dict[str, Any] = None):
        """
        Notify that environment setup has completed using the event emitter.

        Args:
            success: Whether the setup was successful
            details: Additional details about the setup
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Generate environment ID and name
            env_type = getattr(self, "env_type", "unknown")
            env_subtype = getattr(self, "env_sub_type", "")
            environment_type = f"{env_type}_{env_subtype}".rstrip("_")
            environment_name = getattr(self, "env_name", self.__class__.__name__)
            environment_id = f"{environment_type}_{environment_name}"

            # Emit the appropriate event based on success
            if success:
                self.event_emitter.emit_environment_setup_completed(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    environment_type=environment_type,
                    duration_seconds=details.get("duration") if details else None,
                    setup_details=details,
                )
            else:
                error_message = (
                    details.get("error", "Environment setup failed")
                    if details
                    else "Environment setup failed"
                )
                self.event_emitter.emit_environment_setup_failed(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    environment_type=environment_type,
                    error_message=error_message,
                )

    def notify_environment_teardown(self, success: bool, details: dict[str, Any] = None):
        """
        Notify that environment teardown has completed using the event emitter.

        Args:
            success: Whether the teardown was successful
            details: Additional details about the teardown
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Generate environment ID and name
            env_type = getattr(self, "env_type", "unknown")
            env_subtype = getattr(self, "env_sub_type", "")
            environment_type = f"{env_type}_{env_subtype}".rstrip("_")
            environment_name = getattr(self, "env_name", self.__class__.__name__)
            environment_id = f"{environment_type}_{environment_name}"

            # Emit the appropriate event based on success
            if success:
                self.event_emitter.emit_environment_teardown_completed(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    environment_type=environment_type,
                    duration_seconds=details.get("duration") if details else None,
                    cleanup_details=details,
                )
            else:
                error_message = (
                    details.get("error", "Environment teardown failed")
                    if details
                    else "Environment teardown failed"
                )
                self.event_emitter.emit_environment_teardown_failed(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    environment_type=environment_type,
                    error_message=error_message,
                )

    def notify_experiment_early_finish(self, reason: str, details: dict[str, Any] = None):
        """
        Notify that the experiment should finish early using the event emitter.

        Args:
            reason: Why the experiment should finish early
            details: Additional details about the early finish
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Generate environment ID and name for error tracking
            env_type = getattr(self, "env_type", "unknown")
            env_subtype = getattr(self, "env_sub_type", "")
            environment_type = f"{env_type}_{env_subtype}".rstrip("_")
            environment_name = getattr(self, "env_name", self.__class__.__name__)
            environment_id = f"{environment_type}_{environment_name}"

            # Since EnvironmentEventEmitter doesn't have emit_experiment_finished_early,
            # we emit an environment error event instead
            self.event_emitter.emit_environment_error(
                environment_id=environment_id,
                environment_name=environment_name,
                environment_type=environment_type,
                error_message=f"Experiment finished early: {reason}",
                error_type="early_termination",
                error_details=details,
            )
