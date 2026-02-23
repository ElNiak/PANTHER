from typing import Any, Dict, List, Optional

"""
Command Audit Observer

This observer tracks all command generation and modification events for debugging
and auditing purposes. It maintains a complete history of how commands evolve
through the PANTHER workflow.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from panther.core.events.service.events import (
    CommandGeneratedEvent,
    CommandGenerationStartedEvent,
    CommandModifiedEvent,
    ConfigGeneratedEvent,
)
from panther.core.observer.base.typed_observer_interface import ITypedObserver


class CommandAuditObserver(ITypedObserver):
    """

    Observer that tracks all command generation and modification events.

    This observer maintains a complete audit trail of:
    - Command generation for each service and phase
    - Command modifications by execution environments
    - Final configuration generation

    The audit trail is useful for:
    - Debugging command issues
    - Understanding how execution environments modify commands
    - Reproducing exact command sequences
    """

    def __init__(self, output_dir: Path, observer_id: str = "command_audit"):
        """
        Initialize the command audit observer.

        Args:
            output_dir: Directory to store audit logs
            observer_id: Unique identifier for this observer
        """
        super().__init__()
        self.observer_id = observer_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = Path(output_dir)
        self.audit_file = self.output_dir / "command_audit.json"

        # Track command history
        self.command_history: Dict[str, List[Dict[str, Any]]] = {}
        self.generation_in_progress: Dict[str, Dict[str, Any]] = {}

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_supported_event_types(self) -> List[type]:
        """Return the list of event types this observer handles."""
        return [
            CommandGenerationStartedEvent,
            CommandGeneratedEvent,
            CommandModifiedEvent,
            ConfigGeneratedEvent,
        ]

    def handle_command_generation_started(
        self, event: CommandGenerationStartedEvent
    ) -> None:
        """Handle command generation started event."""
        service_id = f"{event.data.get('service_name', 'unknown')}_{event.data.get('phase', 'unknown')}"

        self.generation_in_progress[service_id] = {
            "service_name": event.data.get("service_name"),
            "phase": event.data.get("phase"),
            "started_at": datetime.now().isoformat(),
            "config": event.data.get("config", {}),
        }

        self.logger.info(
            "Command generation started for %s in phase %s",
            event.data.get("service_name"),
            event.data.get("phase"),
        )

    def handle_command_generated(self, event: CommandGeneratedEvent) -> None:
        """Handle command generated event."""
        service_id = f"{event.data.get('service_name', 'unknown')}_{event.data.get('phase', 'unknown')}"

        # Initialize history for this service if needed
        if service_id not in self.command_history:
            self.command_history[service_id] = []

        # Create command record
        command_record = {
            "timestamp": datetime.now().isoformat(),
            "service_name": event.data.get("service_name"),
            "phase": event.data.get("phase"),
            "command": event.data.get("command"),
            "command_type": event.data.get("command_type"),
            "generation_info": self.generation_in_progress.get(service_id, {}),
            "modifications": [],  # Will be populated by CommandModifiedEvent
        }

        self.command_history[service_id].append(command_record)

        # Clear generation in progress
        self.generation_in_progress.pop(service_id, None)

        self.logger.info(
            "Command generated for %s in phase %s: %s",
            event.data.get("service_name"),
            event.data.get("phase"),
            (
                event.data.get("command")[:100] + "..."
                if len(event.data.get("command", "")) > 100
                else event.data.get("command")
            ),
        )

        # Save audit trail
        self._save_audit_trail()

    def handle_command_modified(self, event: CommandModifiedEvent) -> None:
        """Handle command modified event."""
        service_id = f"{event.data.get('service_name', 'unknown')}_{event.data.get('phase', 'unknown')}"

        # Find the latest command record for this service
        if service_id in self.command_history and self.command_history[service_id]:
            latest_record = self.command_history[service_id][-1]

            # Add modification record
            modification = {
                "timestamp": datetime.now().isoformat(),
                "modifier": event.data.get("modifier"),
                "original_command": event.data.get("original_command"),
                "modified_command": event.data.get("modified_command"),
                "modification_details": event.data.get("modification_details", {}),
            }

            latest_record["modifications"].append(modification)

            self.logger.info(
                "Command modified for %s by %s: %s -> %s",
                event.data.get("service_name"),
                event.data.get("modifier"),
                (
                    event.data.get("original_command")[:50] + "..."
                    if len(event.data.get("original_command", "")) > 50
                    else event.data.get("original_command")
                ),
                (
                    event.data.get("modified_command")[:50] + "..."
                    if len(event.data.get("modified_command", "")) > 50
                    else event.data.get("modified_command")
                ),
            )

            # Save audit trail
            self._save_audit_trail()
        else:
            self.logger.warning(
                "Received command modification for unknown service: %s", service_id
            )

    def handle_config_generated(self, event: ConfigGeneratedEvent) -> None:
        """Handle configuration generated event."""
        config_record = {
            "timestamp": datetime.now().isoformat(),
            "config_type": event.data.get("config_type"),
            "config_path": event.data.get("config_path"),
            "services_included": event.data.get("services_included", []),
            "config_preview": (
                event.data.get("config_content", "")[:500]
                if event.data.get("config_content")
                else None
            ),
        }

        # Store config generation separately
        if "config_generation" not in self.command_history:
            self.command_history["config_generation"] = []

        self.command_history["config_generation"].append(config_record)

        self.logger.info(
            "Configuration generated: %s at %s for services: %s",
            event.data.get("config_type"),
            event.data.get("config_path"),
            ", ".join(event.data.get("services_included", [])),
        )

        # Save audit trail
        self._save_audit_trail()

    def _save_audit_trail(self) -> None:
        """Save the complete audit trail to disk."""
        try:
            audit_data = {
                "generated_at": datetime.now().isoformat(),
                "command_history": self.command_history,
                "statistics": self._calculate_statistics(),
            }

            with open(self.audit_file, "w") as f:
                json.dump(audit_data, f, indent=2)

            self.logger.debug("Audit trail saved to %s", self.audit_file)

        except Exception as e:
            self.logger.error("Failed to save audit trail: %s", e)

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics about command generation."""
        stats = {
            "total_services": len(
                [k for k in self.command_history.keys() if k != "config_generation"]
            ),
            "total_commands": sum(
                len(cmds)
                for k, cmds in self.command_history.items()
                if k != "config_generation"
            ),
            "total_modifications": 0,
            "modifications_by_type": {},
            "commands_by_phase": {},
        }

        for service_id, commands in self.command_history.items():
            if service_id == "config_generation":
                continue

            for cmd in commands:
                # Count modifications
                stats["total_modifications"] += len(cmd.get("modifications", []))

                # Track modifications by type
                for mod in cmd.get("modifications", []):
                    modifier = mod.get("modifier", "unknown")
                    stats["modifications_by_type"][modifier] = (
                        stats["modifications_by_type"].get(modifier, 0) + 1
                    )

                # Track commands by phase
                phase = cmd.get("phase", "unknown")
                stats["commands_by_phase"][phase] = (
                    stats["commands_by_phase"].get(phase, 0) + 1
                )

        return stats

    def get_command_history(
        self, service_name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get command history, optionally filtered by service name.

        Args:
            service_name: Optional service name to filter by

        Returns:
            Command history dictionary
        """
        if service_name:
            return {
                k: v
                for k, v in self.command_history.items()
                if k.startswith(f"{service_name}_")
            }
        return self.command_history

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get a summary of the audit trail."""
        return {
            "audit_file": str(self.audit_file),
            "statistics": self._calculate_statistics(),
            "last_updated": datetime.now().isoformat(),
        }
