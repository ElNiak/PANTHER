from typing import Any, Dict, List, Optional, Union

from panther.core.command_processor.command import ShellCommand
from panther.core.command_processor.command_utils import CommandUtils
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.services.service_manager_utils import ServiceManagerUtilities


class ServiceManagerMixin(LoggerMixin):
    """
    Comprehensive mixin for service managers that provides common patterns
    and integrates with PANTHER's existing architecture.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

        # DO NOT initialize commands here - they should be initialized in prepare()
        # after Docker images are built and environment is ready

    def initialize_commands(self) -> None:
        """Initialize the command structure with defaults."""
        if not self._commands_initialized:
            # Create the nested structure expected by Docker Compose templates
            basic_commands = CommandUtils.generate_basic_service_commands()
            self._run_cmd = {
                "pre_compile_cmds": basic_commands.get("pre_compile_cmds", []),
                "compile_cmds": basic_commands.get("compile_cmds", []),
                "post_compile_cmds": basic_commands.get("post_compile_cmds", []),
                "pre_run_cmds": basic_commands.get("pre_run_cmds", []),
                "run_cmd": basic_commands.get(
                    "run_cmd",
                    {
                        "working_dir": "/app",
                        "command_binary": "echo",
                        "command_args": "No run command implemented",
                        "timeout": 60,
                        "environment": {},
                    },
                ),
                "post_run_cmds": basic_commands.get("post_run_cmds", []),
            }
            self._commands_initialized = True

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
        return []

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
            "timeout": 60,
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
        self.initialize_commands()

        # Log what we have before generating new commands
        if hasattr(self, "logger"):
            self.logger.debug(
                "finalize_commands called for %s",
                getattr(self, "service_name", "unknown"),
            )
            self.logger.debug(
                "Existing pre_run_cmds before generation: %s",
                self.run_cmd.get("pre_run_cmds", []),
            )

        # Generate all command phases
        pre_compile = self.generate_pre_compile_commands()
        compile_cmds = self.generate_compile_commands()
        post_compile = self.generate_post_compile_commands()
        pre_run = self.generate_pre_run_commands()
        post_run = self.generate_post_run_commands()
        run_cmd = self.generate_run_command()

        # Preserve existing execution environment modifications by merging instead of overwriting
        existing_pre_compile = self.run_cmd.get("pre_compile_cmds", [])
        existing_compile = self.run_cmd.get("compile_cmds", [])
        existing_post_compile = self.run_cmd.get("post_compile_cmds", [])
        existing_pre_run = self.run_cmd.get("pre_run_cmds", [])
        existing_post_run = self.run_cmd.get("post_run_cmds", [])

        # Merge execution environment modifications with generated commands
        # Execution environment commands come first, then service-specific commands
        self.run_cmd.update(
            {
                "pre_compile_cmds": existing_pre_compile + pre_compile,
                "compile_cmds": existing_compile + compile_cmds,
                "post_compile_cmds": existing_post_compile + post_compile,
                "pre_run_cmds": existing_pre_run + pre_run,
                "post_run_cmds": existing_post_run + post_run,
                "run_cmd": run_cmd,
            }
        )

        # Log the final state
        if hasattr(self, "logger"):
            self.logger.debug(
                "Final pre_run_cmds after merge: %s",
                self.run_cmd.get("pre_run_cmds", []),
            )

        return self.run_cmd

    def get_service_name(self) -> str:
        """Get the service name."""
        return getattr(self, "service_name", self.__class__.__name__)

    def is_tester(self) -> bool:
        """Check if this is a tester service."""
        service_type = getattr(self, "service_type", "").upper()
        return service_type == "TESTERS"
