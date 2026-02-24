#!/usr/bin/env python3
"""
Test script to verify the fix to PantherIvy's generate_compile_commands method.

Uses unittest.mock to patch the deep initialization chain and test only
the command generation logic.
"""
import logging
from unittest.mock import MagicMock, patch

import pytest

logger = logging.getLogger("test_fix")

# Test imports - skip if modules not available
try:
    from panther.plugins.services.service_manager_mixin import ServiceManagerMixin
    from panther.plugins.services.testers.panther_ivy.panther_ivy import (
        PantherIvyServiceManager,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    logger.warning(f"Skipping test_fix_directly: {e}")


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="PantherIvy modules not available")
def test_compile_commands():
    """Test that generate_compile_commands properly combines commands."""
    # Create instance without triggering full init chain
    with patch.object(PantherIvyServiceManager, "__init__", lambda self, **kw: None):
        ivy_manager = PantherIvyServiceManager.__new__(PantherIvyServiceManager)

    # Set up minimal attributes needed by generate_compile_commands
    ivy_manager.structured_commands = {
        "pre_compile": [],
        "compile": [],
        "post_compile": [],
        "pre_run": [],
        "run": [],
        "post_run": [],
    }
    ivy_manager.service_name = "test_ivy"
    ivy_manager._logger = logger

    # Mock the dependencies that generate_compile_commands uses
    ivy_commands = ["echo 'Compilation command 1'", "echo 'Compilation command 2'"]
    ivy_manager.generate_ivy_compile_commands = MagicMock(return_value=ivy_commands)
    ivy_manager.handle_error = MagicMock()

    # Patch the parent class method that super().generate_compile_commands() resolves to
    with patch.object(
        ServiceManagerMixin, "generate_compile_commands", return_value=[]
    ):
        commands = ivy_manager.generate_compile_commands()

    # Verify we got commands back
    assert len(commands) > 0, "Should generate at least one command"

    # Verify the ivy compile commands method was called
    ivy_manager.generate_ivy_compile_commands.assert_called_once()
