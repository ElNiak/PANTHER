from abc import abstractmethod
import logging
import os
import shlex
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Any, TYPE_CHECKING
from panther.core.observer.management.event_manager import EventManager
from panther.core.events import ServiceEventEmitter
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.core.command_processor.command import ShellCommand
from panther.core.command_processor.command_processor import CommandProcessor

# PluginManager functionality now integrated into PluginManager
from panther.plugins.plugin_interface import IPlugin
from panther.plugins.services.service_event_methods import ServiceManagerEventMixin
from panther.core.utils import CommandEventMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


def quote_shell(s: str) -> str:
    """
    Safely quote a string for shell commands using shlex.quote

    Args:
        s: The string to quote

    Returns:
        The quoted string safe for shell execution
    """
    return shlex.quote(str(s))


def quote_yaml(s: str) -> str:
    """
    Safely quote a string for YAML using yaml.safe_dump

    Args:
        s: The string to quote

    Returns:
        The quoted string safe for YAML inclusion
    """
    return yaml.safe_dump(str(s)).strip()


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
            "Validating command structure: %s against schema: %s", command, RUN_CMD_SCHEMA
        )
        # Validate the command structure
        validate_structure(command, RUN_CMD_SCHEMA)
        return command

    return wrapper


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
            raise TypeError(f"Expected a dictionary at '{path}', got {type(data).__name__}.")
        for key, value_schema in schema.items():
            if key not in data:
                raise ValueError(f"Missing key '{key}' in '{path}'.")
            validate_structure(data[key], value_schema, path=f"{path}.{key}")
    elif isinstance(schema, list):
        if not isinstance(data, list):
            raise TypeError(f"Expected a list at '{path}', got {type(data).__name__}.")
        # Optionally, add item validation here if needed
    elif isinstance(schema, tuple):
        if not isinstance(data, schema):
            raise TypeError(f"Expected one of {schema} at '{path}', got {type(data).__name__}.")
    else:
        if not isinstance(data, schema):
            raise TypeError(f"Expected {schema.__name__} at '{path}', got {type(data).__name__}.")


