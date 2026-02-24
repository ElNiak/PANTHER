import os
import shlex
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader


# Helper function to get the template directory path for picoquic
def get_template_path():
    """Get the path to the Picoquic templates directory"""
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
    """Create a Jinja2 environment with the necessary filters"""
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
            "-c /certs/cert.pem -k /certs/key.pem -a h3",
        ),
        # Test client template with special characters in parameters
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
            '"/path with spaces/cert.pem"',
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
            'Hello \\"World\\" & Friends',
        ),
    ],
)
def test_picoquic_structured_templates(
    env, template_name, cmd_args, env_vars, expected_snippet
):
    """Test that the Picoquic structured templates correctly render commands with proper escaping"""
    try:
        template = env.get_template(template_name)
        rendered = template.render(command_args=cmd_args, env_vars=env_vars)

        # Check that the expected snippet is in the rendered output
        assert (
            expected_snippet in rendered
        ), f"Expected '{expected_snippet}' not found in rendered template"

        # For commands with special characters, verify they're properly escaped
        for arg in cmd_args:
            if isinstance(arg, str) and any(c in arg for c in " '\"&|;<>()$`\\"):
                # Space characters should be quoted correctly
                if " " in arg and '"' not in arg:
                    assert (
                        f'"{arg}"' in rendered or f"'{arg}'" in rendered
                    ), f"Spaces in argument '{arg}' not properly quoted in rendered template"

                # Shell metacharacters should be escaped
                if any(c in arg for c in "&|;<>()$`\\"):
                    safely_quoted = shlex.quote(arg)
                    # The original unquoted text shouldn't appear directly
                    for metachar in "&|;<>()$`\\":
                        if metachar in arg:
                            # Check that either the character is escaped or the string is quoted
                            assert (
                                metachar not in rendered
                                or f"\\{metachar}" in rendered
                                or safely_quoted in rendered
                                or arg not in rendered
                            ), f"Shell metacharacter '{metachar}' in '{arg}' not properly escaped in rendered template"

        # For environment variables with special characters, ensure they're properly quoted
        for key, value in env_vars.items():
            # Check that the variable name is in the output
            assert (
                key in rendered
            ), f"Environment variable '{key}' not found in rendered template"

            # Check quotes and special characters in variable values
            if isinstance(value, str) and any(c in value for c in "'\"`:;\\"):
                # The value should be quoted or escaped correctly
                quoted_value = shlex.quote(value)
                assert (
                    quoted_value in rendered or value not in rendered
                ), f"Special characters in env var value '{value}' not properly quoted in rendered template"

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
    """Test that the Picoquic structured templates handle edge cases gracefully"""
    try:
        template = env.get_template(template_name)
        rendered = template.render(command_args=cmd_args, env_vars=env_vars)
        # If we get here, the template rendered without error
        assert rendered is not None, "Template rendered as None"
    except Exception as e:
        pytest.fail(f"Template {template_name} failed to handle edge case: {str(e)}")
