#!/usr/bin/env python3
"""
Test script to verify the fix for the incomplete while loop issue.
"""

from panther.core.command_processor.command import ShellCommand

# The incomplete while loop from the error
incomplete_while = "while [ ! -f /app/sync_logs/ivy_ready.log ]; do"

# Create a ShellCommand instance
cmd = ShellCommand.from_string(incomplete_while)
print(f"Original command: {incomplete_while}")
print(f"Is control structure: {cmd.is_control_structure}")

# Get shell-safe version for execution
safe_command = cmd.get_shell_safe_command()
print("\nShell-safe command:")
print(f"Command: {safe_command}")
print(f"Is multiline: {cmd.is_multiline}")

# Print the final command that would be executed
print("\nThis would be executed in the shell:")
print("-" * 40)
print(safe_command)
print("-" * 40)

# Check if 'done' is included in the auto-completed command
if "done" in cmd.command:
    print("\nSUCCESS: The incomplete while loop was auto-completed with 'done'")
else:
    print("\nFAILURE: The incomplete while loop was NOT properly auto-completed")