class IServiceManager(IPlugin, ServiceManagerEventMixin, CommandEventMixin):
    """
    IServiceManager is an interface for managing services within the PANTHER-SCP framework. It extends the IPlugin class and provides methods for initializing and rendering commands, as well as generating various types of commands required for service deployment and execution.

    Attributes:
        available_types (list): List of valid service types.
        service_type (str): Type of the service (e.g., "testers", "iut").
        templates_dir (str): Directory path for service templates.
        config_versions_dir (str): Directory path for service configuration versions.
        plugin_manager (Optional[PluginManager]): Manager for the plugin.
        service_config_to_test ('ServiceConfig'): Configuration for the service to be tested.
        jinja_env (Environment): Jinja2 environment for template rendering.
        implementation_name (str): Name of the service implementation.
        service_name (str): Name of the service.
        service_protocol (ProtocolConfig): Protocol configuration for the service.
        service_targets (str): Targets for the service.
        service_version (str): Version of the service.
        working_dir (Optional[str]): Working directory for the service.
        process (Optional[subprocess.Popen]): Process for the service.
        available_roles (list): List of available roles for the service.
        volumes (list): List of volumes for the service.
        role (str): Role of the service.
        environments (dict): Environment variables for the service.
        run_cmd (dict): Dictionary containing commands for various stages of service execution.

    Methods:
        render_commands(params, template_name): Renders a command using a Jinja2 template with the provided parameters.
        get_service_name() -> str: Returns the name of the service.
        initialize_commands(): Initializes the commands to be executed.
        generate_pre_compile_commands(): Generates pre-compile commands.
        generate_compile_commands(): Generates compile commands.
        generate_post_compile_commands(): Generates post-compile commands.
        generate_pre_run_commands(): Generates pre-run commands.
        generate_run_command(): Generates the run command.
        generate_post_run_commands(): Generates post-run commands.
        get_implementation_name() -> str: Returns the name of the service implementation.
        is_tester() -> bool: Returns True if the service type is "testers".
        prepare(plugin_manager: Optional[Any] = None): Abstract method to build the Docker image for the implementation.
        generate_deployment_commands() -> str: Abstract method to generate deployment commands based on service parameters.
    """

    def __init__(
        self,
        service_config_to_test: Any,  # Type annotation as Any to avoid circular imports
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: EventManager | None = None,
    ):
        super().__init__()
        CommandEventMixin.__init__(self)  # Initialize the CommandEventMixin

        self.available_types = ["TESTERS", "IUT", "testers", "iut"]
        self.service_type = str(service_type.name)
        self.service_type_normalized = self.service_type.upper()
        assert self.service_type_normalized in [
            "TESTERS",
            "IUT",
        ], f"Invalid service type: {self.service_type}"
        self._plugin_dir = Path(os.path.dirname(__file__))

        # Always use lowercase in paths for consistency with directory structure
        service_type_path = (
            service_type.lower() if isinstance(service_type, str) else service_type.name.lower()
        )

        if self.service_type_normalized == "TESTERS":
            self.templates_dir = (
                f"{os.path.dirname(__file__)}/{service_type_path}/{implementation_name}/templates/"
            )
            self.config_versions_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{implementation_name}/version_configs/"
        else:
            self.templates_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{protocol.name}/{implementation_name}/templates/"
            self.config_versions_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{protocol.name}/{implementation_name}/version_configs/"

        if not os.path.isdir(self.templates_dir):
            self.logger.error("Templates directory '%s' does not exist.", self.templates_dir)
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug("Available templates in '%s': %s", self.templates_dir, templates)

        self.plugin_manager = None

        # The service master configuration represents the configuration
        # file for the service defined by the plugin itself
        self.service_config_to_test = service_config_to_test

        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters["realpath"] = lambda x: os.path.abspath(x)
        self.jinja_env.filters["is_dict"] = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True

        # Initialize event manager and emitter if provided
        self.event_manager = event_manager
        if event_manager:
            self.event_emitter = ServiceEventEmitter(event_manager)
            self.service_emitter = self.event_emitter  # For CommandEventMixin

        # Service-specific attributes
        # Some attributes are set by the plugin manager, others are set by the plugin itself and the experiment manager
        self.implementation_name = implementation_name
        self.service_name = service_config_to_test.name
        self.service_protocol = protocol
        self.service_targets = (
            ""
            if not self.service_config_to_test.protocol.target
            else self.service_config_to_test.protocol.target
        )
        self.service_version = self.service_config_to_test.protocol.version
        self.working_dir = None
        self.process = None
        self.available_roles = []
        self.volumes = []
        self.role = self.service_config_to_test.protocol.role
        self.environments = {}

        # Note eventually create a dataclass
        self.run_cmd = {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "run_cmd": {
                "working_dir": "",
                "command_binary": "",
                "command_args": "",
                "timeout": 60,
                "environment": {},
            },
            "post_run_cmds": [],
        }
        self._plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def render_commands(
        self, params, template_name, command_args=None, env_vars=None, extra_fields=None
    ):
        """
        Renders a command using a Jinja2 template with the provided parameters.

        Args:
            params: Dictionary containing regular parameters for template rendering.
            template_name: Name of the template to render.
            command_args: List of command arguments for structured command generation.
            env_vars: Dictionary of environment variables for structured command generation.
            extra_fields: Additional YAML fragments as a string for structured templates.

        Returns:
            str: The rendered command string.
        """
        self.logger.debug(
            "Rendering command using template '%s' with parameters: %s", template_name, params
        )

        # Register the quoting filters for shell and YAML
        self.jinja_env.filters["quote_shell"] = quote_shell
        self.jinja_env.filters["quote_yaml"] = quote_yaml

        template = self.jinja_env.get_template(template_name)

        # Enhance the params dict with structured command_args, env_vars and extra_fields if provided
        render_params = dict(params)
        if command_args is not None:
            render_params["command_args"] = command_args
        if env_vars is not None:
            render_params["env_vars"] = env_vars
        if extra_fields is not None:
            render_params["extra_fields"] = extra_fields

        command = template.render(**render_params)

        # Clean up the command string, but preserve newlines for multiline commands
        if "\n" not in command:
            command_str = command.replace("\t", " ").strip()
        else:
            command_str = command

        service_name = self.service_config_to_test.name
        self.logger.debug("Generated command for '%s': %s", service_name, command_str)
        return command_str

    def get_service_name(self) -> str:
        return self.service_name

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

        def process_command_list(commands):
            """Process commands using CommandProcessor for better handling."""
            if not commands:
                self.logger.debug("No commands provided, returning empty list.")
                return []

            try:
                processed = processor.process_command_list(commands, detect_properties=True)
                self.logger.debug("Processed %d commands successfully", len(processed))
                return processed
            except Exception as e:
                self.logger.warning(f"Failed to process commands with CommandProcessor: {e}")
                # Fallback to manual conversion for backward compatibility
                result = []
                for cmd in commands:
                    if isinstance(cmd, ShellCommand):
                        result.append(cmd)
                    elif isinstance(cmd, str):
                        result.append(ShellCommand.from_string(cmd))
                    elif isinstance(cmd, dict) and "command" in cmd:
                        result.append(ShellCommand.from_dict(cmd))
                    else:
                        try:
                            result.append(ShellCommand.from_string(str(cmd)))
                        except Exception as inner_e:
                            self.logger.warning(
                                f"Could not convert command: {cmd}, error: {inner_e}"
                            )
                return result

        # Get commands from the respective methods and process them
        self.logger.debug("Generating commands for service '%s' - pre-compile", self.service_name)
        pre_compile = process_command_list(self.generate_pre_compile_commands())
        self.logger.debug("Generating commands for service '%s' - compile", self.service_name)
        compile_cmds = process_command_list(self.generate_compile_commands())
        self.logger.debug("Generating commands for service '%s' - post-compile", self.service_name)
        post_compile = process_command_list(self.generate_post_compile_commands())
        self.logger.debug("Generating commands for service '%s' - pre-run", self.service_name)
        pre_run = process_command_list(self.generate_pre_run_commands())
        self.logger.debug("Generating commands for service '%s' - post-run", self.service_name)
        post_run = process_command_list(self.generate_post_run_commands())

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
            self.run_cmd = processor.process_commands(command_structure, target_format="service")
        except Exception as e:
            self.logger.warning(
                f"Failed to process complete command structure: {e}, using fallback"
            )
            self.run_cmd = command_structure

        self.logger.debug("Run commands: %s", self.run_cmd)
        return self.run_cmd

    def generate_pre_compile_commands(self) -> list:
        """
        Generates a list of shell commands to be executed before compilation.

        Returns:
            list: A list of either string commands or ShellCommand objects if available
        """
        # Emit command generation started event
        self.emit_command_generation_started("pre_compile")

        # ShellCommand is imported at the top of the file, so we use it directly
        # for better shell command representation with metadata and proper escaping

        # Using ShellCommand objects for better structure, error handling, and debugging support
        commands = [
            ShellCommand(command="set -x;", description="Enable command tracing", is_critical=True),
            ShellCommand(
                command="export SHELLOPTS",
                description="Export shell options for subshells",
                is_critical=True,
            ),
            ShellCommand(
                command="export PATH=$PATH:$ADDITIONAL_PATH;",
                description="Set PATH environment variable",
                is_critical=False,  # Non-critical as ADDITIONAL_PATH might be empty
            ),
            ShellCommand(
                command="export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;",
                description="Set PYTHONPATH environment variable",
                is_critical=False,  # Non-critical as ADDITIONAL_PYTHONPATH might be empty
            ),
            ShellCommand(
                command="env >> /app/logs/env.log;",
                description="Log environment variables for debugging",
                is_critical=False,
            ),
        ]
        # Emit command generated event
        for cmd in commands:
            self.logger.debug("Generated pre-compile command: %s", cmd)
        self.emit_command_generated("pre_compile", f"{len(commands)} pre-compile commands")
        return commands

    def generate_compile_commands(self) -> list[str]:
        """
        This method generates and returns a list of compile commands.
        Generates compile commands.

        Returns:
            list: An empty list representing the compile commands.
        """
        # Emit command generation started event
        self.emit_command_generation_started("compile")
        commands = []
        # Emit command generated event
        self.emit_command_generated("compile", "No compile commands")
        return commands

    def generate_post_compile_commands(self) -> list[str]:
        """
        Generate a list of post-compile commands.
        This method returns an empty list of strings representing commands
        to be executed after the compilation process.
        Returns:
            List[str]: An empty list of post-compile commands.
        """
        # Emit command generation started event
        self.emit_command_generation_started("post_compile")
        commands = []
        # Emit command generated event
        self.emit_command_generated("post_compile", "No post-compile commands")
        return commands

    def generate_pre_run_commands(self) -> list[str]:
        """
        Generates a list of pre-run commands.
        This method returns an empty list of strings, which can be overridden by subclasses
        to provide specific pre-run commands required for their execution context.
        Returns:
            List[str]: An empty list of strings representing pre-run commands.
        """
        # Emit command generation started event
        self.emit_command_generation_started("pre_run")
        commands = []
        # Emit command generated event
        self.emit_command_generated("pre_run", "No pre-run commands")
        return commands

    def generate_run_command(self) -> dict:
        """
        Generates a dictionary containing the run command configuration.
        Returns:
            dict: A dictionary with the following keys:
            - "working_dir" (str): The working directory for the command.
            - "command_binary" (str): The binary or executable to run.
            - "command_args" (str): The arguments to pass to the command.
            - "timeout" (int): The timeout value for the command execution.
            - "environment" (dict): The environment variables for the command.
        """
        # Emit command generation started event
        self.emit_command_generation_started("run")

        run_cmd = {
            "working_dir": "",
            "command_binary": "",
            "command_args": "",
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

        # Emit command generated event with a summary
        cmd_summary = f"Run command: {run_cmd.get('command_binary', 'No binary')}"
        self.emit_command_generated("run", cmd_summary)

        return run_cmd

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        # Emit command generation started event
        self.emit_command_generation_started("post_run")
        commands = []
        # Emit command generated event
        self.emit_command_generated("post_run", "No post-run commands")
        return commands

    def get_implementation_name(self) -> str:
        return self.implementation_name

    def is_tester(self):
        """
        Returns True if the plugin is a network service.
        """
        return self.service_type_normalized == "TESTERS"

    @abstractmethod
    def generate_deployment_commands(self) -> str:
        """
        Generates deployment commands based on the service configuration
        """
        raise NotImplementedError()

    def build_command_args(self, command_args):
        """
        Builds a list of command arguments with proper escaping

        Args:
            command_args: List of command arguments or a single string.
                If a string is provided, it will be split on spaces, respecting quoted sections.

        Returns:
            list: A properly escaped list of command arguments
        """
        if command_args is None:
            return []

        if isinstance(command_args, str):
            # Split the string on spaces, respecting quoted sections
            try:
                args = [arg for arg in shlex.split(command_args) if arg.strip()]
                # Remove newline characters from each argument
                args = [arg.replace("\n", "") for arg in args if arg is not None]
            except ValueError as e:
                self.logger.warning("Error splitting command: %s. Using as-is.", e)
                args = [command_args]
        elif isinstance(command_args, list):
            # Ensure all items in the list are strings
            args = [str(arg) for arg in command_args if arg is not None]
        else:
            args = [str(command_args)]

        return args

    def build_env_vars(self, env_dict):
        """
        Builds a dictionary of environment variables with proper escaping

        Args:
            env_dict: Dictionary of environment variables

        Returns:
            dict: A properly escaped dictionary of environment variables
        """
        if not isinstance(env_dict, dict):
            self.logger.warning(
                "Expected dict for env_vars, got %s. Using empty dict.", type(env_dict)
            )
            return {}

        # Ensure all values are strings
        return {k: str(v) for k, v in env_dict.items()}

    def render_template_with_structured_args(
        self,
        template_name,
        params=None,
        command_args=None,
        env_vars=None,
        extra_fields=None,
    ):
        """
        Renders a template with structured parameters for proper quoting

        Args:
            template_name: Name of the template file
            params: Additional parameters to pass to the template
            command_args: List of command arguments or a string to be split
            env_vars: Dictionary of environment variables
            extra_fields: String with additional YAML fragments

        Returns:
            str: The rendered template with properly quoted values
        """
        params = params or {}
        processed_args = self.build_command_args(command_args) if command_args is not None else None
        processed_env = self.build_env_vars(env_vars) if env_vars is not None else None

        return self.render_commands(
            params, template_name, processed_args, processed_env, extra_fields
        )

    def set_event_manager(self, event_manager: EventManager):
        """
        Set the event manager for this service manager.

        Args:
            event_manager: The event manager to set
        """
        self.event_manager = event_manager
        self.event_emitter = ServiceEventEmitter(event_manager)

    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
        """
        Prepare the service with proper event notifications.

        Args:
            plugin_manager: Plugin manager for creating dependencies
        """
        # Logger is provided by LoggerMixin
        self.logger.debug("Preparing service %s", self.service_name)
        self.plugin_manager = plugin_manager

        # Note: event_emitter is already initialized in IServiceManager parent class
        # It uses ServiceEventEmitter which provides typed service events
        if hasattr(self, "event_emitter") and self.event_emitter:
            self.logger.debug("ServiceEventEmitter already initialized")

        try:
            # Get test case name from service_config_to_test if available
            test_case = getattr(self.service_config_to_test, "test_case", "unknown_test")

            # Defensive check for event_emitter before emitting events
            if hasattr(self, "event_emitter") and self.event_emitter:
                # Notify preparation started
                self.notify_service_event(
                    "preparation_started",
                    {
                        "service_name": self.service_name,
                        "service_type": self.service_type,
                        "implementation": self.implementation_name,
                        "test_case": test_case,
                    },
                )
                self.logger.debug("Emitted service preparation started event")

            # Perform preparation
            result = self._do_prepare(plugin_manager)

            # Also emit service started event with defensive check
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_service_started(
                    details={
                        "service_name": self.service_name,
                        "implementation": self.implementation_name,
                        "protocol": (
                            self.service_protocol.name if self.service_protocol else "unknown"
                        ),
                        "test_case": test_case,
                    }
                )
                self.logger.debug("Emitted service started event")

            return result

        # Using a general exception handler here is intended to catch all possible errors
        # during service preparation to ensure proper error notification
        except Exception as e:  # pylint: disable=broad-except
            # Get test case name from service_config_to_test if available
            test_case = getattr(self.service_config_to_test, "test_case", "unknown_test")

            # Defensive check for event_emitter before emitting events
            if hasattr(self, "event_emitter") and self.event_emitter:
                # Notify general error
                self.notify_service_error(
                    error_type="preparation_failed",
                    error_message=str(e),
                    details={
                        "service_name": self.service_name,
                        "implementation": self.implementation_name,
                        "exception_type": type(e).__name__,
                        "test_case": test_case,
                    },
                )
                self.logger.debug("Emitted service error event")

            # Re-raise the exception
            raise

    @abstractmethod
    def _do_prepare(self, plugin_manager: "PluginManager | None" = None):
        """
        Perform the actual preparation work.

        This method should be overridden by subclasses.

        Args:
            plugin_manager: Optional plugin manager to use for preparation
        """
        pass

    def stop(self):
        """
        Stop the service.

        This default implementation just handles event notification.
        Subclasses should override _do_stop to implement actual stop logic.
        """
        self.logger.debug("Stopping service %s", self.service_name)

        try:
            # Notify stopping
            self.notify_service_event(
                "stopping",
                {
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                },
            )

            # Actual stop logic should be implemented in _do_stop
            result = self._do_stop()

            # Notify success
            details = {"implementation": self.implementation_name, "clean_shutdown": True}
            self.notify_service_stopped(True, details)

            return result
        # Using a general exception handler to ensure proper error notification
        except Exception as e:  # pylint: disable=broad-except
            # Notify error
            details = {
                "implementation": self.implementation_name,
                "exception_type": type(e).__name__,
            }
            self.notify_service_stopped(False, details)
            self.notify_service_error(
                error_type="stop_failed", error_message=str(e), details=details
            )
            raise

    def _do_stop(self):
        """
        Perform the actual service stop work.

        To be implemented by subclasses. The default implementation just returns True.

        Returns:
            Implementation-specific result. By default, returns True to indicate success.
        """
        # Default implementation just succeeds
        self.logger.debug("Default _do_stop implementation called for %s", self.service_name)
        return True

    def notify_service_event(self, event_name: str, details: dict = None):
        """
        Notify of a generic service event.

        Args:
            event_name: The name of the event
            details: Additional details about the event
        """
        # Use the mixin methods from ServiceManagerEventMixin instead
        # This method can be overridden if needed, but typically the specific
        # notify methods from ServiceManagerEventMixin should be used
        self.logger.debug("Service event '%s' with details: %s", event_name, details)

    def handle_event(self, event: "BaseEvent") -> None:
        """
        Default implementation of handle_event for service managers.

        This provides a basic event handling mechanism that can be overridden
        by specific service manager implementations if they need custom event handling.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("Service %s received event: %s", self.service_name, event_type)

        # Basic event handling for common service events
        # Subclasses can override this method for more specific handling
        if event_type == "ServiceStartRequestedEvent":
            self.logger.info("Service start requested for %s", self.service_name)
        elif event_type == "ServiceStopRequestedEvent":
            self.logger.info("Service stop requested for %s", self.service_name)
        elif event_type == "TestRunRequestedEvent":
            self.logger.info("Test run requested for %s", self.service_name)
        else:
            # Log unhandled events at debug level
            self.logger.debug(
                "Unhandled event type %s for service %s", event_type, self.service_name
            )
