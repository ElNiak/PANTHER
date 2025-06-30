#!/usr/bin/env python3
"""
Test script to verify that the fix for shell construct combination works.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.absolute()))

from panther.plugins.services.testers.panther_ivy.panther_ivy import PantherIvyServiceManager
from panther.config.core.models import ProtocolRole
from panther.plugins.services.testers.panther_ivy.config_schema import PantherIvyConfig


# Mock config objects for testing
class MockConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Create mock objects
protocol_config = MockConfig(name="quic", role=ProtocolRole.CLIENT)

service_config = PantherIvyConfig(
    test="test_command",
    use_system_models=True,
)


# Test function
def test_command_combination():
    """Test that commands are properly combined"""
    # Create a PantherIvyServiceManager instance with mock configs
    manager = PantherIvyServiceManager(
        service_config_to_test=service_config,
        service_type="test",
        protocol=protocol_config,
        implementation_name="test",
    )

    # Initialize with structured_commands
    manager.structured_commands = {
        "pre_compile": [],
        "compile": [],
        "post_compile": [],
        "pre_run": [],
        "run": [],
        "post_run": [],
    }

    # Override generate methods with test data
    manager.generate_pre_compile_commands = lambda: ["echo 'Pre-compile'"]
    manager.generate_compilation_commands = lambda: ["echo 'Starting compilation'", "make build"]
    manager.generate_post_compile_commands = lambda: ["echo 'Post-compile'"]

    # Call the method we fixed
    commands = manager.generate_compile_commands()

    # Print the result for inspection
    print("Generated commands:")
    for i, cmd in enumerate(commands):
        print(f"{i}: {repr(cmd)}")

    # Verify no commands contain standalone "&&"
    assert all("&&" != cmd.strip() for cmd in commands), "Found standalone '&&' command"

    # Verify the touch command is part of the last compilation command
    last_cmd = commands[-1]
    assert (
        "touch /app/sync_logs/ivy_ready.log" in last_cmd
    ), "Touch command missing from last compilation command"

    print("Test passed! Commands are properly combined.")
    return True


# Run the test
if __name__ == "__main__":
    test_command_combination()
