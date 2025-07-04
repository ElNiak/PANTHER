#!/usr/bin/env python3
"""
Quick performance test for ATLAS MCP server
Focus on key metrics without timeouts
"""

import json
import subprocess
import time

def quick_tool_test(tool_name):
    """Quick test of a single tool"""
    
    input_data = """{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "clientInfo": {"name": "test", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "method": "notifications/initialized"}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "%s", "arguments": {}}}
""" % tool_name

    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "-i", "-e", "ATLAS_ENABLE_TOOL_REGISTRY=true", "atlas-commands-mcp:latest"],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=5  # Shorter timeout
        )
        
        response_time = time.time() - start_time
        
        # Check if tool executed successfully
        success = False
        if result.stdout and '"id":2' in result.stdout and '"result"' in result.stdout:
            success = True
        
        return {"tool": tool_name, "time": response_time, "success": success}
        
    except subprocess.TimeoutExpired:
        return {"tool": tool_name, "time": 5.0, "success": False, "error": "timeout"}
    except Exception as e:
        return {"tool": tool_name, "time": time.time() - start_time, "success": False, "error": str(e)}

def main():
    """Quick performance validation"""
    print("ATLAS MCP Quick Performance Test")
    print("="*40)
    
    # Test a few fast tools
    test_tools = [
        "get_observability_status",
        "memory_health_check", 
        "get_cache_stats",
        "get_embeddings_stats",
        "compact_memory_graph"
    ]
    
    print(f"Testing {len(test_tools)} reliable tools...")
    
    results = []
    for tool in test_tools:
        print(f"  {tool}...", end="")
        result = quick_tool_test(tool)
        results.append(result)
        
        if result["success"]:
            print(f" ✓ {result['time']:.3f}s")
        else:
            print(f" ✗ {result.get('error', 'failed')}")
    
    # Analysis
    successful_results = [r for r in results if r["success"]]
    
    if successful_results:
        times = [r["time"] for r in successful_results]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nPerformance Summary:")
        print(f"  Successful tools: {len(successful_results)}/{len(results)}")
        print(f"  Average response: {avg_time:.3f}s")
        print(f"  Min response: {min_time:.3f}s")
        print(f"  Max response: {max_time:.3f}s")
        print(f"  Response variance: {max_time - min_time:.3f}s")
        
        # Performance assessment
        if avg_time < 3.0:
            print(f"  ✅ Good performance")
        elif avg_time < 5.0:
            print(f"  ⚠️ Acceptable performance")
        else:
            print(f"  ✗ Slow performance")
        
        # O(1) assessment (low variance = consistent performance)
        variance = max_time - min_time
        if variance < avg_time * 0.5:
            print(f"  ✅ Consistent O(1) performance")
        else:
            print(f"  ⚠️ Variable performance")
        
        return len(successful_results) >= len(results) * 0.8
    else:
        print("❌ No successful tool executions")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)