"""Tests for panther ivy CLI commands."""

import pytest

pytest.importorskip("panther_ivy.api", reason="panther_ivy package not installed")

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from api.types import (
    CommandResult,
    CompileResult,
    DiagnosticItem,
    ExecutionResult,
    TestInfo,
)
from click.testing import CliRunner

from panther.cli_click.commands.ivy import ivy


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestIvyGroup:
    def test_help(self, cli_runner):
        result = cli_runner.invoke(ivy, ["--help"])
        assert result.exit_code == 0
        assert "Ivy formal verification" in result.output

    def test_subcommands_listed(self, cli_runner):
        result = cli_runner.invoke(ivy, ["--help"])
        assert "compile" in result.output
        assert "build" in result.output
        assert "list-tests" in result.output
        assert "test" in result.output
        assert "run-test" in result.output


class TestCompileCommand:
    @patch("panther.cli_click.commands.ivy.IvyExecutor")
    @patch("panther.cli_click.commands.ivy.generate_compile_commands")
    @patch("panther.cli_click.commands.ivy.parse_compile_output")
    def test_compile_json_output_success(
        self, mock_parse, mock_gen, mock_executor_cls, cli_runner, tmp_path
    ):
        ivy_file = tmp_path / "test.ivy"
        ivy_file.write_text("# test")

        mock_gen.return_value = CompileResult(
            setup_commands=CommandResult(
                commands=["mkdir -p build"], environment={}, working_dir="."
            ),
            compile_commands=CommandResult(
                commands=["ivyc target=test test.ivy"],
                environment={},
                working_dir=".",
            ),
        )
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.execute_compile.return_value = ExecutionResult(
            exit_code=0, stdout="Done.", stderr="", target="host"
        )
        mock_parse.return_value = []

        result = cli_runner.invoke(ivy, ["compile", str(ivy_file)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert data["diagnostics"] == []

    @patch("panther.cli_click.commands.ivy.IvyExecutor")
    @patch("panther.cli_click.commands.ivy.generate_compile_commands")
    @patch("panther.cli_click.commands.ivy.parse_compile_output")
    def test_compile_json_output_with_errors(
        self, mock_parse, mock_gen, mock_executor_cls, cli_runner, tmp_path
    ):
        ivy_file = tmp_path / "test.ivy"
        ivy_file.write_text("# test")

        mock_gen.return_value = CompileResult(
            setup_commands=CommandResult(commands=[], environment={}, working_dir="."),
            compile_commands=CommandResult(
                commands=["ivyc target=test test.ivy"],
                environment={},
                working_dir=".",
            ),
        )
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.execute_compile.return_value = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="error: test.ivy: line 10: oops",
            target="host",
        )
        mock_parse.return_value = [
            DiagnosticItem(
                file="test.ivy",
                line=10,
                column=0,
                severity="error",
                message="oops",
            )
        ]

        result = cli_runner.invoke(ivy, ["compile", str(ivy_file)])
        # CLI itself succeeds; status field indicates error
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "error"
        assert len(data["diagnostics"]) == 1
        assert data["diagnostics"][0]["line"] == 10

    @patch("panther.cli_click.commands.ivy.IvyExecutor")
    @patch("panther.cli_click.commands.ivy.generate_compile_commands")
    def test_compile_raw_output(
        self, mock_gen, mock_executor_cls, cli_runner, tmp_path
    ):
        ivy_file = tmp_path / "test.ivy"
        ivy_file.write_text("# test")

        mock_gen.return_value = CompileResult(
            setup_commands=CommandResult(commands=[], environment={}, working_dir="."),
            compile_commands=CommandResult(
                commands=["ivyc target=test test.ivy"],
                environment={},
                working_dir=".",
            ),
        )
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.execute_compile.return_value = ExecutionResult(
            exit_code=0,
            stdout="Compiling...\nDone.",
            stderr="",
            target="host",
        )

        result = cli_runner.invoke(ivy, ["compile", str(ivy_file), "--output", "raw"])
        assert result.exit_code == 0
        assert "Compiling" in result.output


class TestListTestsCommand:
    @patch("panther.cli_click.commands.ivy.list_tests")
    def test_list_tests_json(self, mock_list, cli_runner):
        mock_list.return_value = [
            TestInfo(
                name="quic_server_test_stream",
                protocol="quic",
                version="rfc9000",
                role="server",
                ivy_file="/path/test.ivy",
            ),
        ]
        result = cli_runner.invoke(ivy, ["list-tests", "--protocol", "quic"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "tests" in data
        assert len(data["tests"]) == 1
        assert data["tests"][0]["name"] == "quic_server_test_stream"

    @patch("panther.cli_click.commands.ivy.list_tests")
    def test_list_tests_raw(self, mock_list, cli_runner):
        mock_list.return_value = [
            TestInfo(
                name="quic_server_test_stream",
                protocol="quic",
                version="rfc9000",
                role="server",
                ivy_file="/path/test.ivy",
            ),
        ]
        result = cli_runner.invoke(ivy, ["list-tests", "--output", "raw"])
        assert result.exit_code == 0
        assert "quic_server_test_stream" in result.output


class TestBuildCommand:
    @patch("panther.cli_click.commands.ivy.IvyExecutor")
    def test_build_json_output(self, mock_executor_cls, cli_runner):
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.ensure_docker_image.return_value = "panther_ivy:latest"

        result = cli_runner.invoke(ivy, ["build"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert "panther_ivy" in data["image"]
