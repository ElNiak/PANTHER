#!/usr/bin/env python3
"""
Test script to directly verify our fix to the generate_compile_commands method.
"""
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_fix")

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.absolute()))

import pytest

# Test imports - skip if modules not available
try:
    from panther.config.core.models import ProtocolConfig, ProtocolRole
    from panther.plugins.services.testers.panther_ivy.config_schema import (
        PantherIvyConfig,
    )
    from panther.plugins.services.testers.panther_ivy.panther_ivy import (
        PantherIvyServiceManager,
    )

    IMPORTS_AVAILABLE = True
    logger.info("Successfully imported all required modules")
except ImportError as e:
    IMPORTS_AVAILABLE = False
    logger.error(f"Error importing required modules: {e}")

    # Create dummy class for test structure
    class PantherIvyServiceManager:
        pass


# Create a simple subclass for testing
class TestPantherIvy(PantherIvyServiceManager):
    def __init__(self):
        # Skip the full initialization, just set up what we need
        self.structured_commands = {
            "pre_compile": [],
            "compile": [],
            "post_compile": [],
            "pre_run": [],
            "run": [],
            "post_run": [],
        }
        self.service_name = "test_ivy"
        self.logger = logger

    def super_generate_compile_commands(self):
        return ["echo 'Base command 1'", "echo 'Base command 2'"]

    def generate_compilation_commands(self):
        return ["echo 'Compilation command 1'", "echo 'Compilation command 2'"]


def test_compile_commands():
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required modules not available")

    # Create test instance
    ivy_manager = TestPantherIvy()

    # Override super() for testing
    ivy_manager.super_generate_compile_commands = (
        ivy_manager.super_generate_compile_commands
    )

    # Test the fixed method
    commands = ivy_manager.generate_compile_commands()

    # Print the commands
    logger.info(f"Generated {len(commands)} compile commands:")
    for i, cmd in enumerate(commands):
        logger.info(f"Command {i}: {cmd}")

    # Check if the touch command was integrated into the last compile command
    last_command = commands[-1]
    logger.info(f"Last command: {last_command}")

    # Verify the touch command is present
    if "touch /app/sync_logs/ivy_ready.log" in last_command:
        logger.info(
            "The fix works! Touch command is properly included in the last compile command."
        )
        return True
    else:
        logger.error("Fix failed: Touch command not found in the generated commands.")
        return False


if __name__ == "__main__":
    # Override the PantherIvyServiceManager's generate_compile_commands with our own implementation
    # to avoid calling super()
    orig_method = PantherIvyServiceManager.generate_compile_commands

    def patched_super(self):
        return ["echo 'Base command 1'", "echo 'Base command 2'"]

    PantherIvyServiceManager.super_generate_compile_commands = patched_super

    success = test_compile_commands()
    sys.exit(0 if success else 1)
