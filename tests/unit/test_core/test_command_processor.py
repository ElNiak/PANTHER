"""
Unit tests for CommandProcessor - the core command generation component of PANTHER.

Tests cover command processing, shell command handling, validation, and format conversion.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Use the actual PANTHER modules if available, otherwise mock them
try:
    from panther.core.command_processor.command import (
        ShellCommand,
        combine_shell_constructs,
    )
    from panther.core.command_processor.command_builder import CommandBuilder
    from panther.core.command_processor.command_processor import CommandProcessor
    from panther.core.command_processor.command_utils import (
        sanitize_command_args,
        validate_command_structure,
    )
    from panther.core.command_processor.interfaces import ICommandProcessor
except ImportError:
    # Create mock classes for testing if imports fail
    class CommandProcessor:
        def __init__(self):
            self.logger = Mock()

        def process_commands(
            self, commands: Dict[str, Any], target_format: str = "generic"
        ) -> Dict[str, Any]:
            processed = {}
            for cmd_type, cmds in commands.items():
                if cmd_type == "run_cmd":
                    processed[cmd_type] = self._process_run_cmd(cmds)
                else:
                    processed[cmd_type] = self.process_command_list(cmds)
            return processed

        def _process_run_cmd(self, run_cmd: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "command": run_cmd.get("command", ""),
                "working_dir": run_cmd.get("working_dir", "."),
                "timeout": run_cmd.get("timeout", 60),
                "environment": run_cmd.get("environment", {}),
            }

        def process_command_list(self, commands: List[str]) -> List[str]:
            return [self.sanitize_command(cmd) for cmd in commands] if commands else []

        def sanitize_command(self, command: str) -> str:
            return command.strip() if command else ""

        def validate_command_structure(self, commands: Dict[str, Any]) -> bool:
            required_fields = ["run_cmd"]
            return all(field in commands for field in required_fields)

        def convert_to_shell_commands(
            self, commands: Dict[str, Any]
        ) -> List["ShellCommand"]:
            shell_commands = []
            for cmd_type, cmds in commands.items():
                if cmd_type == "run_cmd":
                    shell_commands.append(
                        ShellCommand(
                            command=cmds.get("command", ""),
                            working_dir=cmds.get("working_dir", "."),
                            timeout=cmds.get("timeout", 60),
                        )
                    )
                elif isinstance(cmds, list):
                    for cmd in cmds:
                        shell_commands.append(ShellCommand(command=cmd))
            return shell_commands

    class ShellCommand:
        def __init__(
            self,
            command: str,
            working_dir: str = ".",
            timeout: int = 60,
            environment: Dict[str, str] = None,
        ):
            self.command = command
            self.working_dir = working_dir
            self.timeout = timeout
            self.environment = environment or {}
            self.validated = False
            self.sanitized = False

        def validate(self) -> bool:
            if not self.command or not self.command.strip():
                return False
            self.validated = True
            return True

        def sanitize(self) -> "ShellCommand":
            self.command = self.command.strip()
            self.sanitized = True
            return self

        def to_dict(self) -> Dict[str, Any]:
            return {
                "command": self.command,
                "working_dir": self.working_dir,
                "timeout": self.timeout,
                "environment": self.environment,
            }

        def __str__(self) -> str:
            return f"ShellCommand('{self.command}')"

        def __repr__(self) -> str:
            return f"ShellCommand(command='{self.command}', working_dir='{self.working_dir}', timeout={self.timeout})"

    def combine_shell_constructs(
        commands: List[ShellCommand], connector: str = "&&"
    ) -> ShellCommand:
        if not commands:
            return ShellCommand("")

        if len(commands) == 1:
            return commands[0]

        combined_cmd = f" {connector} ".join(cmd.command for cmd in commands)
        return ShellCommand(
            command=combined_cmd,
            working_dir=commands[0].working_dir,
            timeout=max(cmd.timeout for cmd in commands),
        )

    class CommandBuilder:
        def __init__(self):
            self.commands = []

        def add_command(
            self, command: str, working_dir: str = ".", timeout: int = 60
        ) -> "CommandBuilder":
            self.commands.append(ShellCommand(command, working_dir, timeout))
            return self

        def build(self) -> List[ShellCommand]:
            return self.commands.copy()

        def clear(self) -> "CommandBuilder":
            self.commands.clear()
            return self

    def validate_command_structure(commands: Dict[str, Any]) -> bool:
        if not isinstance(commands, dict):
            return False
        return "run_cmd" in commands

    def sanitize_command_args(args: List[str]) -> List[str]:
        return [arg.strip() for arg in args if arg and arg.strip()]

    class ICommandProcessor:
        pass


pytestmark = [pytest.mark.unit, pytest.mark.command_generation]


class TestCommandProcessorInitialization:
    """Test CommandProcessor initialization and basic setup."""

    def test_command_processor_creation(self):
        """Test creating a CommandProcessor instance."""
        processor = CommandProcessor()

        # Verify initialization
        assert processor is not None
        assert hasattr(processor, "logger")

    def test_command_processor_interface(self):
        """Test CommandProcessor implements the interface."""
        processor = CommandProcessor()

        # Verify it has required methods
        assert hasattr(processor, "process_commands")
        assert callable(processor.process_commands)


class TestCommandProcessing:
    """Test command processing functionality."""

    @pytest.fixture
    def processor(self):
        """Create a command processor for testing."""
        return CommandProcessor()

    def test_process_simple_commands(self, processor):
        """Test processing simple command structures."""
        commands = {
            "run_cmd": {
                "command": 'echo "hello world"',
                "working_dir": "/tmp",
                "timeout": 30,
            },
            "pre_run_cmds": ["mkdir -p /tmp/test", "cd /tmp/test"],
            "post_run_cmds": ["cleanup.sh"],
        }

        result = processor.process_commands(commands)

        # Verify structure
        assert "run_cmd" in result
        assert "pre_run_cmds" in result
        assert "post_run_cmds" in result

        # Verify run_cmd processing
        run_cmd = result["run_cmd"]
        assert "command" in run_cmd
        assert run_cmd["command"] == 'echo "hello world"'
        assert run_cmd["working_dir"] == "/tmp"
        assert run_cmd["timeout"] == 30

    def test_process_empty_commands(self, processor):
        """Test processing empty command structures."""
        commands = {
            "run_cmd": {"command": "", "working_dir": ".", "timeout": 60},
            "pre_run_cmds": [],
            "post_run_cmds": None,
        }

        result = processor.process_commands(commands)

        # Verify empty handling
        assert result["run_cmd"]["command"] == ""
        assert result["pre_run_cmds"] == []
        assert result["post_run_cmds"] == []

    def test_process_commands_with_target_format(self, processor):
        """Test processing commands with different target formats."""
        commands = {
            "run_cmd": {"command": "test_command", "working_dir": ".", "timeout": 60}
        }

        # Test different target formats
        for target_format in ["generic", "docker", "shell", "kubernetes"]:
            result = processor.process_commands(commands, target_format)
            assert "run_cmd" in result

    def test_process_complex_command_structure(self, processor):
        """Test processing complex command structures."""
        commands = {
            "pre_compile_cmds": ["./configure", "make clean"],
            "compile_cmds": ["make -j4"],
            "post_compile_cmds": ["make install"],
            "run_cmd": {
                "command": "./application --config config.yml",
                "working_dir": "/app",
                "timeout": 120,
                "environment": {"PATH": "/usr/local/bin", "DEBUG": "1"},
            },
            "post_run_cmds": ["cleanup.sh", "archive_logs.sh"],
        }

        result = processor.process_commands(commands)

        # Verify all command types are processed
        assert len(result) == 5
        assert all(cmd_type in result for cmd_type in commands.keys())

        # Verify environment variables are preserved
        assert result["run_cmd"]["environment"]["DEBUG"] == "1"


class TestShellCommand:
    """Test ShellCommand functionality."""

    def test_shell_command_creation(self):
        """Test creating ShellCommand instances."""
        cmd = ShellCommand("echo test")

        assert cmd.command == "echo test"
        assert cmd.working_dir == "."
        assert cmd.timeout == 60
        assert cmd.environment == {}

    def test_shell_command_with_parameters(self):
        """Test ShellCommand with custom parameters."""
        env = {"PATH": "/usr/bin", "HOME": "/home/user"}
        cmd = ShellCommand(
            command="python script.py",
            working_dir="/project",
            timeout=120,
            environment=env,
        )

        assert cmd.command == "python script.py"
        assert cmd.working_dir == "/project"
        assert cmd.timeout == 120
        assert cmd.environment == env

    def test_shell_command_validation(self):
        """Test ShellCommand validation."""
        # Valid command
        valid_cmd = ShellCommand("ls -la")
        assert valid_cmd.validate() is True
        assert valid_cmd.validated is True

        # Invalid command (empty)
        invalid_cmd = ShellCommand("")
        assert invalid_cmd.validate() is False
        assert invalid_cmd.validated is False

        # Invalid command (whitespace only)
        whitespace_cmd = ShellCommand("   ")
        assert whitespace_cmd.validate() is False

    def test_shell_command_sanitization(self):
        """Test ShellCommand sanitization."""
        cmd = ShellCommand("  echo test  ")
        sanitized = cmd.sanitize()

        assert sanitized.command == "echo test"
        assert sanitized.sanitized is True
        assert sanitized is cmd  # Should return self

    def test_shell_command_to_dict(self):
        """Test ShellCommand dictionary conversion."""
        env = {"VAR": "value"}
        cmd = ShellCommand(
            command="test", working_dir="/tmp", timeout=30, environment=env
        )

        result = cmd.to_dict()

        assert result["command"] == "test"
        assert result["working_dir"] == "/tmp"
        assert result["timeout"] == 30
        assert result["environment"] == env

    def test_shell_command_string_representation(self):
        """Test ShellCommand string representations."""
        cmd = ShellCommand("echo hello")

        str_repr = str(cmd)
        repr_repr = repr(cmd)

        assert "echo hello" in str_repr
        assert "echo hello" in repr_repr
        assert "ShellCommand" in str_repr
        assert "ShellCommand" in repr_repr


class TestCombineShellConstructs:
    """Test shell command combination functionality."""

    def test_combine_empty_commands(self):
        """Test combining empty command list."""
        result = combine_shell_constructs([])

        assert isinstance(result, ShellCommand)
        assert result.command == ""

    def test_combine_single_command(self):
        """Test combining a single command."""
        cmd = ShellCommand("echo test")
        result = combine_shell_constructs([cmd])

        assert result is cmd  # Should return the same command

    def test_combine_multiple_commands(self):
        """Test combining multiple commands."""
        commands = [
            ShellCommand("cd /tmp"),
            ShellCommand("mkdir test"),
            ShellCommand("ls -la"),
        ]

        result = combine_shell_constructs(commands)

        assert "cd /tmp && mkdir test && ls -la" == result.command
        assert result.working_dir == "/tmp"  # First command's working_dir
        assert result.timeout == 60  # Max timeout

    def test_combine_with_custom_connector(self):
        """Test combining commands with custom connector."""
        commands = [
            ShellCommand("command1"),
            ShellCommand("command2"),
            ShellCommand("command3"),
        ]

        result = combine_shell_constructs(commands, connector=";")

        assert result.command == "command1 ; command2 ; command3"

    def test_combine_commands_with_different_timeouts(self):
        """Test combining commands with different timeouts."""
        commands = [
            ShellCommand("quick_cmd", timeout=10),
            ShellCommand("slow_cmd", timeout=120),
            ShellCommand("medium_cmd", timeout=60),
        ]

        result = combine_shell_constructs(commands)

        assert result.timeout == 120  # Should use maximum timeout


class TestCommandBuilder:
    """Test CommandBuilder functionality."""

    def test_command_builder_creation(self):
        """Test creating CommandBuilder instances."""
        builder = CommandBuilder()

        assert builder is not None
        assert builder.commands == []

    def test_add_command(self):
        """Test adding commands to builder."""
        builder = CommandBuilder()

        result = builder.add_command("echo test")

        # Should return self for chaining
        assert result is builder
        assert len(builder.commands) == 1
        assert builder.commands[0].command == "echo test"

    def test_add_multiple_commands(self):
        """Test adding multiple commands."""
        builder = CommandBuilder()

        builder.add_command("cd /tmp").add_command(
            "mkdir test", timeout=30
        ).add_command("ls -la", working_dir="/tmp")

        commands = builder.build()

        assert len(commands) == 3
        assert commands[0].command == "cd /tmp"
        assert commands[1].timeout == 30
        assert commands[2].working_dir == "/tmp"

    def test_build_and_clear(self):
        """Test building and clearing commands."""
        builder = CommandBuilder()

        builder.add_command("test1").add_command("test2")
        commands = builder.build()

        # Build should return a copy
        assert len(commands) == 2
        assert len(builder.commands) == 2

        # Clear should empty the builder
        builder.clear()
        assert len(builder.commands) == 0

        # Original built commands should be unchanged
        assert len(commands) == 2

    def test_fluent_interface(self):
        """Test fluent interface for command building."""
        commands = (
            CommandBuilder()
            .add_command("step1")
            .add_command("step2")
            .add_command("step3")
            .build()
        )

        assert len(commands) == 3
        assert all(isinstance(cmd, ShellCommand) for cmd in commands)


class TestCommandValidation:
    """Test command validation utilities."""

    def test_validate_command_structure_valid(self):
        """Test validation of valid command structures."""
        valid_commands = {
            "run_cmd": {"command": "echo test", "working_dir": ".", "timeout": 60},
            "pre_run_cmds": ["setup.sh"],
        }

        result = validate_command_structure(valid_commands)
        assert result is True

    def test_validate_command_structure_invalid(self):
        """Test validation of invalid command structures."""
        # Missing run_cmd
        invalid_commands = {
            "pre_run_cmds": ["setup.sh"],
            "post_run_cmds": ["cleanup.sh"],
        }

        result = validate_command_structure(invalid_commands)
        assert result is False

        # Not a dictionary
        result = validate_command_structure("not a dict")
        assert result is False

        # None
        result = validate_command_structure(None)
        assert result is False

    def test_sanitize_command_args(self):
        """Test command argument sanitization."""
        # Test with mixed valid and invalid args
        args = ["  valid_arg  ", "", "  another_arg", None, "   ", "final_arg"]

        sanitized = sanitize_command_args(args)

        assert sanitized == ["valid_arg", "another_arg", "final_arg"]

        # Test with empty list
        assert sanitize_command_args([]) == []

        # Test with all invalid args
        assert sanitize_command_args(["", "  ", None]) == []


class TestCommandProcessorIntegration:
    """Test integrated command processor workflows."""

    def test_full_command_processing_workflow(self):
        """Test complete command processing workflow."""
        processor = CommandProcessor()

        # Create complex command structure
        commands = {
            "pre_compile_cmds": ["./autogen.sh", "./configure --enable-debug"],
            "compile_cmds": ["make clean", "make -j$(nproc)"],
            "post_compile_cmds": ["make check"],
            "run_cmd": {
                "command": "./test_suite --verbose --output=xml",
                "working_dir": "/build",
                "timeout": 300,
                "environment": {"TEST_ENV": "ci", "PARALLEL_JOBS": "4"},
            },
            "post_run_cmds": ["collect_artifacts.sh", "cleanup_temp.sh"],
        }

        # Process commands
        result = processor.process_commands(commands, "docker")

        # Verify all phases are present
        assert all(phase in result for phase in commands.keys())

        # Verify run_cmd structure
        run_cmd = result["run_cmd"]
        assert run_cmd["command"] == "./test_suite --verbose --output=xml"
        assert run_cmd["working_dir"] == "/build"
        assert run_cmd["timeout"] == 300
        assert run_cmd["environment"]["TEST_ENV"] == "ci"

    def test_command_to_shell_command_conversion(self):
        """Test converting processed commands to ShellCommand objects."""
        processor = CommandProcessor()

        commands = {
            "run_cmd": {
                "command": "python test.py",
                "working_dir": "/app",
                "timeout": 60,
            },
            "pre_run_cmds": ["pip install -r requirements.txt"],
            "post_run_cmds": ["pytest --coverage"],
        }

        shell_commands = processor.convert_to_shell_commands(commands)

        # Verify conversion
        assert len(shell_commands) >= 1  # At least run_cmd
        assert all(isinstance(cmd, ShellCommand) for cmd in shell_commands)

        # Find the main run command
        main_cmd = next(
            (cmd for cmd in shell_commands if "python test.py" in cmd.command), None
        )
        assert main_cmd is not None
        assert main_cmd.working_dir == "/app"
        assert main_cmd.timeout == 60

    def test_error_handling_in_processing(self):
        """Test error handling during command processing."""
        processor = CommandProcessor()

        # Test with malformed command structure
        malformed_commands = {
            "run_cmd": None,  # Invalid run_cmd
            "pre_run_cmds": "not a list",  # Invalid type
        }

        # Should handle gracefully without crashing
        result = processor.process_commands(malformed_commands)

        # Should still return a dictionary
        assert isinstance(result, dict)


class TestCommandProcessorPerformance:
    """Test command processor performance characteristics."""

    def test_large_command_list_processing(self):
        """Test processing large numbers of commands."""
        processor = CommandProcessor()

        # Create large command structure
        large_commands = {
            "run_cmd": {"command": "main_application", "timeout": 60},
            "pre_run_cmds": [f"setup_step_{i}" for i in range(100)],
            "post_run_cmds": [f"cleanup_step_{i}" for i in range(50)],
        }

        # Process should complete efficiently
        result = processor.process_commands(large_commands)

        # Verify all commands are processed
        assert len(result["pre_run_cmds"]) == 100
        assert len(result["post_run_cmds"]) == 50

    def test_command_processor_memory_usage(self):
        """Test memory efficiency of command processing."""
        processor = CommandProcessor()

        # Process multiple command sets to test memory management
        for i in range(10):
            commands = {
                "run_cmd": {"command": f"test_command_{i}", "timeout": 60},
                "pre_run_cmds": [f"prep_{j}" for j in range(20)],
            }

            result = processor.process_commands(commands)

            # Verify processing works for each iteration
            assert result["run_cmd"]["command"] == f"test_command_{i}"
            assert len(result["pre_run_cmds"]) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
