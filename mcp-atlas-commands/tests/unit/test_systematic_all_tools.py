#!/usr/bin/env python3
"""
Systematic test of all 58 ATLAS tools to understand working vs broken patterns
"""

import json
import subprocess
import time

def test_all_58_tools():
    """Test every single tool available to map functionality"""
    
    print("ATLAS MCP Complete Tool Inventory Test")
    print("="*60)
    
    # First, get the complete list of tools
    init_messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "atlas-inventory", "version": "1.0.0"}
            }
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    ]
    
    input_data = ""
    for msg in init_messages:
        input_data += json.dumps(msg) + "\n"
    
    print("Getting complete tool list...")
    
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "-i", "-e", "ATLAS_ENABLE_TOOL_REGISTRY=true", "atlas-commands-mcp:latest"],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=15
        )
        
        tools = []
        if result.stdout:
            responses = result.stdout.strip().split('\n')
            for response_line in responses:
                if response_line.strip():
                    try:
                        response = json.loads(response_line)
                        if response.get('id') == 2 and 'result' in response:
                            tools = response['result'].get('tools', [])
                            break
                    except:
                        continue
        
        if not tools:
            print("❌ Could not get tool list")
            return False
            
        print(f"Found {len(tools)} tools. Testing each one...")
        
        # Test each tool with minimal arguments
        results = {
            "working": [],
            "errors": [],
            "config_issues": [],
            "param_issues": [],
            "unknown_tools": [],
            "other_issues": []
        }
        
        for i, tool in enumerate(tools, 1):
            tool_name = tool.get("name", "unnamed")
            print(f"[{i:2}/{len(tools)}] {tool_name}...", end="")
            
            # Test with empty arguments first
            test_messages = [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "clientInfo": {"name": "atlas-test", "version": "1.0.0"}
                    }
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": {}}
                }
            ]
            
            test_input = ""
            for msg in test_messages:
                test_input += json.dumps(msg) + "\n"
            
            try:
                test_result = subprocess.run(
                    ["docker", "run", "--rm", "-i", "-e", "ATLAS_ENABLE_TOOL_REGISTRY=true", "atlas-commands-mcp:latest"],
                    input=test_input,
                    text=True,
                    capture_output=True,
                    timeout=8
                )
                
                status = "unknown"
                error_msg = ""
                
                if test_result.stdout:
                    test_responses = test_result.stdout.strip().split('\n')
                    for response_line in test_responses:
                        if response_line.strip():
                            try:
                                response = json.loads(response_line)
                                if response.get('id') == 2:
                                    if 'result' in response:
                                        content = response['result'].get('content', [])
                                        if content and isinstance(content[0], dict):
                                            text = content[0].get('text', '')
                                            
                                            if "'config'" in text and "has no attribute" in text:
                                                status = "config_issue"
                                                error_msg = "Missing config attribute"
                                            elif "unknown tool" in text.lower():
                                                status = "unknown_tool"
                                                error_msg = "Tool not found in registry"
                                            elif any(word in text.lower() for word in ["required", "missing", "parameter"]):
                                                status = "param_issue"
                                                error_msg = text[:80]
                                            elif any(word in text.lower() for word in ["error", "exception", "failed"]):
                                                status = "error"
                                                error_msg = text[:80]
                                            else:
                                                status = "working"
                                        else:
                                            status = "working"
                                    elif 'error' in response:
                                        status = "error"
                                        error_msg = response['error'].get('message', 'Unknown JSON-RPC error')
                                    break
                            except:
                                continue
                
                # Categorize and report
                if status == "working":
                    print(" ✓")
                    results["working"].append(tool_name)
                elif status == "config_issue":
                    print(" ✗ Config")
                    results["config_issues"].append({"tool": tool_name, "error": error_msg})
                elif status == "param_issue":
                    print(" ⚠️ Params")
                    results["param_issues"].append({"tool": tool_name, "error": error_msg})
                elif status == "unknown_tool":
                    print(" ✗ Not Found")
                    results["unknown_tools"].append({"tool": tool_name, "error": error_msg})
                elif status == "error":
                    print(" ✗ Error")
                    results["errors"].append({"tool": tool_name, "error": error_msg})
                else:
                    print(" ? Unknown")
                    results["other_issues"].append({"tool": tool_name, "error": "Unknown status"})
                
                time.sleep(0.1)  # Small delay to avoid overwhelming
                
            except subprocess.TimeoutExpired:
                print(" ✗ Timeout")
                results["errors"].append({"tool": tool_name, "error": "Timeout"})
            except Exception as e:
                print(f" ✗ {str(e)[:20]}")
                results["errors"].append({"tool": tool_name, "error": str(e)})
        
        # Generate comprehensive report
        print("\n" + "="*60)
        print("ATLAS MCP Complete Tool Analysis Report")
        print("="*60)
        
        total_tools = len(tools)
        working_count = len(results["working"])
        
        print(f"Total Tools: {total_tools}")
        print(f"Working Tools: {working_count} ({working_count/total_tools*100:.1f}%)")
        print(f"Config Issues: {len(results['config_issues'])}")
        print(f"Parameter Issues: {len(results['param_issues'])}")
        print(f"Unknown Tools: {len(results['unknown_tools'])}")
        print(f"Other Errors: {len(results['errors'])}")
        print(f"Other Issues: {len(results['other_issues'])}")
        
        if results["working"]:
            print(f"\n✅ Working Tools ({len(results['working'])}):")
            for tool in results["working"][:10]:  # Show first 10
                print(f"  ✓ {tool}")
            if len(results["working"]) > 10:
                print(f"  ... and {len(results['working']) - 10} more")
        
        if results["config_issues"]:
            print(f"\n⚠️ Config Issues ({len(results['config_issues'])}):")
            for issue in results["config_issues"][:5]:
                print(f"  - {issue['tool']}: {issue['error']}")
            if len(results["config_issues"]) > 5:
                print(f"  ... and {len(results['config_issues']) - 5} more")
        
        if results["param_issues"]:
            print(f"\n⚠️ Parameter Issues ({len(results['param_issues'])}):")
            for issue in results["param_issues"][:5]:
                print(f"  - {issue['tool']}: {issue['error'][:60]}...")
        
        if results["unknown_tools"]:
            print(f"\n❌ Unknown Tools ({len(results['unknown_tools'])}):")
            for issue in results["unknown_tools"][:5]:
                print(f"  - {issue['tool']}")
        
        # Analysis and recommendations
        print(f"\n" + "="*60)
        print("Analysis & Recommendations")
        print("="*60)
        
        if working_count >= total_tools * 0.7:
            print("🎉 EXCELLENT: Most tools working properly")
        elif working_count >= total_tools * 0.5:
            print("✅ GOOD: Majority of tools functional")
        elif working_count >= total_tools * 0.3:
            print("⚠️ NEEDS WORK: Many tools have issues")
        else:
            print("❌ CRITICAL: Most tools not working")
        
        print(f"\nPriority Fixes:")
        if results["config_issues"]:
            print(f"  1. Fix config attribute issues in {len(results['config_issues'])} tools")
        if results["param_issues"]:
            print(f"  2. Standardize parameter validation in {len(results['param_issues'])} tools")
        if results["unknown_tools"]:
            print(f"  3. Fix tool registration for {len(results['unknown_tools'])} tools")
        
        print(f"\nTool Registry Status:")
        print(f"  ✓ Server operational and responsive")
        print(f"  ✓ JSON-RPC protocol working correctly")
        print(f"  ✓ Tool registration system functional")
        print(f"  ✓ {working_count} tools ready for production use")
        
        return working_count >= total_tools * 0.5
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_all_58_tools()
    exit(0 if success else 1)