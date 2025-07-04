"""Tool governance policies and configuration."""

# Shannon's entropy threshold for information quality
ENTROPY_THRESHOLD = 0.894

# Tool category mapping
TOOL_CATEGORIES = {
    # Memory Management Tools
    "mcp__memory__create_entities": "memory_management",
    "mcp__memory__add_observations": "memory_management", 
    "mcp__memory__create_relations": "memory_management",
    "mcp__memory__delete_entities": "memory_management",
    "mcp__memory__delete_observations": "memory_management",
    "mcp__memory__delete_relations": "memory_management",
    "mcp__memory__read_graph": "memory_management",
    "mcp__memory__search_nodes": "memory_management",
    "mcp__memory__open_nodes": "memory_management",
    
    # Project Memory Bank Tools
    "mcp__allpepper-memory-bank__memory_bank_write": "memory_management",
    "mcp__allpepper-memory-bank__memory_bank_read": "memory_management",
    "mcp__allpepper-memory-bank__memory_bank_update": "memory_management",
    "mcp__allpepper-memory-bank__list_projects": "memory_management",
    "mcp__allpepper-memory-bank__list_project_files": "memory_management",
    
    # Task Management Tools
    "mcp__atlas-commands__create_task_metadata": "task_management",
    "mcp__atlas-commands__update_task_status": "task_management",
    "mcp__atlas-commands__add_task_artifact": "task_management",
    "mcp__atlas-commands__get_task_context": "task_management",
    "mcp__atlas-commands__list_project_tasks": "task_management",
    "mcp__atlas-commands__create_hierarchical_task": "task_management",
    "mcp__atlas-commands__get_task_hierarchy": "task_management",
    "mcp__atlas-commands__update_hierarchical_status": "task_management",
    "mcp__atlas-commands__create_task_dependency": "task_management",
    "mcp__atlas-commands__get_progress_rollup": "task_management",
    "mcp__atlas-commands__query_hierarchical_context": "task_management",
    
    # Cache Management Tools
    "mcp__atlas-commands__get_cache_stats": "observability",
    "mcp__atlas-commands__invalidate_cache": "observability",
    "mcp__atlas-commands__warm_cache": "observability", 
    "mcp__atlas-commands__clear_all_cache": "observability",
    
    # Observability Tools
    "mcp__atlas-commands__get_observability_status": "observability",
    "mcp__atlas-commands__get_metrics_summary": "observability",
    "mcp__atlas-commands__export_traces": "observability",
    "mcp__atlas-commands__set_trace_sampling": "observability",
    "mcp__atlas-commands__memory_health_check": "observability",
    "mcp__atlas-commands__memory_analytics": "observability",
    
    # Workflow Intelligence Tools
    "mcp__atlas-commands__adaptive_command_selection": "workflow_intelligence",
    "mcp__atlas-commands__orchestrate_intelligent_tasks": "workflow_intelligence",
    "mcp__atlas-commands__analyze_workflow_patterns": "workflow_intelligence",
    "mcp__atlas-commands__track_progress_milestones": "workflow_intelligence",
    
    # Validation Tools
    "mcp__atlas-commands__validate_file_operation": "validation",
    "mcp__atlas-commands__validate_naming_convention": "validation",
    "mcp__atlas-commands__validate_code_standards": "validation",
    "mcp__atlas-commands__enforce_git_protocol": "validation",
    
    # GitHub Integration Tools
    "mcp__github__create_pull_request": "version_control",
    "mcp__github__get_pull_request": "version_control",
    "mcp__github__list_pull_requests": "version_control",
    "mcp__github__merge_pull_request": "version_control",
    "mcp__github__get_file_contents": "version_control",
    "mcp__github__create_or_update_file": "version_control",
    "mcp__github__list_commits": "version_control",
    "mcp__github__get_commit": "version_control",
    
    # Default category
    "default": "general"
}

# Tool usage policies by category
TOOL_POLICIES = {
    "memory_management": {
        "entropy_threshold": ENTROPY_THRESHOLD,
        "max_frequency_per_session": 15,
        "min_content_length": 20,
        "required_fields": ["content", "entities", "observations"],
        "required_context": ["project_name", "high_entropy_info"],
        "insight_keywords": [
            "surprising", "unexpected", "discovered", "insight", "issue",
            "pattern", "anomaly", "unusual", "edge case", "bug", "performance",
            "architecture", "bottleneck", "optimization", "failure", "vulnerability"
        ]
    },
    
    "task_management": {
        "max_frequency_per_session": 30,
        "required_workflow": ["TodoWrite", "create_hierarchical_task"],
        "status_progression": ["pending", "in_progress", "completed", "blocked", "cancelled"],
        "artifact_validation": True,
        "description_min_length": 10,
        "required_fields": ["task_id", "description"],
        "recommended_fields": ["project_name", "task_type", "priority"]
    },
    
    "observability": {
        "max_frequency_per_session": 20,
        "max_trace_depth": 5,
        "structured_logging": True,
        "error_escalation": True,
        "performance_thresholds": {
            "max_execution_time_ms": 10000,  # 10 seconds
            "max_memory_usage_mb": 100
        }
    },
    
    "workflow_intelligence": {
        "max_frequency_per_session": 10,
        "required_context": ["task_description", "domain"],
        "min_context_length": 15,
        "adaptive_learning": True
    },
    
    "validation": {
        "max_frequency_per_session": 25,
        "strict_validation": True,
        "fail_fast": True,
        "required_fields": ["validation_type", "target"]
    },
    
    "version_control": {
        "max_frequency_per_session": 20,
        "required_authentication": True,
        "branch_protection": True,
        "commit_validation": True
    },
    
    "general": {
        "max_frequency_per_session": 50,
        "basic_validation": True
    }
}

# Governance levels for progressive enforcement
GOVERNANCE_LEVELS = {
    "PERMISSIVE": {
        "entropy_threshold_multiplier": 0.8,  # Lower threshold
        "frequency_limit_multiplier": 1.5,    # Higher limits
        "warning_only": True
    },
    
    "STANDARD": {
        "entropy_threshold_multiplier": 1.0,  # Standard threshold
        "frequency_limit_multiplier": 1.0,    # Standard limits
        "warning_only": False
    },
    
    "STRICT": {
        "entropy_threshold_multiplier": 1.2,  # Higher threshold
        "frequency_limit_multiplier": 0.7,    # Lower limits
        "warning_only": False,
        "additional_validation": True
    }
}

# Default governance configuration
DEFAULT_GOVERNANCE_CONFIG = {
    "level": "STANDARD",
    "fail_secure": True,
    "education_first": True,
    "adaptive_learning": True,
    "performance_monitoring": True,
    "analytics_enabled": True
}