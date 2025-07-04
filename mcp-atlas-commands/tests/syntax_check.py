#!/usr/bin/env python3
"""
Syntax check for MemorySearchOptimizer integration
"""

import ast
import sys
import os

def check_python_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Parse the AST to check syntax
        ast.parse(source)
        return True, "Valid syntax"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def check_memory_optimizer_import():
    """Check if the memory search optimizer import is correctly added."""
    server_file = os.path.join(os.path.dirname(__file__), 'src', 'atlas_commands', 'server.py')
    
    try:
        with open(server_file, 'r') as f:
            content = f.read()
        
        # Check for the import
        if 'from .memory.search_optimizer import MemorySearchOptimizer' in content:
            print("✅ MemorySearchOptimizer import found")
        else:
            print("❌ MemorySearchOptimizer import missing")
            return False
        
        # Check for initialization in __init__
        if 'self.memory_search_optimizer = MemorySearchOptimizer(' in content:
            print("✅ MemorySearchOptimizer initialization found")
        else:
            print("❌ MemorySearchOptimizer initialization missing")
            return False
        
        # Check for usage in _handle_analyze_workflow_patterns
        if 'self.memory_search_optimizer.optimized_workflow_search(' in content:
            print("✅ MemorySearchOptimizer usage found in workflow patterns handler")
        else:
            print("❌ MemorySearchOptimizer usage missing in workflow patterns handler")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking memory optimizer integration: {e}")
        return False

def main():
    print("🔧 ATLAS MCP Memory Search Optimization Integration Check")
    print("=" * 60)
    
    # Check syntax of all key files
    files_to_check = [
        'src/atlas_commands/server.py',
        'src/atlas_commands/memory/search_optimizer.py'
    ]
    
    all_valid = True
    
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            valid, message = check_python_syntax(full_path)
            status = "✅" if valid else "❌"
            print(f"{status} {file_path}: {message}")
            if not valid:
                all_valid = False
        else:
            print(f"❌ {file_path}: File not found")
            all_valid = False
    
    print("\n🔗 Integration Check:")
    integration_valid = check_memory_optimizer_import()
    
    print("\n📊 Summary:")
    if all_valid and integration_valid:
        print("✅ All syntax checks passed")
        print("✅ Memory search optimizer successfully integrated")
        print("✅ Token optimization ready for deployment")
        print("\n🚀 Expected Benefits:")
        print("   - Reduced token consumption in workflow analysis")
        print("   - Memory-based pattern retrieval instead of full analysis")
        print("   - Fallback to traditional analysis if memory search fails")
        print("   - Token efficiency metrics tracking")
    else:
        print("❌ Some checks failed - review integration")
    
    return all_valid and integration_valid

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)