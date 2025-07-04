#!/usr/bin/env python3
"""
Test Atlas cache performance and warming with Redis
"""

import json
import subprocess
import time
from datetime import datetime

def run_atlas_command(tool_name, arguments, timeout=30):
    """Run Atlas MCP tool via Docker with Redis"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    docker_cmd = [
        "docker", "run", "-i", "--rm",
        "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
        "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
        "-e", "PROJECT_NAME=ATLAS_PERFORMANCE_TEST",
        "-e", "REDIS_URL=redis://host.docker.internal:6379/0",
        "-e", "ATLAS_LOG_PERFORMANCE=True",
        "--add-host", "host.docker.internal:host-gateway",
        "atlas-commands-mcp:latest",
        "python", "-m", "atlas_commands.server"
    ]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            docker_cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        execution_time = time.time() - start_time
        
        # Extract last JSON line from stdout (response)
        lines = result.stdout.strip().split('\n')
        json_response = None
        for line in reversed(lines):
            if line.startswith('{"jsonrpc"'):
                try:
                    json_response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        return {
            "tool": tool_name,
            "execution_time": execution_time,
            "success": result.returncode == 0,
            "response": json_response,
            "stderr_lines": len(result.stderr.split('\n')) if result.stderr else 0
        }
        
    except subprocess.TimeoutExpired:
        return {
            "tool": tool_name,
            "execution_time": timeout,
            "success": False,
            "response": None,
            "error": "timeout"
        }

def test_cache_warming():
    """Test cache warming performance"""
    print("=== Atlas Cache Warming & Performance Test ===")
    print(f"Started at: {datetime.now()}")
    print()
    
    # Phase 1: Initial cache population
    print("Phase 1: Cache Population")
    print("-" * 40)
    
    cache_population_tests = [
        ("warm_cache", {"namespace": "task", "operation": "list_project_tasks", "project_name": "ATLAS_PERFORMANCE_TEST"}),
        ("warm_cache", {"namespace": "memory", "operation": "search_patterns"}),
        ("warm_cache", {"namespace": "workflow", "operation": "command_recommendations"}),
    ]
    
    population_results = []
    for tool, args in cache_population_tests:
        print(f"Warming cache: {args['namespace']}")
        result = run_atlas_command(tool, args)
        population_results.append(result)
        print(f"  Time: {result['execution_time']:.2f}s | Success: {result['success']}")
    
    print()
    
    # Phase 2: Performance comparison
    print("Phase 2: Performance Benchmarking")
    print("-" * 40)
    
    # Test tasks that should benefit from caching
    performance_tests = [
        ("create_hierarchical_task", {
            "project_name": "ATLAS_PERFORMANCE_TEST",
            "task_name": "Cache Performance Test Task",
            "task_type": "task",
            "description": "Testing cache performance improvements",
            "domain": "performance"
        }),
        ("list_project_tasks", {
            "project_name": "ATLAS_PERFORMANCE_TEST",
            "recent_only": True,
            "page_size": 10
        }),
        ("get_cache_stats", {}),
        ("search_similar_tasks", {
            "query": "performance optimization caching",
            "max_results": 5
        }),
        ("adaptive_command_selection", {
            "task_description": "Optimize system performance",
            "domain": "performance",
            "previous_commands": ["test", "benchmark", "profile"]
        })
    ]
    
    # Run each test multiple times to measure consistency
    benchmark_results = []
    for tool, args in performance_tests:
        print(f"Benchmarking: {tool}")
        
        times = []
        for run in range(3):  # 3 runs per test
            result = run_atlas_command(tool, args, timeout=45)
            times.append(result['execution_time'])
            print(f"  Run {run+1}: {result['execution_time']:.2f}s | Success: {result['success']}")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        benchmark_results.append({
            "tool": tool,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "consistency": max_time - min_time,
            "times": times
        })
        
        print(f"  Average: {avg_time:.2f}s | Range: {min_time:.2f}s - {max_time:.2f}s")
        print()
    
    # Phase 3: Cache statistics
    print("Phase 3: Cache Analysis")
    print("-" * 40)
    
    cache_stats_result = run_atlas_command("get_cache_stats", {})
    print(f"Cache stats query time: {cache_stats_result['execution_time']:.2f}s")
    
    # Check Redis directly
    try:
        redis_info = subprocess.run(
            ["docker", "exec", "atlas-redis", "redis-cli", "info", "stats"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        redis_keys = subprocess.run(
            ["docker", "exec", "atlas-redis", "redis-cli", "dbsize"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print("Redis Status:")
        if redis_info.returncode == 0:
            for line in redis_info.stdout.split('\n'):
                if 'keyspace_hits' in line or 'keyspace_misses' in line:
                    print(f"  {line}")
        
        if redis_keys.returncode == 0:
            print(f"  Total keys: {redis_keys.stdout.strip()}")
            
    except Exception as e:
        print(f"Redis analysis failed: {e}")
    
    print()
    
    # Summary
    print("=== Performance Summary ===")
    total_tests = len(benchmark_results)
    avg_execution_time = sum(r['avg_time'] for r in benchmark_results) / total_tests
    most_consistent = min(benchmark_results, key=lambda x: x['consistency'])
    fastest = min(benchmark_results, key=lambda x: x['min_time'])
    
    print(f"Total tools tested: {total_tests}")
    print(f"Average execution time: {avg_execution_time:.2f}s")
    print(f"Fastest tool: {fastest['tool']} ({fastest['min_time']:.2f}s)")
    print(f"Most consistent: {most_consistent['tool']} (±{most_consistent['consistency']:.2f}s)")
    
    # Identify performance patterns
    fast_tools = [r for r in benchmark_results if r['avg_time'] < 5.0]
    slow_tools = [r for r in benchmark_results if r['avg_time'] > 10.0]
    
    if fast_tools:
        print(f"Fast tools (< 5s): {[r['tool'] for r in fast_tools]}")
    if slow_tools:
        print(f"Slow tools (> 10s): {[r['tool'] for r in slow_tools]}")
    
    # Save detailed results
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_type": "atlas_cache_performance",
        "cache_population": population_results,
        "benchmarks": benchmark_results,
        "cache_stats": cache_stats_result,
        "summary": {
            "total_tests": total_tests,
            "avg_execution_time": avg_execution_time,
            "fastest_tool": fastest['tool'],
            "fastest_time": fastest['min_time'],
            "most_consistent_tool": most_consistent['tool'],
            "consistency_range": most_consistent['consistency']
        }
    }
    
    with open("atlas_cache_performance_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: atlas_cache_performance_results.json")
    
    return results

if __name__ == "__main__":
    test_cache_warming()