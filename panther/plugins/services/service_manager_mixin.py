import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from panther.core.command_processor import CommandProcessor
from panther.core.command_processor.models import ShellCommand
from panther.core.command_processor.utils import CommandUtils
from panther.core.outputs.phase_collection_standard import PhaseCollectionStandard
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.services.service_manager_utils import ServiceManagerUtilities

RUN_CMD_SCHEMA = {
    "pre_compile_cmds": list,
    "compile_cmds": list,
    "post_compile_cmds": list,
    "pre_run_cmds": list,
    "run_cmd": {
        "working_dir": str,
        "command_binary": str,
        "command_args": (list, str),  # Allow both list and string
        "timeout": (int, float),
        "environment": dict,
    },
    "post_run_cmds": list,
}


def validate_structure(data, schema, path="root"):
    """
    Recursively validates a dictionary or list structure against a schema.

    Args:
        data: The data to validate.
        schema: The expected schema structure.
        path: The current path in the nested structure (for error messages).

    Raises:
        ValueError: If the structure does not match the schema.
        TypeError: If a value does not match the expected type.
    """
    if isinstance(schema, dict):
        if not isinstance(data, dict):
            raise TypeError(
                f"Expected a dictionary at '{path}', got {type(data).__name__}."
            )
        for key, value_schema in schema.items():
            if key in data:
                validate_structure(data[key], value_schema, path=f"{path}.{key}")
            else:
                raise ValueError(f"Missing key '{key}' in '{path}'.")
    elif isinstance(schema, list):
        if not isinstance(data, list):
            raise TypeError(f"Expected a list at '{path}', got {type(data).__name__}.")
        # Optionally, add item validation here if needed
    elif isinstance(schema, tuple):
        if not isinstance(data, schema):
            raise TypeError(
                f"Expected one of {schema} at '{path}', got {type(data).__name__}."
            )
    elif not isinstance(data, schema):
        raise TypeError(
            f"Expected {schema.__name__} at '{path}', got {type(data).__name__}."
        )


def validate_cmd(func):
    """
    Decorator to validate command structure against the RUN_CMD_SCHEMA.

    Args:
        func: The function to decorate

    Returns:
        The decorated function that validates its returned command structure
    """

    def wrapper(*args, **kwargs):
        command = func(*args, **kwargs)
        logging.debug(
            "Validating command structure against schema: %s",
            RUN_CMD_SCHEMA,
        )
        for key, value in command.items():
            logging.debug("Command key '%s': %s", key, value)
        # Validate the command structure
        validate_structure(command, RUN_CMD_SCHEMA)
        return command

    return wrapper


