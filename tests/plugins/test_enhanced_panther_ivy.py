#!/usr/bin/env python3
"""
Test module for the enhanced PantherIvy service implementation
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from panther.config.core.models import (
    ImplementationType,
    ProtocolConfig,
    ProtocolRole,
    ServiceConfig,
)
from panther.plugins.services.testers.panther_ivy.config_schema import PantherIvyConfig

# Import the necessary modules
from panther.plugins.services.testers.panther_ivy.panther_ivy import (
    PantherIvyServiceManager,
)


class TestEnhancedPantherIvy(unittest.TestCase):
    """Test cases for the enhanced PantherIvy service implementation."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for test output
        self.test_dir = tempfile.mkdtemp()

        # Create a mock protocol config
        self.protocol_config = ProtocolConfig(
            name="quic",
            version="rfc9000",
            role=ProtocolRole.SERVER,
            target=None,
        )

        # Create a mock ServiceConfig with a PantherIvyConfig implementation
        self.service_config = ServiceConfig(
            name="ivy_server", timeout=100, protocol=self.protocol_config
        )

        # Configure implementation details for PantherIvy
        self.service_config.implementation = {
            "name": "panther_ivy",
            "type": "testers",
            "test": "quic_client_test_max",
            "use_system_models": False,
            "parameters": {
                "tests_build_dir": {"value": "build/"},
                "internal_iterations_per_test": {"value": 10},
                "log_level": "INFO",
            },
        }

        # Create a PantherIvyConfig as the implementation
        self.implementation_config = PantherIvyConfig(
            name="panther_ivy",
            type=ImplementationType.TESTERS,
            test="quic_client_test_max",
            use_system_models=False,
        )

        # Set the implementation in the service config
        self.service_config.implementation = self.implementation_config

        # Set service name for tests
        self.service_name = "ivy_server"

    def tearDown(self):
        """Clean up after the test."""
        shutil.rmtree(self.test_dir)

    def test_update_ivy_tool(self):
        """Test the update_ivy_tool method and ensure it defines the update_ivy_wrapper function."""
        # Create a PantherIvyServiceManager instance
        service_manager = PantherIvyServiceManager(
            self.service_config, "testers", self.protocol_config, self.service_name
        )

        # Set _plugin_dir attribute for testing
        service_manager._plugin_dir = os.path.dirname(os.path.abspath(__file__))

        # Initialize commands
        service_manager.initialize_commands()

        # Call the update_ivy_tool method
        print("\nCalling update_ivy_tool...")
        result = service_manager.update_ivy_tool()
        print(f"Returned {len(result)} commands")

        # Verify that the update_ivy_wrapper function is defined
        commands = service_manager.get_structured_commands()

        # Debug: print all commands
        print("\nStructured commands:")
        for phase, cmds in commands.items():
            print(f"  {phase}: {len(cmds)} commands")
            functions_in_phase = [
                cmd for cmd in cmds if cmd.get("is_function_definition", False)
            ]
            calls_in_phase = [
                cmd for cmd in cmds if not cmd.get("is_function_definition", False)
            ]
            print(f"    Functions: {len(functions_in_phase)}")
            print(f"    Calls: {len(calls_in_phase)}")

            # Print function details
            for i, cmd in enumerate(
                functions_in_phase[:3]
            ):  # Limit to first 3 to avoid verbose output
                name = (
                    cmd.get("description", "")
                    if cmd.get("description", "")
                    else "Unknown function"
                )
                print(f"      Function {i+1}: {name}")

            # Print call details
            for i, cmd in enumerate(
                calls_in_phase[:3]
            ):  # Limit to first 3 to avoid verbose output
                print(f"      Call {i+1}: {cmd.get('command', '')}")

        # Check if the update_ivy_wrapper function is defined in any phase
        function_defined_pre_compile = False
        function_defined_compile = False
        function_called = False
        update_ivy_defined = False

        # Check pre_compile phase for function definitions
        for command in commands.get("pre_compile", []):
            if command.get("is_function_definition", False):
                if "update_ivy_wrapper" in command.get("command", ""):
                    function_defined_pre_compile = True
                    print("Found update_ivy_wrapper function definition in pre_compile")
                elif "update_ivy_tool" in command.get("command", ""):
                    update_ivy_defined = True
                    print("Found update_ivy_tool function definition in pre_compile")

        # Check compile phase for function definitions and calls
        for command in commands.get("compile", []):
            if command.get(
                "is_function_definition", False
            ) and "update_ivy_wrapper" in command.get("command", ""):
                function_defined_compile = True
                print("Found update_ivy_wrapper function definition in compile")
            elif not command.get(
                "is_function_definition", False
            ) and "update_ivy_wrapper" in command.get("command", ""):
                function_called = True
                print(
                    f"Found update_ivy_wrapper function call in compile: {command.get('command', '')}"
                )

        self.assertTrue(
            update_ivy_defined, "update_ivy_tool function should be defined"
        )
        self.assertTrue(
            function_defined_pre_compile,
            "update_ivy_wrapper function should be defined in pre_compile phase",
        )
        self.assertTrue(
            function_defined_compile,
            "update_ivy_wrapper function should be defined in compile phase",
        )
        self.assertTrue(function_called, "update_ivy_wrapper function should be called")

        # Verify there are commands in each phase
        for phase in ["pre_compile", "compile"]:
            self.assertGreater(
                len(commands.get(phase, [])),
                0,
                f"There should be commands in the {phase} phase",
            )

    def test_generate_entrypoint_script(self):
        """Test that the structured commands can be rendered into an entrypoint script."""
        # Create a PantherIvyServiceManager instance
        service_manager = PantherIvyServiceManager(
            self.service_config, "testers", self.protocol_config, self.service_name
        )

        # Set _plugin_dir attribute for testing
        service_manager._plugin_dir = os.path.dirname(os.path.abspath(__file__))

        # Initialize the commands
        service_manager.initialize_commands()

        # Call the update_ivy_tool method to set up the function
        service_manager.update_ivy_tool()

        # Get the structured commands
        commands = service_manager.get_structured_commands()

        # Debug information
        print("\nTesting direct template rendering")
        print(f"Pre-compile commands: {len(commands['pre_compile'])}")
        print(f"Compile commands: {len(commands['compile'])}")

        # Create a Jinja2 template directly for testing
        from jinja2 import Template

        template_str = """#!/bin/bash
# Test template for unit tests
{% for cmd in pre_compile_commands %}
{% if cmd.get('is_function_definition', False) %}
# Function definition: {{ cmd.get('description', '') }}
{{ cmd.get('command', '') }}
{% else %}
# Command: {{ cmd.get('description', '') }}
{{ cmd.get('command', '') }}
{% endif %}
{% endfor %}

{% for cmd in compile_commands %}
{% if cmd.get('is_function_definition', False) %}
# Function definition: {{ cmd.get('description', '') }}
{{ cmd.get('command', '') }}
{% else %}
# Command: {{ cmd.get('description', '') }}
{{ cmd.get('command', '') }}
{% endif %}
{% endfor %}
"""
        template = Template(template_str)

        # Render the template directly
        rendered = template.render(
            service_name=service_manager.service_name,
            pre_compile_commands=commands.get("pre_compile", []),
            compile_commands=commands.get("compile", []),
        )

        # Write to a file
        entrypoint_path = os.path.join(self.test_dir, "test_entrypoint.sh")
        with open(entrypoint_path, "w") as f:
            f.write(rendered)

        # Check that the entrypoint script was created
        self.assertTrue(
            os.path.exists(entrypoint_path),
            f"Entrypoint script should be created at {entrypoint_path}",
        )

        # Read the entrypoint script and check for the update_ivy_wrapper function
        with open(entrypoint_path) as f:
            content = f.read()
            print(f"Entrypoint script content preview:\n{content[:300]}...")
            self.assertIn(
                "update_ivy_wrapper",
                content,
                "Entrypoint script should contain the update_ivy_wrapper function",
            )

        # Verify that functions and their calls are in the script
        with open(entrypoint_path) as f:
            content = f.read()
            # Check for function definitions
            self.assertTrue(
                "update_ivy_tool" in content and "()" in content,
                "Script should contain update_ivy_tool function definition",
            )
            self.assertTrue(
                "update_ivy_wrapper" in content and "()" in content,
                "Script should contain update_ivy_wrapper function definition",
            )

            # Check for function calls - make sure the command calls exist separately from definitions
            function_defs = [
                line for line in content.splitlines() if "Function definition" in line
            ]
            command_calls = [
                line for line in content.splitlines() if "Command:" in line
            ]

            print(f"\nFound {len(function_defs)} function definitions")
            print(f"Found {len(command_calls)} command calls")

            self.assertGreater(
                len(function_defs), 0, "Script should contain function definitions"
            )
            self.assertGreater(
                len(command_calls), 0, "Script should contain command calls"
            )


if __name__ in {"__main__", "__mp_main__"}:
    unittest.main()
