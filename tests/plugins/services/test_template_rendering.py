import os
import shlex

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader


# Path to the plugin's template directory - adjust for the specific plugin being tested
def get_template_path():
    return os.path.join(
        os.path.dirname(__file__),
        "../../panther/plugins/services/iut/quic/picoquic/templates/",
    )


@pytest.fixture
def env():
    """Create Jinja2 Environment with shell and YAML quoting filters."""
    env = Environment(loader=FileSystemLoader(get_template_path()), autoescape=False)
    env.filters["quote_shell"] = lambda s: shlex.quote(s)
    env.filters["quote_yaml"] = lambda s: yaml.safe_dump(s).strip()
    return env


@pytest.fixture
def enhanced_env():
    """Create Jinja2 Environment for the enhanced command template."""
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(__file__)), autoescape=False
    )
    env.filters["quote_shell"] = lambda s: shlex.quote(s)
    env.filters["quote_yaml"] = lambda s: yaml.safe_dump(s).strip()
    return env


@pytest.mark.parametrize(
    "cmd_args, env_vars, expected_snippet",
    [
        # Simple arguments
        (
            ["/bin/sh", "-c", 'echo "Hello & Goodbye"'],
            {"PATH": "/usr/local/bin"},
            'echo \\"Hello & Goodbye\\"',
        ),
        # Path with spaces and special characters
        (
            ["python3", "-m", "panther", "--config", "/path/to/some & dir/file.txt"],
            {},
            "--config /path/to/some\\ \\&\\ dir/file.txt",
        ),
        # Environment variables with special characters
        (
            ["echo", "test"],
            {"KEY": "value:with:colon", "PATH": "/usr/bin:/bin"},
            "KEY=value:with:colon",
        ),
        # Command with quotes and ampersands
        (
            [
                "openssl",
                "s_client",
                "-connect",
                "example.com:443",
                "-servername",
                "example.com",
            ],
            {"SSL_CERT": "/path/to/cert.pem"},
            "openssl s_client -connect example.com:443 -servername example.com",
        ),
        # Empty arguments should be handled properly
        ([], {}, ""),
        # Argument with spaces should be quoted
        (["echo", "hello world"], {}, 'echo "hello world"'),
    ],
)
def test_client_command_template(env, cmd_args, env_vars, expected_snippet):
    """Test that the client command template properly quotes arguments."""
    template = env.get_template("client_command.jinja")

    # Additional parameters needed by the template
    params = {
        "certificates": {
            "cert_param": "--cert",
            "cert_file": "/path/to/cert.pem",
            "key_param": "--key",
            "key_file": "/path/to/key.pem",
        },
        "ticket_file": {"param": "--ticket", "file": "/path/to/ticket.bin"},
        "protocol": {
            "alpn": {"param": "--alpn", "value": "h3"},
            "additional_parameters": "--no-verify",
        },
        "network": {
            "port": 443,
            "interface": {"param": "--interface", "value": "eth0"},
        },
        "target": "server",
        "logging": {
            "log_path": "/app/logs/client.log",
            "err_path": "/app/logs/client.err",
        },
    }

    if cmd_args:
        rendered = template.render(**params, command_args=cmd_args, env_vars=env_vars)
    else:
        rendered = template.render(**params)

    # Check if the expected snippet is in the rendered output
    if expected_snippet:
        assert expected_snippet in rendered

    # If we have environment variables, check they're properly set
    if env_vars:
        for key, value in env_vars.items():
            if key != "PATH":  # PATH is special and might be handled differently
                assert f"{key}={value}" in rendered or f'{key}="{value}"' in rendered


@pytest.mark.parametrize(
    "cmd_args, env_vars, extra_fields, expected_snippets",
    [
        (
            ["/bin/sh", "-c", 'echo "Complex string with spaces & special chars"'],
            {"ENV_VAR": "value with spaces", "PATH": "/usr/bin:/bin"},
            "extra_yaml: true\nconfig:\n  nested: value",
            [
                '"/bin/sh" "-c" "echo \\"Complex string with spaces & special chars\\""',
                'ENV_VAR="value with spaces"',
                "extra_yaml: true",
            ],
        ),
        (
            ["python3", "-m", "server", "--port", "8080"],
            {"DEBUG": "1", "SERVER_NAME": "test-server"},
            None,
            [
                '"python3" "-m" "server" "--port" "8080"',
                'DEBUG="1"',
                'SERVER_NAME="test-server"',
            ],
        ),
    ],
)
def test_command_template(
    enhanced_env, cmd_args, env_vars, extra_fields, expected_snippets
):
    """Test that the enhanced command template works with structured arguments."""
    template = enhanced_env.get_template("enhanced_command.jinja")

    # Additional parameters needed by the template
    params = {
        "certificates": {
            "cert_param": "--cert",
            "cert_file": "/path/to/cert.pem",
            "key_param": "--key",
            "key_file": "/path/to/key.pem",
        },
        "ticket_file": {"param": "--ticket", "file": "/path/to/ticket.bin"},
        "protocol": {
            "alpn": {"param": "--alpn", "value": "h3"},
            "additional_parameters": "--no-verify",
        },
        "network": {
            "port": 443,
            "interface": {"param": "--interface", "value": "eth0"},
        },
        "target": "server",
        "logging": {
            "log_path": "/app/logs/client.log",
            "err_path": "/app/logs/client.err",
        },
    }

    rendered = template.render(
        **params, command_args=cmd_args, env_vars=env_vars, extra_fields=extra_fields
    )

    # Check that each expected snippet is in the rendered output
    for snippet in expected_snippets:
        assert snippet in rendered

    # When using extra_fields, ensure it can be loaded as valid YAML
    if extra_fields:
        try:
            loaded_yaml = yaml.safe_load(rendered.split("\n\n")[-1])
            assert isinstance(loaded_yaml, dict)
        except yaml.YAMLError as e:
            pytest.fail(f"Failed to parse rendered YAML: {e}")
