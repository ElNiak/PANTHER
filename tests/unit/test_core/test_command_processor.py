"""Unit tests for CommandProcessor - the core command generation component of PANTHER.

Tests cover command processing, shell command creation, property detection,
and error handling using real PANTHER classes (no fake fallbacks).
"""

from typing import Any, Dict
from unittest.mock import Mock

import pytest

from panther.core.command_processor import CommandProcessor, ShellCommand
from panther.core.command_processor.core.interfaces import ICommandProcessor
from panther.core.command_processor.models.shell_command import CommandMetadata
from panther.core.command_processor.utils.shell_utils import combine_shell_constructs

pytestmark = [pytest.mark.unit, pytest.mark.command_generation]


# ---------------------------------------------------------------------------
# CommandProcessor initialization
# ---------------------------------------------------------------------------


class TestCommandProcessorInitialization:
    """Test CommandProcessor initialization and basic setup."""

    def test_command_processor_creation(self, real_command_processor):
        """Test creating a CommandProcessor instance."""
        assert real_command_processor is not None
        assert hasattr(real_command_processor, "logger")

    def test_command_processor_implements_interface(self, real_command_processor):
        """Test CommandProcessor implements ICommandProcessor."""
        assert isinstance(real_command_processor, ICommandProcessor)

    def test_command_processor_has_required_methods(self, real_command_processor):
        """Test CommandProcessor exposes the three ICommandProcessor methods."""
        assert callable(getattr(real_command_processor, "process_commands", None))
        assert callable(getattr(real_command_processor, "process_command_list", None))
        assert callable(
            getattr(real_command_processor, "detect_command_properties", None)
        )


# ---------------------------------------------------------------------------
# process_commands -- the main entry point
# ---------------------------------------------------------------------------


class TestProcessCommands:
    """Test CommandProcessor.process_commands() with real implementation.

    The real _process_run_cmd returns keys:
        working_dir, command_binary, command_args, environment, timeout

    The real process_command_list returns a list of ShellCommand.to_dict() dicts
    with keys: command, raw_command, shell_safe_command, executable, arguments,
    redirections, metadata.
    """

    def test_process_run_cmd_structure(self, real_command_processor):
        """process_commands extracts run_cmd with real key names."""
        commands = {
            "run_cmd": {
                "command_binary": "echo",
                "command_args": "hello world",
                "working_dir": "/tmp",
                "timeout": 30,
            }
        }

        result = real_command_processor.process_commands(commands)

        assert "run_cmd" in result
        run_cmd = result["run_cmd"]
        # Real _process_run_cmd returns these keys
        assert "command_binary" in run_cmd
        assert "command_args" in run_cmd
        assert run_cmd["working_dir"] == "/tmp"
        assert run_cmd["timeout"] == 30

    def test_process_run_cmd_with_environment(self, real_command_processor):
        """Environment variables are preserved through processing."""
        commands = {
            "run_cmd": {
                "command_binary": "./app",
                "command_args": "--verbose",
                "working_dir": "/app",
                "timeout": 120,
                "environment": {"DEBUG": "1", "PATH": "/usr/local/bin"},
            }
        }

        result = real_command_processor.process_commands(commands)
        assert result["run_cmd"]["environment"]["DEBUG"] == "1"
        assert result["run_cmd"]["environment"]["PATH"] == "/usr/local/bin"

    def test_process_run_cmd_empty(self, real_command_processor):
        """Empty/None run_cmd returns default structure."""
        commands = {"run_cmd": None}
        result = real_command_processor.process_commands(commands)

        run_cmd = result["run_cmd"]
        assert run_cmd["working_dir"] == ""
        assert run_cmd["command_args"] == [] or run_cmd["command_args"] == ""
        assert run_cmd["environment"] == {}
        assert run_cmd["timeout"] == 60

    def test_process_run_cmd_with_command_args_list(self, real_command_processor):
        """command_args can be a list; real processor joins them."""
        commands = {
            "run_cmd": {
                "command_binary": "python",
                "command_args": ["-m", "pytest", "--verbose"],
                "working_dir": ".",
                "timeout": 60,
            }
        }

        result = real_command_processor.process_commands(commands)
        # Real processor joins list args into a space-separated string
        args = result["run_cmd"]["command_args"]
        assert "-m" in args
        assert "pytest" in args
        assert "--verbose" in args

    def test_process_command_lists(self, real_command_processor):
        """Non-run_cmd entries are processed through process_command_list."""
        commands = {
            "run_cmd": {"command_binary": "main", "timeout": 60},
            "pre_run_cmds": ["mkdir -p /tmp/test", "cd /tmp/test"],
            "post_run_cmds": ["cleanup.sh"],
        }

        result = real_command_processor.process_commands(commands)

        assert "pre_run_cmds" in result
        assert "post_run_cmds" in result
        # process_command_list returns list of ShellCommand.to_dict() dicts
        assert isinstance(result["pre_run_cmds"], list)
        assert isinstance(result["post_run_cmds"], list)

        # Each processed command is a dict with 'command' key
        for cmd_dict in result["pre_run_cmds"]:
            assert isinstance(cmd_dict, dict)
            assert "command" in cmd_dict

    def test_process_empty_command_list(self, real_command_processor):
        """Empty command lists return empty lists."""
        commands = {
            "run_cmd": {"command_binary": "test", "timeout": 60},
            "pre_run_cmds": [],
        }

        result = real_command_processor.process_commands(commands)
        assert result["pre_run_cmds"] == []

    def test_process_commands_preserves_all_keys(self, real_command_processor):
        """All command type keys are present in the output."""
        commands = {
            "pre_compile_cmds": ["./configure", "make clean"],
            "compile_cmds": ["make -j4"],
            "post_compile_cmds": ["make install"],
            "run_cmd": {
                "command_binary": "./test_suite",
                "command_args": "--verbose --output=xml",
                "working_dir": "/build",
                "timeout": 300,
                "environment": {"TEST_ENV": "ci"},
            },
            "post_run_cmds": ["collect_artifacts.sh", "cleanup_temp.sh"],
        }

        result = real_command_processor.process_commands(commands)
        assert set(result.keys()) == set(commands.keys())

    def test_process_commands_with_target_format(self, real_command_processor):
        """target_format parameter is accepted (forwarded, no crash)."""
        commands = {"run_cmd": {"command_binary": "test_cmd", "timeout": 60}}

        for fmt in ["generic", "docker", "shell"]:
            result = real_command_processor.process_commands(commands, fmt)
            assert "run_cmd" in result


