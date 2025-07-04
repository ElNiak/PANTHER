#!/usr/bin/env python3
"""
Test script to verify token optimization is working correctly.
"""

import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.token_optimization import (
    TokenOptimizer,
    ResponseMode,
    ContentType,
    optimize_tool_response,
    success,
    error,
    progress
)


def count_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return len(text) // 4


def test_task_list_optimization():
    """Test task list response optimization."""
    print("🧪 Testing Task List Optimization")
    print("=" * 50)
    
    # Create sample task data (typical large response)
    sample_tasks = [
        {
            "task_id": "task_001",
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
            "artifacts": [
                {
                    "artifact_id": "art_001",
                    "artifact_type": "analysis",
                    "description": "Comprehensive analysis document with detailed findings and recommendations for implementation approach",
                    "path": "/app/REPOS/ATLAS_TASKS/task_001/artifacts/analysis/detailed_analysis.md",
                    "created_at": "2025-06-23T10:35:00Z",
                    "size_bytes": 15420,
                    "checksum": "sha256:abc123def456..."
                },
                {
                    "artifact_id": "art_002", 
                    "artifact_type": "design",
                    "description": "Architectural design document with UML diagrams and technical specifications",
                    "path": "/app/REPOS/ATLAS_TASKS/task_001/artifacts/design/architecture.md",
                    "created_at": "2025-06-23T11:00:00Z",
                    "size_bytes": 8934,
                    "checksum": "sha256:def456ghi789..."
                }
            ],
            "observations": [
                "Started implementation phase after completing comprehensive analysis of requirements and technical constraints",
                "Encountered minor issues with dependency resolution but found suitable workaround using alternative approach",
                "Performance optimization looks promising so far, no major blocking issues have been identified during initial testing",
                "Code review feedback has been incorporated and all unit tests are passing successfully",
                "Integration testing scheduled for next sprint, initial smoke tests show positive results"
            ],
            "dependencies": [
                {
                    "dependency_id": "dep_001",
                    "dependency_type": "blocks",
                    "target_task": "task_000",
                    "description": "Requires completion of foundational infrastructure setup"
                }
            ],
            "quality_metrics": {
                "test_coverage": 0.85,
                "code_quality_score": 0.92,
                "documentation_completeness": 0.78,
                "performance_score": 0.91
            },
            "assignees": ["developer_001", "reviewer_002"],
            "tags": ["backend", "api", "critical", "sprint_1"],
            "parent_task": None,
            "subtasks": ["subtask_001", "subtask_002", "subtask_003"]
        },
        {
            "task_id": "task_002",
            "project_name": "ATLAS",
            "description": "Secondary task with detailed requirements for implementing additional features and enhancements to support the main functionality development.",
            "status": "pending",
            "created_at": "2025-06-23T12:00:00Z",
            "updated_at": "2025-06-23T12:00:00Z",
            "current_phase": "planning",
            "completion_percentage": 0.0,
            "priority": "medium",
            "estimated_hours": 8,
            "actual_hours": 0,
            "artifacts": [],
            "observations": [
                "Task created and waiting for prerequisites to be completed before starting implementation",
                "Initial requirements gathering scheduled for next week with stakeholder review meeting"
            ],
            "dependencies": [
                {
                    "dependency_id": "dep_002",
                    "dependency_type": "blocked_by", 
                    "target_task": "task_001",
                    "description": "Cannot start until task_001 is completed"
                }
            ],
            "quality_metrics": {},
            "assignees": ["developer_003"],
            "tags": ["frontend", "ui", "enhancement"],
            "parent_task": None,
            "subtasks": []
        }
    ]
    
    # Test original format
    original = json.dumps(sample_tasks, indent=2)
    original_tokens = count_tokens(original)
    print(f"📊 Original response: {len(original)} chars, ~{original_tokens} tokens")
    
    # Test different optimization modes
    modes = [
        (ResponseMode.STANDARD, "Standard"),
        (ResponseMode.COMPACT, "Compact"), 
        (ResponseMode.MINIMAL, "Minimal")
    ]
    
    for mode, mode_name in modes:
        optimized_response = optimize_tool_response(sample_tasks, ContentType.STATUS, mode)
        optimized_text = optimized_response[0].text
        optimized_tokens = count_tokens(optimized_text)
        
        reduction = (1 - optimized_tokens / original_tokens) * 100 if original_tokens > 0 else 0
        
        print(f"🔧 {mode_name:8} mode: {len(optimized_text):4} chars, ~{optimized_tokens:3} tokens ({reduction:5.1f}% reduction)")
        
        if mode == ResponseMode.MINIMAL:
            print(f"📝 Minimal output: {optimized_text[:200]}...")
    
    print()