class ServiceManagerMixin(LoggerMixin):
    """
    Comprehensive mixin for service managers that provides common patterns
    and integrates with PANTHER's existing architecture.

    MRO: Base mixin. Used by: IUTServiceManagerMixin, TesterServiceManagerMixin
    """

    def __init__(self, *args, global_config=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Store global configuration
        self.global_config = global_config
        self._commands_initialized = False
        self._run_cmd = None

    def standardized_initialization(
        self,
        service_config_to_test: Any,
        service_type: str,
        protocol: Any,
        implementation_name: str,
        event_manager=None,
    ) -> None:
        """
        Perform standardized service manager initialization.

        This method sets up attributes and configuration but does NOT initialize commands.
        Commands should be initialized later in prepare() after Docker images are built.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service
            protocol: Protocol configuration
            implementation_name: Implementation name
            event_manager: Event manager instance
        """
        # Set up standard attributes
        ServiceManagerUtilities.setup_service_attributes(
            self, service_config_to_test, service_type, protocol, implementation_name
        )

        # Store event manager
        self.event_manager = event_manager

        # Standard logging
        ServiceManagerUtilities.standardize_initialization_logging(
            self.logger, implementation_name, service_config_to_test
        )

    @validate_cmd
    def initialize_commands(self) -> dict:
        """
        Initializes and generates a dictionary of commands to be executed at different stages
        of the process (pre-compile, compile, post-compile, pre-run, run, post-run).

        The dictionary keys are:
            - "pre_compile_cmds": Commands to be executed before compilation.
            - "compile_cmds": Commands to be executed during compilation.
            - "post_compile_cmds": Commands to be executed after compilation.
            - "pre_run_cmds": Commands to be executed before running.
            - "run_cmd": Command to be executed to run the main process.
            - "post_run_cmds": Commands to be executed after running.

        Returns:
            dict: A dictionary containing the commands for each stage.
        """

        # Use CommandProcessor for intelligent command processing
        processor = CommandProcessor()

        # Get commands from the respective methods and process them
        self.logger.debug(
            "Generating commands for service '%s' - pre-compile", self.service_name
        )
        pre_compile = self.generate_pre_compile_commands()
        self.logger.debug(
            "Generating commands for service '%s' - compile", self.service_name
        )
        for cmd in pre_compile:
            if isinstance(cmd, ShellCommand):
                cmd.metadata.is_critical = (
                    True  # Ensure pre-compile commands are critical
                )
        compile_cmds = self.generate_compile_commands()
        self.logger.debug(
            "Generating commands for service '%s' - post-compile", self.service_name
        )
        for cmd in compile_cmds:
            if isinstance(cmd, ShellCommand):
                cmd.metadata.is_critical = True
        post_compile = self.generate_post_compile_commands()
        self.logger.debug(
            "Generating commands for service '%s' - pre-run", self.service_name
        )
        pre_run = self.generate_pre_run_commands()
        self.logger.debug(
            "Generating commands for service '%s' - post-run", self.service_name
        )
        post_run = self.generate_post_run_commands()

        # Special handling for run_cmd which is a dict, not a list
        self.logger.debug("Generating run command for service '%s'", self.service_name)
        run_cmd = self.generate_run_command()

        # Build the complete command structure
        command_structure = {
            "pre_compile_cmds": pre_compile,
            "compile_cmds": compile_cmds,
            "post_compile_cmds": post_compile,
            "pre_run_cmds": pre_run,
            "run_cmd": run_cmd,
            "post_run_cmds": post_run,
        }

        # Process the entire structure through CommandProcessor for consistency
        try:
            self._run_cmd = processor.process_commands(
                command_structure, target_format="service"
            )
        except Exception as e:
            self.logger.warning(
                f"Failed to process complete command structure: {e}, using fallback"
            )
            self._run_cmd = command_structure

        self.logger.debug("Run commands: %s", self._run_cmd)

        # Note: Network substitutions are now handled by placeholder resolution
        # in the environment's _resolve_network_placeholders_in_commands method
        self._commands_initialized = True
        self.logger.debug("Commands initialized for service '%s'", self.service_name)
        return self._run_cmd

    @property
    def run_cmd(self) -> Dict[str, Any]:
        """Get the run command structure."""
        if self._run_cmd is None:
            self.initialize_commands()
        return self._run_cmd

    @run_cmd.setter
    def run_cmd(self, value: Dict[str, Any]) -> None:
        """Set the run command structure."""
        self._run_cmd = value

    def generate_pre_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate pre-compile commands. Override in subclasses."""
        self.emit_command_generation_started("pre_compile")

        # ShellCommand is imported at the top of the file, so we use it directly
        # for better shell command representation with metadata and proper escaping

        # Using ShellCommand objects for better structure, error handling, and debugging support
        commands: List[ShellCommand] = [
            ShellCommand(
                command="set -x;",
                is_critical=True,
            ),
            ShellCommand(
                command="export SHELLOPTS;",
                is_critical=True,
                is_environment_variable_assignment=True,
            ),
            ShellCommand(
                command="export PATH=$PATH:$ADDITIONAL_PATH;",
                is_environment_variable_assignment=True,  # Non-critical as ADDITIONAL_PATH might be empty (TODO - set defaults?)
            ),
            ShellCommand(
                command="export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;",
                is_environment_variable_assignment=True,  # Non-critical as ADDITIONAL_PYTHONPATH might be empty (TODO - set defaults?)
            ),
            ShellCommand(
                command="env >> /app/logs/env.log;",
                is_critical=False,
            ),
        ]
        # Emit command generated event
        for cmd in commands:
            self.logger.debug("Generated pre-compile command: %s", cmd)
        self.emit_command_generated(
            "pre_compile", f"{len(commands)} pre-compile commands"
        )
        return commands

    def generate_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate compile commands. Override in subclasses."""
        return []

    def generate_post_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate post-compile commands. Override in subclasses."""
        return []

    def generate_pre_run_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate pre-run commands. Override in subclasses."""
        return []

    def generate_post_run_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate post-run commands. Override in subclasses."""
        return []

    def generate_run_command(self) -> Dict[str, Any]:
        """Generate the main run command. Must be implemented by subclasses."""
        return {
            "working_dir": "/app",
            "command_binary": "echo",
            "command_args": "No run command implemented",
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

    def create_standard_shell_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ShellCommand:
        """
        Create a ShellCommand with service-specific defaults.

        Args:
            command: Command string
            working_dir: Working directory (defaults to service working_dir)
            environment: Environment variables
            timeout: Command timeout

        Returns:
            ShellCommand: Configured command object
        """
        if working_dir is None:
            working_dir = getattr(self, "working_dir", "/app")

        return CommandUtils.create_shell_command(
            command=command,
            working_dir=working_dir,
            environment=environment,
            timeout=timeout,
        )

    def add_environment_variable(self, key: str, value: str) -> None:
        """
        Add an environment variable to the run command.

        Args:
            key: Environment variable name
            value: Environment variable value
        """
        self.logger.debug(
            "Adding environment variable '%s' with value '%s' to run command",
            key,
            value,
        )
        # Ensure commands are initialized
        if not self._commands_initialized:
            self.initialize_commands()

        # Ensure the run_cmd structure exists
        if "run_cmd" not in self.run_cmd:
            self.run_cmd["run_cmd"] = self.generate_run_command()

        if "environment" not in self.run_cmd["run_cmd"]:
            self.run_cmd["run_cmd"]["environment"] = {}

        self.run_cmd["run_cmd"]["environment"][key] = value

    def finalize_commands(self) -> Dict[str, Any]:
        """
        Finalize and structure all commands for the service.
        Preserves any modifications made by execution environments.

        Returns:
            dict: Complete command structure
        """
        service_name = getattr(self, "service_name", "unknown")
        self.logger.info(
            f"ServiceManagerMixin.finalize_commands called for {service_name}"
        )

        # Only initialize commands if not already done
        if not self._commands_initialized:
            self.initialize_commands()
        else:
            self.logger.debug(
                f"Commands already initialized for {service_name}, skipping duplicate initialization"
            )

        # Commands already generated in initialize_commands(), retrieve them from run_cmd
        pre_compile = self.run_cmd.get("pre_compile_cmds", [])
        compile_cmds = self.run_cmd.get("compile_cmds", [])
        post_compile = self.run_cmd.get("post_compile_cmds", [])
        pre_run = self.run_cmd.get("pre_run_cmds", [])
        post_run = self.run_cmd.get("post_run_cmds", [])
        run_cmd = self.run_cmd.get("run_cmd", {})

        # Get existing execution environment modifications
        existing_pre_compile = self.run_cmd.get("pre_compile_cmds", [])
        existing_compile = self.run_cmd.get("compile_cmds", [])
        existing_post_compile = self.run_cmd.get("post_compile_cmds", [])
        existing_pre_run = self.run_cmd.get("pre_run_cmds", [])
        existing_post_run = self.run_cmd.get("post_run_cmds", [])
        existing_run_cmd = self.run_cmd.get("run_cmd", {})

        # Helper function to merge commands without duplicates
        def merge_commands_unique(existing, new):
            """Merge command lists, avoiding duplicates based on command content."""
            if not existing:
                return new
            if not new:
                return existing

            # Convert to comparable format for deduplication
            existing_commands = set()
            for cmd in existing:
                cmd_str = (
                    cmd
                    if isinstance(cmd, str)
                    else (
                        str(cmd.get("command", cmd))
                        if hasattr(cmd, "get")
                        else str(cmd)
                    )
                )
                existing_commands.add(cmd_str)

            # Add only new commands that don't already exist
            unique_new = []
            for cmd in new:
                cmd_str = (
                    cmd
                    if isinstance(cmd, str)
                    else (
                        str(cmd.get("command", cmd))
                        if hasattr(cmd, "get")
                        else str(cmd)
                    )
                )
                if cmd_str not in existing_commands:
                    unique_new.append(cmd)

            return existing + unique_new

        # Merge execution environment modifications with generated commands, avoiding duplicates
        # Execution environment commands come first, then unique service-specific commands
        self.run_cmd.update(
            {
                "pre_compile_cmds": merge_commands_unique(
                    existing_pre_compile, pre_compile
                ),
                "compile_cmds": merge_commands_unique(existing_compile, compile_cmds),
                "post_compile_cmds": merge_commands_unique(
                    existing_post_compile, post_compile
                ),
                "pre_run_cmds": merge_commands_unique(existing_pre_run, pre_run),
                "post_run_cmds": merge_commands_unique(existing_post_run, post_run),
                "run_cmd": run_cmd,
            }
        )

        for phase, cmds in self.run_cmd.items():
            if isinstance(cmds, list):
                self.logger.debug("Phase '%s' has %d commands", phase, len(cmds))
                for cmd in cmds:
                    self.logger.debug(" - Command: %s", cmd)
            else:
                self.logger.debug("Phase '%s' has command: %s", phase, cmds)

        return self.run_cmd

    def get_service_name(self) -> str:
        """Get the service name."""
        return getattr(self, "service_name", self.__class__.__name__)

    def is_tester(self) -> bool:
        """Check if this is a tester service."""
        service_type = getattr(self, "service_type", "").upper()
        return service_type == "TESTERS"

    # ================================
    # Phase Collection Standardization
    # ================================

    def get_default_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get comprehensive default patterns combining all standard patterns.
        Services should call this and extend as needed.
        """
        protocol = self._detect_protocol()
        service_type = self._detect_service_type()
        service_name = self.get_service_name()
        language = self._detect_language()

        patterns = PhaseCollectionStandard.get_patterns_for_service(
            protocol, service_type, service_name, language
        )

        return patterns

    def _get_custom_patterns(self) -> List[Tuple[str, str]]:
        """Override in subclasses to add service-specific patterns."""
        return []

    def _detect_protocol(self) -> str:
        """Detect protocol from service configuration."""
        if hasattr(self, "service_config_to_test") and hasattr(
            self.service_config_to_test, "protocol"
        ):
            return getattr(self.service_config_to_test.protocol, "name", "unknown")

        # Fallback: detect from class path
        module_path = self.__class__.__module__
        return PhaseCollectionStandard.detect_protocol_from_path(module_path)

    def _detect_service_type(self) -> str:
        """Detect if this is a tester or IUT service."""
        module_path = self.__class__.__module__
        return PhaseCollectionStandard.detect_service_type_from_path(module_path)

    def _detect_language(self) -> str:
        """Detect programming language from service module path."""
        module_path = self.__class__.__module__
        return PhaseCollectionStandard.detect_language_from_path(module_path)

    def validate_output_patterns(
        self, patterns: List[Tuple[str, str]] = None
    ) -> Tuple[bool, List[str]]:
        """Validate output patterns follow expected format."""
        if patterns is None:
            # Get patterns from the service's get_output_patterns method if it exists
            if hasattr(self, "get_output_patterns"):
                patterns = self.get_output_patterns()
            else:
                patterns = self.get_default_output_patterns()

        return PhaseCollectionStandard.validate_patterns(patterns)