# ---------------------------------------------------------------------------
# process_command_list
# ---------------------------------------------------------------------------


class TestProcessCommandList:
    """Test CommandProcessor.process_command_list() in isolation."""

    def test_process_string_commands(self, real_command_processor):
        """String commands are converted to ShellCommand dicts."""
        cmds = ["echo hello", "ls -la"]
        result = real_command_processor.process_command_list(cmds)

        assert len(result) >= 1
        for item in result:
            assert isinstance(item, dict)
            assert "command" in item

    def test_process_empty_list(self, real_command_processor):
        """Empty input returns empty output."""
        assert real_command_processor.process_command_list([]) == []
        assert real_command_processor.process_command_list(None) == []

    def test_process_filters_empty_strings(self, real_command_processor):
        """Empty/blank strings are filtered out."""
        cmds = ["echo hello", "", "   ", "ls"]
        result = real_command_processor.process_command_list(cmds)

        # Only non-blank commands should remain
        commands = [d["command"] for d in result]
        for cmd in commands:
            assert cmd.strip() != ""

    def test_process_shell_command_objects(self, real_command_processor):
        """ShellCommand objects are accepted and converted to dicts."""
        shell_cmd = ShellCommand("echo from_object", validate=False)
        result = real_command_processor.process_command_list([shell_cmd])

        assert len(result) >= 1
        assert any("echo from_object" in d["command"] for d in result)

    def test_process_dict_commands(self, real_command_processor):
        """Dict commands with 'command' key are accepted."""
        cmds = [{"command": "echo from_dict"}]
        result = real_command_processor.process_command_list(cmds)

        assert len(result) >= 1
        assert any("echo from_dict" in d["command"] for d in result)


# ---------------------------------------------------------------------------
# ShellCommand -- real model tests
# ---------------------------------------------------------------------------


