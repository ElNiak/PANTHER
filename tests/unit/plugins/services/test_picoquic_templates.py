import os
import shlex
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader


# Helper function to get the template directory path for picoquic
def get_template_path():
    """Get the path to the Picoquic templates directory."""
    plugin_dir = Path(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
        )
    )
    return os.path.join(
        plugin_dir,
        "panther",
        "plugins",
        "services",
        "iut",
        "quic",
        "picoquic",
        "templates",
    )


@pytest.fixture
def env():
    """Create a Jinja2 environment with the necessary filters."""
    template_dir = get_template_path()
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    # Register the essential filters for proper escaping
    env.filters["quote_shell"] = lambda s: shlex.quote(str(s))
    env.filters["quote_yaml"] = lambda s: yaml.safe_dump(str(s)).strip()
    return env


@pytest.mark.parametrize(
    "template_name,cmd_args,env_vars,expected_snippet",
    [
        # Test server template with basic arguments
        (
            "server_command_structured.jinja",
            [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-a",
                "h3",
                "-p",
                "4433",
                ">",
                "/app/logs/server.log",
            ],
            {"QUIC_DEBUG": "1", "PICOQUIC_LOG": "debug"},
            # The template outputs args separated by spaces (no quoting)
            "-c",
        ),
        # Test client template with path arguments
        (
            "client_command_structured.jinja",
            [
                "-c",
                "/path with spaces/cert.pem",
                "-k",
                "/path & special/key.pem",
                "localhost",
                "4433",
                ">",
                "/app/logs/client.log",
            ],
            {"PATH": "/usr/bin:/usr/local/bin", "CONFIG": "name=value;other=thing"},
            # The template outputs raw args; paths with spaces appear unquoted
            "/path with spaces/cert.pem",
        ),
        # Test with complex arguments including quotes
        (
            "server_command_structured.jinja",
            [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "--message",
                'Hello "World" & Friends',
                "-p",
                "4433",
            ],
            {"QUOTE_TEST": 'Contains "quotes" inside'},
            # The template outputs raw args; quotes appear as-is
            'Hello "World" & Friends',
        ),
    ],
)
def test_picoquic_structured_templates(
    env, template_name, cmd_args, env_vars, expected_snippet
):
    """Test that the Picoquic structured templates correctly render commands."""
    try:
        template = env.get_template(template_name)
        rendered = template.render(command_args=cmd_args, env_vars=env_vars)

        # Check that the expected snippet is in the rendered output
        assert (
            expected_snippet in rendered
        ), f"Expected '{expected_snippet}' not found in rendered template"

        # Verify all arguments appear in the rendered output
        for arg in cmd_args:
            if isinstance(arg, str):
                assert (
                    str(arg) in rendered
                ), f"Argument '{arg}' not found in rendered template"

    except Exception as e:
        pytest.fail(f"Error rendering template {template_name}: {str(e)}")


# Test edge cases and error conditions
@pytest.mark.parametrize(
    "template_name,cmd_args,env_vars",
    [
        # Edge case: binary characters in arguments
        (
            "server_command_structured.jinja",
            ["-c", "/cert.pem", "-k", "/key.pem", b"\x00\x01\x02\x03"],
            {"TEST": "value"},
        ),
        # Edge case: very long arguments
        (
            "client_command_structured.jinja",
            ["-c", "/c.pem", "-k", "/k.pem", "--very-long-option-" + "x" * 1000],
            {"LONG": "x" * 1000},
        ),
        # Edge case: unicode characters
        (
            "server_command_structured.jinja",
            ["-c", "/c.pem", "-k", "/k.pem", "Hello 😀 World 🌎"],
            {"UNICODE": "😀🌎💫"},
        ),
    ],
)
def test_picoquic_template_edge_cases(env, template_name, cmd_args, env_vars):
    """Test that the Picoquic structured templates handle edge cases gracefully."""
    try:
        template = env.get_template(template_name)
        rendered = template.render(command_args=cmd_args, env_vars=env_vars)
        # If we get here, the template rendered without error
        assert rendered is not None, "Template rendered as None"
    except Exception as e:
        pytest.fail(f"Template {template_name} failed to handle edge case: {str(e)}")
