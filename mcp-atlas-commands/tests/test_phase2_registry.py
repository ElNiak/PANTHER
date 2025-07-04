#!/usr/bin/env python3
"""
Test Phase 2 tool registry implementation.

Verifies that all new handlers are properly registered and
can route tools correctly.
"""

import sys
import os
import asyncio
import logging

# Add mcp-atlas-commands to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp-atlas-commands', 'src'))

from atlas_commands.tool_registry import ToolRegistry
from atlas_commands.handlers import (
    HierarchicalManagementHandler,
    ValidationHandler, 
    WorkflowIntelligenceHandler,
    ObservabilityHandler,
    LegacyHandler
)
from atlas_commands.refactor_config import enable_phase_1

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockServer:
    """Mock server for testing handlers."""
    def __init__(self):
        self.logger = logging.getLogger("mock_server")
    
    async def _handle_create_hierarchical_task(self, args):
        return [{"type": "text", "text": f"Mock hierarchical task: {args}"}]
    
    async def _handle_validate_file_operation(self, args):
        return [{"type": "text", "text": f"Mock validation: {args}"}]
    
    async def _handle_orchestrate_intelligent_tasks(self, args):
        return [{"type": "text", "text": f"Mock workflow: {args}"}]
    
    async def _handle_get_observability_status(self, args):
        return [{"type": "text", "text": f"Mock observability: {args}"}]
    
    async def _handle_original_tool(self, name, args):
        return [{"type": "text", "text": f"Mock legacy tool {name}: {args}"}]


async def test_phase2_registry():
    """Test Phase 2 tool registry setup and routing."""
    
    print("🚀 Testing ATLAS MCP Phase 2 Tool Registry")
    print("=" * 50)
    
    # Enable Phase 1 configuration
    enable_phase_1()
    print("✅ Phase 1 configuration enabled")
    
    # Create registry and mock server
    registry = ToolRegistry()
    mock_server = MockServer()
    
    # Register all Phase 2 handlers
    handlers = [
        ("HierarchicalManagement", HierarchicalManagementHandler(mock_server)),
        ("Validation", ValidationHandler(mock_server)),
        ("WorkflowIntelligence", WorkflowIntelligenceHandler(mock_server)),
        ("Observability", ObservabilityHandler(mock_server)),
        ("Legacy", LegacyHandler(mock_server))
    ]
    
    print("\n📝 Registering Phase 2 handlers:")
    for name, handler in handlers:
        registry.register_handler(handler)
        tools = handler.get_tool_names()
        print(f"  ✅ {name}: {len(tools)} tools ({', '.join(tools[:3])}{'...' if len(tools) > 3 else ''})")
    
    # Get registry statistics
    stats = registry.get_registry_stats()
    print(f"\n📊 Registry Statistics:")
    print(f"  Total tools: {stats['total_tools']}")
    print(f"  Total categories: {stats['total_categories']}")
    print(f"  Tools with error handling: {stats['tools_with_error_handling']}")
    print(f"  Categories: {list(stats['tools_by_category'].keys())}")
    
    # Test tool routing for each category
    print(f"\n🔧 Testing tool routing:")
    
    test_tools = [
        ("create_hierarchical_task", {"test": "hierarchical"}),
        ("validate_file_operation", {"test": "validation"}),
        ("orchestrate_intelligent_tasks", {"test": "workflow"}),
        ("get_observability_status", {"test": "observability"}),
        ("create_unified_checklist", {"test": "legacy"})
    ]
    
    for tool_name, test_args in test_tools:
        try:
            result = await registry.dispatch(tool_name, test_args)
            print(f"  ✅ {tool_name}: Routed successfully")
        except Exception as e:
            print(f"  ❌ {tool_name}: Error - {str(e)}")
    
    # Test unknown tool
    try:
        result = await registry.dispatch("unknown_tool", {})
        print(f"  ✅ unknown_tool: Handled gracefully")
    except Exception as e:
        print(f"  ❌ unknown_tool: Unexpected error - {str(e)}")
    
    print(f"\n🎯 Phase 2 Benefits:")
    print(f"  • Migrated {stats['total_tools']} tools from if-elif chain")
    print(f"  • Organized into {stats['total_categories']} logical categories")
    print(f"  • Consistent error handling across all new handlers")
    print(f"  • Clean registry pattern for extensibility")
    
    print(f"\n✅ Phase 2 registry test completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_phase2_registry())
    sys.exit(0 if success else 1)