class TestShellCommand:
    """Test ShellCommand model with the real implementation."""

    def test_creation_from_string(self):
        """ShellCommand.from_string creates a valid instance."""
        cmd = ShellCommand.from_string("echo test")
        assert cmd.command is not None
        assert "echo" in cmd.command

    def test_creation_with_metadata(self):
        """ShellCommand accepts metadata kwargs."""
        cmd = ShellCommand(
            "python script.py",
            is_critical=True,
            timeout=120,
            validate=False,
        )
        assert cmd.metadata.is_critical is True
        assert cmd.metadata.timeout == 120

    def test_to_dict_structure(self):
        """to_dict returns the expected key structure."""
        cmd = ShellCommand("ls -la", validate=False)
        d = cmd.to_dict()

        assert "command" in d
        assert "raw_command" in d
        assert "shell_safe_command" in d
        assert "executable" in d
        assert "arguments" in d
        assert "redirections" in d
        assert "metadata" in d
        assert isinstance(d["metadata"], dict)
        assert "is_critical" in d["metadata"]

    def test_from_dict_roundtrip(self):
        """from_dict + to_dict roundtrip preserves command text."""
        original = ShellCommand("echo roundtrip", validate=False)
        d = original.to_dict()
        restored = ShellCommand.from_dict(d)

        assert restored.command == original.command

    def test_str_contains_command(self):
        """String representation contains the command text."""
        cmd = ShellCommand("echo hello", validate=False)
        assert "echo hello" in str(cmd)

    def test_repr_contains_command(self):
        """Repr contains the command text."""
        cmd = ShellCommand("echo hello", validate=False)
        assert "echo hello" in repr(cmd)

    def test_shell_safe_command(self):
        """shell_safe_command property returns a string."""
        cmd = ShellCommand("echo test", validate=False)
        safe = cmd.shell_safe_command
        assert isinstance(safe, str)
        assert "echo" in safe

    def test_is_complex_for_single_command(self):
        """Single commands are not complex."""
        cmd = ShellCommand("echo simple", validate=False)
        assert cmd.is_complex() is False

    def test_with_timeout(self):
        """with_timeout returns a new ShellCommand with updated timeout."""
        cmd = ShellCommand("echo test", validate=False)
        timed = cmd.with_timeout(300)
        assert timed.metadata.timeout == 300
        # Original should be unchanged
        assert cmd.metadata.timeout != 300

    def test_with_environment(self):
        """with_environment returns a new ShellCommand with merged env."""
        cmd = ShellCommand("echo test", validate=False)
        env_cmd = cmd.with_environment({"FOO": "bar"})
        assert env_cmd.metadata.environment["FOO"] == "bar"


# ---------------------------------------------------------------------------
# detect_command_properties
# ---------------------------------------------------------------------------


class TestDetectCommandProperties:
    """Test CommandProcessor.detect_command_properties()."""

    def test_single_line_is_not_multiline(self, real_command_processor):
        """Single-line command is not detected as multiline."""
        props = real_command_processor.detect_command_properties("echo hello")
        assert props["is_multiline"] is False

    def test_multiline_detection(self, real_command_processor):
        """Commands containing newlines are detected as multiline."""
        multi = "line1\nline2"
        props = real_command_processor.detect_command_properties(multi)
        assert props["is_multiline"] is True

    def test_function_definition_detection(self, real_command_processor):
        """Function definitions are detected."""
        func = "my_func() {\n  echo hello\n}"
        props = real_command_processor.detect_command_properties(func)
        assert props["is_function_definition"] is True

    def test_control_structure_detection(self, real_command_processor):
        """Control structures (if/for/while/case) are detected."""
        if_block = "if true; then\n  echo yes\nfi"
        props = real_command_processor.detect_command_properties(if_block)
        assert props["is_control_structure"] is True

    def test_for_loop_detection(self, real_command_processor):
        """For loop is detected as control structure."""
        for_loop = "for i in 1 2 3; do\n  echo $i\ndone"
        props = real_command_processor.detect_command_properties(for_loop)
        assert props["is_control_structure"] is True

    def test_simple_command_has_no_special_properties(self, real_command_processor):
        """Simple command has all properties False."""
        props = real_command_processor.detect_command_properties("ls -la")
        assert props["is_multiline"] is False
        assert props["is_function_definition"] is False
        assert props["is_control_structure"] is False


# ---------------------------------------------------------------------------
# combine_shell_constructs -- the real function
# ---------------------------------------------------------------------------


