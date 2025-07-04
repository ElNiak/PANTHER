"""Complete catalog of all 44 ATLAS MCP tools organized by category"""

from typing import Dict, List, Any

class ToolCatalog:
    """Central registry of all 44 ATLAS MCP tools"""
    
    # All 44 MCP tools organized by functional category
    TOOL_CATEGORIES = {
        "task_management": [
            "create_unified_checklist",
            "create_task_metadata", 
            "update_task_status",
            "add_task_artifact",
            "get_task_context",
            "list_project_tasks",
            "create_task_backup",
            "archive_task",
            "filter_tasks"
        ],
        "hierarchical": [
            "calculate_task_progress",
            "create_hierarchical_backup",
            "list_checkpoints", 
            "restore_from_checkpoint",
            "create_hierarchical_task",
            "get_task_hierarchy",
            "update_hierarchical_status",
            "create_task_dependency",
            "get_progress_rollup",
            "query_hierarchical_context"
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
        "storage_memory": [
            # Memory graph operations
            "create_entities",
            "create_relations", 
            "add_observations",
            "delete_entities",
            "delete_observations",
            "delete_relations",
            "read_graph",
            "search_nodes",
            "open_nodes"
        ],
        "observability": [
            # Observability and metrics
            "trace_operation",
            "collect_metrics",
            "log_structured", 
            "create_span",
            "add_span_attributes",
            "end_span",
            "export_traces",
            "query_metrics",
            "alert_threshold",
            "dashboard_update",
            "health_check",
            "performance_baseline",
            "anomaly_detection"
        ]
    }
    
    @classmethod
    def get_all_tools(cls) -> List[str]:
        """Get flat list of all 44 tools"""
        all_tools = []
        for category_tools in cls.TOOL_CATEGORIES.values():
            all_tools.extend(category_tools)
        return all_tools
    
    @classmethod
    def get_tool_count(cls) -> int:
        """Get total tool count"""
        return len(cls.get_all_tools())
    
    @classmethod
    def get_category_tools(cls, category: str) -> List[str]:
        """Get tools for specific category"""
        return cls.TOOL_CATEGORIES.get(category, [])
    
    @classmethod
    def get_tool_category(cls, tool_name: str) -> str:
        """Find which category a tool belongs to"""
        for category, tools in cls.TOOL_CATEGORIES.items():
            if tool_name in tools:
                return category
        return "unknown"
    
    @classmethod
    def get_test_parameters(cls, tool_name: str) -> Dict[str, Any]:
        """Get appropriate test parameters for each tool"""
        
        # Task Management Tools
        task_mgmt_params = {
            "create_unified_checklist": {
                "command_name": "test_command",
                "task_id": "test_task_001", 
                "title": "Test Checklist",
                "items": ["item1", "item2"]
            },
            "create_task_metadata": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001",
                "task_type": "testing",
                "description": "Integration test task"
            },
            "update_task_status": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001", 
                "status": "active"
            },
            "add_task_artifact": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001",
                "artifact_type": "analysis",
                "content": "Test artifact content",
                "filename": "test_artifact.md"
            },
            "get_task_context": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            },
            "list_project_tasks": {
                "project_name": "TEST_PROJECT"
            },
            "create_task_backup": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            },
            "archive_task": {
                "project_name": "TEST_PROJECT", 
                "task_id": "test_task_001"
            },
            "filter_tasks": {
                "project_name": "TEST_PROJECT",
                "status": "active"
            }
        }
        
        # Hierarchical Tools
        hierarchical_params = {
            "calculate_task_progress": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            },
            "create_hierarchical_backup": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            },
            "list_checkpoints": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            },
            "restore_from_checkpoint": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001", 
                "checkpoint_id": "test_checkpoint_001"
            },
            "create_hierarchical_task": {
                "project_name": "TEST_PROJECT",
                "task_name": "test-hierarchical",
                "task_type": "task",
                "description": "Test hierarchical task",
                "domain": "testing"
            },
            "get_task_hierarchy": {
                "project_name": "TEST_PROJECT",
                "root_task_id": "test_task_001"
            },
            "update_hierarchical_status": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001",
                "status": "active"
            },
            "create_task_dependency": {
                "project_name": "TEST_PROJECT",
                "from_task_id": "test_task_001",
                "to_task_id": "test_task_002", 
                "dependency_type": "blocks"
            },
            "get_progress_rollup": {
                "project_name": "TEST_PROJECT",
                "root_task_id": "test_task_001"
            },
            "query_hierarchical_context": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            }
        }
        
        # Validation Tools
        validation_params = {
            "validate_file_operation": {
                "operation": "create",
                "file_path": "/tmp/test_file.txt"
            },
            "validate_naming_convention": {
                "name": "test_function",
                "type": "function"
            },
            "validate_code_standards": {
                "file_path": "/tmp/test_code.py"
            },
            "enforce_git_protocol": {
                "action": "status"
            }
        }
        
        # Workflow Intelligence Tools
        workflow_params = {
            "orchestrate_intelligent_tasks": {
                "task_context": {
                    "description": "Test task orchestration",
                    "complexity": "simple",
                    "domain": "testing"
                }
            },
            "adaptive_command_selection": {
                "task_description": "Test adaptive command selection",
                "domain": "testing"
            },
            "analyze_workflow_patterns": {
                "workflow_data": [{
                    "command_sequence": ["test_command"],
                    "outcome": "success",
                    "timestamps": ["2025-06-22T15:00:00"]
                }]
            },
            "track_progress_milestones": {
                "task_id": "test_task_001"
            }
        }
        
        # Storage/Memory Tools
        storage_params = {
            "create_entities": {
                "entities": [{
                    "name": "TestEntity",
                    "entityType": "TestType",
                    "observations": ["Test observation"]
                }]
            },
            "create_relations": {
                "relations": [{
                    "from": "TestEntity1", 
                    "to": "TestEntity2",
                    "relationType": "test_relation"
                }]
            },
            "add_observations": {
                "observations": [{
                    "entityName": "TestEntity",
                    "contents": ["New test observation"]
                }]
            },
            "delete_entities": {
                "entityNames": ["TestEntity"]
            },
            "delete_observations": {
                "deletions": [{
                    "entityName": "TestEntity",
                    "observations": ["Old observation"]
                }]
            },
            "delete_relations": {
                "relations": [{
                    "from": "TestEntity1",
                    "to": "TestEntity2", 
                    "relationType": "test_relation"
                }]
            },
            "read_graph": {},
            "search_nodes": {
                "query": "test query"
            },
            "open_nodes": {
                "names": ["TestEntity"]
            }
        }
        
        # Observability Tools
        observability_params = {
            "trace_operation": {
                "operation_name": "test_operation",
                "operation_type": "test"
            },
            "collect_metrics": {
                "metric_name": "test_metric",
                "value": 1.0
            },
            "log_structured": {
                "level": "info",
                "message": "Test log message"
            },
            "create_span": {
                "span_name": "test_span"
            },
            "add_span_attributes": {
                "attributes": {"test_key": "test_value"}
            },
            "end_span": {},
            "export_traces": {},
            "query_metrics": {
                "metric_name": "test_metric"
            },
            "alert_threshold": {
                "metric": "test_metric",
                "threshold": 10.0
            },
            "dashboard_update": {
                "dashboard_name": "test_dashboard"
            },
            "health_check": {},
            "performance_baseline": {
                "operation": "test_operation"
            },
            "anomaly_detection": {
                "metric": "test_metric"
            }
        }
        
        # Combine all parameter maps
        all_params = {
            **task_mgmt_params,
            **hierarchical_params, 
            **validation_params,
            **workflow_params,
            **storage_params,
            **observability_params
        }
        
        # Return specific params or generic fallback
        return all_params.get(tool_name, {"test": True})
    
    @classmethod
    def validate_catalog(cls) -> Dict[str, Any]:
        """Validate the catalog completeness"""
        all_tools = cls.get_all_tools()
        tool_count = len(all_tools)
        
        # Check for duplicates
        unique_tools = set(all_tools)
        has_duplicates = len(unique_tools) != tool_count
        
        # Check categories
        category_counts = {
            category: len(tools) 
            for category, tools in cls.TOOL_CATEGORIES.items()
        }
        
        return {
            "total_tools": tool_count,
            "expected_tools": 44,
            "is_complete": tool_count == 44,
            "has_duplicates": has_duplicates,
            "duplicate_count": tool_count - len(unique_tools),
            "category_counts": category_counts,
            "categories": list(cls.TOOL_CATEGORIES.keys())
        }

# Validation check
if __name__ == "__main__":
    validation = ToolCatalog.validate_catalog()
    print("Tool Catalog Validation:")
    print(f"Total Tools: {validation['total_tools']}")
    print(f"Expected: {validation['expected_tools']}")
    print(f"Complete: {validation['is_complete']}")
    print(f"Categories: {validation['categories']}")
    print(f"Category Counts: {validation['category_counts']}")