"""
Test the fixed server entrypoint without token optimization mocking.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from atlas_commands.server import EnhancedAtlasCommandsServer


def test_server_initialization_with_token_optimization():
    """Test server initializes with real token optimization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch.dict(os.environ, {'ATLAS_STORAGE_PATH': temp_dir}):
            with patch('atlas_commands.server.MemoryGuardianInterface') as mock_guardian:
                mock_guardian.return_value = MagicMock()
                
                # This should work now without mocking token optimization
                server = EnhancedAtlasCommandsServer()
                
                # Verify server was created
                assert server is not None
                assert hasattr(server, 'server')
                assert hasattr(server, 'storage_manager')
                assert server.server.name == "atlas-commands"


if __name__ == "__main__":
    test_server_initialization_with_token_optimization()
    print("✅ Server entrypoint test passed with real token optimization!")