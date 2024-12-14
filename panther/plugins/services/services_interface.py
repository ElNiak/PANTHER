from abc import abstractmethod
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.plugin_interface import IPlugin


RUN_CMD_SCHEMA = {
    "pre_compile_cmds": list,
    "compile_cmds": list,
    "post_compile_cmds": list,
    "pre_run_cmds": list,
    "run_cmd": {
        "working_dir": str,
        "command_binary": str,
        "command_args": str,
        "timeout": (int, float),
        "command_env": dict,
    },
    "post_run_cmds": list,
}


def validate_cmd(func):
    def wrapper(*args, **kwargs):
        command = func(*args, **kwargs)
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
            raise TypeError(
                f"Expected a dictionary at '{path}', got {type(data).__name__}."
            )
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
            raise TypeError(
                f"Expected one of {schema} at '{path}', got {type(data).__name__}."
            )
    else:
        if not isinstance(data, schema):
            raise TypeError(
                f"Expected {schema.__name__} at '{path}', got {type(data).__name__}."
            )


class IServiceManager(IPlugin):
    """
    IServiceManager is an interface for managing services within the PANTHER-SCP framework. It extends the IPlugin class and provides methods for initializing and rendering commands, as well as generating various types of commands required for service deployment and execution.

    Attributes:
        available_types (list): List of valid service types.
        service_type (str): Type of the service (e.g., "testers", "iut").
        templates_dir (str): Directory path for service templates.
        config_versions_dir (str): Directory path for service configuration versions.
        plugin_loader (Optional[PluginLoader]): Loader for the plugin.
        service_config_to_test (ServiceConfig): Configuration for the service to be tested.
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
        generate_deployment_commands(service_params: ServiceConfig, environment: str) -> Dict[str, str]: Abstract method to generate deployment commands based on service parameters.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__()

        self.available_types = ["testers", "iut"]
        self.service_type = service_type
        assert (
            self.service_type in self.available_types
        ), f"Invalid service type: {self.service_type}"
        self._plugin_dir = Path(os.path.dirname(__file__))
        if self.service_type == "testers":
            self.templates_dir = f"{os.path.dirname(__file__)}/{service_type}/{implementation_name}/templates/"
            self.config_versions_dir = f"{os.path.dirname(__file__)}/{service_type}/{implementation_name}/version_configs/"
        else:
            self.templates_dir = f"{os.path.dirname(__file__)}/{service_type}/{protocol.name}/{implementation_name}/templates/"
            self.config_versions_dir = f"{os.path.dirname(__file__)}/{service_type}/{protocol.name}/{implementation_name}/version_configs/"

        if not os.path.isdir(self.templates_dir):
            self.logger.error(
                f"Templates directory '{self.templates_dir}' does not exist."
            )
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug(
                f"Available templates in '{self.templates_dir}': {templates}"
            )

        self.plugin_loader = None

        # The service master configuration represents the configuration file for the service defined by the plugin
        # itself
        self.service_config_to_test = service_config_to_test

        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters["realpath"] = lambda x: os.path.abspath(x)
        self.jinja_env.filters["is_dict"] = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True

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
                "command_env": {},
            },
            "post_run_cmds": [],
        }

    def render_commands(self, params, template_name):
        self.logger.debug(
            f"Rendering command using template '{template_name}' with parameters: {params}"
        )
        template = self.jinja_env.get_template(template_name)
        command = template.render(**params)
        # Clean up the command string
        command_str = command.replace("\t", " ").replace("\n", " ").strip()
        service_name = self.service_config_to_test.name
        self.logger.debug(f"Generated command for '{service_name}': {command_str}")
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
        self.run_cmd = {
            "pre_compile_cmds": self.generate_pre_compile_commands(),
            "compile_cmds": self.generate_compile_commands(),
            "post_compile_cmds": self.generate_post_compile_commands(),
            "pre_run_cmds": self.generate_pre_run_commands(),
            "run_cmd": self.generate_run_command(),
            "post_run_cmds": self.generate_post_run_commands(),
        }
        self.logger.debug(f"Run commands: {self.run_cmd}")
        return self.run_cmd

    def generate_pre_compile_commands(self) -> list[str]:
        """
        Generates a list of shell commands to be executed before compilation.
        Returns:
            list: A list of strings, each representing a shell command.
        """

        return [
            "set -x;",
            "export PATH=$$PATH:$$ADDITIONAL_PATH;",
            "export PYTHONPATH=$$PYTHONPATH:$$ADDITIONAL_PYTHONPATH;",
            "env >> /app/logs/ivy_setup.log;",
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
            - "command_env" (dict): The environment variables for the command.
        """

        return {
            "working_dir": "",
            "command_binary": "",
            "command_args": "",
            "timeout": self.service_config_to_test.timeout,
            "command_env": {},
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
        return self.service_type == "testers"

    @abstractmethod
    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Builds the Docker image for the implementation based on the environment.
        """
        raise NotImplementedError()

    @abstractmethod
    def generate_deployment_commands(
        self, service_params: ServiceConfig, environment: str
    ) -> dict[str, str]:
        """
        Generates deployment commands based on service parameter
        """
        raise NotImplementedError()
