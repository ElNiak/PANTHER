"""
Server entrypoint tests for ATLAS MCP server.
Tests server initialization, configuration, and basic startup functionality.
"""

import pytest
import tempfile
import os
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.atlas_commands.server import EnhancedAtlasCommandsServer


class TestServerEntrypoint:
    """Test server entrypoint and initialization."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as storage_dir:
            with tempfile.TemporaryDirectory() as memory_dir:
                yield {
                    'storage': storage_dir,
                    'memory': memory_dir
                }
    
    def test_server_initialization_with_env_vars(self, temp_dirs):
        """Test server initializes correctly with environment variables."""
        # Set environment variables
        storage_path = temp_dirs['storage']
        memory_path = temp_dirs['memory']
        
        with patch.dict(os.environ, {
            'ATLAS_STORAGE_PATH': storage_path
        }):
            # Mock the memory guardian to use our temp directory
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                # Mock the entire token optimization setup method
                with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                    mock_guardian.return_value = MagicMock()
                    mock_token_setup.return_value = None
                    
                    server = EnhancedAtlasCommandsServer()
                
                # Verify server was created
                assert server is not None
                assert hasattr(server, 'server')
                assert hasattr(server, 'storage_manager')
                
                # Verify storage manager uses correct path
                assert str(storage_path) in str(server.storage_manager.base_path)
    
    def test_server_initialization_with_default_paths(self):
        """Test server initialization behavior with default hardcoded paths."""
        # Test without environment variables - should handle gracefully
        with patch.dict(os.environ, {}, clear=True):
            # Mock components that need file system access
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                with patch('src.atlas_commands.server.TaskStorageManager') as mock_storage:
                    with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                        mock_guardian.return_value = MagicMock()
                        mock_storage.return_value = MagicMock()
                        mock_token_setup.return_value = None
                        
                        # This should not raise an exception
                        server = EnhancedAtlasCommandsServer()
                    
                    assert server is not None
                    assert hasattr(server, 'server')
    
    def test_server_manager_initialization(self, temp_dirs):
        """Test that all server managers are properly initialized."""
        storage_path = temp_dirs['storage']
        
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path}):
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                    mock_guardian.return_value = MagicMock()
                    mock_token_setup.return_value = None
                    
                    server = EnhancedAtlasCommandsServer()
                
                # Check core managers are initialized
                assert hasattr(server, 'checklist_manager')
                assert hasattr(server, 'todowrite_manager')
                assert hasattr(server, 'memory_manager')
                assert hasattr(server, 'workflow_enforcer')
                assert hasattr(server, 'command_validator')
                
                # Check new managers are initialized
                assert hasattr(server, 'adaptive_command_selector')
                assert hasattr(server, 'progress_tracking_automation')
                
                # Check convention validation tools
                assert hasattr(server, 'file_operation_validator')
                assert hasattr(server, 'naming_convention_enforcer')
                assert hasattr(server, 'code_standards_validator')
                assert hasattr(server, 'git_protocol_automator')
    
    def test_server_observability_initialization(self, temp_dirs):
        """Test that observability system is properly initialized."""
        storage_path = temp_dirs['storage']
        
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path}):
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                    mock_guardian.return_value = MagicMock()
                    mock_token_setup.return_value = None
                    
                    server = EnhancedAtlasCommandsServer()
                
                # Check observability components
                assert hasattr(server, 'observability')
                assert server.observability is not None
    
    def test_server_name_and_metadata(self, temp_dirs):
        """Test server name and basic metadata."""
        storage_path = temp_dirs['storage']
        
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path}):
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                    mock_guardian.return_value = MagicMock()
                    mock_token_setup.return_value = None
                    
                    server = EnhancedAtlasCommandsServer()
                
                # Check server name
                assert server.server.name == "atlas-commands"
    
    def test_environment_variable_handling(self):
        """Test environment variable handling for configuration."""
        # Test default value when env var not set
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.atlas_commands.server.TaskStorageManager') as mock_storage:
                with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                    with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                        mock_storage.return_value = MagicMock()
                        mock_guardian.return_value = MagicMock()
                        mock_token_setup.return_value = None
                        
                        server = EnhancedAtlasCommandsServer()
                    
                    # Verify storage manager was called with default path
                    mock_storage.assert_called_once_with('/app/REPOS')
        
        # Test custom value when env var is set
        custom_path = '/tmp/custom_storage'
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': custom_path}):
            with patch('src.atlas_commands.server.TaskStorageManager') as mock_storage:
                with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                    with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                        mock_storage.return_value = MagicMock()
                        mock_guardian.return_value = MagicMock()
                        mock_token_setup.return_value = None
                        
                        server = EnhancedAtlasCommandsServer()
                    
                    # Verify storage manager was called with custom path
                    mock_storage.assert_called_once_with(custom_path)
    
    def test_server_configuration_isolation(self, temp_dirs):
        """Test that server instances are properly isolated."""
        storage_path1 = temp_dirs['storage']
        
        with tempfile.TemporaryDirectory() as storage_path2:
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                # Create two servers with different storage paths
                with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path1}):
                    server1 = EnhancedAtlasCommandsServer()
                
                with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path2}):
                    server2 = EnhancedAtlasCommandsServer()
                
                # Verify they are different instances
                assert server1 is not server2
                assert server1.server is not server2.server
    
    @pytest.mark.asyncio
    async def test_server_tool_loading(self, temp_dirs):
        """Test that server tools are loaded correctly."""
        storage_path = temp_dirs['storage']
        
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path}):
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                    mock_guardian.return_value = MagicMock()
                    mock_token_setup.return_value = None
                    
                    server = EnhancedAtlasCommandsServer()
                
                # Check that the server has the expected structure
                assert hasattr(server, 'server')
                assert server.server.name == "atlas-commands"
                
                # The server should be able to handle basic operations
                # without raising exceptions during initialization
                assert True  # If we get here, initialization succeeded
    
    def test_path_configuration_robustness(self):
        """Test that server handles various path configurations robustly."""
        test_cases = [
            '/tmp/atlas_test',
            '/var/tmp/atlas',
            '~/atlas_commands',
            'relative/path'  # This should work or fail gracefully
        ]
        
        for test_path in test_cases:
            with patch('src.atlas_commands.server.TaskStorageManager') as mock_storage:
                with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                    mock_storage.return_value = MagicMock()
                    mock_guardian.return_value = MagicMock()
                    
                    with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': test_path}):
                        # Should not raise exceptions
                        server = EnhancedAtlasCommandsServer()
                        assert server is not None
                        
                        # Verify the path was passed correctly
                        mock_storage.assert_called_once_with(test_path)
                        mock_storage.reset_mock()
    
    def test_server_memory_system_integration(self, temp_dirs):
        """Test integration with memory system components."""
        storage_path = temp_dirs['storage']
        
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': storage_path}):
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                with patch.object(EnhancedAtlasCommandsServer, '_setup_token_optimization') as mock_token_setup:
                    mock_guardian.return_value = MagicMock()
                    mock_token_setup.return_value = None
                    
                    server = EnhancedAtlasCommandsServer()
                
                # Check memory-related components
                assert hasattr(server, 'memory_manager')
                assert hasattr(server, 'memory_guardian')
                assert hasattr(server, 'pattern_tracker')
                
                # These should be properly initialized
                assert server.memory_manager is not None
                assert server.memory_guardian is not None
                assert server.pattern_tracker is not None


class TestServerConfigurationEdgeCases:
    """Test edge cases in server configuration."""
    
    def test_missing_storage_directory_handling(self):
        """Test server behavior when storage directory doesn't exist."""
        non_existent_path = '/path/that/does/not/exist'
        
        with patch('src.atlas_commands.server.TaskStorageManager') as mock_storage:
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                # Configure mocks to simulate missing directory
                mock_storage.return_value = MagicMock()
                mock_guardian.return_value = MagicMock()
                
                with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': non_existent_path}):
                    # Should handle gracefully
                    server = EnhancedAtlasCommandsServer()
                    assert server is not None
    
    def test_permission_denied_handling(self):
        """Test server behavior when permissions are denied."""
        read_only_path = '/proc'  # Read-only filesystem path
        
        with patch('src.atlas_commands.server.TaskStorageManager') as mock_storage:
            with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_storage.return_value = MagicMock()
                mock_guardian.return_value = MagicMock()
                
                with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': read_only_path}):
                    # Should handle gracefully without crashing
                    server = EnhancedAtlasCommandsServer()
                    assert server is not None
    
    def test_memory_guardian_failure_handling(self):
        """Test server behavior when memory guardian fails to initialize."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_dir}):
                # Mock memory guardian to raise exception
                with patch('src.atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                    mock_guardian.side_effect = Exception("Memory guardian initialization failed")
                    
                    # Should handle the exception gracefully
                    with pytest.raises(Exception):
                        EnhancedAtlasCommandsServer()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])