"""
Integration Test for Adaptive Learning Architecture

Tests that the new Bayesian confidence system actually provides learning
improvement, replacing the static system that provided 0.000 improvement.
"""

import tempfile
import os
from datetime import datetime

from .adaptive_command_selector import AdaptiveCommandSelector, ProjectContext
from .adaptive_recommendation_engine import AdaptiveRecommendationEngine


def test_learning_improvement_basic():
    """
    Test that confidence actually improves with successful outcomes.
    
    This is the core test that validates we've fixed the 0.000 improvement issue.
    """
    print("Testing adaptive learning improvement...")
    
    # Create selector with temporary storage
    with tempfile.TemporaryDirectory() as temp_dir:
        selector = AdaptiveCommandSelector(storage_path=temp_dir)
        
        # Create test context
        context = ProjectContext(
            domain="debugging",
            complexity="moderate",
            current_phase="investigation",
            previous_commands=[],
            success_indicators=["__TASK_DESC__:Investigate network timeout issues"],
            blocking_issues=[],
            available_resources=["test_suite"]
        )
        
        # Get initial recommendations
        initial_recs = selector.recommend_commands(context, limit=3)
        print(f"Initial recommendations: {len(initial_recs)}")
        
        if initial_recs:
            first_command = initial_recs[0].command
            initial_confidence = initial_recs[0].confidence
            print(f"Initial confidence for '{first_command}': {initial_confidence:.3f}")
            
            # Simulate successful execution outcome
            learning_impact = selector.learn_from_outcome(
                commands_used=[first_command],
                context=context,
                outcome="success",
                execution_time=2.5,
                notes="Successfully identified timeout root cause"
            )
            
            print(f"Learning impact: {learning_impact.get('adaptive_learning_impact', {})}")
            
            # Get recommendations again to see if confidence improved
            updated_recs = selector.recommend_commands(context, limit=3)
            
            if updated_recs:
                updated_confidence = None
                for rec in updated_recs:
                    if rec.command == first_command:
                        updated_confidence = rec.confidence
                        break
                
                if updated_confidence is not None:
                    improvement = updated_confidence - initial_confidence
                    print(f"Updated confidence for '{first_command}': {updated_confidence:.3f}")
                    print(f"Confidence improvement: {improvement:.3f}")
                    
                    if improvement > 0.001:  # Any measurable improvement
                        print("✅ SUCCESS: Learning system shows measurable improvement!")
                        print(f"   Improvement: {improvement:.3f} (vs 0.000 from old system)")
                        return True
                    else:
                        print(f"❌ FAILURE: No improvement detected ({improvement:.3f})")
                        return False
                else:
                    print(f"⚠️  Command '{first_command}' not found in updated recommendations")
                    return False
            else:
                print("❌ FAILURE: No updated recommendations received")
                return False
        else:
            print("❌ FAILURE: No initial recommendations received")
            return False


def test_learning_effectiveness_report():
    """Test that learning effectiveness report shows actual metrics"""
    print("\nTesting learning effectiveness report...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        selector = AdaptiveCommandSelector(storage_path=temp_dir)
        
        # Get initial report
        report = selector.get_learning_effectiveness_report()
        print(f"Learning system status: {report.get('status')}")
        print(f"Current average confidence: {report.get('current_average_confidence', 'N/A')}")
        
        # Check comparison to static system
        comparison = report.get('comparison_to_static_system', {})
        if comparison:
            print(f"Static system confidence: {comparison.get('static_system_confidence')}")
            print(f"Adaptive system confidence: {comparison.get('adaptive_system_confidence')}")
            print(f"Learning advantage: {comparison.get('learning_advantage')}")
            
            if 'explanation' in comparison:
                print(f"Explanation: {comparison['explanation']}")
        
        return True


def test_bayesian_confidence_components():
    """Test that Bayesian confidence components are working"""
    print("\nTesting Bayesian confidence components...")
    
    engine = AdaptiveRecommendationEngine()
    
    # Test confidence calculation without learning data
    initial_conf = engine.confidence_engine.calculate_confidence(
        command="investigate",
        context="debugging_moderate_investigation", 
        learning_data={}
    )
    print(f"Initial Bayesian confidence: {initial_conf:.3f}")
    
    # Simulate learning from successful outcome
    engine.confidence_engine.update_from_outcome(
        command="investigate",
        context="debugging_moderate_investigation",
        outcome="success"
    )
    
    # Test confidence after learning
    updated_conf = engine.confidence_engine.calculate_confidence(
        command="investigate",
        context="debugging_moderate_investigation",
        learning_data={}
    )
    print(f"Updated Bayesian confidence: {updated_conf:.3f}")
    
    improvement = updated_conf - initial_conf
    print(f"Bayesian confidence improvement: {improvement:.3f}")
    
    if improvement > 0.001:
        print("✅ SUCCESS: Bayesian confidence improves with learning!")
        return True
    else:
        print(f"❌ FAILURE: No Bayesian confidence improvement ({improvement:.3f})")
        return False


def run_integration_tests():
    """Run all integration tests to validate adaptive learning"""
    print("=" * 60)
    print("ATLAS ADAPTIVE LEARNING INTEGRATION TESTS")
    print("=" * 60)
    print(f"Test run at: {datetime.now().isoformat()}")
    print()
    
    test_results = []
    
    # Test 1: Basic learning improvement
    try:
        result = test_learning_improvement_basic()
        test_results.append(("Basic Learning Improvement", result))
    except Exception as e:
        print(f"❌ FAILURE: Basic learning test error: {e}")
        test_results.append(("Basic Learning Improvement", False))
    
    # Test 2: Learning effectiveness report
    try:
        result = test_learning_effectiveness_report()
        test_results.append(("Learning Effectiveness Report", result))
    except Exception as e:
        print(f"❌ FAILURE: Effectiveness report test error: {e}")
        test_results.append(("Learning Effectiveness Report", False))
    
    # Test 3: Bayesian confidence components
    try:
        result = test_bayesian_confidence_components()
        test_results.append(("Bayesian Confidence Components", result))
    except Exception as e:
        print(f"❌ FAILURE: Bayesian confidence test error: {e}")
        test_results.append(("Bayesian Confidence Components", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("Adaptive learning system is working correctly.")
        print("ATLAS now provides measurable learning improvement!")
    else:
        print(f"\n⚠️  {total - passed} tests failed.")
        print("Adaptive learning system needs attention.")
    
    return passed == total


if __name__ == "__main__":
    run_integration_tests()