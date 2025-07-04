#!/usr/bin/env python3
"""Comprehensive testing for Adaptive Command Selection MCP tool."""

import json
import asyncio
from datetime import datetime
from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector, 
    ProjectContext,
    ContextType
)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

def print_recommendation(rec, index):
    """Print a formatted recommendation."""
    print(f"{index}. Command: {rec.command}")
    print(f"   Confidence: {rec.confidence:.2f}")
    print(f"   Reasoning: {rec.reasoning}")
    print(f"   Risk Level: {rec.risk_level}")
    print(f"   Estimated Time: {rec.estimated_time:.1f} hours")
    print(f"   Prerequisites: {rec.prerequisites}")
    print(f"   Expected Outcome: {rec.expected_outcome}")
    print()

def test_context_analysis():
    """Test context analysis with various scenarios."""
    print_section("Testing Context Analysis")
    
    selector = AdaptiveCommandSelector()
    
    test_cases = [
        {
            "name": "Greenfield Project",
            "task": "Create new authentication system with OAuth2 support",
            "domain": "authentication",
            "phase": "planning",
            "previous": []
        },
        {
            "name": "Bug Fix",
            "task": "Fix login timeout issue causing user sessions to expire prematurely",
            "domain": "debugging",
            "phase": "investigation",
            "previous": ["investigate", "reproduce"]
        },
        {
            "name": "Performance Optimization",
            "task": "Optimize database queries to improve response time",
            "domain": "optimization",
            "phase": "analysis",
            "previous": ["profile", "analyze"]
        },
        {
            "name": "Refactoring",
            "task": "Refactor legacy authentication module to use modern patterns",
            "domain": "refactoring",
            "phase": "planning",
            "previous": ["analyze"]
        }
    ]
    
    for test in test_cases:
        print(f"\nTest Case: {test['name']}")
        print(f"Task: {test['task']}")
        
        context = selector.analyze_context(
            task_description=test['task'],
            domain=test['domain'],
            current_phase=test['phase'],
            previous_commands=test['previous'],
            project_state={"has_tests": True, "has_ci": True}
        )
        
        print(f"Analyzed Context:")
        print(f"  - Domain: {context.domain}")
        print(f"  - Complexity: {context.complexity}")
        print(f"  - Current Phase: {context.current_phase}")
        print(f"  - Success Indicators: {context.success_indicators}")
        print(f"  - Blocking Issues: {context.blocking_issues}")
        print(f"  - Available Resources: {context.available_resources}")

