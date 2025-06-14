import tempfile
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class MockServiceManager(IServiceManager):
    def __init__(self, service_name="test_service"):
        self.service_name = service_name
        self.service_config_to_test = MagicMock()
        self.service_config_to_test.timeout = 60
        self.service_config_to_test.name = service_name
        self.service_protocol = MagicMock()
        self.implementation_name = "mock_implementation"
        self.logger = MagicMock()
        self.role = MagicMock()
        self.role.name = "client"
        self.volumes = []
        self.environments = {}

        # Set up run_cmd with complex values
        self.run_cmd = {
            "pre_compile_cmds": ["echo 'Starting pre-compile'", "export VAR='value with spaces'"],
            "compile_cmds": ["make", "cc -o output file.c"],
            "post_compile_cmds": ["echo 'Compile complete'"],
            "pre_run_cmds": ["cd /app"],
            "run_cmd": {
                "working_dir": "/app/src",
                "command_binary": "python3",
                "command_args": ["-m", "server", "--host", "0.0.0.0", "--port", "8080"],
                "timeout": 60,
                "command_env": {"DEBUG": "1", "SERVER_NAME": "test-server:8080"},
            },
            "post_run_cmds": ["echo 'Run complete'"],
        }

    def prepare(self, plugin_loader=None):
        pass

    def generate_deployment_commands(self, service_params, environment):
        return {}

    def build_command_args(self, command_args):
        """Implementation of build_command_args from IServiceManager"""
        import shlex

        if isinstance(command_args, str):
            try:
                args = [arg for arg in shlex.split(command_args) if arg.strip()]
            except ValueError:
                args = [command_args]
        elif isinstance(command_args, list):
            args = command_args
        else:
            args = [str(command_args)]
        return args

    def build_env_vars(self, env_dict):
        """Implementation of build_env_vars from IServiceManager"""
        if not isinstance(env_dict, dict):
            return {}
        return {k: str(v) for k, v in env_dict.items()}


@pytest.fixture
def docker_compose_env():
    """Create a test Docker Compose environment"""
    env_config = MagicMock()
    output_dir = tempfile.mkdtemp()
    env_type = "network_environment"
    env_sub_type = "docker_compose"
    event_manager = MagicMock()

    # Mock the jinja environment
    with patch(
        "panther.plugins.environments.network_environment.network_environment_interface.Environment"
    ) as mock_env:
        mock_template = MagicMock()
        mock_template.render.return_value = "# Rendered template content"
        mock_env.return_value.get_template.return_value = mock_template

        env = DockerComposeEnvironment(
            env_config_to_test=env_config,
            output_dir=output_dir,
            env_type=env_type,
            env_sub_type=env_sub_type,
            event_manager=event_manager,
        )

        env.services_managers = [MockServiceManager()]
        return env


def test_generate_entrypoint_with_structured_args(docker_compose_env):
    """Test that generate_entrypoint_with_structured_args properly processes and structures command arguments"""
    # Setup
    service = docker_compose_env.services_managers[0]
    paths = {"base_log_dir": "/tmp/logs"}
    timestamp = "20250602_120000"
    output_path = Path("/tmp/entrypoint_test.sh")
    template_path = Path("/tmp/entrypoint_template.sh")

    # Exercise
    with patch(
        "panther.plugins.environments.network_environment.docker_compose.docker_compose.Path"
    ):
        with patch("builtins.open", create=True):
            docker_compose_env.generate_entrypoint_with_structured_args(
                service, paths, timestamp, output_path, template_path
            )

    # Verify
    calls = docker_compose_env.jinja_env.get_template.mock_calls
    assert len(calls) > 0

    # Verify the structured_commands parameter is passed to generate_from_template
    mock_render = docker_compose_env.jinja_env.get_template.return_value.render
    calls = mock_render.mock_calls
    assert len(calls) > 0

    # Get the keyword arguments passed to render
    args, kwargs = calls[0].args, calls[0].kwargs

    # Verify structured_commands is in the kwargs
    assert "structured_commands" in kwargs
    structured_cmds = kwargs["structured_commands"]

    # Verify the structure of the processed commands
    assert "run_cmd" in structured_cmds
    assert "command_args" in structured_cmds["run_cmd"]
    assert structured_cmds["run_cmd"]["command_args"][0] == "python3"

    # Verify environment variables are properly processed
    assert "env_vars" in structured_cmds["run_cmd"]
    assert "SERVER_NAME" in structured_cmds["run_cmd"]["env_vars"]
    assert structured_cmds["run_cmd"]["env_vars"]["SERVER_NAME"] == "test-server:8080"

    # Verify other command lists are processed
    assert "pre_compile_cmds" in structured_cmds
    assert len(structured_cmds["pre_compile_cmds"]) == 2
    assert "echo 'Starting pre-compile'" in structured_cmds["pre_compile_cmds"]


def test_docker_compose_env_with_complex_commands(docker_compose_env):
    """Test Docker Compose environment handling of complex commands with special characters"""
    # Setup - create a service with complex command arguments
    service = docker_compose_env.services_managers[0]

    # Add complex commands with special characters
    service.run_cmd["pre_compile_cmds"].append("echo 'Value with & and ; characters'")
    service.run_cmd["run_cmd"]["command_args"] = ["python3", "-c", "print('Hello & Goodbye')"]
    service.run_cmd["run_cmd"]["command_env"]["PATH_WITH_COLON"] = "/usr/bin:/usr/local/bin"

    paths = {"base_log_dir": "/tmp/logs"}
    timestamp = "20250602_120000"
    output_path = Path("/tmp/entrypoint_test.sh")
    template_path = Path("/tmp/entrypoint_template.sh")

    # Exercise
    with patch(
        "panther.plugins.environments.network_environment.docker_compose.docker_compose.Path"
    ):
        with patch("builtins.open", create=True):
            docker_compose_env.generate_entrypoint_with_structured_args(
                service, paths, timestamp, output_path, template_path
            )

    # Verify
    mock_render = docker_compose_env.jinja_env.get_template.return_value.render
    calls = mock_render.mock_calls
    args, kwargs = calls[0].args, calls[0].kwargs

    # Check command arguments are properly structured
    structured_cmds = kwargs["structured_commands"]
    assert structured_cmds["run_cmd"]["command_args"] == [
        "python3",
        "-c",
        "print('Hello & Goodbye')",
    ]

    # Check environment variables with special characters
    assert structured_cmds["run_cmd"]["env_vars"]["PATH_WITH_COLON"] == "/usr/bin:/usr/local/bin"

    # Check special characters in pre_compile_cmds
    special_cmd = "echo 'Value with & and ; characters'"
    assert special_cmd in structured_cmds["pre_compile_cmds"]
