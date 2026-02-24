import logging
import os
import shlex
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from panther.config.core.models import ProtocolConfig
from panther.core.command_processor import ShellCommand
from panther.core.events.service.emitter import ServiceEventEmitter
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils import CommandEventMixin

# PluginManager functionality now integrated into PluginManager
from panther.plugins.plugin_interface import IPlugin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


def quote_shell(s: str) -> str:
    """Quote string for safe shell command execution.

    Uses shlex.quote to properly escape special characters in shell arguments,
    preventing command injection vulnerabilities.

    Args:
        s: String to quote for shell safety.

    Returns:
        Shell-safe quoted string.

    Example:
        >>> quote_shell("file with spaces.txt")
        "'file with spaces.txt'"
        >>> quote_shell("normal_file.txt")
        "normal_file.txt"
    """
    return shlex.quote(str(s))


def quote_yaml(s: str) -> str:
    """Quote string for safe YAML document inclusion.

    Uses yaml.safe_dump to properly escape YAML special characters and
    ensure the string can be safely included in YAML documents.

    Args:
        s: String to quote for YAML safety.

    Returns:
        YAML-safe quoted string.

    Example:
        >>> quote_yaml("key: value")
        "'key: value'"
        >>> quote_yaml("simple_string")
        "simple_string"
    """
    return yaml.safe_dump(str(s)).strip()


