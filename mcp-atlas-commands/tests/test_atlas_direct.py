#!/usr/bin/env python3
"""
Direct test of Atlas MCP functionality inside container
"""

import subprocess
import json
import tempfile
from datetime import datetime

def test_atlas_direct():
    """Test Atlas functionality directly inside the container"""
    
    print("=== Direct Atlas MCP Test ===")
    print(f"Started at: {datetime.now()}")
    
    # Create a test script to run inside the container
    test_script = '''
import sys
import json
import asyncio
from datetime import datetime

sys.path.append('/app/src')

async def test_atlas_tools():
    """Test Atlas tools directly"""
    print("=== Atlas Tools Direct Test ===")
    
    try:
        # Import the main components
        from atlas_commands.storage.task_storage_manager import TaskStorageManager
        from atlas_commands.checklist.manager import ChecklistManager
        from atlas_commands.memory.graph_manager import MemoryGraphManager
        from atlas_commands.observability.manager import ObservabilityManager
        
        print("✅ Core modules imported successfully")
        
        # Test 1: Storage Manager
        print("\\n1. Testing TaskStorageManager...")
        storage = TaskStorageManager(base_path="/app/REPOS")
        
        # Create a test task
        task_data = {
            "task_id": "test-task-001",
            "project_name": "ATLAS_TEST",
            "task_type": "testing",
            "description": "Direct test task",
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        result = await storage.create_task("ATLAS_TEST", task_data)
        print(f"✅ Task created: {result}")
        
        # Test 2: List tasks
        print("\\n2. Testing task listing...")
        tasks = await storage.list_tasks("ATLAS_TEST")
        print(f"✅ Found {len(tasks)} tasks")
        
        # Test 3: Checklist Manager
        print("\\n3. Testing ChecklistManager...")
        checklist_manager = ChecklistManager()
        
        checklist_data = {
            "items": ["Test item 1", "Test item 2"],
            "task_id": "test-task-001"
        }
        
        checklist = await checklist_manager.create_checklist("ATLAS_TEST", checklist_data)
        print(f"✅ Checklist created: {type(checklist).__name__}")
        
        # Test 4: Memory Manager
        print("\\n4. Testing MemoryGraphManager...")
        memory_manager = MemoryGraphManager()
        
        entity_data = {
            "name": "TestEntity",
            "type": "task",
            "properties": {"test": True}
        }
        
        entity = await memory_manager.create_entity("ATLAS_TEST", entity_data)
        print(f"✅ Memory entity created: {entity}")
        
        # Test 5: Observability
        print("\\n5. Testing ObservabilityManager...")
        obs_manager = ObservabilityManager()
        status = await obs_manager.get_status()
        print(f"✅ Observability status: {status}")
        
        print("\\n✅ All direct tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in direct test: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the async test
result = asyncio.run(test_atlas_tools())
print(f"\\nFinal result: {'SUCCESS' if result else 'FAILED'}")
'''
    
    # Write test script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        # Run the test script inside the container
        cmd = [
            "docker", "run", "--rm",
            "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
            "-v", f"{temp_script}:/app/test_script.py",
            "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
            "-e", "PROJECT_NAME=ATLAS_TEST",
            "-e", "ATLAS_ENABLE_MEMORY=true",
            "atlas-commands-mcp:latest",
            "python", "/app/test_script.py"
        ]
        
        print("Running direct test inside container...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\\n{result.stderr}")
        
        success = result.returncode == 0 and "SUCCESS" in result.stdout
        print(f"\\nDirect test: {'✅ PASSED' if success else '❌ FAILED'}")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Direct test timed out")
        return False
    except Exception as e:
        print(f"❌ Error running direct test: {e}")
        return False
    finally:
        # Cleanup temp file
        import os
        try:
            os.unlink(temp_script)
        except:
            pass

def test_mcp_protocol():
    """Test MCP protocol compliance"""
    print("\\n=== MCP Protocol Compliance Test ===")
    
    # Test the server's MCP protocol implementation
    test_script = '''
import sys
import json
import asyncio

sys.path.append('/app/src')

async def test_mcp_protocol():
    """Test MCP protocol implementation"""
    try:
        from mcp.server import Server
        from mcp.types import Tool
        
        print("✅ MCP library imports successful")
        
        # Try to create a server instance
        server = Server("atlas-test")
        print("✅ MCP Server instance created")
        
        # Check if we can list our tools (without actually running)
        from atlas_commands.server import get_available_tools
        tools = get_available_tools()
        print(f"✅ Found {len(tools)} available tools")
        
        # Show some tool names
        for i, tool in enumerate(tools[:5]):
            print(f"  {i+1}. {tool}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_mcp_protocol())
print(f"\\nMCP Protocol test: {'SUCCESS' if result else 'FAILED'}")
'''
    
    # Write test script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{temp_script}:/app/mcp_test.py",
            "atlas-commands-mcp:latest",
            "python", "/app/mcp_test.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\\n{result.stderr}")
        
        success = result.returncode == 0 and "SUCCESS" in result.stdout
        print(f"MCP Protocol test: {'✅ PASSED' if success else '❌ FAILED'}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error in MCP protocol test: {e}")
        return False
    finally:
        import os
        try:
            os.unlink(temp_script)
        except:
            pass

def main():
    """Run comprehensive direct tests"""
    print("=== Comprehensive Atlas Direct Testing ===")
    
    results = []
    
    # Test 1: Direct functionality
    result1 = test_atlas_direct()
    results.append(("Direct Functionality", result1))
    
    # Test 2: MCP Protocol
    result2 = test_mcp_protocol()
    results.append(("MCP Protocol", result2))
    
    # Summary
    print(f"\\n{'='*50}")
    print("FINAL TEST SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print(f"Completed at: {datetime.now()}")

if __name__ == "__main__":
    main()