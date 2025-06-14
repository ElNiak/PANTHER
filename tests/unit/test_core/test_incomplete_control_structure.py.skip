#!/usr/bin/env python3
"""
Test for handling incomplete control structures in ShellCommand

This test verifies that the ShellCommand class properly handles and autocompletes
incomplete control structures like while loops that end with 'do' but have no body or 'done'.
"""

import unittest
from panther.core.command_processor.command import ShellCommand, format_multiline_command


class TestIncompleteControlStructures(unittest.TestCase):
    """Test case for handling incomplete control structures."""

    def test_incomplete_while_loop_ending_with_do(self):
        """Test handling of a while loop that ends with 'do' but no body or 'done'."""
        # This is the exact pattern from the error log
        command_str = "while [ ! -f /app/sync_logs/ivy_ready.log ]; do"

        # Create the shell command instance
        shell_cmd = ShellCommand.from_string(command_str)

        # Verify it's detected as a control structure
        self.assertTrue(shell_cmd.is_control_structure, "Should be detected as a control structure")

        # Make the command safe for execution
        shell_cmd.make_safe()

        # Verify it now contains both 'do' and 'done'
        self.assertIn("do", shell_cmd.command, "Command should contain 'do'")
        self.assertIn(
            "done",
            shell_cmd.command,
            "Command should contain 'done', indicating it was auto-completed",
        )

        # Verify it has a body (something between do and done)
        lines = shell_cmd.command.split("\n")
        do_line = -1
        done_line = -1

        for i, line in enumerate(lines):
            if "do" in line and "done" not in line:
                do_line = i
            if "done" in line:
                done_line = i

        # Check that there's at least one line between 'do' and 'done'
        self.assertGreater(
            done_line, do_line + 1, "Should have at least one line between 'do' and 'done'"
        )

    def test_format_multiline_command_autocompletes_while_loop(self):
        """Test that format_multiline_command properly autocompletes a while loop ending with 'do'."""
        # Same pattern from the error log
        command_str = "while [ ! -f /app/sync_logs/ivy_ready.log ]; do"

        # Format the command directly
        formatted = format_multiline_command(command_str)

        # Verify it contains both 'do' and 'done'
        self.assertIn("do", formatted, "Formatted command should contain 'do'")
        self.assertIn("done", formatted, "Formatted command should contain 'done'")

        # Verify it has a body with appropriate content for a file check
        self.assertIn(
            "Waiting for file", formatted, "Should include waiting for file message in the body"
        )


if __name__ == "__main__":
    unittest.main()
