"""Pytest configuration and fixtures for ATLAS Commands tests."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp(prefix="atlas_test_")
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_checklist_manager():
    """Create a mock checklist manager."""
    manager = Mock()
    manager.create_checklist.return_value = {
        "checklist_markdown": "## Test Checklist (0/3 complete)\n",
        "checklist_id": "test-checklist-123",
        "item_count": 3
    }
    manager.update_item.return_value = {
        "success": True,
        "checklist_id": "test-checklist-123",
        "item_id": "item-1",
        "new_status": "COMPLETED"
    }
    return manager


@pytest.fixture
def mock_todowrite():
    """Create a mock TodoWrite integration."""
    todowrite = Mock()
    todowrite.sync_checklist_to_todos.return_value = {
        "success": True,
        "todos_created": 3,
        "todos_updated": 0
    }
    return todowrite


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory graph manager."""
    manager = Mock()
    manager.create_workflow_entity.return_value = {
        "entity_name": "workflow_test_target_plan",
        "command_type": "plan",
        "target": "target",
        "observation_count": 2
    }
    return manager


@pytest.fixture
def mock_workflow_enforcer():
    """Create a mock workflow enforcer."""
    enforcer = Mock()
    enforcer.validate_command.return_value = {
        "valid": True,
        "can_execute": True,
        "warnings": []
    }
    return enforcer


@pytest.fixture
def sample_checklist_items():
    """Sample checklist items for testing."""
    return [
        {
            "id": "item-1",
            "title": "Initialize project",
            "status": "PENDING",
            "priority": "HIGH",
            "dependencies": []
        },
        {
            "id": "item-2",
            "title": "Write core implementation",
            "status": "PENDING",
            "priority": "HIGH",
            "dependencies": ["item-1"]
        },
        {
            "id": "item-3",
            "title": "Add tests",
            "status": "PENDING",
            "priority": "MEDIUM",
            "dependencies": ["item-2"]
        }
    ]


@pytest.fixture
def sample_workflow_steps():
    """Sample workflow steps for testing."""
    return [
        {
            "command": "explore",
            "target": "codebase structure",
            "description": "Understand the existing code"
        },
        {
            "command": "plan",
            "target": "refactoring strategy",
            "description": "Create detailed plan"
        },
        {
            "command": "code",
            "target": "implementation",
            "description": "Implement the changes"
        }
    ]


@pytest.fixture
def mock_mcp_context():
    """Create a mock MCP server context."""
    return {
        "request_id": "test-request-123",
        "session_id": "test-session-456",
        "user": "test-user"
    }


@pytest.fixture
def resource_monitor():
    """Create a resource monitor for testing."""
    return ResourceMonitor()


@pytest.fixture
def input_validator():
    """Create an input validator for testing."""
    return InputValidator()


@pytest.fixture
def output_validator():
    """Create an output validator for testing."""
    return OutputValidator()


@pytest.fixture
def error_recovery():
    """Create an error recovery handler for testing."""
    return ErrorRecovery()


@pytest.fixture
async def mcp_server():
    """Create an MCP server instance for testing."""
    # Mock the MCP transport
    with patch('atlas_commands.server.stdio_transport'):
        server = EnhancedAtlasCommandsServer()
        yield server


@pytest.fixture
def mock_memory_graph():
    """Mock memory graph responses."""
    return {
        "entities": [
            {
                "name": "workflow_test_target_plan",
                "type": "workflow_step",
                "observations": ["Planning phase completed", "3 subtasks identified"]
            }
        ],
        "relations": [
            {
                "from": "workflow_test_target_plan",
                "to": "workflow_test_target_execute",
                "type": "precedes"
            }
        ]
    }


@pytest.fixture
def performance_metrics():
    """Sample performance metrics for testing."""
    return {
        "operation_duration": 1.5,
        "memory_usage_mb": 45.2,
        "cpu_percent": 25.0,
        "success_rate": 0.95
    }