def test_command_recommendations():
    """Test command recommendations for different scenarios."""
    print_section("Testing Command Recommendations")
    
    selector = AdaptiveCommandSelector()
    
    scenarios = [
        {
            "name": "Starting New Feature",
            "context": ProjectContext(
                domain="development",
                complexity="complex",
                current_phase="planning",
                previous_commands=[],
                success_indicators=["feature_complete"],
                blocking_issues=[],
                available_resources=["basic_tools", "test_suite"]
            )
        },
        {
            "name": "Mid-Development",
            "context": ProjectContext(
                domain="development",
                complexity="moderate",
                current_phase="implementation",
                previous_commands=["explore", "plan", "design"],
                success_indicators=["tests_passing"],
                blocking_issues=[],
                available_resources=["basic_tools", "test_suite", "continuous_integration"]
            )
        },
        {
            "name": "Debugging Session",
            "context": ProjectContext(
                domain="debugging",
                complexity="complex",
                current_phase="investigation",
                previous_commands=["investigate"],
                success_indicators=["issue_resolved"],
                blocking_issues=["missing_test_setup"],
                available_resources=["basic_tools"]
            )
        },
        {
            "name": "Ready for Completion",
            "context": ProjectContext(
                domain="development",
                complexity="simple",
                current_phase="validation",
                previous_commands=["explore", "plan", "implement", "test"],
                success_indicators=["tests_passing", "deployment_ready"],
                blocking_issues=[],
                available_resources=["basic_tools", "test_suite", "continuous_integration"]
            )
        }
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        recommendations = selector.recommend_commands(
            context=scenario['context'],
            limit=5,
            include_alternatives=True
        )
        
        print(f"Generated {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print_recommendation(rec, i)

def test_learning_capability():
    """Test the learning from outcome functionality."""
    print_section("Testing Learning Capability")
    
    selector = AdaptiveCommandSelector()
    
    # Initial context
    context = ProjectContext(
        domain="automation",
        complexity="moderate",
        current_phase="implementation",
        previous_commands=["explore", "plan"],
        success_indicators=["automation_working"],
        blocking_issues=[],
        available_resources=["basic_tools", "test_suite"]
    )
    
    print("Initial Recommendations:")
    initial_recs = selector.recommend_commands(context, limit=3)
    for i, rec in enumerate(initial_recs, 1):
        print(f"{i}. {rec.command} (confidence: {rec.confidence:.2f})")
    
    # Learn from successful outcome
    print("\nLearning from successful outcome...")
    selector.learn_from_outcome(
        commands_used=["implement", "test", "verify"],
        context=context,
        outcome="success",
        execution_time=4.5,
        notes="Implementation went smoothly with TDD approach"
    )
    
    # Learn from failed outcome
    print("Learning from failed outcome...")
    failed_context = ProjectContext(
        domain="automation",
        complexity="moderate",
        current_phase="implementation",
        previous_commands=["plan"],  # Skipped explore
        success_indicators=["automation_working"],
        blocking_issues=[],
        available_resources=["basic_tools", "test_suite"]
    )
    
    selector.learn_from_outcome(
        commands_used=["implement", "deploy"],  # Skipped testing
        context=failed_context,
        outcome="failure",
        execution_time=2.0,
        notes="Deployment failed due to missing test coverage"
    )
    
    # Get recommendations after learning
    print("\nRecommendations after learning:")
    learned_recs = selector.recommend_commands(context, limit=3)
    for i, rec in enumerate(learned_recs, 1):
        print(f"{i}. {rec.command} (confidence: {rec.confidence:.2f})")
    
    # Show learning cache
    print("\nLearning Cache Summary:")
    for key, data in selector.success_cache.items():
        print(f"\nContext: {key}")
        print(f"  Successful patterns: {len(data['successful_patterns'])}")
        print(f"  Failed patterns: {len(data['failed_patterns'])}")

def test_edge_cases():
    """Test edge cases and error handling."""
    print_section("Testing Edge Cases")
    
    selector = AdaptiveCommandSelector()
    
    # Test 1: Empty previous commands
    print("Test 1: Empty command history")
    context = selector.analyze_context(
        task_description="Build something new",
        domain="general",
        current_phase="planning",
        previous_commands=[],
        project_state={}
    )
    recs = selector.recommend_commands(context, limit=3)
    print(f"Got {len(recs)} recommendations for empty history")
    
    # Test 2: Very long command history
    print("\nTest 2: Long command history")
    long_history = ["explore", "plan", "design", "implement", "test", "fix", "test", "review", "refactor"]
    context = selector.analyze_context(
        task_description="Complete the feature",
        domain="development",
        current_phase="completion",
        previous_commands=long_history,
        project_state={}
    )
    recs = selector.recommend_commands(context, limit=3)
    print(f"Got {len(recs)} recommendations for long history")
    
    # Test 3: Unknown domain
    print("\nTest 3: Unknown domain")
    context = selector.analyze_context(
        task_description="Do something unusual",
        domain="quantum_computing",
        current_phase="exploration",
        previous_commands=[],
        project_state={}
    )
    recs = selector.recommend_commands(context, limit=3)
    print(f"Got {len(recs)} recommendations for unknown domain")
    
    # Test 4: Complex task with all features
    print("\nTest 4: Complex scenario with all features")
    context = selector.analyze_context(
        task_description="Migrate entire authentication system to new architecture while maintaining zero downtime",
        domain="migration",
        current_phase="planning",
        previous_commands=["research", "analyze"],
        project_state={
            "has_tests": True,
            "has_ci": True,
            "has_docs": True,
            "custom_field": "ignored"
        }
    )
    recs = selector.recommend_commands(context, limit=5, include_alternatives=True)
    print(f"Got {len(recs)} recommendations for complex scenario")
    
    # Get confidence explanations
    print("\nConfidence Explanations for top 2:")
    for i, rec in enumerate(recs[:2], 1):
        explanation = selector.get_confidence_explanation(rec)
        print(f"\n{i}. {explanation['command']}:")
        print(f"   Confidence: {explanation['confidence']:.2f}")
        for factor, desc in explanation['factors'].items():
            print(f"   - {factor}: {desc}")

def test_context_type_classification():
    """Test context type classification logic."""
    print_section("Testing Context Type Classification")
    
    selector = AdaptiveCommandSelector()
    
    test_descriptions = [
        ("Create new microservice", "greenfield"),
        ("Fix login bug", "maintenance"),
        ("Refactor payment module", "refactoring"),
        ("Debug memory leak", "debugging"),
        ("Optimize query performance", "optimization"),
        ("Integrate third-party API", "integration"),
        ("Build new feature", "greenfield"),
        ("Investigate server crash", "debugging")
    ]
    
    for desc, expected in test_descriptions:
        context = selector.analyze_context(desc, "testing", "planning")
        # Use internal method to classify
        context_type = selector._classify_context_type(context)
        print(f"'{desc}' -> {context_type.value} (expected: {expected})")

def run_all_tests():
    """Run all test functions."""
    print_section("ADAPTIVE COMMAND SELECTOR COMPREHENSIVE TESTING")
    print(f"Started at: {datetime.now().isoformat()}")
    
    test_functions = [
        test_context_analysis,
        test_command_recommendations,
        test_learning_capability,
        test_edge_cases,
        test_context_type_classification
    ]
    
    for test_func in test_functions:
        try:
            test_func()
        except Exception as e:
            print(f"\nERROR in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print_section("Testing Complete")
    print(f"Finished at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    run_all_tests()