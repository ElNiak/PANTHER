"""
Execution Environment Mixins

This module provides standardized mixins for execution environment plugins
to ensure consistent behavior across all environments.
"""

import os
import time
from abc import ABC
from typing import Any

from panther.core.outputs.output_collector import IOutputCollector


class StandardOutputCollectorMixin(IOutputCollector, ABC):
    """
    Standardized output collection for execution environments.

    This mixin provides a consistent way to register, collect, and manage
    outputs from execution environments. It handles container path mapping
    and provides metadata about collected outputs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_files = {}

    def register_output_file(
        self, output_type: str, file_path: str, service_name: str = None
    ) -> None:
        """
        Register an output file for collection.

        Args:
            output_type: Type of output (e.g., 'trace', 'profile', 'memcheck')
            file_path: Path to the output file
            service_name: Optional service name for multi-service environments
        """
        key = f"{output_type}_{service_name}" if service_name else output_type
        self.output_files[key] = {
            "path": file_path,
            "type": output_type,
            "service": service_name,
            "registered_at": time.time(),
        }

        if hasattr(self, "logger"):
            self.logger.debug(f"Registered output file: {key} -> {file_path}")

    def collect_outputs(self) -> dict[str, str]:
        """
        Collect all registered outputs.

        Returns:
            Dictionary mapping output type to file path
        """
        outputs = {}

        self.logger.debug(
            "Output directory: %s", getattr(self, "output_dir", "not set")
        )
        self.logger.debug("Registered output files: %s", self.output_files)

        for key, info in self.output_files.items():
            file_path = info["path"]
            service_name = info["service"]

            # Handle container path mapping
            if file_path.startswith("/app/logs/"):
                # Map container path to host path using proper service-specific directory
                if hasattr(self, "output_dir") and service_name:
                    # Container /app/logs/ maps to {output_dir}/logs/{service_name}/
                    host_path = file_path.replace(
                        "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                    )
                elif hasattr(self, "output_dir"):
                    # Fallback to general logs directory if no service name
                    host_path = file_path.replace(
                        "/app/logs/", f"{self.output_dir}/logs/"
                    )
                else:
                    # Fallback if output_dir not set
                    host_path = file_path
            else:
                host_path = file_path

            if os.path.exists(host_path):
                outputs[key] = host_path
                if hasattr(self, "logger"):
                    self.logger.debug(f"Collected {info['type']} output: {host_path}")
            else:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        f"Output file not found: {host_path} (mapped from container path: {file_path})"
                    )

        return outputs

    def get_output_metadata(self) -> dict[str, Any]:
        """
        Get metadata about collected outputs.

        Returns:
            Dictionary with metadata for each output file
        """
        metadata = {}

        for key, info in self.output_files.items():
            file_path = info["path"]
            service_name = info["service"]

            # Handle container path mapping
            if file_path.startswith("/app/logs/"):
                # Map container path to host path using proper service-specific directory
                if hasattr(self, "output_dir") and service_name:
                    # Container /app/logs/ maps to {output_dir}/logs/{service_name}/
                    host_path = file_path.replace(
                        "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                    )
                elif hasattr(self, "output_dir"):
                    # Fallback to general logs directory if no service name
                    host_path = file_path.replace(
                        "/app/logs/", f"{self.output_dir}/logs/"
                    )
                else:
                    # Fallback if output_dir not set
                    host_path = file_path
            else:
                host_path = file_path

            if os.path.exists(host_path):
                stat_info = os.stat(host_path)
                metadata[key] = {
                    "size_bytes": stat_info.st_size,
                    "format": self._get_output_format(info["type"]),
                    "timestamp": time.ctime(stat_info.st_mtime),
                    "path": host_path,
                    "environment": getattr(self, "env_sub_type", "unknown"),
                    "type": info["type"],
                    "service": info["service"],
                }
            else:
                metadata[key] = {
                    "error": "File not found",
                    "path": host_path,
                    "type": info["type"],
                    "service": info["service"],
                }

        return metadata

    def _get_output_format(self, output_type: str) -> str:
        """
        Get the format for a given output type.

        Args:
            output_type: Type of output

        Returns:
            Format string for the output type
        """
        format_map = {
            "trace": "strace",
            "cpu_profile": "gperf_cpu_profile",
            "heap_profile": "gperf_heap_profile",
            "memcheck": "valgrind_xml",
            "helgrind": "valgrind_xml",
            "log": "text",
            "profile": "binary",
            "perf": "perf_data",
        }
        return format_map.get(output_type, "unknown")


class CommandModificationMixin:
    """
    Mixin for standardized command modification in execution environments.

    This mixin provides a consistent way to modify service commands
    with proper event emission and state tracking.
    """

    def modify_service_commands(
        self, service, modification_type: str, modifications: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Modify service commands with proper event emission.

        Args:
            service: Service manager instance
            modification_type: Type of modification (e.g., 'command_wrapping')
            modifications: Dictionary of modifications to apply

        Returns:
            Dictionary of applied modifications
        """
        service_name = getattr(service, "service_name", service.__class__.__name__)
        self.logger.info(
            f"Modifying service {service_name} command with {modification_type} modifications: {modifications}"
        )

        # Debug: Check the service object structure
        self.logger.debug(f"Service object attributes: {dir(service)}")
        self.logger.debug(f"Service has run_cmd: {hasattr(service, 'run_cmd')}")
        if hasattr(service, "run_cmd"):
            self.logger.debug(f"Service run_cmd before modification: {service.run_cmd}")
            self.logger.debug(f"Service run_cmd type: {type(service.run_cmd)}")
            if isinstance(service.run_cmd, dict):
                self.logger.debug(f"Keys in run_cmd: {list(service.run_cmd.keys())}")
                self.logger.debug(
                    f"pre_run_cmds current value: {service.run_cmd.get('pre_run_cmds', 'KEY_NOT_FOUND')}"
                )
                self.logger.debug(
                    f"pre_run_cmds type: {type(service.run_cmd.get('pre_run_cmds'))}"
                )
        # Emit start event
        if hasattr(self, "environment_emitter") and self.environment_emitter:
            self.environment_emitter.emit_environment_modification_started(
                environment_id=f"{self.env_sub_type}_{service_name}",
                environment_name=self.env_sub_type,
                environment_type="execution",
                target_service=service_name,
                modification_type=modification_type,
            )

        # Store original state
        original_state = {}

        # Apply modifications
        applied_modifications = {}

        for key, value in modifications.items():
            if key == "pre_run_cmds":
                # Store original state
                original_state["pre_run_cmds"] = service.run_cmd.get(
                    "pre_run_cmds", []
                ).copy()
                self.logger.debug(
                    f"Original pre_run_cmds: {original_state['pre_run_cmds']}"
                )
                self.logger.debug(f"Adding commands: {value}")
                # Apply modification
                current_cmds = service.run_cmd.get("pre_run_cmds", [])
                self.logger.debug(f"Current commands before append: {current_cmds}")
                service.run_cmd["pre_run_cmds"] = current_cmds + value
                self.logger.debug(
                    f"Commands after append: {service.run_cmd['pre_run_cmds']}"
                )
                applied_modifications["pre_run_cmds"] = service.run_cmd["pre_run_cmds"]

            elif key == "post_run_cmds":
                # Store original state
                original_state["post_run_cmds"] = service.run_cmd.get(
                    "post_run_cmds", []
                ).copy()
                # Apply modification
                service.run_cmd["post_run_cmds"] = (
                    service.run_cmd.get("post_run_cmds", []) + value
                )
                applied_modifications["post_run_cmds"] = service.run_cmd[
                    "post_run_cmds"
                ]

            elif key == "environment":
                # Ensure nested structure exists
                if "run_cmd" not in service.run_cmd:
                    service.run_cmd["run_cmd"] = {}
                if "command_env" not in service.run_cmd["run_cmd"]:
                    service.run_cmd["run_cmd"]["command_env"] = {}

                # Store original state
                original_state["environment"] = service.run_cmd["run_cmd"][
                    "command_env"
                ].copy()
                # Apply modification
                service.run_cmd["run_cmd"]["command_env"].update(value)
                applied_modifications["environment"] = service.run_cmd["run_cmd"][
                    "command_env"
                ]

        # Log the modifications
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Applied {modification_type} modifications to {service_name}"
            )
            for key, value in applied_modifications.items():
                self.logger.debug(f"  {key}: {value}")

        # Emit completion event
        if hasattr(self, "environment_emitter") and self.environment_emitter:
            self.environment_emitter.emit_environment_modification_completed(
                environment_id=f"{self.env_sub_type}_{service_name}",
                environment_name=self.env_sub_type,
                environment_type="execution",
                modifications={
                    k: {
                        "original": original_state.get(k, {}),
                        "modified": applied_modifications.get(k, {}),
                    }
                    for k in modifications.keys()
                },
                modification_summary=f"Applied {modification_type} modifications",
            )

        return applied_modifications

    def wrap_command_with_tool(
        self, service, tool_command: str, output_file: str = None
    ) -> str:
        """
        Helper method to wrap a service command with a tool command.

        Args:
            service: Service manager instance
            tool_command: Tool command to wrap with
            output_file: Optional output file path

        Returns:
            Complete wrapped command
        """
        # Build the command
        if output_file:
            full_command = f"{tool_command} -o {output_file}"
        else:
            full_command = tool_command

        # Apply the modification
        self.modify_service_commands(
            service, "command_wrapping", {"pre_run_cmds": [full_command]}
        )

        return full_command
