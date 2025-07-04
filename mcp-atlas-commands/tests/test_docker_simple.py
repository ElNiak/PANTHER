#!/usr/bin/env python3
"""Simple Docker container test for Atlas MCP."""

import subprocess
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_docker_container():
    """Test Docker container functionality."""
    results = {
        "container_build": False,
        "container_startup": False,
        "import_test": False,
        "basic_server_test": False,
        "tool_registry_test": False,
        "overall_success": False
    }
    
    container_name = "atlas-simple-test"
    
    try:
        # Clean up any existing container
        subprocess.run(['docker', 'stop', container_name], capture_output=True, check=False)
        subprocess.run(['docker', 'rm', container_name], capture_output=True, check=False)
        
        # Test 1: Container build validation
        result = subprocess.run(['docker', 'images', 'atlas-commands-mcp:latest'], 
                              capture_output=True, text=True)
        if 'atlas-commands-mcp' in result.stdout:
            results["container_build"] = True
            logger.info("✅ Container build: PASS")
        
        # Test 2: Container startup
        result = subprocess.run([
            'docker', 'run', '-d', '--name', container_name,
            'atlas-commands-mcp:latest', 'sleep', '30'
        ], capture_output=True, text=True, check=True)
        
        time.sleep(3)  # Give container time to start
        
        status_result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}'], 
                                     capture_output=True, text=True)
        if container_name in status_result.stdout:
            results["container_startup"] = True
            logger.info("✅ Container startup: PASS")
        
        # Test 3: Import test
        import_result = subprocess.run([
            'docker', 'exec', container_name,
            'python', '-c', 'from src.atlas_commands.server import EnhancedAtlasCommandsServer; print("SUCCESS")'
        ], capture_output=True, text=True)
        
        if import_result.returncode == 0 and "SUCCESS" in import_result.stdout:
            results["import_test"] = True
            logger.info("✅ Import test: PASS")
        else:
            logger.warning(f"❌ Import test: FAIL - {import_result.stderr}")
        
        # Test 4: Basic server instantiation (lightweight)
        server_result = subprocess.run([
            'docker', 'exec', container_name,
            'python', '-c', '''
import os
os.environ["ATLAS_STORAGE_PATH"] = "/tmp"  # Use temp storage to avoid volume issues
try:
    from src.atlas_commands.server import EnhancedAtlasCommandsServer
    server = EnhancedAtlasCommandsServer()
    print("SERVER_SUCCESS")
except Exception as e:
    print(f"SERVER_ERROR: {e}")
'''
        ], capture_output=True, text=True, timeout=60)
        
        if server_result.returncode == 0 and "SERVER_SUCCESS" in server_result.stdout:
            results["basic_server_test"] = True
            logger.info("✅ Basic server test: PASS")
        else:
            logger.warning(f"❌ Basic server test: FAIL - {server_result.stderr}")
        
        # Test 5: Tool registry test (lightweight)
        registry_result = subprocess.run([
            'docker', 'exec', container_name,
            'python', '-c', '''
import os
os.environ["ATLAS_STORAGE_PATH"] = "/tmp"
try:
    from src.atlas_commands.server import EnhancedAtlasCommandsServer
    server = EnhancedAtlasCommandsServer()
    tools = server._get_available_tools()
    print(f"TOOLS_COUNT: {len(tools)}")
    if len(tools) > 40:  # Expect at least 40 tools
        print("REGISTRY_SUCCESS")
    else:
        print(f"REGISTRY_INSUFFICIENT: {len(tools)}")
except Exception as e:
    print(f"REGISTRY_ERROR: {e}")
'''
        ], capture_output=True, text=True, timeout=60)
        
        if registry_result.returncode == 0 and "REGISTRY_SUCCESS" in registry_result.stdout:
            results["tool_registry_test"] = True
            logger.info("✅ Tool registry test: PASS")
            
            # Extract tool count
            for line in registry_result.stdout.split('\n'):
                if line.startswith("TOOLS_COUNT:"):
                    tool_count = line.split(":")[1].strip()
                    logger.info(f"📊 Tool count: {tool_count}")
        else:
            logger.warning(f"❌ Tool registry test: FAIL - {registry_result.stderr}")
        
        # Calculate overall success
        results["overall_success"] = all([
            results["container_build"],
            results["container_startup"], 
            results["import_test"],
            results["basic_server_test"],
            results["tool_registry_test"]
        ])
        
    except Exception as e:
        logger.error(f"Docker test failed: {e}")
    
    finally:
        # Cleanup
        subprocess.run(['docker', 'stop', container_name], capture_output=True, check=False)
        subprocess.run(['docker', 'rm', container_name], capture_output=True, check=False)
    
    return results

def main():
    """Run Docker container tests."""
    logger.info("🐳 Starting Simple Docker Container Tests")
    
    results = test_docker_container()
    
    # Report results
    logger.info("\n" + "="*60)
    logger.info("📊 DOCKER CONTAINER TEST RESULTS")
    logger.info("="*60)
    
    test_names = [
        ("Container Build", "container_build"),
        ("Container Startup", "container_startup"),
        ("Import Test", "import_test"),
        ("Basic Server Test", "basic_server_test"),
        ("Tool Registry Test", "tool_registry_test")
    ]
    
    for name, key in test_names:
        status = "✅ PASS" if results[key] else "❌ FAIL"
        logger.info(f"{name}: {status}")
    
    success_rate = sum(1 for _, key in test_names if results[key]) / len(test_names) * 100
    logger.info(f"\nSuccess Rate: {success_rate:.1f}%")
    
    logger.info("\n" + "="*60)
    if results["overall_success"]:
        logger.info("🎉 DOCKER CONTAINER TESTS: ALL PASS")
        logger.info("🚀 Atlas MCP Docker container is functional")
        return 0
    else:
        logger.warning("⚠️ DOCKER CONTAINER TESTS: SOME FAILURES")
        logger.warning("🔧 Atlas MCP Docker container needs investigation")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)