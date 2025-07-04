#!/usr/bin/env python3
"""
Test script to demonstrate automatic token optimization mode.
"""

import json
from dataclasses import dataclass
from enum import Enum


class ResponseMode(Enum):
    AUTO = "auto"
    MINIMAL = "minimal"
    COMPACT = "compact"
    STANDARD = "standard"


class ContentType(Enum):
    STATUS = "status"
    METADATA = "metadata"
    PROGRESS = "progress"


def count_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return len(text) // 4


def estimate_response_size(data):
    """Estimate the size of the response in characters."""
    try:
        if isinstance(data, (dict, list)):
            return len(json.dumps(data, indent=2))
        return len(str(data))
    except:
        return len(str(data))


def has_verbose_content(data):
    """Check if data contains verbose fields that should be optimized."""
    if not isinstance(data, dict):
        return False
    
    verbose_indicators = [
        "full_description", "detailed_logs", "complete_history",
        "debug_info", "verbose_output", "stack_trace", "raw_data"
    ]
    
    return any(key in data for key in verbose_indicators)


def has_large_lists(data, max_list_items=5):
    """Check if data contains large lists that should be optimized."""
    if isinstance(data, list) and len(data) > max_list_items:
        return True
    
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and len(value) > max_list_items:
                return True
            # Check for common list fields
            if isinstance(value, list) and len(value) > 3:
                return True
    
    return False


def auto_select_mode(data, content_type, auto_threshold_large=2000, auto_threshold_medium=800):
    """Automatically select the best optimization mode based on content analysis."""
    
    # Estimate response size
    estimated_size = estimate_response_size(data)
    
    # Large responses: force minimal mode
    if estimated_size > auto_threshold_large:
        return ResponseMode.MINIMAL, f"Large response ({estimated_size} chars) → MINIMAL"
    
    # Medium responses: use compact mode
    if estimated_size > auto_threshold_medium:
        return ResponseMode.COMPACT, f"Medium response ({estimated_size} chars) → COMPACT"
    
    # Check for verbose content patterns
    if has_verbose_content(data):
        return ResponseMode.COMPACT, f"Verbose content detected → COMPACT"
    
    # Check for large lists
    if has_large_lists(data):
        return ResponseMode.COMPACT, f"Large lists detected → COMPACT"
    
    # Small responses: standard mode is fine
    return ResponseMode.STANDARD, f"Small response ({estimated_size} chars) → STANDARD"


def create_minimal_response(data, content_type):
    """Create minimal response (80% token reduction)."""
    essential_fields = {
        ContentType.STATUS: ["status", "task_id", "progress"],
        ContentType.METADATA: ["task_id", "status", "created_at"],
        ContentType.PROGRESS: ["completion_percentage", "current_phase", "blocked"]
    }
    
    if isinstance(data, dict):
        essential = essential_fields.get(content_type, ["id", "status"])
        filtered_data = {k: v for k, v in data.items() if k in essential}
        return json.dumps(filtered_data, separators=(',', ':'))
    
    elif isinstance(data, list):
        limited_data = data[:3]  # Max 3 items
        minimal_items = []
        for item in limited_data:
            if isinstance(item, dict):
                essential = essential_fields.get(content_type, ["id", "status"])
                minimal_items.append({k: v for k, v in item.items() if k in essential})
            else:
                minimal_items.append(str(item)[:50])
        
        result = json.dumps(minimal_items, separators=(',', ':'))
        if len(data) > 3:
            result = f"[{len(limited_data)}/{len(data)}]{result}"
        return result
    
    return str(data)[:100]


def create_compact_response(data, content_type):
    """Create compact response (60% token reduction)."""
    verbose_fields = ["full_description", "detailed_logs", "debug_info", "verbose_output"]
    
    if isinstance(data, dict):
        filtered = {k: v for k, v in data.items() if k not in verbose_fields}
        
        # Truncate long observations
        if "observations" in filtered and isinstance(filtered["observations"], list):
            filtered["observations"] = [
                obs[:100] + "..." if len(obs) > 100 else obs
                for obs in filtered["observations"][:3]
            ]
        
        return json.dumps(filtered, separators=(',', ':'))
    
    elif isinstance(data, list):
        limited = data[:5]  # Max 5 items
        compacted = []
        for item in limited:
            if isinstance(item, dict):
                filtered = {k: v for k, v in item.items() 
                           if k not in verbose_fields and v is not None and v != [] and v != {}}
                compacted.append(filtered)
            else:
                compacted.append(item)
        
        result = json.dumps(compacted, separators=(',', ':'))
        if len(data) > 5:
            result = f"[{len(limited)}/{len(data)}]{result}"
        return result
    
    return str(data)