class IServiceManager(IPlugin, CommandEventMixin):
    """Service manager interface for PANTHER network protocol testing framework.

    Manages service lifecycle, command generation, and configuration for network
    protocol implementations and testing services. Supports both Implementation
    Under Test (IUT) and Tester service types with event-driven architecture.

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
        get_output_patterns() -> List[Tuple[str, str]]: Returns service-specific output patterns.
    """

    def __init__(
        self,
        service_config_to_test: Any,  # Type annotation as Any to avoid circular imports
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: Optional[EventManager] = None,
        test_case: Optional[
            Any
        ] = None,  # Reference to parent test case for execution environment access
    ):
        super().__init__()
        CommandEventMixin.__init__(self)  # Initialize the CommandEventMixin

        self.available_types = ["TESTERS", "IUT", "testers", "iut"]
        # Handle both string and enum types
        if hasattr(service_type, "name"):
            self.service_type = str(service_type.name)
        else:
            self.service_type = str(service_type)

        self.service_type_normalized = self.service_type.upper()

        assert self.service_type_normalized in [
            "TESTERS",
            "IUT",
        ], f"Invalid service type: {self.service_type}"

        self._plugin_dir = Path(os.path.dirname(__file__))

        # Always use lowercase in paths for consistency with directory structure
        service_type_path = (
            service_type.lower()
            if isinstance(service_type, str)
            else service_type.name.lower()
        )

        if self.service_type_normalized == "TESTERS":
            self.templates_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{implementation_name}/templates/{protocol.name}/"
            self.config_versions_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{implementation_name}/version_configs/{protocol.name}/"
        else:
            self.templates_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{protocol.name}/{implementation_name}/templates/"
            self.config_versions_dir = f"{os.path.dirname(__file__)}/{service_type_path}/{protocol.name}/{implementation_name}/version_configs/"

        if not os.path.isdir(self.templates_dir):
            self.logger.error(
                "Templates directory '%s' does not exist.", self.templates_dir
            )
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug(
                "Available templates in '%s': %s", self.templates_dir, templates
            )

        self.plugin_manager = None

        # The service master configuration represents the configuration
        # file for the service defined by the plugin itself
        self.service_config_to_test = service_config_to_test

        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html", "xml", "sh"]),
        )
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

        # Store reference to parent test case for execution environment access
        self.test_case = test_case
        self.volumes = []
        self.role = self.service_config_to_test.protocol.role
        self.environments = {}

        # Load environment variables from version_config
        self._load_version_environment_variables()

        volumes = [
            "shared_logs:/app/sync_logs",
        ]

        if hasattr(self, "volumes"):
            self.volumes.extend(volumes)
        else:
            self.volumes = volumes

        # Default output patterns for this service
        self._output_patterns = self._get_default_output_patterns()
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
        self._plugin_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        # Test context to track which test this service belongs to
        self._test_context = None

        self.build_mode = ""
        self.runtime_mode = "minimal"
        self.z3_source = "local"
        self.docker_image_tag = ""

    def set_test_context(self, test_name: str) -> None:
        """
        Set the test context for this service manager.

        Args:
            test_name: Name of the test this service belongs to
        """
        self._test_context = test_name
        self.logger.debug(
            "Set test context for service %s: %s", self.service_name, test_name
        )

    def get_test_context(self) -> Optional[str]:
        """
        Get the test context for this service manager.

        Returns:
            The test name this service belongs to, or None if not set
        """
        return self._test_context

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
            "Rendering command using template '%s' with parameters: %s",
            template_name,
            params,
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

    def _load_version_environment_variables(self):
        """
        Load environment variables from version_config into self.environments.

        Extracts environment variables from the 'env' section of version_config
        and makes them available for Docker Compose environment generation.
        Also adds dynamic environment variables based on service role and configuration.
        """
        try:
            self.logger.debug(
                "Loading environment variables from version_config for service %s",
                self.service_name,
            )
            # Check if implementation has version_config with environment variables
            impl_config = getattr(self.service_config_to_test, "implementation", None)
            if not impl_config:
                self.logger.debug(
                    f"No implementation config found for service {self.service_name}"
                )
                return

            version_config = getattr(impl_config, "version_config", None)
            if not version_config or not isinstance(version_config, dict):
                self.logger.debug(
                    f"No version_config found for service {self.service_name}"
                )
                return

            # Extract environment variables from the 'env' section
            env_vars = version_config.get("env", {})
            if not env_vars:
                self.logger.debug(
                    f"No environment variables in version_config for service {self.service_name}"
                )
                # Don't return here - we still want to add dynamic variables

            # Process environment variables, handling variable substitution
            for env_name, env_value in env_vars.items():
                if isinstance(env_value, str):
                    # Handle $SOURCE_DIR substitution and other common patterns
                    processed_value = env_value.replace("$SOURCE_DIR", "/opt")
                    self.environments[env_name] = processed_value
                    self.logger.debug(
                        f"Set environment variable {env_name}={processed_value} for service {self.service_name}"
                    )
                else:
                    # Handle non-string values by converting to string
                    self.environments[env_name] = str(env_value)
                    self.logger.debug(
                        f"Set environment variable {env_name}={env_value} for service {self.service_name}"
                    )

            # Add dynamic environment variables
            # 1. IS_CLIENT based on service role
            if hasattr(self.service_config_to_test, "protocol") and hasattr(
                self.service_config_to_test.protocol, "role"
            ):
                role = self.service_config_to_test.protocol.role
                # Handle both enum and string values for role
                if hasattr(role, "value"):
                    role_str = role.value.lower()
                else:
                    role_str = str(role).lower()
                # Set IS_CLIENT: "1" for client role, "0" for server role
                is_client = "1" if role_str == "client" else "0"
                self.environments["IS_CLIENT"] = is_client
                self.role = role_str  # Set the role attribute
                self.logger.debug(
                    f"Set IS_CLIENT={is_client} based on role '{role}' for service {self.service_name}"
                )

            # 2. PROOTPATH and ROOTPATH - these should match the processed SOURCE_DIR
            # If SOURCE_DIR was already set from version config, use its processed value
            # Otherwise, use the default /opt
            source_dir = self.environments.get(
                "SOURCE_DIR", "/opt"
            )  # TODO false -> set by enviornment plugin
            self.environments["PROOTPATH"] = source_dir
            self.environments["ROOTPATH"] = source_dir
            self.logger.debug(
                f"Set PROOTPATH={source_dir} and ROOTPATH={source_dir} for service {self.service_name}"
            )

            if use_system_models := getattr(impl_config, "use_system_models", False):
                # For system models, we might need different paths
                self.environments["MODEL_TYPE"] = "system"
                self.logger.debug(
                    f"Set MODEL_TYPE=system for service {self.service_name}"
                )
            else:
                self.environments["MODEL_TYPE"] = "protocol"
                self.logger.debug(
                    f"Set MODEL_TYPE=protocol for service {self.service_name}"
                )

            self.logger.info(
                f"Loaded {len(self.environments)} environment variables (including dynamic) for service {self.service_name}"
            )

        except Exception as e:
            self.logger.warning(
                f"Failed to load environment variables from version_config for service {self.service_name}: {e}"
            )

    def _resolve_environment_variables(self, cmd_str: str) -> str:
        """
        Replace ${VAR} patterns with actual values from self.environments.

        Args:
            cmd_str: Command string potentially containing ${VAR} patterns

        Returns:
            Command string with variables resolved
        """
        if not isinstance(cmd_str, str):
            return cmd_str

        # Replace ${VAR} patterns with values from self.environments
        import re

        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            var_name = match.group(1)
            if var_name in self.environments:
                return self.environments[var_name]
            # Keep original if not found
            return match.group(0)

        resolved = re.sub(pattern, replacer, cmd_str)

        # Also handle $VAR patterns (without braces)
        pattern2 = r"\$([A-Z_][A-Z0-9_]*)"

        def replacer2(match):
            var_name = match.group(1)
            if var_name in self.environments:
                return self.environments[var_name]
            # Keep original if not found
            return match.group(0)

        resolved = re.sub(pattern2, replacer2, resolved)

        return resolved

    def _apply_network_substitutions(self, cmd_dict: Dict) -> Dict:
        """
        Apply environment variable substitutions to all command phases.

        Args:
            cmd_dict: Dictionary containing command phases

        Returns:
            Dictionary with substitutions applied
        """
        if not self.environments:
            # No substitutions to apply
            return cmd_dict

        # Process each command phase
        for phase in [
            "pre_compile_cmds",
            "compile_cmds",
            "post_compile_cmds",
            "pre_run_cmds",
            "post_run_cmds",
        ]:
            if phase in cmd_dict and isinstance(cmd_dict[phase], list):
                resolved_cmds = []
                for cmd in cmd_dict[phase]:
                    if isinstance(cmd, str):
                        resolved_cmds.append(self._resolve_environment_variables(cmd))
                    elif isinstance(cmd, ShellCommand):
                        # Update the command string in ShellCommand
                        cmd.command = self._resolve_environment_variables(cmd.command)
                        resolved_cmds.append(cmd)
                    else:
                        resolved_cmds.append(cmd)
                cmd_dict[phase] = resolved_cmds

        # Process run_cmd
        if "run_cmd" in cmd_dict and isinstance(cmd_dict["run_cmd"], dict):
            if "command_args" in cmd_dict["run_cmd"]:
                if isinstance(cmd_dict["run_cmd"]["command_args"], str):
                    cmd_dict["run_cmd"][
                        "command_args"
                    ] = self._resolve_environment_variables(
                        cmd_dict["run_cmd"]["command_args"]
                    )
                elif isinstance(cmd_dict["run_cmd"]["command_args"], list):
                    cmd_dict["run_cmd"]["command_args"] = [
                        self._resolve_environment_variables(arg)
                        if isinstance(arg, str)
                        else arg
                        for arg in cmd_dict["run_cmd"]["command_args"]
                    ]

            # Also process environment variables in the run_cmd environment
            if "environment" in cmd_dict["run_cmd"]:
                for key, value in cmd_dict["run_cmd"]["environment"].items():
                    if isinstance(value, str):
                        cmd_dict["run_cmd"]["environment"][
                            key
                        ] = self._resolve_environment_variables(value)

        return cmd_dict

    def generate_pre_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """
        Generates a list of shell commands to be executed before compilation.

        Returns:
            list: A list of either string commands or ShellCommand objects if available
        """
        # Emit command generation started event
        self.emit_command_generation_started("pre_compile")
        return []

    def generate_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """
        This method generates and returns a list of compile commands.
        Generates compile commands.

        Returns:
            list: An empty list representing the compile commands.
        """
        # Emit command generation started event
        self.emit_command_generation_started("compile")
        commands = []
        # Only emit if there are actual commands
        if commands:
            self.emit_command_generated("compile", f"{len(commands)} compile commands")
        return commands

    def generate_post_compile_commands(self) -> List[Union[str, ShellCommand]]:
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
        # Only emit if there are actual commands
        if commands:
            self.emit_command_generated(
                "post_compile", f"{len(commands)} post-compile commands"
            )
        return commands

    def generate_pre_run_commands(self) -> List[Union[str, ShellCommand]]:
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
        # Only emit if there are actual commands
        if commands:
            self.emit_command_generated("pre_run", f"{len(commands)} pre-run commands")
        return commands

    def generate_run_command(self) -> Dict[str, Any]:
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

        # Only emit if there's an actual command binary
        command_binary = run_cmd.get("command_binary", "")
        if command_binary:
            cmd_summary = f"Run command: {command_binary}"
            self.emit_command_generated("run", cmd_summary)

        return run_cmd

    def generate_post_run_commands(self) -> List[Union[str, ShellCommand]]:
        """
        Generates post-run commands.
        """
        # Emit command generation started event
        self.emit_command_generation_started("post_run")
        commands = []
        # Only emit if there are actual commands
        if commands:
            self.emit_command_generated(
                "post_run", f"{len(commands)} post-run commands"
            )
        return commands

    def get_implementation_name(self) -> str:
        return self.implementation_name

    def is_tester(self):
        """
        Returns True if this service is a tester (as opposed to an IUT implementation).
        """
        return self.service_type_normalized == "TESTERS"

    @property
    def role(self) -> str:
        """Get the service role (client/server)."""
        return self._role

    @role.setter
    def role(self, value) -> None:
        """Set the service role."""
        self._role = value

    @property
    def protocol_version(self) -> str:
        """Get the protocol version."""
        return self._protocol_version or "default"

    def is_client(self) -> bool:
        """Check if this service is a client."""
        return self.role.lower() == "client"

    def is_server(self) -> bool:
        """Check if this service is a server."""
        return self.role.lower() == "server"

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
        processed_args = (
            self.build_command_args(command_args) if command_args is not None else None
        )
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

    def _do_prepare(self, plugin_manager: "Optional[PluginManager]" = None):
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
            test_case = getattr(
                self.service_config_to_test, "test_case", "unknown_test"
            )

            # Defensive check for event_emitter before emitting events
            if hasattr(self, "event_emitter") and self.event_emitter:
                # Notify preparation started
                self.notify_service_event(
                    "preparation_started",
                    service_id=self.implementation_name,
                    service_name=self.service_name,
                    details={
                        "service_type": self.service_type,
                        "implementation": self.implementation_name,
                        "test_case": test_case,
                    },
                )
                self.logger.debug("Emitted service preparation started event")

            # Note: Preparation logic is handled by ServiceManagerDockerMixin.prepare() via MRO.
            # The _do_prepare() hook is no longer called from this base class.
            result = None

            # Also emit service started event with defensive check
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_service_started(
                    details={
                        "service_name": self.service_name,
                        "implementation": self.implementation_name,
                        "protocol": (
                            self.service_protocol.name
                            if self.service_protocol
                            else "unknown"
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
            test_case = getattr(
                self.service_config_to_test, "test_case", "unknown_test"
            )

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
                service_id=self.implementation_name,
                service_name=self.service_name,
                details={
                    "service_type": self.service_type,
                },
            )

            # Actual stop logic should be implemented in _do_stop
            result = self._do_stop()

            # Notify success
            details = {
                "implementation": self.implementation_name,
                "clean_shutdown": True,
            }
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
        self.logger.debug(
            "Default _do_stop implementation called for %s", self.service_name
        )
        return True

    def _get_default_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get default output patterns based on service type and protocol.

        Returns:
            List of (output_type, filename_pattern) tuples
        """
        # Base patterns common to all services
        base_patterns = [
            ("stdout", "stdout.log"),
            ("stderr", "stderr.log"),
            ("logs", "{service_name}.log"),
        ]

        # Add protocol-specific patterns if available
        if hasattr(self, "service_protocol") and self.service_protocol:
            protocol_name = getattr(self.service_protocol, "name", None)
            if protocol_name:
                base_patterns.extend(
                    self._get_protocol_specific_patterns(protocol_name)
                )

        # Add service type specific patterns
        if self.service_type_normalized == "TESTERS":
            base_patterns.extend(
                [
                    ("test_results", "test_results.json"),
                    ("test_log", "test_{service_name}.log"),
                    ("analysis", "analysis_{service_name}.json"),
                ]
            )

        return base_patterns

    def _get_protocol_specific_patterns(self, protocol: str) -> List[Tuple[str, str]]:
        """
        Get protocol-specific output patterns.

        Args:
            protocol: Protocol name (e.g., 'quic', 'tcp', 'http')

        Returns:
            List of (output_type, filename_pattern) tuples
        """
        protocol_patterns = {
            "quic": [
                ("qlog", "*.qlog"),
                ("keys", "*keys.log"),
                ("sslkeylog", "sslkeylogfile.txt"),
                ("pcap", "{service_name}.pcap"),
                ("congestion", "*congestion*.log"),
            ],
            "tcp": [
                ("pcap", "{service_name}.pcap"),
                ("tcpdump", "*.pcap"),
                ("netstat", "*netstat*.log"),
            ],
            "http": [
                ("access_log", "access.log"),
                ("error_log", "error.log"),
                ("har", "*.har"),
                ("sslkeylog", "sslkeylogfile.txt"),
            ],
            "http3": [  # HTTP/3 over QUIC
                ("qlog", "*.qlog"),
                ("keys", "*keys.log"),
                ("har", "*.har"),
                ("h3_log", "*h3*.log"),
            ],
        }

        return protocol_patterns.get(protocol.lower(), [])

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get output patterns for this service.

        This method can be overridden by subclasses to provide custom patterns.

        Returns:
            List of (output_type, filename_pattern) tuples where:
            - output_type: Category of output (e.g., 'stdout', 'pcap', 'qlog')
            - filename_pattern: Pattern to match files (supports {service_name} placeholder and glob patterns)
        """
        return self._output_patterns

    def add_output_pattern(self, output_type: str, filename_pattern: str):
        """
        Add a custom output pattern for this service.

        Args:
            output_type: Type/category of the output
            filename_pattern: File pattern (can include {service_name} placeholder)
        """
        self._output_patterns.append((output_type, filename_pattern))
        self.logger.debug(f"Added output pattern: {output_type} -> {filename_pattern}")

    def configure_environment_outputs(self, env_type: str) -> None:
        """
        Configure output patterns based on the environment type.

        This method allows services to customize their output patterns based on
        which execution environment they're running in.

        Args:
            env_type: Type of execution environment (e.g., 'strace', 'memcheck', 'gperf')
        """
        # Override in subclasses to add environment-specific outputs
        pass

    def get_additional_output_discovery_patterns(self) -> Dict[str, List[str]]:
        """
        Get additional patterns for discovering outputs not covered by standard patterns.

        Override this in subclasses to provide custom discovery patterns.

        Returns:
            Dict mapping output types to lists of glob patterns
        """
        return {}

    def get_output_file_paths(self, log_base_path: str = "/app/logs") -> Dict[str, str]:
        """
        Get the actual output file paths that will be used by this service.

        This method converts output patterns into concrete file paths that can be
        used in entrypoint scripts for redirecting output.

        Args:
            log_base_path: Base path where logs will be stored (default: /app/logs)

        Returns:
            Dict mapping output types to concrete file paths
        """
        output_paths = {}
        service_name = self.service_name

        for output_type, pattern in self.get_output_patterns():
            # Skip glob patterns for command generation
            if "*" in pattern:
                continue

            # Replace {service_name} placeholder
            filename = pattern.format(service_name=service_name)

            # Create full path
            full_path = f"{log_base_path}/{filename}"
            output_paths[output_type] = full_path

        return output_paths

    def get_standard_redirections(self) -> Dict[str, str]:
        """
        Get standard I/O redirections for command execution.

        Returns:
            Dict with 'stdout' and 'stderr' paths, or empty dict if using defaults
        """
        paths = self.get_output_file_paths()
        redirections = {}

        # Check for stdout/stderr in output patterns
        if "stdout" in paths:
            redirections["stdout"] = paths["stdout"]
        if "stderr" in paths:
            redirections["stderr"] = paths["stderr"]

        return redirections
