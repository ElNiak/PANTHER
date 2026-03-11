#!/usr/bin/env python3
"""Test script for the ShellCommand class with trailing control operators."""

from panther.core.command_processor import ShellCommand
from panther.core.command_processor.utils.shell_utils import normalize_command_ending


def test_normalize_command_ending():
    """Test the normalize_command_ending function."""
    # Test regular commands
    assert normalize_command_ending("ls -la") == "ls -la"
    assert normalize_command_ending("echo 'hello'") == "echo 'hello'"

    # Test commands with trailing operators
    assert normalize_command_ending("ls -la;") == "ls -la"
    assert normalize_command_ending("echo 'hello' &&") == "echo 'hello'"
    assert normalize_command_ending("find . -name '*.py' &") == "find . -name '*.py'"
    # Pipe is a valid operator, not stripped by normalize_command_ending
    assert (
        normalize_command_ending("grep 'pattern' file.txt |")
        == "grep 'pattern' file.txt |"
    )

    # Test commands with trailing whitespace and operators
    assert normalize_command_ending("ls -la; ") == "ls -la"
    assert normalize_command_ending("echo 'hello' && ") == "echo 'hello'"


def test_shell_command():
    """Test the ShellCommand class with various commands."""
    # Regular command
    cmd1 = ShellCommand("ls -la")
    cmd1.get_shell_safe_command()

    # Command with trailing semicolon
    cmd2 = ShellCommand("ls -la;")
    cmd2.get_shell_safe_command()

    # Command with trailing &&
    cmd3 = ShellCommand("echo 'test' &&")
    cmd3.get_shell_safe_command()

    # Command with trailing &
    cmd4 = ShellCommand("find . -name '*.py' &")
    cmd4.get_shell_safe_command()

    # Command with trailing pipe
    cmd5 = ShellCommand("grep 'pattern' file.txt |")
    cmd5.get_shell_safe_command()

    print("All commands after make_safe():")
    print(f"1. Regular command: {cmd1.command}")
    print(f"2. Command with trailing semicolon: {cmd2.command}")
    print(f"3. Command with trailing &&: {cmd3.command}")
    print(f"4. Command with trailing &: {cmd4.command}")
    print(f"5. Command with trailing pipe: {cmd5.command}")


if __name__ == "__main__":
    print("Testing normalize_command_ending function:")
    test_normalize_command_ending()
    print("\nAll normalize_command_ending tests passed!")

    print("\nTesting ShellCommand with trailing control operators:")
    test_shell_command()
