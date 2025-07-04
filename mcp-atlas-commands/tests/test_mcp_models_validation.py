"""
MCP Models Validation Tests
Tests our ATLAS MCP server capabilities using models following the official MCP Inspector patterns.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from atlas_commands.server import EnhancedAtlasCommandsServer


class TestMCPModelsValidation:
    """Test MCP server capabilities using models and capabilities validation."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mcp_server(self, temp_storage):
        """Create a properly mocked ATLAS MCP server for testing."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                server = EnhancedAtlasCommandsServer()
                yield server
    
    def test_mcp_server_capabilities_model(self, mcp_server):
        """Test server exposes standard MCP capabilities model."""
        # Based on MCP Inspector docs, servers should expose capabilities
        
        # Verify server has core MCP server instance
        assert hasattr(mcp_server, 'server')
        assert mcp_server.server is not None
        
        # Server should have a name (required MCP model field)
        assert hasattr(mcp_server.server, 'name')
        assert isinstance(mcp_server.server.name, str)
        assert mcp_server.server.name == "atlas-commands"
    
    def test_mcp_tools_model_compliance(self, mcp_server):
        """Test tools model compliance with MCP specification."""
        # The MCP Inspector validates tools through the Tools tab
        
        # ATLAS should have multiple tool categories
        tool_managers = [
            'checklist_manager',
            'todowrite_manager',
            'memory_manager',
            'workflow_enforcer',
            'adaptive_command_selector'
        ]
        
        for manager_name in tool_managers:
            assert hasattr(mcp_server, manager_name), f"Missing tool manager: {manager_name}"
            manager = getattr(mcp_server, manager_name)
            assert manager is not None, f"Tool manager {manager_name} is None"
    
    def test_mcp_resources_model_compliance(self, mcp_server):
        """Test resources model compliance with MCP specification."""
        # The MCP Inspector validates resources through the Resources tab
        
        # ATLAS should have resource management capabilities
        resource_components = [
            'storage_manager',
            'memory_manager',
            'pattern_tracker'
        ]
        
        for component_name in resource_components:
            assert hasattr(mcp_server, component_name), f"Missing resource component: {component_name}"
            component = getattr(mcp_server, component_name)
            assert component is not None, f"Resource component {component_name} is None"
    
    def test_mcp_notifications_model_compliance(self, mcp_server):
        """Test notifications model compliance with MCP specification."""
        # The MCP Inspector monitors notifications through the Notifications pane
        
        # ATLAS should have observability for notifications
        assert hasattr(mcp_server, 'observability')
        observability = mcp_server.observability
        assert observability is not None
        
        # Should have proper service identification
        assert hasattr(observability, 'service_name')
        assert hasattr(observability, 'service_version')
    
    def test_mcp_coordination_model_validation(self, mcp_server):
        """Test coordination model validation with 5 optimization features."""
        # ATLAS implements 5 coordination optimizations as models
        coordination_models = [
            ('compression_manager', 'CompressionManager'),
            ('saga_coordinator', 'SagaCoordinator'),
            ('entropy_processor', 'EntropyProcessor'),
            ('incremental_memory_manager', 'IncrementalMemoryManager'),
            ('concurrent_exporter', 'ConcurrentExporter')
        ]
        
        for attr_name, model_name in coordination_models:
            assert hasattr(mcp_server, attr_name), f"Missing coordination model: {model_name}"
            model_instance = getattr(mcp_server, attr_name)
            assert model_instance is not None, f"Coordination model {model_name} is None"
    
    def test_mcp_token_optimization_model(self, mcp_server):
        """Test token optimization model compliance."""
        # Verify token optimization functions work (the ones we fixed for Docker)
        from atlas_commands.token_optimization import (
            set_response_mode, 
            get_response_mode, 
            ResponseMode,
            TokenOptimizer,
            OptimizedResponse
        )
        
        # Test ResponseMode enum model
        assert hasattr(ResponseMode, 'COMPACT')
        assert hasattr(ResponseMode, 'STANDARD')
        assert hasattr(ResponseMode, 'MINIMAL')
        assert hasattr(ResponseMode, 'BALANCED')
        
        # Test global mode functions (the ones that fixed Docker error)
        original_mode = get_response_mode()
        set_response_mode(ResponseMode.COMPACT)
        assert get_response_mode() == ResponseMode.COMPACT
        
        # Reset to original
        set_response_mode(original_mode)
        
        # Test TokenOptimizer model
        optimizer = TokenOptimizer()
        assert optimizer is not None
        assert hasattr(optimizer, 'optimize_response')
        assert hasattr(optimizer, 'optimize_response_with_collider')
    
    def test_mcp_memory_model_integration(self, mcp_server):
        """Test memory model integration following MCP patterns."""
        # Memory models should integrate properly
        memory_models = [
            'memory_manager',
            'memory_guardian',
            'pattern_tracker'
        ]
        
        for model_name in memory_models:
            assert hasattr(mcp_server, model_name), f"Missing memory model: {model_name}"
            model = getattr(mcp_server, model_name)
            assert model is not None, f"Memory model {model_name} is None"
    
    def test_mcp_workflow_intelligence_models(self, mcp_server):
        """Test workflow intelligence models compliance."""
        # Workflow intelligence models for adaptive behavior
        workflow_models = [
            'adaptive_command_selector',
            'progress_tracking_automation',
            'pattern_analyzer'
        ]
        
        for model_name in workflow_models:
            assert hasattr(mcp_server, model_name), f"Missing workflow model: {model_name}"
            model = getattr(mcp_server, model_name)
            assert model is not None, f"Workflow model {model_name} is None"
    
    def test_mcp_embeddings_models_present(self, mcp_server):
        """Test embeddings models are properly initialized."""
        # Embeddings models for semantic operations
        embeddings_models = [
            'embedding_generator',
            'embedding_storage',
            'embedding_trainer'
        ]
        
        for model_name in embeddings_models:
            assert hasattr(mcp_server, model_name), f"Missing embeddings model: {model_name}"
            model = getattr(mcp_server, model_name)
            assert model is not None, f"Embeddings model {model_name} is None"
    
    def test_mcp_convention_validation_models(self, mcp_server):
        """Test convention validation models compliance."""
        # Convention validation models for code quality
        convention_models = [
            'file_operation_validator',
            'naming_convention_enforcer',
            'code_standards_validator',
            'git_protocol_automator'
        ]
        
        for model_name in convention_models:
            assert hasattr(mcp_server, model_name), f"Missing convention model: {model_name}"
            model = getattr(mcp_server, model_name)
            assert model is not None, f"Convention model {model_name} is None"


class TestMCPInspectorInteractionModels:
    """Test interaction with MCP Inspector models and capabilities."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_mcp_inspector_server_connection_model(self, temp_storage):
        """Test server connection model works with MCP Inspector patterns."""
        # Following the MCP Inspector documentation patterns
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                # Server should initialize without errors (Inspector requirement)
                server = EnhancedAtlasCommandsServer()
                assert server is not None
                
                # Should have MCP server instance for Inspector connection
                assert hasattr(server, 'server')
                assert server.server.name == "atlas-commands"
    
    def test_mcp_inspector_capability_negotiation_model(self, temp_storage):
        """Test capability negotiation model with Inspector patterns."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                server = EnhancedAtlasCommandsServer()
                
                # Inspector validates that servers expose their capabilities
                # Server should have all expected capability components
                capability_components = [
                    'server',  # Core MCP server
                    'storage_manager',  # Resource capabilities
                    'observability',  # Monitoring capabilities
                    'memory_manager'   # Memory capabilities
                ]
                
                for component in capability_components:
                    assert hasattr(server, component), f"Missing capability: {component}"
    
    def test_mcp_inspector_message_monitoring_model(self, temp_storage):
        """Test message monitoring model for Inspector notifications."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                server = EnhancedAtlasCommandsServer()
                
                # Inspector monitors server messages - verify observability
                assert hasattr(server, 'observability')
                observability = server.observability
                
                # Should have message/notification handling
                assert observability is not None
                assert hasattr(observability, 'service_name')


