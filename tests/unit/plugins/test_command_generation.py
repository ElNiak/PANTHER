import pytest
import os
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from unittest.mock import patch

from panther.config.core.models.service import ProtocolConfig, ServiceConfig
from panther.plugins.services import (
    IServiceManager,
    quote_shell,
    quote_yaml,
    validate_cmd,
    validate_structure,
)


def _make_service_config(**overrides) -> ServiceConfig:
    """Create a minimal real ServiceConfig for command generation tests."""
    defaults = dict(
        timeout=60,
        implementation={"name": "test_service", "type": "iut"},
        protocol={"name": "quic", "version": "rfc9000", "role": "server", "target": None},
    )
    defaults.update(overrides)
    return ServiceConfig(**defaults)


def _make_protocol_config(**overrides) -> ProtocolConfig:
    """Create a minimal real ProtocolConfig for command generation tests."""
    defaults = dict(name="quic", version="rfc9000", role="server")
    defaults.update(overrides)
    return ProtocolConfig(**defaults)


def test_quote_shell():
    """Test that the quote_shell function correctly quotes strings for shell usage."""
    # Basic strings
    assert quote_shell("simple") == "simple"

    # Strings with spaces
    assert quote_shell("hello world") == "'hello world'"

    # Strings with special shell characters
    assert quote_shell("echo Hello && echo Goodbye") == "'echo Hello && echo Goodbye'"
    assert quote_shell("file with $var") == "'file with $var'"

    # Strings with quotes
    assert quote_shell('echo "hello"') == "'echo \"hello\"'"

    # Empty string
    assert quote_shell("") == "''"


def test_quote_yaml():
    """Test that the quote_yaml function correctly formats strings for YAML.

    Note: quote_yaml uses yaml.safe_dump().strip() which appends a YAML
    document-end marker ('\\n...') for plain scalars. Assertions below
    match the current implementation behavior.
    """
    # Basic strings -- yaml.safe_dump adds document-end marker for plain scalars
    assert quote_yaml("simple") == "simple\n..."

    # Strings that need quoting in YAML (no document-end marker)
    assert quote_yaml("string: with colon") == "'string: with colon'"
    assert quote_yaml("2001: A Space Odyssey") == "'2001: A Space Odyssey'"

    # Special characters
    special = quote_yaml("string with newline\nand tab\tcharacters")
    assert "newline" in special and "tab" in special

    # Empty string
    assert quote_yaml("") == "''"


class TestServiceManager(IServiceManager):
    """Test implementation of IServiceManager.

    This is a proper concrete test implementation of the abstract
    IServiceManager interface. It bypasses the complex __init__ and
    sets only the attributes needed by the methods under test.
    """

    def __init__(self):
        self._plugin_dir = Path(os.path.dirname(__file__))
        self.templates_dir = os.path.join(os.path.dirname(__file__))
        self.service_config_to_test = _make_service_config()
        self.service_protocol = _make_protocol_config()
        self.service_name = "test_service"
        # logger is a property from LoggerMixin -- do not assign directly

        # Initialize Jinja environment
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters["quote_shell"] = quote_shell
        self.jinja_env.filters["quote_yaml"] = quote_yaml

    def prepare(self, plugin_loader=None):
        """No-op implementation of abstract prepare."""
        pass

    def generate_deployment_commands(self, service_params, environment):
        """No-op implementation of abstract generate_deployment_commands."""
        return {}

    def handle_event(self, event):
        """No-op implementation of abstract handle_event."""
        pass


@pytest.fixture
def service_manager():
    """Create a test service manager instance."""
    return TestServiceManager()


def test_build_command_args(service_manager):
    """Test that build_command_args correctly processes string and list inputs."""
    # String input
    assert service_manager.build_command_args("command arg1 arg2") == ["command", "arg1", "arg2"]

    # String with quotes
    assert service_manager.build_command_args('echo "hello world"') == ["echo", "hello world"]

    # List input
    assert service_manager.build_command_args(["command", "arg1", "arg2"]) == [
        "command",
        "arg1",
        "arg2",
    ]

    # Empty inputs
    assert service_manager.build_command_args("") == []
    assert service_manager.build_command_args([]) == []

    # Non-string input
    assert service_manager.build_command_args(123) == ["123"]


def test_build_env_vars(service_manager):
    """Test that build_env_vars correctly processes dict inputs."""
    # Basic dict
    assert service_manager.build_env_vars({"KEY": "value"}) == {"KEY": "value"}

    # Dict with non-string values
    assert service_manager.build_env_vars({"PORT": 8080}) == {"PORT": "8080"}

    # Empty dict
    assert service_manager.build_env_vars({}) == {}

    # Non-dict input
    assert service_manager.build_env_vars("not a dict") == {}


