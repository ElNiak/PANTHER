import os
import pytest
import shlex
import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


# Helper function to get the template directory path
def get_template_path():
    """Get the path to the PantherIvy templates directory"""
    plugin_dir = Path(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
        )
    )
    return os.path.join(
        plugin_dir, "panther", "plugins", "services", "testers", "panther_ivy", "templates"
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
    "cmd_args,env_vars,expected_snippet,should_contain",
    [
        # Test regular arguments
        (
            [
                "/opt/panther_ivy/protocol-testing/apt/test_client",
                "server_addr=",
                "$TARGET_IP_HEX",
                ">",
                "/app/logs/testers.log",
                "2>",
                "/app/logs/testers.err",
            ],
            {"IVY_LOG_LEVEL": "debug", "TEST_NAME": "test_client"},
            "server_addr= $TARGET_IP_HEX",
            True,
        ),
        # Test arguments with special characters
        (
            [
                "/opt/panther_ivy/test_client",
                "server_addr=",
                "192.168.1.1",
                "message='Hello & Goodbye'",
                ">",
                "/app/logs/log.txt",
            ],
            {"PATH": "/usr/local/bin:/usr/bin", "SPECIAL": "key:value;something"},
            "message='Hello & Goodbye'",
            True,
        ),
        # Test command with spaces in paths
        (
            [
                "/opt/test client",
                "-c",
                "server_addr= $ADDR",
                "port= 8080",
                ">",
                "/path with spaces/log.txt",
            ],
            {"ADDR": "192.168.1.1"},
            '"/opt/test client"',
            True,
        ),
        # Test command that should NOT contain unquoted special characters
        (["/bin/sh", "-c", 'echo "This & that" > /tmp/file'], {}, "echo This & that", False),
    ],
)
def test_command_template_rendering(env, cmd_args, env_vars, expected_snippet, should_contain):
    """Test that command templates render with proper escaping"""
    # Since PantherIvy doesn't have command templates like other plugins,
    # we'll test the general quoting functionality

    # Create a simple test template that uses quote_shell filter
    template_content = """#!/bin/bash
# Test template for command rendering
{% for key, value in env_vars.items() %}
export {{ key }}={{ value|quote_shell }}
{% endfor %}

# Execute command
cd /working/dir
{% for arg in cmd_args %}{{ arg|quote_shell }} {% endfor %}
"""

    # Create a temporary template file
    template_path = os.path.join(os.path.dirname(__file__), "test_template.jinja2")
    with open(template_path, "w") as f:
        f.write(template_content)

    # Add the template file to the environment
    env.loader.searchpath.append(os.path.dirname(template_path))

    # Render the template
    template = env.get_template("test_template.jinja2")
    rendered = template.render(cmd_args=cmd_args, env_vars=env_vars)

    # Perform assertions based on expected behavior
    if should_contain:
        assert (
            expected_snippet in rendered
        ), f"Expected '{expected_snippet}' to be in rendered output"
    else:
        assert (
            expected_snippet not in rendered
        ), f"Expected '{expected_snippet}' NOT to be in rendered output"

    # Check that proper quoting is applied
    for arg in cmd_args:
        if " " in arg or "&" in arg or '"' in arg or "'" in arg:
            # Arguments with special chars should be quoted in output
            quoted_arg = shlex.quote(arg)
            assert (
                quoted_arg in rendered
            ), f"Expected properly quoted arg '{quoted_arg}' in rendered output"

    # Clean up
    if os.path.exists(template_path):
        os.unlink(template_path)
