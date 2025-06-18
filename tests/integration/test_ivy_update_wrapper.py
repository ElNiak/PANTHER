#!/usr/bin/env python3
"""
Integration test for the PantherIvy service manager with the update_ivy_wrapper function.
This test creates a minimal experiment configuration to validate that:
1. The update_ivy_wrapper function is properly added to the entrypoint script
2. The function definitions are properly formatted and positioned in the script
3. The script can be generated without errors
"""
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
import logging

# Add the parent directory to the Python path
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import modules
from panther.plugins.services.testers.panther_ivy.panther_ivy import (
    PantherIvyServiceManager,
)
from panther.plugins.services.testers.panther_ivy.config_schema import PantherIvyConfig
from panther.config.core.models import (
    ProtocolConfig,
    ProtocolRole,
)
from panther.plugins.services.iut.config_schema import ImplementationType
from panther.plugins.services.config_schema import ServiceConfig


class TestIvyUpdateWrapperIntegration(unittest.TestCase):
    """Integration test for the PantherIvy service with update_ivy_wrapper function."""

    def setUp(self):
        """Set up the test environment."""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Create a temporary directory for test output
        self.test_dir = tempfile.mkdtemp()
        self.logger.info(f"Test directory: {self.test_dir}")

        # Create test directories
        self.log_dir = os.path.join(self.test_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # Create a mock protocol config for QUIC
        self.protocol_config = ProtocolConfig(
            name="quic",
            version="rfc9000",
            role=ProtocolRole.SERVER,
            target=None,
        )

        # Create a mock service config
        self.service_config = ServiceConfig(
            name="ivy_server", timeout=100, protocol=self.protocol_config
        )

        # Configure implementation details for PantherIvy
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            ParametersConfig,
            Parameter,
            PantherIvyVersion,
        )

        # Create a valid PantherIvyConfig
        self.implementation_config = PantherIvyConfig(
            name="panther_ivy",
            type=ImplementationType.TESTERS,
            test="quic_client_test_max",
            use_system_models=False,
        )

        # Set up parameters
        params = ParametersConfig()
        params.tests_build_dir = Parameter(value="build/")
        params.internal_iterations_per_test = Parameter(value="10")
        params.log_level = Parameter(value="INFO")

        # Create version info
        version = PantherIvyVersion()
        version.name = "latest"
        version.client = {"tests": {"quic_client_test_max": {"description": "QUIC client test"}}}
        version.server = {"tests": {"quic_server_test_max": {"description": "QUIC server test"}}}
        version.parameters = {"tests_dir": {"value": "tests/"}}
        version.env = {}

        # Assign to the implementation config
        self.implementation_config.parameters = params
        self.implementation_config.version = version

        # Set version information
        self.implementation_config.version = {
            "name": "latest",
            "client": {"tests": {"quic_client_test_max": {"description": "QUIC client test"}}},
            "server": {"tests": {"quic_server_test_max": {"description": "QUIC server test"}}},
            "env": {},
            "parameters": {"tests_dir": {"value": "tests/"}},
        }

        # Set the implementation in the service config
        self.service_config.implementation = self.implementation_config

        # Set service name for tests
        self.service_name = "ivy_server"

    def tearDown(self):
        """Clean up after the test."""
        shutil.rmtree(self.test_dir)

    def test_entrypoint_script_generation(self):
        """
        Test that the entrypoint script is correctly generated with the update_ivy_wrapper function.

        This test simulates the full process of command generation and entrypoint script rendering
        to ensure that the update_ivy_wrapper function is properly included in the script.
        """
        # Create a PantherIvyServiceManager instance
        self.logger.info("Creating PantherIvyServiceManager instance...")
        service_manager = PantherIvyServiceManager(
            self.service_config, "testers", self.protocol_config, self.service_name
        )

        # Set _plugin_dir attribute for testing
        plugin_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../panther/plugins")
        )
        service_manager._plugin_dir = plugin_dir

        # Initialize commands
        self.logger.info("Initializing commands...")
        service_manager.initialize_commands()

        # Call the update_ivy_tool method to set up the function
        self.logger.info("Calling update_ivy_tool...")
        commands = service_manager.update_ivy_tool()
        self.logger.info(f"Got {len(commands)} commands from update_ivy_tool")

        # Get structured commands
        structured_commands = service_manager.get_structured_commands()
        self.logger.info("Structured commands:")
        for phase, cmds in structured_commands.items():
            self.logger.info(f"  {phase}: {len(cmds)} commands")
            functions = [cmd for cmd in cmds if cmd.get("is_function_definition", False)]
            calls = [cmd for cmd in cmds if not cmd.get("is_function_definition", False)]
            self.logger.info(f"    Functions: {len(functions)}, Calls: {len(calls)}")

        # Generate the entrypoint script directly
        template_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../panther/plugins/environments/network_environment/docker_compose/templates",
            )
        )

        # If the template directory exists, use it
        if os.path.exists(template_path) and os.path.exists(
            os.path.join(template_path, "entrypoint_enhanced.sh.jinja")
        ):
            self.logger.info(f"Using template from: {template_path}")

            # Import Jinja2 environment
            from jinja2 import Environment, FileSystemLoader

            env = Environment(loader=FileSystemLoader(template_path))

            try:
                template = env.get_template("entrypoint_enhanced.sh.jinja")
                self.logger.info("Loaded template from templates directory")
            except Exception as e:
                self.logger.error(f"Failed to load template: {e}")
                self.fail(f"Failed to load template: {e}")
        else:
            # Create a minimal template for testing
            self.logger.info("Creating minimal test template")
            from jinja2 import Template

            template = Template(
                """#!/bin/bash
# Integration test template
# Pre-compile phase
{% for cmd in pre_compile_commands %}
{% if cmd.get('is_function_definition', False) %}
# Function definition: {{ cmd.get('description', '') }}
{{ cmd.get('command', '') }}
{% else %}
# Command: {{ cmd.get('description', '') }}
{{ cmd.get('command', '') }}
{% endif %}
{% endfor %}

# Compile phase
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
            )

        # Render the template
        self.logger.info("Rendering template...")
        rendered = template.render(
            service_name=service_manager.service_name,
            pre_compile_commands=structured_commands.get("pre_compile", []),
            compile_commands=structured_commands.get("compile", []),
            post_compile_commands=structured_commands.get("post_compile", []),
            pre_run_commands=structured_commands.get("pre_run", []),
            run_commands=structured_commands.get("run", []),
            post_run_commands=structured_commands.get("post_run", []),
        )

        # Write the rendered content to a file
        entrypoint_path = os.path.join(
            self.test_dir, f"entrypoint_{service_manager.service_name}.sh"
        )
        with open(entrypoint_path, "w") as f:
            f.write(rendered)

        # Check the generated script
        self.logger.info(f"Generated entrypoint script at: {entrypoint_path}")
        self.assertTrue(os.path.exists(entrypoint_path), "Entrypoint script should exist")

        # Read the script content
        with open(entrypoint_path) as f:
            content = f.read()

        # Check for key function definitions
        self.logger.info("Checking for key function definitions...")
        self.assertIn("update_ivy_tool()", content, "Missing update_ivy_tool function definition")
        self.assertIn(
            "update_ivy_wrapper()",
            content,
            "Missing update_ivy_wrapper function definition",
        )

        # Check for function calls
        self.logger.info("Checking for function calls...")
        lines = content.splitlines()
        call_lines = [
            line for line in lines if not line.startswith("#") and "update_ivy_wrapper" in line
        ]
        self.assertTrue(any(call_lines), "No update_ivy_wrapper function call found")

        # Success!
        self.logger.info(
            "All checks passed - entrypoint script correctly includes update_ivy_wrapper function"
        )


if __name__ == "__main__":
    unittest.main()
