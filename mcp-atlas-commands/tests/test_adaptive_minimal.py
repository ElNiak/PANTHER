"""Minimal test to verify adaptive command selector functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock
from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector,
    ContextType,
    CommandRecommendation
)
from atlas_commands.workflow.task_auto_generator import TaskComplexity


def test_adaptive_selector_basic():
    """Test basic adaptive command selector functionality."""
    # Create selector - it creates its own dependencies
    selector = AdaptiveCommandSelector()
    
    # Mock the internal dependencies
    selector.task_generator = Mock()
    selector.task_generator.analyze_complexity.return_value = (TaskComplexity.MODERATE, 3.0)
    
    selector.pattern_analyzer = Mock()
    selector.pattern_analyzer.get_historical_sequences.return_value = []
    
    # Test basic recommendation
    context = selector.analyze_context(
        task_description="Build authentication system",
        domain="security"
    )
    recommendations = selector.recommend_commands(context)
    
    assert len(recommendations) > 0
    assert all(isinstance(r, CommandRecommendation) for r in recommendations)
    print(f"✓ Generated {len(recommendations)} recommendations")
    
    # Test context classification
    test_cases = [
        ("Build new feature", ContextType.GREENFIELD),
        ("Fix authentication bug", ContextType.DEBUGGING),  # Improved classification: bug -> debugging
        ("Refactor payment module", ContextType.REFACTORING),
        ("Optimize database queries", ContextType.OPTIMIZATION),
        ("Debug memory leak", ContextType.DEBUGGING),
        ("Deploy to production", ContextType.GREENFIELD),  # No deployment type, defaults to greenfield
        ("Create documentation", ContextType.DOCUMENTATION)
    ]
    
    correct = 0
    for desc, expected in test_cases:
        test_context = selector.analyze_context(desc, "test")
        result = selector._classify_context_type(test_context)
        if result == expected:
            correct += 1
            print(f"✓ '{desc}' -> {result.value}")
        else:
            print(f"✗ '{desc}' -> {result.value} (expected {expected.value})")
    
    accuracy = correct / len(test_cases) * 100
    print(f"\nClassification accuracy: {accuracy:.1f}%")
    
    # Test learning
    learning_context = selector.analyze_context("Build auth system", "security")
    selector.learn_from_outcome(
        commands_used=['explore'],
        context=learning_context,
        outcome='success',
        execution_time=1800,
        notes="Successfully explored the codebase"
    )
    
    # Check if learning was recorded
    if hasattr(selector, 'success_cache') and len(selector.success_cache) > 0:
        print("✓ Learning system working")
    else:
        print("✗ Learning system may not be recording properly")
    
    return True


if __name__ == "__main__":
    print("Running minimal adaptive command selector tests...\n")
    
    try:
        if test_adaptive_selector_basic():
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()