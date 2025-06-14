import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from panther.plugins.services.testers.panther_ivy.panther_ivy import (
    PantherIvyServiceManager,
    InvalidCommandFormatError,
    is_func_def,
)


class TestPantherIvyCommands(unittest.TestCase):

    def test_is_func_def_with_valid_bool(self):
        """Test is_func_def with valid boolean flags."""
        cmd_true = {"is_function_definition": True, "command": "func() { echo hi; }"}
        cmd_false = {"is_function_definition": False, "command": "echo hi"}

        self.assertTrue(is_func_def(cmd_true))
        self.assertFalse(is_func_def(cmd_false))

    def test_is_func_def_with_missing_key(self):
        """Test is_func_def with missing is_function_definition key."""
        cmd_missing = {"command": "echo hi"}

        with self.assertRaises(InvalidCommandFormatError) as context:
            is_func_def(cmd_missing)

        self.assertIn("Missing is_function_definition flag", str(context.exception))

    def test_is_func_def_with_wrong_type(self):
        """Test is_func_def with non-boolean is_function_definition."""
        cmd_string = {"is_function_definition": "yes", "command": "echo hi"}

        with self.assertRaises(InvalidCommandFormatError) as context:
            is_func_def(cmd_string)

        self.assertIn("is_function_definition must be a bool", str(context.exception))

    @patch(
        "panther.plugins.services.testers.panther_ivy.panther_ivy.PantherIvyServiceManager._load_service_config"
    )
    @patch(
        "panther.plugins.services.testers.panther_ivy.panther_ivy.PantherIvyServiceManager._load_tests"
    )
    def test_add_command_flag_validation(self, mock_load_tests, mock_load_config):
        """Test add_command validates boolean flag types."""
        # Setup mock service manager
        mock_service_config = MagicMock()
        mock_service_config.name = "test_service"
        mock_service_config.implementation.parameters.log_level = "debug"

        manager = PantherIvyServiceManager(
            service_config_to_test=mock_service_config,
            service_type="test_type",
            protocol=MagicMock(),
            implementation_name="test_impl",
        )

        # Initialize structured_commands
        manager.structured_commands = {
            "compile": [],
            "pre_compile": [],
            "post_compile": [],
            "pre_run": [],
            "run": [],
            "post_run": [],
        }

        # Test with valid bool flags
        manager.add_command(
            phase="compile", command="func() { echo hi; }", is_function_definition=True
        )
        self.assertTrue(manager.structured_commands["compile"][0]["is_function_definition"])

        # Test with non-bool is_function_definition
        with self.assertRaises(TypeError):
            manager.add_command(
                phase="compile", command="echo hi", is_function_definition="yes"  # Wrong type
            )

        # Test with non-bool is_multiline
        with self.assertRaises(TypeError):
            manager.add_command(
                phase="compile", command="echo hi", is_multiline="yes"  # Wrong type
            )

        # Test with non-bool is_critical
        with self.assertRaises(TypeError):
            manager.add_command(phase="compile", command="echo hi", is_critical="yes")  # Wrong type


if __name__ == "__main__":
    unittest.main()