class TestMCPInspectorToolsTabValidation:
    """Test tools validation following MCP Inspector Tools tab patterns."""
    
    @pytest.fixture  
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_atlas_tools_schema_validation(self, temp_storage):
        """Test ATLAS tools have valid schemas for Inspector validation."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                server = EnhancedAtlasCommandsServer()
                
                # Inspector validates tool schemas - verify managers exist
                tool_managers = [
                    'checklist_manager',      # Checklist tools
                    'todowrite_manager',      # Todo management tools  
                    'memory_manager',         # Memory operation tools
                    'workflow_enforcer',      # Workflow tools
                    'command_validator',      # Validation tools
                    'adaptive_command_selector'  # Adaptive tools
                ]
                
                for manager_name in tool_managers:
                    assert hasattr(server, manager_name), f"Missing tool manager for Inspector: {manager_name}"
                    manager = getattr(server, manager_name)
                    assert manager is not None, f"Tool manager {manager_name} is None"
    
    def test_atlas_tool_execution_model(self, temp_storage):
        """Test tool execution model follows Inspector patterns."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                server = EnhancedAtlasCommandsServer()
                
                # Inspector tests tool execution - verify execution infrastructure
                execution_components = [
                    'workflow_enforcer',          # Tool execution orchestration
                    'command_validator',          # Tool validation
                    'adaptive_command_selector',  # Intelligent tool selection
                    'progress_tracking_automation'  # Execution monitoring
                ]
                
                for component_name in execution_components:
                    assert hasattr(server, component_name), f"Missing execution component: {component_name}"
                    component = getattr(server, component_name)
                    assert component is not None, f"Execution component {component_name} is None"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])