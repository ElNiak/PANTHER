from typing import Any, Dict


class CommandModificationMixin:
    """
    Mixin for standardized command modification in execution environments.

    This mixin provides a consistent way to modify service commands
    with proper event emission and state tracking.
    """

    def modify_service_commands(
        self, service, modification_type: str, modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
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
