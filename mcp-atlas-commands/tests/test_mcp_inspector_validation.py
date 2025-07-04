"""
MCP Inspector Validation Tests
Tests our ATLAS MCP server against MCP protocol specifications using patterns from the official inspector.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock
import tempfile
import os

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from atlas_commands.server import EnhancedAtlasCommandsServer


class TestMCPInspectorValidation:
    """Validate ATLAS MCP server against MCP protocol specifications."""
    
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
    
    def test_server_initialization_mcp_compliance(self, mcp_server):
        """Test server initializes according to MCP specifications."""
        # Verify basic MCP server structure
        assert hasattr(mcp_server, 'server')
        assert mcp_server.server.name == "atlas-commands"
        
        # Verify server can be accessed
        assert mcp_server.server is not None
    
    def test_server_has_required_mcp_capabilities(self, mcp_server):
        """Test server exposes required MCP capabilities."""
        # According to MCP Inspector, servers should have these core capabilities
        
        # Check tool registry exists (for tools capability)
        assert hasattr(mcp_server, '_tools') or hasattr(mcp_server, 'tool_registry')
        
        # Check memory/storage capabilities
        assert hasattr(mcp_server, 'storage_manager')
        assert hasattr(mcp_server, 'memory_manager')
        
        # Check observability capabilities
        assert hasattr(mcp_server, 'observability')
    
    def test_server_managers_initialization(self, mcp_server):
        """Test all server managers are properly initialized per MCP patterns."""
        # Core managers that should be available
        required_managers = [
            'checklist_manager',
            'todowrite_manager', 
            'memory_manager',
            'workflow_enforcer',
            'command_validator',
            'adaptive_command_selector',
            'progress_tracking_automation'
        ]
        
        for manager_name in required_managers:
            assert hasattr(mcp_server, manager_name), f"Missing required manager: {manager_name}"
            manager = getattr(mcp_server, manager_name)
            assert manager is not None, f"Manager {manager_name} is None"
    
    def test_server_convention_tools_available(self, mcp_server):
        """Test convention validation tools are available."""
        convention_tools = [
            'file_operation_validator',
            'naming_convention_enforcer', 
            'code_standards_validator',
            'git_protocol_automator'
        ]
        
        for tool_name in convention_tools:
            assert hasattr(mcp_server, tool_name), f"Missing convention tool: {tool_name}"
            tool = getattr(mcp_server, tool_name)
            assert tool is not None, f"Convention tool {tool_name} is None"
    
    def test_server_coordination_optimizations_loaded(self, mcp_server):
        """Test coordination optimization features are properly loaded."""
        # These are the 5 coordination optimizations mentioned in the documentation
        coordination_features = [
            'compression_manager',
            'saga_coordinator', 
            'entropy_processor',
            'incremental_memory_manager',
            'concurrent_exporter'
        ]
        
        for feature_name in coordination_features:
            assert hasattr(mcp_server, feature_name), f"Missing coordination feature: {feature_name}"
            feature = getattr(mcp_server, feature_name)
            assert feature is not None, f"Coordination feature {feature_name} is None"
    
    def test_server_token_optimization_configured(self, mcp_server):
        """Test token optimization is properly configured."""
        # Should have token optimization setup
        assert hasattr(mcp_server, '_token_optimization_enabled')
        
        # Token optimization should be configured
        # This validates our fix for the Docker import error
        from atlas_commands.token_optimization import set_response_mode, get_response_mode, ResponseMode
        
        # Test the functions we implemented
        original_mode = get_response_mode()
        set_response_mode(ResponseMode.COMPACT)
        assert get_response_mode() == ResponseMode.COMPACT
        
        # Reset to original
        set_response_mode(original_mode)
    
    def test_server_storage_paths_configurable(self, mcp_server):
        """Test storage paths are configurable via environment variables."""
        # This validates the Docker mount path configuration
        storage_manager = mcp_server.storage_manager
        assert storage_manager is not None
        
        # Should have a configured base path
        assert hasattr(storage_manager, 'base_path')
        assert storage_manager.base_path is not None
    
    def test_server_observability_system_functional(self, mcp_server):
        """Test observability system is functional."""
        observability = mcp_server.observability
        assert observability is not None
        
        # Should have proper service identification
        assert hasattr(observability, 'service_name')
        assert hasattr(observability, 'service_version')
    
    def test_server_memory_integration_available(self, mcp_server):
        """Test memory integration components are available."""
        # Memory system components
        memory_components = [
            'memory_manager',
            'memory_guardian',
            'pattern_tracker'
        ]
        
        for component_name in memory_components:
            assert hasattr(mcp_server, component_name), f"Missing memory component: {component_name}"
            component = getattr(mcp_server, component_name)
            assert component is not None, f"Memory component {component_name} is None"
    
    def test_server_embeddings_system_present(self, mcp_server):
        """Test embeddings system components are present."""
        # Embeddings system should be initialized
        embeddings_components = [
            'embedding_generator',
            'embedding_storage', 
            'semantic_search_engine',
            'embedding_trainer'
        ]
        
        for component_name in embeddings_components:
            assert hasattr(mcp_server, component_name), f"Missing embeddings component: {component_name}"
            component = getattr(mcp_server, component_name)
            assert component is not None, f"Embeddings component {component_name} is None"
    
    def test_server_workflow_intelligence_enabled(self, mcp_server):
        """Test workflow intelligence features are enabled."""
        # Workflow intelligence components
        workflow_components = [
            'adaptive_command_selector',
            'progress_tracking_automation',
            'pattern_analyzer'
        ]
        
        for component_name in workflow_components:
            assert hasattr(mcp_server, component_name), f"Missing workflow component: {component_name}"
            component = getattr(mcp_server, component_name)
            assert component is not None, f"Workflow component {component_name} is None"


class TestMCPProtocolCompliance:
    """Test compliance with MCP protocol specifications."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_mcp_server_name_specification(self, temp_storage):
        """Test server name follows MCP naming conventions."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                server = EnhancedAtlasCommandsServer()
                
                # MCP servers should have descriptive names
                assert server.server.name == "atlas-commands"
                assert isinstance(server.server.name, str)
                assert len(server.server.name) > 0
    
    def test_server_graceful_initialization(self, temp_storage):
        """Test server initializes gracefully without errors."""
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_storage}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                # Should not raise exceptions during initialization
                try:
                    server = EnhancedAtlasCommandsServer()
                    assert server is not None
                except Exception as e:
                    pytest.fail(f"Server initialization failed: {e}")
    
    def test_server_environment_variable_handling(self):
        """Test server handles environment variables properly."""
        # Test with custom path
        custom_path = '/tmp/test_atlas_storage'
        
        with patch('atlas_commands.server.TaskStorageManager') as mock_storage:
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_storage.return_value = MagicMock()
                mock_guardian.return_value = MagicMock()
                
                with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': custom_path}):
                    server = EnhancedAtlasCommandsServer()
                    
                    # Verify custom path was used
                    mock_storage.assert_called_once_with(custom_path)
        
        # Test with default path
        with patch('atlas_commands.server.TaskStorageManager') as mock_storage:
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_storage.return_value = MagicMock()
                mock_guardian.return_value = MagicMock()
                
                with patch.dict(os.environ, {}, clear=True):
                    server = EnhancedAtlasCommandsServer()
                    
                    # Verify default path was used
                    mock_storage.assert_called_once_with('/app/REPOS')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])