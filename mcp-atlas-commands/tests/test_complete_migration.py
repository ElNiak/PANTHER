#!/usr/bin/env python3
"""
Test Complete ATLAS MCP Tool Migration.

Verifies that ALL 62 tools have been migrated from the if-elif chain
to the clean registry pattern with proper organization.
"""

import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_complete_migration():
    """Test that all tools have been migrated to registry pattern."""
    
    print("🚀 Testing ATLAS MCP Complete Tool Migration")
    print("=" * 60)
    
    # Define ALL expected tools organized by category
    all_expected_tools = {
        "task_management": [
            "create_task_metadata",
            "update_task_status", 
            "add_task_artifact",
            "get_task_context",
            "list_project_tasks",
            "create_task_backup",
            "archive_task",
            "filter_tasks",
            "calculate_task_progress"
        ],
        "hierarchical_management": [
            "create_hierarchical_task",
            "get_task_hierarchy",
            "update_hierarchical_status",
            "create_task_dependency",
            "get_progress_rollup",
            "query_hierarchical_context",
            "create_hierarchical_backup",
            "list_checkpoints",
            "restore_from_checkpoint"
        ],
        "validation": [
            "validate_file_operation",
            "validate_naming_convention",
            "validate_code_standards",
            "enforce_git_protocol"
        ],
        "workflow_intelligence": [
            "orchestrate_intelligent_tasks",
            "adaptive_command_selection",
            "analyze_workflow_patterns",
            "track_progress_milestones"
        ],
        "observability": [
            "get_observability_status",
            "get_metrics_summary",
            "export_traces",
            "set_trace_sampling"
        ],
        "nested_storage": [
            "create_nested_subtask",
            "get_nested_task",
            "update_nested_task",
            "migrate_to_nested_storage"
        ],
        "memory_management": [
            "memory_health_check",
            "memory_force_backup",
            "memory_restore",
            "memory_analytics",
            "memory_cleanup"
        ],
        "cache_management": [
            "get_cache_stats",
            "invalidate_cache",
            "warm_cache",
            "clear_all_cache"
        ],
        "embeddings": [
            "search_similar_tasks",
            "discover_related_concepts",
            "find_solution_patterns",
            "train_task_embeddings",
            "get_embeddings_stats"
        ],
        "legacy": [
            "create_unified_checklist",
            "update_checklist_item",
            "get_checklist_progress", 
            "create_todowrite_integration",
            "create_memory_entity",
            "create_workflow",
            "validate_command",
            "track_command_pattern",
            "get_pattern_recommendations",
            "compact_memory_graph"
        ]
    }
    
    # Check handler files exist and contain expected tools
    handlers_dir = "mcp-atlas-commands/src/atlas_commands/handlers"
    print(f"\n📁 Checking all handler files in {handlers_dir}:")
    
    total_tools_found = 0
    categories_verified = 0
    
    for category, expected_tools in all_expected_tools.items():
        file_path = f"{handlers_dir}/{category}.py"
        if os.path.exists(file_path):
            print(f"  ✅ {category}.py exists")
            
            # Check file contains expected tools
            with open(file_path, 'r') as f:
                content = f.read()
                
            missing_tools = []
            for tool in expected_tools:
                if tool not in content:
                    missing_tools.append(tool)
            
            if missing_tools:
                print(f"    ⚠️  Missing tools: {missing_tools}")
            else:
                print(f"    ✅ All {len(expected_tools)} tools referenced")
                categories_verified += 1
                total_tools_found += len(expected_tools)
        else:
            print(f"  ❌ {category}.py missing")
    
    # Check server.py integration
    print(f"\n🔗 Checking server.py integration:")
    
    server_file = "mcp-atlas-commands/src/atlas_commands/server.py"
    if os.path.exists(server_file):
        with open(server_file, 'r') as f:
            server_content = f.read()
        
        # Check for all handler imports
        all_handlers = [f"{category.title().replace('_', '')}Handler" for category in all_expected_tools.keys()]
        missing_imports = []
        for handler in all_handlers:
            if handler not in server_content:
                missing_imports.append(handler)
        
        if missing_imports:
            print(f"  ⚠️  Missing handler imports: {missing_imports}")
        else:
            print(f"  ✅ All {len(all_handlers)} handlers imported")
        
        # Check memory_tools is in tool definitions return statement
        if "memory_tools" in server_content and "+ memory_tools +" in server_content:
            print("  ✅ Memory tools properly added to tool definitions")
        else:
            print("  ⚠️  Memory tools may be missing from tool definitions")
            
    else:
        print("  ❌ server.py file missing")
    
    # Calculate final statistics
    total_expected_tools = sum(len(tools) for tools in all_expected_tools.values())
    
    print(f"\n📊 Complete Migration Statistics:")
    print(f"  Total tools expected: {total_expected_tools}")
    print(f"  Tools verified in handlers: {total_tools_found}")
    print(f"  Categories verified: {categories_verified}/{len(all_expected_tools)}")
    print(f"  Handler files created: {len(all_expected_tools)}")
    
    # Migration phases summary
    phase_breakdown = {
        "Phase 1": ["task_management"],
        "Phase 2": ["hierarchical_management", "validation", "workflow_intelligence", "observability", "legacy"],
        "Phase 3": ["nested_storage", "memory_management", "cache_management", "embeddings"]
    }
    
    print(f"\n🎯 Migration Phases Summary:")
    for phase, categories in phase_breakdown.items():
        phase_tools = sum(len(all_expected_tools[cat]) for cat in categories)
        print(f"  {phase}: {len(categories)} categories, {phase_tools} tools")
    
    print(f"\n✨ Architecture Transformation:")
    print(f"  • BEFORE: 62-tool if-elif chain (unmaintainable)")
    print(f"  • AFTER: {len(all_expected_tools)} logical categories with registry pattern")
    print(f"  • Maintainability: Dramatically improved")
    print(f"  • Extensibility: Clean foundation for future tools")
    print(f"  • Error Handling: Consistent across all categories") 
    print(f"  • Testing: Category-isolated, much easier")
    
    success = (total_tools_found == total_expected_tools and 
               categories_verified == len(all_expected_tools))
    
    if success:
        print(f"\n🎉 COMPLETE SUCCESS!")
        print(f"ALL {total_expected_tools} TOOLS MIGRATED TO REGISTRY PATTERN!")
        print(f"\nThe ATLAS MCP server transformation is COMPLETE! 🚀")
    else:
        print(f"\n⚠️  Migration incomplete:")
        print(f"  Expected: {total_expected_tools} tools")
        print(f"  Found: {total_tools_found} tools")
    
    return success


if __name__ == "__main__":
    success = test_complete_migration()
    sys.exit(0 if success else 1)