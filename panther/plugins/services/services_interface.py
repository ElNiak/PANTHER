from abc import abstractmethod
import logging
import os
import shlex
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Any, TYPE_CHECKING
from panther.core.observer.event_manager import EventManager
from panther.core.events import ServiceEventEmitter
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.core.command_processor.command import ShellCommand
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.plugin_interface import IPlugin
from panther.plugins.services.service_event_methods import ServiceManagerEventMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    pass


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


class IServiceManager(IPlugin, ServiceManagerEventMixin):
    """
    IServiceManager is an interface for managing services within the PANTHER-SCP framework. It extends the IPlugin class and provides methods for initializing and rendering commands, as well as generating various types of commands required for service deployment and execution.

    Attributes:
        available_types (list): List of valid service types.
        service_type (str): Type of the service (e.g., "testers", "iut").
        templates_dir (str): Directory path for service templates.
        config_versions_dir (str): Directory path for service configuration versions.
        plugin_loader (Optional[PluginLoader]): Loader for the plugin.
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
        prepare(plugin_loader: Optional[PluginLoader] = None): Abstract method to build the Docker image for the implementation.
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

        self.plugin_loader = None

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

        # Service-specific attributes
        # Some attributes are set by the plugin loader, others are set by the plugin itself and the experiment manager
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

        # Helper function to convert items to ShellCommand objects
        def convert_to_shell_commands(commands):
            if not commands:
                self.logger.debug("No commands provided, returning empty list.")
                return []

            result = []
            for cmd in commands:
                if isinstance(cmd, ShellCommand):
                    self.logger.debug("Using existing ShellCommand object: %s", cmd)
                    result.append(cmd)
                elif isinstance(cmd, str):
                    self.logger.debug("Converting string command to ShellCommand: %s", cmd)
                    result.append(ShellCommand.from_string(cmd))
                elif isinstance(cmd, dict) and "command" in cmd:
                    self.logger.debug("Converting dict command to ShellCommand: %s", cmd)
                    # Handle dict with command field
                    result.append(ShellCommand.from_dict(cmd))
                elif isinstance(cmd, list):
                    self.logger.debug("Converting list command to ShellCommand: %s", cmd)
                    # Handle list of commands, recursively convert each item
                    result.extend(convert_to_shell_commands(cmd))
                else:
                    # Try to convert to string as a fallback
                    self.logger.debug("Converting fallback command to ShellCommand: %s", cmd)
                    try:
                        result.append(ShellCommand.from_string(str(cmd)))
                    except Exception as e:
                        self.logger.warning(
                            f"Could not convert command to ShellCommand: {cmd}, error: {e}"
                        )
                        # Skip this command
            self.logger.debug("Converted commands to ShellCommand objects: %s", len(result))
            return result

        # Get commands from the respective methods
        self.logger.debug("Generating commands for service '%s' - pre-compile", self.service_name)
        pre_compile = convert_to_shell_commands(self.generate_pre_compile_commands())
        self.logger.debug("Generating commands for service '%s' - compile", self.service_name)
        compile_cmds = convert_to_shell_commands(self.generate_compile_commands())
        self.logger.debug("Generating commands for service '%s' - post-compile", self.service_name)
        post_compile = convert_to_shell_commands(self.generate_post_compile_commands())
        self.logger.debug("Generating commands for service '%s' - pre-run", self.service_name)
        pre_run = convert_to_shell_commands(self.generate_pre_run_commands())
        self.logger.debug("Generating commands for service '%s' - post-run", self.service_name)
        post_run = convert_to_shell_commands(self.generate_post_run_commands())

        # Special handling for run_cmd which is a dict, not a list
        self.logger.debug("Generating run command for service '%s'", self.service_name)
        run_cmd = self.generate_run_command()

        self.run_cmd = {
            "pre_compile_cmds": pre_compile,
            "compile_cmds": compile_cmds,
            "post_compile_cmds": post_compile,
            "pre_run_cmds": pre_run,
            "run_cmd": run_cmd,
            "post_run_cmds": post_run,
        }
        self.logger.debug("Run commands: %s", self.run_cmd)
        return self.run_cmd

    def generate_pre_compile_commands(self) -> list:
        """
        Generates a list of shell commands to be executed before compilation.

        Returns:
            list: A list of either string commands or ShellCommand objects if available
        """
        # ShellCommand is imported at the top of the file, so we use it directly
        # for better shell command representation with metadata and proper escaping

        try:
            # Using ShellCommand objects for better structure, error handling, and debugging support
            return [
                ShellCommand(
                    command="set -x;", description="Enable command tracing", is_critical=True
                ),
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
        except (ImportError, AttributeError) as e:
            # Fallback to plain string commands if ShellCommand can't be used
            self.logger.warning(
                "Error using ShellCommand objects: %s. Falling back to legacy string commands.",
                str(e),
            )
            return [
                "set -x;",
                "export SHELLOPTS",
                "export PATH=$PATH:$ADDITIONAL_PATH;",
                "export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;",
                "env >> /app/logs/env.log;",
            ]

    def generate_compile_commands(self) -> list[str]:
        """
        This method generates and returns a list of compile commands.
        Generates compile commands.

        Returns:
            list: An empty list representing the compile commands.
        """
        return []

    def generate_post_compile_commands(self) -> list[str]:
        """
        Generate a list of post-compile commands.
        This method returns an empty list of strings representing commands
        to be executed after the compilation process.
        Returns:
            List[str]: An empty list of post-compile commands.
        """

        return []

    def generate_pre_run_commands(self) -> list[str]:
        """
        Generates a list of pre-run commands.
        This method returns an empty list of strings, which can be overridden by subclasses
        to provide specific pre-run commands required for their execution context.
        Returns:
            List[str]: An empty list of strings representing pre-run commands.
        """

        return []

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

        return {
            "working_dir": "",
            "command_binary": "",
            "command_args": "",
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return []

    def get_implementation_name(self) -> str:
        return self.implementation_name

    def is_tester(self):
        """
        Returns True if the plugin is a network service.
        """
        return self.service_type_normalized == "TESTERS"

    @abstractmethod
    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Builds the Docker image for the implementation based on the environment.
        """
        raise NotImplementedError()

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

    def add_command(
        self,
        phase,
        command,
        description=None,
        is_function_definition=False,
        is_function_call=False,
        is_variable_assignment=False,
        is_multiline=False,
        is_critical=True,
        working_dir=None,
        environment=None,
        timeout=None,
    ):
        """
        Add a command to a specific phase of execution

        Args:
            phase: The phase to add the command to (pre_compile, compile, post_compile, pre_run, run, post_run)
            command: The command to add (str or ShellCommand)
            description: Optional description of the command
            is_function_definition: Whether this command is a shell function definition
            is_multiline: Whether this command spans multiple lines
            is_critical: Whether failure of this command should halt execution
            working_dir: Working directory for the command execution
            environment: Environment variables for the command
            timeout: Command timeout in seconds

        Returns:
            None

        Raises:
            ValueError: If the phase is invalid
        """
        valid_phases = ["pre_compile", "compile", "post_compile", "pre_run", "post_run"]
        if phase not in valid_phases:
            raise ValueError(
                f"Invalid command phase: {phase}. Must be one of: {', '.join(valid_phases)}"
            )

        command_key = f"{phase}_cmds"
        if command_key not in self.run_cmd:
            self.run_cmd[command_key] = []

        # Check if the command is already a ShellCommand object
        if isinstance(command, ShellCommand):
            # Use the existing ShellCommand object
            self.logger.debug("Adding %s to %s phase", command.description, phase)
            self.run_cmd[command_key].append(command)
        elif isinstance(command, list):
            # Convert each item in the list to a ShellCommand if it's a string
            for cmd in command:
                if isinstance(cmd, ShellCommand):
                    self.run_cmd[command_key].append(cmd)
                else:
                    # Create a new ShellCommand object
                    shell_cmd = ShellCommand(
                        command=cmd,
                        description=description
                        or f"Command: {cmd[:40]}{'...' if len(cmd) > 40 else ''}",
                        is_critical=is_critical,
                        is_multiline=is_multiline,
                        is_function_definition=is_function_definition,
                        is_function_call=is_function_call,
                        working_dir=working_dir,
                        environment=environment,
                        timeout=timeout,
                    )
                    self.run_cmd[command_key].append(shell_cmd)
        else:
            # Create a new ShellCommand object for a string command
            if description:
                self.logger.debug("Adding %s to %s phase", description, phase)

            shell_cmd = ShellCommand(
                command=command,
                description=description
                or f"Command: {command[:40]}{'...' if len(command) > 40 else ''}",
                is_critical=is_critical,
                is_multiline=is_multiline,
                is_function_definition=is_function_definition,
                working_dir=working_dir,
                is_function_call=is_function_call,
                environment=environment,
                timeout=timeout,
            )
            self.run_cmd[command_key].append(shell_cmd)

    def set_event_manager(self, event_manager: EventManager):
        """
        Set the event manager for this service manager.

        Args:
            event_manager: The event manager to set
        """
        self.event_manager = event_manager
        self.event_emitter = ServiceEventEmitter(event_manager)