class TestCombineShellConstructs:
    """Test combine_shell_constructs with real implementation.

    The real function combines consecutive list elements that form a
    single shell construct (while/for/if blocks, function definitions).
    """

    def test_empty_input(self):
        """Empty list returns empty list."""
        assert combine_shell_constructs([]) == []

    def test_single_simple_command(self):
        """Single non-construct command passes through unchanged."""
        result = combine_shell_constructs(["echo hello"])
        assert len(result) == 1
        # Result may be a string or ShellCommand
        cmd_text = result[0] if isinstance(result[0], str) else result[0].command
        assert "echo hello" in cmd_text

    def test_combines_for_loop(self):
        """Split for-loop elements are combined into one multiline command."""
        cmds = ["for i in 1 2 3; do", "echo $i", "done"]
        result = combine_shell_constructs(cmds)

        # The three elements should be combined into one
        assert len(result) < len(cmds)
        combined = result[0] if isinstance(result[0], str) else result[0].command
        assert "for" in combined
        assert "done" in combined

    def test_combines_while_loop(self):
        """Split while-loop elements are combined."""
        cmds = ["while true; do", "echo running", "done"]
        result = combine_shell_constructs(cmds)

        assert len(result) < len(cmds)
        combined = result[0] if isinstance(result[0], str) else result[0].command
        assert "while" in combined
        assert "done" in combined

    def test_combines_if_block(self):
        """Split if/fi block is combined."""
        cmds = ["if true; then", "echo yes", "fi"]
        result = combine_shell_constructs(cmds)

        assert len(result) < len(cmds)
        combined = result[0] if isinstance(result[0], str) else result[0].command
        assert "if" in combined
        assert "fi" in combined

    def test_standalone_commands_not_combined(self):
        """Non-construct commands are kept as separate elements."""
        cmds = ["echo one", "echo two", "echo three"]
        result = combine_shell_constructs(cmds)

        assert len(result) == 3

    def test_invalid_input_returns_empty(self):
        """None or non-list input returns empty list."""
        assert combine_shell_constructs(None) == []
        assert combine_shell_constructs("not a list") == []

    def test_shell_command_objects_accepted(self):
        """ShellCommand objects are accepted as input."""
        cmds = [
            ShellCommand("echo standalone", validate=False),
        ]
        result = combine_shell_constructs(cmds)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestCommandProcessorErrorHandling:
    """Test error handling in command processing."""

    def test_non_dict_input_raises(self, real_command_processor):
        """process_commands raises on non-dict input."""
        with pytest.raises(Exception):
            real_command_processor.process_commands("not a dict")

    def test_non_dict_run_cmd_raises(self, real_command_processor):
        """run_cmd that is not a dict (and not None) raises."""
        with pytest.raises(Exception):
            real_command_processor.process_commands({"run_cmd": "bad"})

    def test_empty_dict_does_not_crash(self, real_command_processor):
        """Empty dict is accepted (warning logged, no crash)."""
        result = real_command_processor.process_commands({})
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_none_command_list_entry_filtered(self, real_command_processor):
        """None entries in command lists are gracefully filtered."""
        cmds = ["echo good", None, "echo also_good"]
        result = real_command_processor.process_command_list(cmds)
        # None should be filtered; only real commands remain
        assert all(isinstance(d, dict) for d in result)


# ---------------------------------------------------------------------------
# Performance / scale
# ---------------------------------------------------------------------------


class TestCommandProcessorPerformance:
    """Test command processor with larger inputs."""

    def test_large_command_list_processing(self, real_command_processor):
        """Processing 100 commands completes without error."""
        commands = {
            "run_cmd": {"command_binary": "main_app", "timeout": 60},
            "pre_run_cmds": [f"setup_step_{i}" for i in range(100)],
            "post_run_cmds": [f"cleanup_step_{i}" for i in range(50)],
        }

        result = real_command_processor.process_commands(commands)

        # All pre_run and post_run commands should be processed
        assert len(result["pre_run_cmds"]) > 0
        assert len(result["post_run_cmds"]) > 0

    def test_repeated_processing_is_stable(self, real_command_processor):
        """Processing the same structure multiple times gives consistent results."""
        commands = {
            "run_cmd": {"command_binary": "test_cmd", "timeout": 60},
            "pre_run_cmds": ["echo step1", "echo step2"],
        }

        results = []
        for _ in range(5):
            results.append(real_command_processor.process_commands(commands))

        # All runs should produce the same structure
        for r in results:
            assert set(r.keys()) == {"run_cmd", "pre_run_cmds"}
            assert r["run_cmd"]["timeout"] == 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