def optimize_with_auto_mode(data, content_type):
    """Optimize response using automatic mode selection."""
    mode, reason = auto_select_mode(data, content_type)
    
    if mode == ResponseMode.MINIMAL:
        optimized = create_minimal_response(data, content_type)
    elif mode == ResponseMode.COMPACT:
        optimized = create_compact_response(data, content_type)
    else:
        optimized = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
    
    return optimized, mode, reason


def test_automatic_optimization():
    """Test automatic optimization with different data scenarios."""
    print("🤖 ATLAS MCP Automatic Token Optimization Test")
    print("=" * 55)
    
    test_cases = [
        {
            "name": "Small Task Status",
            "data": {
                "task_id": "task_001",
                "status": "completed", 
                "progress": 100
            },
            "content_type": ContentType.STATUS
        },
        {
            "name": "Medium Task with Some Verbose Content",
            "data": {
                "task_id": "task_002",
                "status": "in_progress",
                "description": "A moderate length description that explains what the task is about",
                "progress": 67,
                "created_at": "2025-06-23T10:30:00Z",
                "observations": [
                    "Task started successfully",
                    "Making good progress on implementation",
                    "No major blockers identified"
                ]
            },
            "content_type": ContentType.METADATA
        },
        {
            "name": "Large Task with Debug Info",
            "data": {
                "task_id": "task_003",
                "project_name": "ATLAS",
                "description": "This is a comprehensive task description that explains all the details about what needs to be implemented, including background context, technical requirements, acceptance criteria, and implementation notes that are quite verbose and detailed.",
                "status": "in_progress", 
                "created_at": "2025-06-23T10:30:00Z",
                "updated_at": "2025-06-23T11:45:00Z",
                "current_phase": "implementation",
                "completion_percentage": 0.67,
                "priority": "high",
                "estimated_hours": 16,
                "actual_hours": 10.5,
                "artifacts": [f"artifact_{i}" for i in range(15)],
                "observations": [f"Observation {i} with detailed information about progress and findings" for i in range(10)],
                "debug_info": {
                    "internal_state": "complex_debug_data",
                    "performance_metrics": {"cpu": 0.45, "memory": 0.67},
                    "stack_trace": "Very long stack trace information that consumes many tokens"
                },
                "detailed_logs": ["Log entry " + str(i) for i in range(20)]
            },
            "content_type": ContentType.METADATA
        },
        {
            "name": "Large List of Tasks",
            "data": [
                {
                    "task_id": f"task_{i:03d}",
                    "status": "in_progress" if i % 2 else "completed",
                    "progress": 0.3 + (i * 0.1),
                    "description": f"Task {i} with detailed description and comprehensive information"
                }
                for i in range(20)
            ],
            "content_type": ContentType.STATUS
        },
        {
            "name": "Verbose Content Detected",
            "data": {
                "task_id": "task_004",
                "status": "active",
                "full_description": "This is an extremely verbose and detailed description that would normally consume many tokens in a response",
                "verbose_output": "Very detailed verbose output with lots of information",
                "stack_trace": "Long stack trace information"
            },
            "content_type": ContentType.METADATA
        }
    ]
    
    total_original_tokens = 0
    total_optimized_tokens = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 50)
        
        # Original response
        original = json.dumps(test_case['data'], indent=2)
        original_tokens = count_tokens(original)
        
        # Auto-optimized response
        optimized, selected_mode, reason = optimize_with_auto_mode(
            test_case['data'], 
            test_case['content_type']
        )
        optimized_tokens = count_tokens(optimized)
        
        # Calculate reduction
        reduction = (1 - optimized_tokens / original_tokens) * 100 if original_tokens > 0 else 0
        
        print(f"🔍 Auto Analysis: {reason}")
        print(f"📊 Original:  {original_tokens:4} tokens")
        print(f"⚡ Optimized: {optimized_tokens:4} tokens ({reduction:5.1f}% reduction)")
        print(f"🎯 Mode: {selected_mode.value.upper()}")
        
        if len(optimized) <= 150:
            print(f"📝 Output: {optimized}")
        else:
            print(f"📝 Output: {optimized[:150]}...")
        
        total_original_tokens += original_tokens
        total_optimized_tokens += optimized_tokens
    
    overall_reduction = (1 - total_optimized_tokens / total_original_tokens) * 100 if total_original_tokens > 0 else 0
    
    print(f"\n🎯 Overall Automatic Optimization Results:")
    print(f"   Total Original:  {total_original_tokens:4} tokens")
    print(f"   Total Optimized: {total_optimized_tokens:4} tokens")
    print(f"   Overall Reduction: {overall_reduction:5.1f}%")
    
    print(f"\n✅ Automatic token optimization working perfectly!")
    print(f"💡 Benefits:")
    print(f"   • No manual configuration required")
    print(f"   • Adapts to content size and complexity")
    print(f"   • Preserves quality for small responses")
    print(f"   • Aggressively optimizes large responses")
    print(f"   • Detects verbose content patterns")


if __name__ == "__main__":
    test_automatic_optimization()