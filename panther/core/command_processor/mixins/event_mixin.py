"""
Command Event Mixin

This module provides a mixin class for emitting command generation and Docker build events
from service managers.
"""

from typing import TYPE_CHECKING, Optional


class CommandEventMixin:
    """
    Mixin class that provides methods for emitting command generation and Docker build events.

    This mixin should be used by service managers to emit events during command generation
    and Docker image building phases.
    """

    def emit_command_generation_started(self, phase: str) -> None:
        """
        Emit an event when command generation starts for a specific phase.

        Args:
            phase: The command generation phase (pre_compile, compile, post_compile, run, post_run)
        """
        if hasattr(self, "service_emitter") and self.service_emitter:
            service_name = getattr(self, "service_name", self.__class__.__name__)
            self.service_emitter.emit_command_generation_started(
                service_id=service_name,
                service_name=service_name,
                phase=phase,
                implementation=getattr(self, "implementation_name", "unknown"),
                protocol=(
                    getattr(self.protocol, "name", "unknown")
                    if hasattr(self, "protocol")
                    else "unknown"
                ),
            )
            self.logger.debug(
                f"Emitted command generation started event for phase: {phase}"
            )

    def emit_command_generated(self, phase: str, command: str) -> None:
        """
        Emit an event when a command has been generated.

        Args:
            phase: The command generation phase
            command: The generated command (or command description)
        """
        if hasattr(self, "service_emitter") and self.service_emitter:
            service_name = getattr(self, "service_name", self.__class__.__name__)

            # Truncate command if too long for logging
            command_preview = command[:200] + "..." if len(command) > 200 else command

            self.service_emitter.emit_command_generated(
                service_id=service_name,
                service_name=service_name,
                phase=phase,
                command=command_preview,
                implementation=getattr(self, "implementation_name", "unknown"),
                protocol=(
                    getattr(self.protocol, "name", "unknown")
                    if hasattr(self, "protocol")
                    else "unknown"
                ),
            )
            self.logger.debug(
                f"Emitted command generated event for phase {phase}: {command_preview}"
            )

    def emit_docker_build_started(
        self, dockerfile_path: str, image_name: str = None
    ) -> None:
        """
        Emit an event when Docker image build starts.

        Args:
            dockerfile_path: Path to the Dockerfile being built
            image_name: Name of the image being built (optional)
        """
        if hasattr(self, "service_emitter") and self.service_emitter:
            service_name = getattr(self, "service_name", self.__class__.__name__)
            # Use provided image_name or try to infer from implementation_name
            if image_name is None:
                image_name = getattr(self, "implementation_name", "unknown")

            self.service_emitter.emit_docker_build_started(
                service_id=service_name,
                service_name=service_name,
                dockerfile_path=dockerfile_path,
                implementation=getattr(self, "implementation_name", "unknown"),
                image_name=image_name,
            )
            self.logger.info(
                f"Emitted Docker build started event for: {dockerfile_path}"
            )

    def emit_docker_build_completed(
        self, image_name: str, success: bool, error_message: str = None
    ) -> None:
        """
        Emit an event when Docker image build completes.

        Args:
            image_name: Name of the Docker image that was built
            success: Whether the build was successful
            error_message: Optional error message if build failed
        """
        if hasattr(self, "service_emitter") and self.service_emitter:
            service_name = getattr(self, "service_name", self.__class__.__name__)

            if success:
                self.service_emitter.emit_docker_build_completed(
                    service_id=service_name,
                    service_name=service_name,
                    image_name=image_name,
                    success=True,
                    build_duration=0,  # Duration would need to be tracked separately
                )
                self.logger.info(
                    f"Emitted Docker build completed event for image: {image_name}"
                )
            else:
                # For failed builds, use emit_docker_build_failed which accepts error_message
                if hasattr(self.service_emitter, "emit_docker_build_failed"):
                    self.service_emitter.emit_docker_build_failed(
                        service_id=service_name,
                        service_name=service_name,
                        error_message=error_message or "Docker build failed",
                        dockerfile_path="",  # Would need to be passed in
                        build_duration=0,
                    )
                else:
                    # Fallback: just emit completed with success=False
                    self.service_emitter.emit_docker_build_completed(
                        service_id=service_name,
                        service_name=service_name,
                        image_name=image_name,
                        success=False,
                        build_duration=0,
                    )
                self.logger.error(
                    f"Emitted Docker build failed event for image: {image_name}"
                )

    def emit_command_execution_started(self, phase: str, command: str) -> None:
        """
        Emit an event when command execution starts.

        Args:
            phase: The execution phase
            command: The command being executed
        """
        if hasattr(self, "service_emitter") and self.service_emitter:
            service_name = getattr(self, "service_name", self.__class__.__name__)
            # Use a generic service event for command execution
            self.service_emitter.emit_service_event(
                event_type="command_execution_started",
                service_id=service_name,
                service_name=service_name,
                details={
                    "phase": phase,
                    "command": command[:200] + "..." if len(command) > 200 else command,
                },
            )

    def emit_command_execution_completed(
        self, phase: str, success: bool, duration: float = None
    ) -> None:
        """
        Emit an event when command execution completes.

        Args:
            phase: The execution phase
            success: Whether the execution was successful
            duration: Optional execution duration in seconds
        """
        if hasattr(self, "service_emitter") and self.service_emitter:
            service_name = getattr(self, "service_name", self.__class__.__name__)
            # Use a generic service event for command execution
            self.service_emitter.emit_service_event(
                event_type="command_execution_completed",
                service_id=service_name,
                service_name=service_name,
                details={"phase": phase, "success": success, "duration": duration},
            )
