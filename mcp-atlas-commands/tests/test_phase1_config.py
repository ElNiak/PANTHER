#!/usr/bin/env python3
"""
Test Phase 1 configuration without MCP dependencies.
"""

import os
import sys
from pathlib import Path

# Add the source directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Test Phase 1 configuration."""
    print("🧪 Testing Phase 1 Configuration...")
    
    try:
        from atlas_commands.refactor_config import enable_phase_1, get_config
        
        # Enable Phase 1 features
        enable_phase_1()
        
        # Get current config
        config = get_config()
        
        print("\n✅ Phase 1 Configuration Successfully Loaded:")
        print(f"  Tool Registry Enabled: {config.enable_tool_registry}")
        print(f"  Error Handling Enabled: {config.enable_consistent_error_handling}")
        print(f"  Fallback to Legacy: {config.fallback_to_legacy}")
        
        # Test tool registry class (without MCP dependencies)
        from atlas_commands.tool_registry import ToolRegistry
        
        registry = ToolRegistry()
        print(f"\n✅ Tool Registry Class: {registry.__class__.__name__}")
        print(f"  Initial tools: {len(registry.list_tools())}")
        print(f"  Initial categories: {len(registry.list_categories())}")
        
        print(f"\n🎯 Phase 1 Infrastructure: READY")
        print("Configuration files loaded successfully!")
        
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())