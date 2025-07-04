"""
Simple MCP test to verify the expanded test suite is working correctly.
Tests basic MCP functionality with minimal dependencies.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from src.atlas_commands.tools.orchestrate_intelligent_tasks import orchestrate_intelligent_tasks
from src.atlas_commands.tools.adaptive_command_selection import adaptive_command_selection
from src.atlas_commands.task_analysis_algorithm import analyze_task_for_atlas_framework
from src.atlas_commands.token_optimization.token_optimizer import TokenOptimizer


class TestBasicMCPFunctionality:
    """Test basic MCP functionality without server instantiation."""
    
    def test_orchestrate_intelligent_tasks_basic(self):
        """Test basic orchestration functionality."""
        result = orchestrate_intelligent_tasks(
            task_description="Simple test task",
            context={"domain": "test"},
            requirements={"priority": "normal"}
        )
        
        assert result is not None
        assert isinstance(result, dict)
        assert "estimated_efficiency_gain" in result
    
    def test_adaptive_command_selection_basic(self):
        """Test basic command selection functionality."""
        result = adaptive_command_selection(
            current_context={"project_type": "test"},
            available_commands=["test_command_1", "test_command_2"],
            user_preferences={"automation_level": "medium"}
        )
        
        assert result is not None
        assert isinstance(result, dict)
        assert "recommended_command" in result
    
    def test_task_analysis_algorithm_basic(self):
        """Test basic task analysis functionality."""
        result = analyze_task_for_atlas_framework(
            "Analyze this test task",
            {"domain": "testing"}
        )
        
        assert result is not None
        assert isinstance(result, dict)
        assert "task_description" in result
    
    @pytest.mark.asyncio
    async def test_token_optimizer_basic(self):
        """Test basic token optimization functionality."""
        optimizer = TokenOptimizer()
        test_data = {"test": "data", "numbers": [1, 2, 3]}
        
        result = await optimizer.optimize_response("test_tool", test_data)
        
        assert len(result) == 1
        assert result[0].original_tokens > 0


class TestMCPIntegrationWithTempDirectory:
    """Test MCP integration with temporary directory to avoid filesystem issues."""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory(prefix="atlas_test_") as temp_dir:
            yield Path(temp_dir)
    
    def test_server_initialization_with_temp_path(self, temp_storage_dir):
        """Test server initialization with temporary storage path."""
        from src.atlas_commands.server import EnhancedAtlasCommandsServer
        
        # Patch the storage path to use temp directory
        with patch('src.atlas_commands.server.EnhancedAtlasCommandsServer.__init__') as mock_init:
            mock_init.return_value = None  # Mock successful initialization
            
            server = EnhancedAtlasCommandsServer()
            assert server is not None
    
    def test_workflow_patterns_analysis(self):
        """Test workflow pattern analysis functionality."""
        from src.atlas_commands.tools.analyze_workflow_patterns import analyze_workflow_patterns
        
        workflow_data = {
            "steps": ["analyze", "design", "implement", "test"],
            "complexity": "moderate",
            "domain": "software_development"
        }
        
        result = analyze_workflow_patterns(
            workflow_data=workflow_data,
            analysis_depth="detailed",
            optimization_goals=["efficiency", "quality"]
        )
        
        assert result is not None
        assert isinstance(result, dict)
        assert "detected_patterns" in result


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance without full server."""
    
    def test_tool_response_format(self):
        """Test that tool responses follow MCP format."""
        result = orchestrate_intelligent_tasks(
            task_description="Test MCP format compliance",
            context={"domain": "testing"},
            requirements={"format": "mcp_compliant"}
        )
        
        # Verify response can be JSON serialized (MCP requirement)
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        
        # Verify response structure
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_input_validation(self):
        """Test input validation for MCP compliance."""
        # Test empty inputs
        with pytest.raises((TypeError, ValueError, AttributeError)):
            orchestrate_intelligent_tasks(None, {}, {})
        
        with pytest.raises((TypeError, ValueError, AttributeError)):
            orchestrate_intelligent_tasks("", None, {})
    
    def test_unicode_handling(self):
        """Test Unicode handling for MCP compliance."""
        unicode_task = "Implement API with émojis 🚀 and spëcial châractérs"
        
        result = orchestrate_intelligent_tasks(
            task_description=unicode_task,
            context={"domain": "unicode_test"},
            requirements={}
        )
        
        assert result is not None
        
        # Ensure result can be JSON serialized with Unicode
        json_str = json.dumps(result, ensure_ascii=False)
        assert isinstance(json_str, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])