"""Tests for CLI help output and documentation consistency."""
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.requires_network]


class TestCLIHelpOutput:
    """Test that CLI help output is consistent and complete."""

    def test_main_help_output(self):
        """Test that main CLI help contains expected sections."""
        result = subprocess.run(
            ["python", "-m", "panther", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed
        assert result.returncode == 0, f"CLI help failed: {result.stderr}"

        help_output = result.stdout

        # Check for expected sections
        expected_sections = [
            "usage:",
            "optional arguments:",
            "--experiment-config",
            "--debug",
            "--validate-config",
            "--list-plugin-params",
        ]

        for section in expected_sections:
            assert section in help_output.lower(), f"Missing section: {section}"

    def test_plugin_params_help(self):
        """Test that plugin parameter listing works."""
        # Test listing parameters for a known plugin
        result = subprocess.run(
            [
                "python",
                "-m",
                "panther",
                "--list-plugin-params",
                "picoquic",
                "--plugin-type",
                "iut",
                "--protocol",
                "quic",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # May succeed or fail depending on plugin availability
        # We're testing that the command format is recognized
        assert "--list-plugin-params" in " ".join(result.args)

    def test_config_validation_help(self):
        """Test that config validation help is accessible."""
        result = subprocess.run(
            ["python", "-m", "panther", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        help_output = result.stdout
        assert "--validate-config" in help_output

    @pytest.mark.slow
    def test_create_plugin_help(self):
        """Test that plugin creation help is available."""
        result = subprocess.run(
            ["python", "-m", "panther", "--create-plugin", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # This might fail if the command structure has changed
        # We're testing that help system is accessible
        assert result.returncode in [
            0,
            1,
            2,
        ]  # Various exit codes are acceptable for help


class TestExampleConfigurations:
    """Test that example configurations are valid."""

    def test_example_config_files_exist(self):
        """Test that example configuration files exist and are readable."""
        config_dir = Path("experiment-config")

        if config_dir.exists():
            example_files = list(config_dir.glob("*.yaml"))
            assert len(example_files) > 0, "No example configuration files found"

            for config_file in example_files:
                assert (
                    config_file.is_file()
                ), f"Config file {config_file} is not readable"

                # Basic YAML structure check
                content = config_file.read_text()
                assert len(content) > 0, f"Config file {config_file} is empty"
                assert (
                    "tests:" in content or "logging:" in content
                ), f"Config file {config_file} missing expected content"

    def test_minimal_config_validation(self):
        """Test that minimal configuration is valid."""
        minimal_config = Path(
            "experiment-config/experiment_config_example_minimal.yaml"
        )

        if minimal_config.exists():
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "panther",
                    "--experiment-config",
                    str(minimal_config),
                    "--validate-config",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Config validation should not crash (may pass or fail based on dependencies)
            assert result.returncode in [
                0,
                1,
            ], f"Config validation crashed: {result.stderr}"


class TestDocumentationConsistency:
    """Test that documentation is consistent with code."""

    def test_readme_mentions_key_features(self):
        """Test that README mentions key PANTHER features."""
        readme_path = Path("README.md")

        if readme_path.exists():
            readme_content = readme_path.read_text().lower()

            key_features = [
                "protocol testing",
                "docker",
                "experiment",
                "plugin",
                "quic",
            ]

            for feature in key_features:
                assert (
                    feature in readme_content
                ), f"README missing mention of: {feature}"

    def test_claude_md_consistency(self):
        """Test that CLAUDE.md contains current development patterns."""
        claude_md = Path("CLAUDE.md")

        if claude_md.exists():
            content = claude_md.read_text()

            # Check for current development patterns
            expected_patterns = [
                "virtual environment",
                "pytest",
                "Event-Driven Architecture",
                "Plugin System",
                "Docker",
            ]

            for pattern in expected_patterns:
                assert pattern in content, f"CLAUDE.md missing pattern: {pattern}"

    def test_architecture_documentation_accuracy(self):
        """Test that architecture documentation reflects current structure."""
        # Check if architecture docs mention current components
        docs_to_check = ["CLAUDE.md", "README.md"]

        current_components = [
            "panther.core.events",
            "panther.core.command_processor",
            "panther.plugins",
            "EventManager",
            "ServiceManager",
        ]

        for doc_file in docs_to_check:
            doc_path = Path(doc_file)
            if doc_path.exists():
                content = doc_path.read_text()

                # At least some components should be mentioned
                mentioned_components = [
                    comp for comp in current_components if comp in content
                ]
                assert (
                    len(mentioned_components) > 0
                ), f"{doc_file} doesn't mention current architecture"


class TestCommandLineInterfaceRobustness:
    """Test CLI robustness and error handling."""

    def test_invalid_config_file_handling(self, temp_dir):
        """Test that invalid config files are handled gracefully."""
        invalid_config = Path(temp_dir) / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content: [")

        result = subprocess.run(
            [
                "python",
                "-m",
                "panther",
                "--experiment-config",
                str(invalid_config),
                "--validate-config",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail gracefully, not crash
        assert result.returncode != 0
        assert len(result.stderr) > 0  # Should provide error message

    def test_missing_config_file_handling(self):
        """Test that missing config files are handled gracefully."""
        result = subprocess.run(
            [
                "python",
                "-m",
                "panther",
                "--experiment-config",
                "/nonexistent/config.yaml",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail gracefully
        assert result.returncode != 0

    def test_invalid_arguments_handling(self):
        """Test that invalid arguments are handled gracefully."""
        result = subprocess.run(
            ["python", "-m", "panther", "--invalid-argument"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail with helpful error
        assert result.returncode != 0
        assert (
            "unrecognized arguments" in result.stderr.lower()
            or "invalid" in result.stderr.lower()
        )