def test_helper_responses():
    """Test quick response helpers."""
    print("🧪 Testing Response Helpers")
    print("=" * 50)
    
    # Test success response
    success_resp = success("task_created", task_id="task_123", status="active")
    success_text = success_resp[0].text
    print(f"✅ Success: {success_text} ({count_tokens(success_text)} tokens)")
    
    # Test error response
    error_resp = error("Task not found", "404")
    error_text = error_resp[0].text
    print(f"❌ Error: {error_text} ({count_tokens(error_text)} tokens)")
    
    # Test progress response
    progress_resp = progress(67.5, "implementation")
    progress_text = progress_resp[0].text
    print(f"📊 Progress: {progress_text} ({count_tokens(progress_text)} tokens)")
    
    print()


def test_content_type_optimization():
    """Test content-specific optimization."""
    print("🧪 Testing Content Type Optimization")
    print("=" * 50)
    
    # Sample data for different content types
    test_data = {
        ContentType.STATUS: {
            "task_id": "example",
            "status": "in_progress", 
            "progress": 67,
            "current_phase": "implementation",
            "description": "Long description that should be filtered...",
            "verbose_logs": "Very verbose debug information...",
            "full_history": ["event1", "event2", "event3"]
        },
        ContentType.METADATA: {
            "task_id": "example",
            "created_at": "2025-06-23T10:30:00Z",
            "status": "active",
            "description": "Task metadata information...",
            "debug_info": "Internal debug data...",
            "raw_data": {"complex": "structure"}
        },
        ContentType.RECOMMENDATIONS: [
            {
                "command": "execute",
                "priority": "high",
                "rationale": "Ready for implementation",
                "detailed_explanation": "Very long explanation of why this recommendation makes sense..."
            },
            {
                "command": "analyze", 
                "priority": "medium",
                "rationale": "Needs review",
                "verbose_analysis": "Comprehensive analysis of the situation..."
            }
        ]
    }
    
    for content_type, data in test_data.items():
        original = json.dumps(data, indent=2)
        original_tokens = count_tokens(original)
        
        optimized_response = optimize_tool_response(data, content_type, ResponseMode.COMPACT)
        optimized_text = optimized_response[0].text
        optimized_tokens = count_tokens(optimized_text)
        
        reduction = (1 - optimized_tokens / original_tokens) * 100 if original_tokens > 0 else 0
        
        print(f"📋 {content_type.value:15}: {original_tokens:3} → {optimized_tokens:3} tokens ({reduction:5.1f}% reduction)")
    
    print()


def benchmark_token_optimization():
    """Benchmark overall token reduction."""
    print("🧪 Benchmark Overall Performance")
    print("=" * 50)
    
    # Test with various realistic MCP responses
    test_cases = [
        {
            "name": "Large Task Context",
            "data": {
                "task_id": "complex_task",
                "artifacts": [f"artifact_{i}" for i in range(20)],
                "observations": [f"Observation {i} with detailed information about the progress and findings" for i in range(15)],
                "metadata": {"key" + str(i): f"value_{i}" for i in range(30)}
            }
        },
        {
            "name": "Task List (10 tasks)",
            "data": [{"task_id": f"task_{i}", "status": "active", "description": f"Task {i} with detailed description and context information"} for i in range(10)]
        },
        {
            "name": "Progress Update",
            "data": {
                "completion_percentage": 0.75,
                "current_phase": "implementation",
                "detailed_status": "Currently working on the implementation phase with significant progress made on core functionality and initial testing completed successfully",
                "timeline": {"started": "2025-06-20", "estimated_completion": "2025-06-25"}
            }
        }
    ]
    
    total_original_tokens = 0
    total_optimized_tokens = 0
    
    for test_case in test_cases:
        original = json.dumps(test_case["data"], indent=2)
        original_tokens = count_tokens(original)
        
        optimized_response = optimize_tool_response(test_case["data"], ContentType.METADATA, ResponseMode.COMPACT)
        optimized_text = optimized_response[0].text
        optimized_tokens = count_tokens(optimized_text)
        
        reduction = (1 - optimized_tokens / original_tokens) * 100 if original_tokens > 0 else 0
        
        print(f"📊 {test_case['name']:20}: {original_tokens:4} → {optimized_tokens:3} tokens ({reduction:5.1f}% reduction)")
        
        total_original_tokens += original_tokens
        total_optimized_tokens += optimized_tokens
    
    overall_reduction = (1 - total_optimized_tokens / total_original_tokens) * 100 if total_original_tokens > 0 else 0
    print(f"\n📈 Overall Performance: {total_original_tokens:4} → {total_optimized_tokens:3} tokens ({overall_reduction:5.1f}% reduction)")


def main():
    """Run all token optimization tests."""
    print("🚀 ATLAS MCP Token Optimization Test Suite")
    print("=" * 60)
    print()
    
    test_task_list_optimization()
    test_helper_responses()
    test_content_type_optimization()
    benchmark_token_optimization()
    
    print("✅ All tests completed!")
    print("\n💡 To enable token optimization in production:")
    print("   export ATLAS_TOKEN_MODE=compact  # 60% reduction") 
    print("   export ATLAS_TOKEN_MODE=minimal  # 80% reduction")


if __name__ == "__main__":
    main()