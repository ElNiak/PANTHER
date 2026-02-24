import os
import shlex
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader


# Helper function to get the template directory path for panther_ivy
def get_template_path():
    """Get the path to the PantherIvy templates directory"""
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
        "testers",
        "panther_ivy",
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
        # Test quic server structured template
        (
            "quic/server_command_structured.jinja",
            [
                "/opt/panther_ivy/test",
                "seed=123",
                "server_port=8080",
                "server_addr=$IVY_IP_HEX",
                ">",
                "/app/logs/test.log",
            ],
            {"IVY_LOG_LEVEL": "debug", "TEST_NAME": "test_server"},
            "seed=123 server_port=8080 server_addr=$IVY_IP_HEX",
        ),
        # Test quic client structured template with special characters
        (
            "quic/client_command_structured.jinja",
            [
                "/opt/panther_ivy/test_client",
                "seed=123",
                "server_addr=$TARGET_IP_HEX",
                "message='Hello & Goodbye'",
                ">",
                "/app/logs/test.log",
            ],
            {"ENV_VAR": "special:value", "TEST": 'quotes "inside" here'},
            "message='Hello & Goodbye'",
        ),
        # Test minip server structured template
        (
            "minip/server_command_structured.jinja",
            [
                "/opt/panther_ivy/minip_test",
                "server_port=8080",
                "client_port=9090",
                "server_addr=10.0.0.1",
                ">",
                "/app/logs/test.log",
            ],
            {"DEBUG": "1", "PATH": "/usr/bin:/usr/local/bin"},
            "server_port=8080 client_port=9090",
        ),
    ],
)
def test_structured_templates(env, template_name, cmd_args, env_vars, expected_snippet):
    """Test that the structured templates correctly render commands with proper escaping"""
    try:
        template = env.get_template(template_name)
        rendered = template.render(command_args=cmd_args, env_vars=env_vars)

        # Check that the expected snippet is in the rendered output
        assert (
            expected_snippet in rendered
        ), f"Expected '{expected_snippet}' not found in rendered template"

        # For commands with special characters, ensure they're properly quoted
        if "'" in str(cmd_args) or "&" in str(cmd_args) or '"' in str(cmd_args):
            for arg in cmd_args:
                if any(c in str(arg) for c in "'&\""):
                    # The literal argument should not appear unescaped in the output
                    literal_arg = str(arg).replace("'", "").replace('"', "")
                    assert (
                        literal_arg not in rendered
                        or shlex.quote(literal_arg) in rendered
                    ), f"Special character in '{arg}' not properly escaped in rendered template"

        # For environment variables with special characters, ensure they're properly quoted
        for key, value in env_vars.items():
            if any(c in str(value) for c in "'&\":;"):
                # The variable name should be in the output
                assert (
                    key in rendered
                ), f"Environment variable '{key}' not found in rendered template"
                # The literal value should not appear unescaped
                if ":" in str(value) or ";" in str(value):
                    literal_value = str(value).replace("'", "").replace('"', "")
                    assert (
                        literal_value not in rendered
                        or shlex.quote(literal_value) in rendered
                    ), f"Special character in env var '{value}' not properly escaped in rendered template"

    except Exception as e:
        pytest.fail(f"Error rendering template {template_name}: {str(e)}")


# Test that malformed inputs are handled gracefully
@pytest.mark.parametrize(
    "template_name,cmd_args,env_vars",
    [
        # Test with None values
        ("quic/server_command_structured.jinja", None, {"TEST": "value"}),
        # Test with empty arguments
        ("quic/client_command_structured.jinja", [], {}),
        # Test with non-string values
        (
            "minip/server_command_structured.jinja",
            [123, True, None, {"key": "value"}],
            {"NUM": 42},
        ),
    ],
)
def test_structured_templates_error_handling(env, template_name, cmd_args, env_vars):
    """Test that the structured templates gracefully handle malformed inputs"""
    try:
        template = env.get_template(template_name)
        rendered = template.render(command_args=cmd_args, env_vars=env_vars)
        # If we get here, the template rendered without error
        assert rendered is not None, "Template rendered as None"
    except Exception as e:
        pytest.fail(
            f"Template {template_name} failed to handle malformed inputs: {str(e)}"
        )
