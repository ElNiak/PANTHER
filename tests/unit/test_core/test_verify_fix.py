#!/usr/bin/env python3
"""Test script to verify that the fix for shell construct combination works.

Uses unittest.mock to patch the deep initialization chain and test only
the command generation logic in PantherIvyServiceManager.
"""
import logging
from unittest.mock import MagicMock, patch

import pytest

logger = logging.getLogger("test_verify_fix")

# Test imports - skip if modules not available
try:
    from panther.plugins.services.service_manager_mixin import ServiceManagerMixin
    from panther.plugins.services.testers.panther_ivy.panther_ivy import (
        PantherIvyServiceManager,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    logger.warning(f"Skipping test_verify_fix: {e}")


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="PantherIvy modules not available")
def test_command_combination():
    """Test that commands are properly combined without standalone '&&'."""
    # Create instance without triggering full init chain
    with patch.object(PantherIvyServiceManager, "__init__", lambda self, **kw: None):
        manager = PantherIvyServiceManager.__new__(PantherIvyServiceManager)

    # Set up minimal attributes needed by generate_compile_commands
    manager.structured_commands = {
        "pre_compile": [],
        "compile": [],
        "post_compile": [],
        "pre_run": [],
        "run": [],
        "post_run": [],
    }
    manager.service_name = "test_ivy"
    manager._logger = logger

    # Mock the methods called by generate_compile_commands
    base_commands = ["echo 'Pre-compile'", "echo 'Starting compilation'", "make build"]
    manager.generate_ivy_compile_commands = MagicMock(return_value=base_commands)
    manager.handle_error = MagicMock()

    # Patch the parent class method that super().generate_compile_commands() resolves to
    with patch.object(
        ServiceManagerMixin, "generate_compile_commands", return_value=[]
    ):
        commands = manager.generate_compile_commands()

    # Verify no commands contain standalone "&&"
    for cmd in commands:
        cmd_str = str(cmd).strip()
        assert cmd_str != "&&", f"Found standalone '&&' command: {repr(cmd)}"

    # Verify we got commands back
    assert len(commands) > 0, "Should generate at least one command"
