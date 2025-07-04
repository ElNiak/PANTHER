"""Integration tests for the MCP Server."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

from atlas_commands.server import server, EnhancedAtlasCommandsServer
from atlas_commands.errors import AtlasCommandError


class TestServerIntegration:
    """Integration tests for the complete MCP server."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initialization and tool listing."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # List available tools
        tools = await atlas_server.list_tools()
        
        assert len(tools) == 10
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "create_unified_checklist",
            "update_checklist_item",
            "get_checklist_progress",
            "create_todowrite_integration",
            "create_memory_entity",
            "create_workflow",
            "validate_command",
            "track_command_pattern",
            "get_pattern_recommendations",
            "compact_memory_graph"
        ]
        
        for expected in expected_tools:
            assert expected in tool_names
    
    @pytest.mark.asyncio
    async def test_create_checklist_flow(self, sample_checklist_items):
        """Test complete checklist creation flow."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Create checklist
        create_args = {
            "command_name": "plan",
            "task_id": "integration-test-123",
            "items": sample_checklist_items
        }
        
        create_result = await atlas_server.call_tool("create_unified_checklist", create_args)
        
        assert create_result[0]["checklist_id"] == "plan_integration-test-123"
        assert create_result[0]["item_count"] == 3
        
        # Update item
        update_args = {
            "checklist_id": create_result[0]["checklist_id"],
            "item_id": "item-1",
            "status": "COMPLETED"
        }
        
        update_result = await atlas_server.call_tool("update_checklist_item", update_args)
        
        assert update_result[0]["success"] is True
        assert update_result[0]["new_status"] == "COMPLETED"
        
        # Get progress
        progress_args = {
            "checklist_id": create_result[0]["checklist_id"]
        }
        
        progress_result = await atlas_server.call_tool("get_checklist_progress", progress_args)
        
        assert progress_result[0]["completed"] == 1
        assert progress_result[0]["total"] == 3
    
    @pytest.mark.asyncio
    async def test_workflow_creation_and_validation(self, sample_workflow_steps):
        """Test workflow creation and command validation."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Create workflow
        workflow_args = {
            "workflow_id": "test-workflow-integration",
            "pattern": "explore-plan-code-commit",
            "target": "integration-feature",
            "steps": sample_workflow_steps
        }
        
        workflow_result = await atlas_server.call_tool("create_workflow", workflow_args)
        
        assert workflow_result[0]["workflow_id"] == "test-workflow-integration"
        assert workflow_result[0]["step_count"] == 3
        
        # Validate command
        validate_args = {
            "command": "plan",
            "parameters": {
                "task_type": "feature",
                "description": "Test feature"
            }
        }
        
        validate_result = await atlas_server.call_tool("validate_command", validate_args)
        
        assert validate_result[0]["valid"] is True
        assert validate_result[0]["can_execute"] is True
    
    @pytest.mark.asyncio
    async def test_memory_integration(self):
        """Test memory graph integration."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Create memory entity
        entity_args = {
            "command_type": "analyze",
            "target": "performance-bottleneck",
            "observations": [
                "Database queries taking 2s+",
                "N+1 query pattern detected",
                "Missing index on user_id column"
            ]
        }
        
        entity_result = await atlas_server.call_tool("create_memory_entity", entity_args)
        
        assert "entity_name" in entity_result[0]
        assert entity_result[0]["observation_count"] == 3
        
        # Create another entity
        entity2_args = {
            "command_type": "execute",
            "target": "performance-bottleneck",
            "observations": ["Added database index", "Query time reduced to 50ms"]
        }
        
        entity2_result = await atlas_server.call_tool("create_memory_entity", entity2_args)
        
        # Add relation
        relation_args = {
            "from_entity": entity_result[0]["entity_name"],
            "to_entity": entity2_result[0]["entity_name"],
            "relation_type": "solved_by"
        }
        
        relation_result = await atlas_server.call_tool("add_memory_relation", relation_args)
        
        assert relation_result[0]["success"] is True
        
        # Search patterns
        search_args = {
            "command_type": "analyze",
            "target_pattern": "performance"
        }
        
        search_result = await atlas_server.call_tool("search_memory_patterns", search_args)
        
        assert len(search_result[0]["entities"]) > 0
    
    @pytest.mark.asyncio
    async def test_pattern_tracking(self):
        """Test command pattern tracking."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Track successful pattern
        track_args = {
            "command": "execute",
            "target": "feature-implementation",
            "outcome": "success",
            "duration": 180.5,
            "observations": [
                "Implemented core functionality",
                "All tests passing",
                "Code coverage at 85%"
            ]
        }
        
        track_result = await atlas_server.call_tool("track_command_pattern", track_args)
        
        assert track_result[0]["tracked"] is True
        assert "pattern_id" in track_result[0]
        
        # Track failure pattern
        failure_args = {
            "command": "execute",
            "target": "complex-refactor",
            "outcome": "failure",
            "duration": 45.0,
            "observations": ["Tests failing", "Circular dependency detected"]
        }
        
        failure_result = await atlas_server.call_tool("track_command_pattern", failure_args)
        
        assert failure_result[0]["tracked"] is True
    
    @pytest.mark.asyncio
    async def test_todowrite_sync(self, sample_checklist_items):
        """Test TodoWrite synchronization."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Create checklist first
        checklist_args = {
            "command_name": "execute",
            "task_id": "todo-sync-test",
            "items": sample_checklist_items
        }
        
        checklist_result = await atlas_server.call_tool("create_unified_checklist", checklist_args)
        
        # Sync to TodoWrite
        sync_args = {
            "checklist_id": checklist_result[0]["checklist_id"],
            "command": "execute"
        }
        
        sync_result = await atlas_server.call_tool("sync_checklist_to_todos", sync_args)
        
        assert sync_result[0]["success"] is True
        assert sync_result[0]["todos_created"] == 3
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test server error handling."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Invalid tool name
        with pytest.raises(ValueError):
            await atlas_server.call_tool("invalid_tool_name", {})
        
        # Missing required arguments
        result = await atlas_server.call_tool("update_checklist_item", {})
        
        # Should return error in result
        assert isinstance(result[0], dict)
        assert "error" in result[0]
        assert "checklist_id is required" in result[0]["error"]
    
    @pytest.mark.asyncio
    async def test_resource_monitoring(self):
        """Test resource monitoring during operations."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Check initial resource state
        initial_usage = atlas_server.resource_monitor.get_current_usage()
        assert initial_usage.memory_mb > 0
        
        # Perform memory-intensive operation
        large_items = [
            {
                "id": f"item-{i}",
                "title": f"Task {i} with long description " * 100,
                "status": "PENDING"
            }
            for i in range(100)
        ]
        
        args = {
            "command_name": "plan",
            "task_id": "memory-test",
            "items": large_items
        }
        
        # Operation should track resources
        result = await atlas_server.call_tool("create_unified_checklist", args)
        
        # Check resource usage increased
        final_usage = atlas_server.resource_monitor.get_current_usage()
        assert len(atlas_server.resource_monitor.usage_history) > 1
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test handling concurrent tool calls."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Create multiple operations concurrently
        tasks = []
        
        for i in range(5):
            args = {
                "command_name": "plan",
                "task_id": f"concurrent-{i}",
                "template_type": "standard"
            }
            task = atlas_server.call_tool("create_unified_checklist", args)
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        assert all(r[0].get("checklist_id") for r in results)
        
        # All should have unique IDs
        ids = [r[0]["checklist_id"] for r in results]
        assert len(set(ids)) == 5
    
    @pytest.mark.asyncio
    async def test_validation_with_auto_fix(self):
        """Test validation with auto-fix functionality."""
        atlas_server = EnhancedAtlasCommandsServer()
        
        # Invalid task ID format
        args = {
            "command_name": "plan",
            "task_id": "invalid task id!!!",  # Bad format
            "template_type": "standard"
        }
        
        # Should auto-fix and succeed
        result = await atlas_server.call_tool("create_unified_checklist", args)
        
        assert "checklist_id" in result[0]
        # Task ID should be fixed
        assert "invalid-task-id" in result[0]["checklist_id"]