def test_render_template_with_structured_args(service_manager, tmp_path):
    """Test that render_template_with_structured_args correctly renders templates."""
    # Create a test template
    test_template = """
    {# Environment variables #}
    {% if env_vars %}
    {% for key, value in env_vars.items() %}
    export {{ key }}={{ value|quote_shell }}
    {% endfor %}
    {% endif %}

    {# Command arguments #}
    {% if command_args %}
    {% for arg in command_args %}{{ arg|quote_shell }} {% endfor %}
    {% else %}
    echo "No command args"
    {% endif %}

    {# Extra fields #}
    {% if extra_fields %}
    {{ extra_fields }}
    {% endif %}
    """

    # Write test template to temp file
    template_path = tmp_path / "test_template.jinja"
    with open(template_path, "w") as f:
        f.write(test_template)

    # Mock the render_commands method
    with patch.object(service_manager, "render_commands") as mock_render:
        # Set up the mock to return the rendered content
        def side_effect(params, template_name, cmd_args=None, env_vars=None, extra_fields=None):
            return f"RENDERED: template={template_name}, args={cmd_args}, env={env_vars}, extra={extra_fields}"

        mock_render.side_effect = side_effect

        # Test with all parameters
        result = service_manager.render_template_with_structured_args(
            "test_template.jinja",
            {"param": "value"},
            ["command", "arg1", "arg2"],
            {"ENV": "value"},
            "extra: true",
        )

        # Verify correct parameters were passed
        mock_render.assert_called_with(
            {"param": "value"},
            "test_template.jinja",
            ["command", "arg1", "arg2"],
            {"ENV": "value"},
            "extra: true",
        )

        # Check result
        assert "RENDERED" in result
        assert "template=test_template.jinja" in result

        # Test with minimal parameters
        result = service_manager.render_template_with_structured_args("test_template.jinja")
        assert "RENDERED" in result
        assert "args=None" in result
        assert "env=None" in result
        assert "extra=None" in result


def test_validate_structure_valid():
    """Test that validate_structure accepts valid structures."""
    # Valid flat structure
    schema = {"key1": str, "key2": int}
    data = {"key1": "value", "key2": 42}
    validate_structure(data, schema)

    # Valid nested structure
    schema = {"outer": {"inner": str}}
    data = {"outer": {"inner": "value"}}
    validate_structure(data, schema)

    # Valid with tuple type (either-or)
    schema = {"key": (int, float)}
    validate_structure({"key": 42}, schema)
    validate_structure({"key": 3.14}, schema)

    # Valid list
    schema = {"items": list}
    validate_structure({"items": [1, 2, 3]}, schema)


def test_validate_structure_invalid():
    """Test that validate_structure rejects invalid structures."""
    # Missing key
    schema = {"key1": str, "key2": int}
    data = {"key1": "value"}
    with pytest.raises(ValueError):
        validate_structure(data, schema)

    # Wrong type
    schema = {"key": str}
    data = {"key": 42}
    with pytest.raises(TypeError):
        validate_structure(data, schema)

    # Wrong nested type
    schema = {"outer": {"inner": str}}
    data = {"outer": {"inner": 42}}
    with pytest.raises(TypeError):
        validate_structure(data, schema)

    # Wrong type for tuple specification
    schema = {"key": (int, float)}
    data = {"key": "not a number"}
    with pytest.raises(TypeError):
        validate_structure(data, schema)


@validate_cmd
def valid_command_function():
    """Return a valid command structure for testing."""
    return {
        "pre_compile_cmds": ["echo 'Pre-compile'"],
        "compile_cmds": ["make"],
        "post_compile_cmds": ["echo 'Post-compile'"],
        "pre_run_cmds": ["echo 'Pre-run'"],
        "run_cmd": {
            "working_dir": "/app",
            "command_binary": "python3",
            "command_args": "-m server",
            "timeout": 60,
            "environment": {"DEBUG": "1"},
        },
        "post_run_cmds": ["echo 'Post-run'"],
    }


@validate_cmd
def invalid_command_function():
    """Return an invalid command structure for testing."""
    return {
        "pre_compile_cmds": ["echo 'Pre-compile'"],
        # Missing compile_cmds
        "post_compile_cmds": ["echo 'Post-compile'"],
        "pre_run_cmds": ["echo 'Pre-run'"],
        "run_cmd": {
            "working_dir": "/app",
            "command_binary": "python3",
            # Missing command_args
            "timeout": 60,
            "environment": {"DEBUG": "1"},
        },
        "post_run_cmds": ["echo 'Post-run'"],
    }


def test_validate_cmd_decorator():
    """Test that the validate_cmd decorator correctly validates command structures."""
    # Valid command structure should not raise
    valid_command_function()

    # Invalid command structure should raise
    with pytest.raises(ValueError):
        invalid_command_function()
