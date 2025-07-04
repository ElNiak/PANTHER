#!/usr/bin/env python3
"""
Test Atlas MCP with Redis integration
"""

import json
import subprocess
import time
from datetime import datetime

def test_atlas_with_redis():
    """Test Atlas MCP functions that utilize Redis caching"""
    
    print("=== Atlas Redis Integration Test ===")
    print(f"Started at: {datetime.now()}")
    print()
    
    # Test commands that should populate Redis cache
    test_commands = [
        {
            "name": "create_task_metadata",
            "args": {
                "project_name": "ATLAS_REDIS_TEST",
                "task_id": "redis-test-001",
                "task_type": "testing", 
                "description": "Test Redis caching with Atlas MCP"
            }
        },
        {
            "name": "list_project_tasks",
            "args": {
                "project_name": "ATLAS_REDIS_TEST"
            }
        },
        {
            "name": "get_cache_stats",
            "args": {}
        },
        {
            "name": "memory_health_check", 
            "args": {
                "include_details": True
            }
        }
    ]
    
    results = []
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"{i}. Testing {cmd['name']}...")
        
        # Create JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": {
                "name": cmd["name"],
                "arguments": cmd["args"]
            }
        }
        
        # Run via Docker with Redis connection
        docker_cmd = [
            "docker", "run", "-i", "--rm",
            "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
            "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
            "-e", "PROJECT_NAME=ATLAS_REDIS_TEST", 
            "-e", "REDIS_URL=redis://host.docker.internal:6379/0",
            "--add-host", "host.docker.internal:host-gateway",
            "atlas-commands-mcp:latest",
            "python", "-m", "atlas_commands.server"
        ]
        
        try:
            result = subprocess.run(
                docker_cmd,
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ {cmd['name']}: SUCCESS")
                # Try to extract JSON response from stdout
                lines = result.stdout.strip().split('\n')
                json_line = None
                for line in reversed(lines):
                    if line.startswith('{"jsonrpc"'):
                        json_line = line
                        break
                
                if json_line:
                    try:
                        response = json.loads(json_line)
                        results.append({
                            "command": cmd["name"],
                            "status": "success",
                            "response": response
                        })
                    except json.JSONDecodeError:
                        results.append({
                            "command": cmd["name"], 
                            "status": "success",
                            "response": "Non-JSON response"
                        })
                else:
                    results.append({
                        "command": cmd["name"],
                        "status": "success", 
                        "response": "No JSON found"
                    })
            else:
                print(f"❌ {cmd['name']}: FAILED")
                results.append({
                    "command": cmd["name"],
                    "status": "failed",
                    "error": result.stderr
                })
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {cmd['name']}: TIMEOUT")
            results.append({
                "command": cmd["name"],
                "status": "timeout"
            })
        except Exception as e:
            print(f"💥 {cmd['name']}: ERROR - {e}")
            results.append({
                "command": cmd["name"],
                "status": "error", 
                "error": str(e)
            })
        
        print()
    
    # Check Redis after operations
    print("=== Redis Status Check ===")
    try:
        redis_result = subprocess.run(
            ["docker", "exec", "atlas-redis-integrated", "redis-cli", "info", "keyspace"],
            capture_output=True,
            text=True
        )
        print("Redis Keyspace Info:")
        print(redis_result.stdout)
        
        redis_keys = subprocess.run(
            ["docker", "exec", "atlas-redis-integrated", "redis-cli", "keys", "*"],
            capture_output=True, 
            text=True
        )
        print("Redis Keys:")
        print(redis_keys.stdout or "No keys found")
        
    except Exception as e:
        print(f"Redis check failed: {e}")
    
    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    total = len(results)
    
    print("=== Test Summary ===")
    print(f"Commands tested: {total}")
    print(f"Successful: {successful}")
    print(f"Success rate: {(successful/total)*100:.1f}%")
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "test_type": "atlas_redis_integration",
        "total_commands": total,
        "successful_commands": successful,
        "success_rate": successful/total,
        "results": results
    }
    
    with open("atlas_redis_test_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: atlas_redis_test_results.json")
    return results

if __name__ == "__main__":
    test_atlas_with_redis()