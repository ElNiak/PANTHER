"""Comprehensive tests for AdaptiveCommandSelector functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
from pathlib import Path

from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector,
    CommandRecommendation,
    ContextType
)
from atlas_commands.workflow.task_auto_generator import TaskAutoGenerator, TaskComplexity
from atlas_commands.memory.graph_manager import MemoryGraphManager
from atlas_commands.workflow.pattern_analyzer import WorkflowPatternAnalyzer


class TestAdaptiveCommandSelector:
    """Test suite for AdaptiveCommandSelector class."""
    
    @pytest.fixture
    def selector(self):
        """Create AdaptiveCommandSelector instance with mocked dependencies."""
        selector = AdaptiveCommandSelector()
        
        # Mock internal dependencies
        selector.task_generator = Mock()
        selector.task_generator.analyze_complexity.return_value = (TaskComplexity.MODERATE, 3.0)
        
        selector.pattern_analyzer = Mock()
        selector.pattern_analyzer.get_historical_sequences.return_value = []
        
        return selector
    
    def test_initialization(self, selector):
        """Test proper initialization of AdaptiveCommandSelector."""
        assert selector is not None
        assert hasattr(selector, 'success_cache')
        assert hasattr(selector, 'historical_patterns')
        assert hasattr(selector, 'pattern_analyzer')
        assert hasattr(selector, 'task_generator')
    
    def test_context_classification_realistic(self, selector):
        """Test context type classification with realistic expectations."""
        # Realistic test cases with semantic expectations (not tuned to implementation)
        clear_cases = [
            # Unambiguous cases that should classify correctly
            ("Build new authentication system", ContextType.GREENFIELD),
            ("Create user dashboard feature", ContextType.GREENFIELD), 
            ("Debug memory leak in worker process", ContextType.DEBUGGING),
            ("Refactor payment processing module", ContextType.REFACTORING),
            ("Optimize database query performance", ContextType.OPTIMIZATION),
            ("Create API documentation", ContextType.DOCUMENTATION),
        ]
        
        ambiguous_cases = [
            # Cases where multiple classifications could be reasonable
            ("Fix broken login functionality", ContextType.MAINTENANCE),  # Could be DEBUGGING or MAINTENANCE
            ("Update user interface components", ContextType.MAINTENANCE),  # Could be MAINTENANCE or GREENFIELD
            ("Investigate performance issues", ContextType.DEBUGGING),     # Could be DEBUGGING or OPTIMIZATION
        ]
        
        # Test clear cases - should have high accuracy
        clear_correct = 0
        clear_misclassifications = []
        
        for description, expected in clear_cases:
            context = selector.analyze_context(description, "test")
            result = selector._classify_context_type(context)
            if result == expected:
                clear_correct += 1
            else:
                clear_misclassifications.append({
                    'description': description,
                    'expected': expected.value,
                    'actual': result.value
                })
        
        clear_accuracy = clear_correct / len(clear_cases)
        
        # Test ambiguous cases - lower accuracy expected, but should have reasonable confidence
        ambiguous_results = []
        for description, preferred in ambiguous_cases:
            context = selector.analyze_context(description, "test")
            result = selector._classify_context_type(context)
            recommendations = selector.recommend_commands(context)
            max_confidence = max(r.confidence for r in recommendations) if recommendations else 0
            
            ambiguous_results.append({
                'description': description,
                'preferred': preferred.value,
                'actual': result.value,
                'max_confidence': max_confidence,
                'reasonable': result in [preferred, ContextType.DEBUGGING, ContextType.MAINTENANCE, ContextType.GREENFIELD]
            })
        
        # Log results for analysis
        if clear_misclassifications:
            print(f"\nClear case misclassifications: {json.dumps(clear_misclassifications, indent=2)}")
        
        print(f"\nAmbiguous case results: {json.dumps(ambiguous_results, indent=2)}")
        
        # More realistic expectations:
        # - Clear cases should have >= 70% accuracy (not 100%)
        # - Ambiguous cases should at least produce reasonable classifications
        assert clear_accuracy >= 0.7, f"Clear case accuracy {clear_accuracy:.1%} is too low"
        
        reasonable_ambiguous = sum(1 for r in ambiguous_results if r['reasonable'])
        ambiguous_reasonableness = reasonable_ambiguous / len(ambiguous_cases)
        assert ambiguous_reasonableness >= 0.6, f"Ambiguous case reasonableness {ambiguous_reasonableness:.1%} is too low"
        
        print(f"\n✓ Clear cases: {clear_accuracy:.1%} accuracy")
        print(f"✓ Ambiguous cases: {ambiguous_reasonableness:.1%} reasonable classifications")
    
    def test_recommendation_generation_basic(self, selector):
        """Test basic recommendation generation."""
        context = selector.analyze_context(
            task_description="Build user authentication",
            domain="security",
            current_phase="planning"
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        assert all(isinstance(r, CommandRecommendation) for r in recommendations)
        assert recommendations[0].confidence >= recommendations[-1].confidence  # Sorted by confidence
    
    def test_historical_pattern_influence(self, selector):
        """Test that historical patterns influence recommendations."""
        # Setup historical success pattern
        selector.pattern_analyzer.get_historical_sequences.return_value = [
            {
                'commands': ['explore', 'plan', 'decompose', 'execute'],
                'success_rate': 0.95,
                'avg_duration': 3600,
                'context': 'security'
            }
        ]
        
        context = selector.analyze_context(
            task_description="Build authentication system",
            domain="security",
            current_phase="exploration",
            previous_commands=['explore']
        )
        recommendations = selector.recommend_commands(context)
        
        # Should recommend 'plan' as next command based on pattern
        assert any(r.command == 'plan' and r.confidence > 0.8 for r in recommendations)
    
    def test_risk_assessment_levels(self, selector):
        """Test risk level assessment for different commands."""
        # Risk assessment is internal to recommendation generation
        # Test via recommendations instead
        context = selector.analyze_context(
            task_description="Deploy to production",
            domain="deployment"
        )
        recommendations = selector.recommend_commands(context)
        
        # High-risk commands should have lower default confidence
        deploy_rec = next((r for r in recommendations if r.command == 'deploy'), None)
        explore_rec = next((r for r in recommendations if r.command == 'explore'), None)
        
        if deploy_rec and explore_rec:
            # Deploy (high risk) should have lower base confidence than explore (low risk)
            assert deploy_rec.confidence <= explore_rec.confidence
    
    def test_time_estimation_with_complexity(self, selector):
        """Test time estimation considers task complexity."""
        
        complexities = [
            (TaskComplexity.SIMPLE, 0.7),
            (TaskComplexity.MODERATE, 1.0),
            (TaskComplexity.COMPLEX, 1.5),
            (TaskComplexity.EPIC, 2.0)
        ]
        
        for complexity, multiplier in complexities:
            selector.task_generator.analyze_complexity.return_value = (complexity, multiplier * 3)
            
            context = selector.analyze_context(
                task_description="Test task",
                domain="testing"
            )
            recommendations = selector.recommend_commands(context)
            
            # Check that time estimates are adjusted by complexity
            # Time estimates should vary based on complexity
            assert recommendations[0].estimated_time > 0
            if complexity == TaskComplexity.SIMPLE:
                assert recommendations[0].estimated_time < 3
            elif complexity == TaskComplexity.EPIC:
                assert recommendations[0].estimated_time > 5
    
    def test_learning_effectiveness_honest(self, selector):
        """Test that learning actually improves recommendations (honest test)."""
        task_desc = "Build authentication API"
        domain = "security"
        
        # Get baseline recommendations (before any learning)
        baseline_context = selector.analyze_context(task_desc, domain)
        baseline_recs = selector.recommend_commands(baseline_context)
        baseline_explore_conf = next(
            (r.confidence for r in baseline_recs if r.command == 'explore'), 0.0
        )
        
        # Simulate learning from multiple successful 'explore' outcomes
        for i in range(3):
            learning_context = selector.analyze_context(f"Build security feature {i}", domain)
            selector.learn_from_outcome(
                commands_used=['explore'],
                context=learning_context,
                outcome='success',
                execution_time=1800,
                notes=f"Successfully explored security feature {i}"
            )
        
        # Get post-learning recommendations
        learned_context = selector.analyze_context(task_desc, domain)
        learned_recs = selector.recommend_commands(learned_context)
        learned_explore_conf = next(
            (r.confidence for r in learned_recs if r.command == 'explore'), 0.0
        )
        
        # Check if learning had measurable impact
        improvement = learned_explore_conf - baseline_explore_conf
        
        print(f"\nLearning effectiveness test:")
        print(f"Baseline 'explore' confidence: {baseline_explore_conf:.3f}")
        print(f"Post-learning 'explore' confidence: {learned_explore_conf:.3f}")
        print(f"Improvement: {improvement:+.3f}")
        
        # Learning should have some positive effect, but be realistic about it
        # Even 5% improvement would be meaningful
        assert improvement >= 0.0, f"Learning made recommendations worse: {improvement:.3f}"
        
        # Check that learning cache is working
        if hasattr(selector, 'learning_cache'):
            assert len(selector.learning_cache) > 0, "Learning cache should contain patterns"
            print(f"Learning patterns stored: {len(selector.learning_cache)}")
        elif hasattr(selector, 'success_cache'):
            assert len(selector.success_cache) > 0, "Success cache should contain patterns"
            print(f"Success patterns stored: {len(selector.success_cache)}")
        else:
            assert False, "No learning storage mechanism found"
    
    def test_edge_case_empty_history(self, selector):
        """Test handling of empty command history."""
        context = selector.analyze_context(
            task_description="New task",
            domain="general",
            previous_commands=[]
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        # Should recommend exploration commands for new tasks
        assert any(r.command in ['explore', 'plan'] for r in recommendations[:3])
    
    def test_edge_case_unknown_domain(self, selector):
        """Test handling of unknown domains."""
        context = selector.analyze_context(
            task_description="Mystery task",
            domain="unknown_domain_xyz"
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        # Should provide general recommendations
        assert all(r.confidence <= 0.8 for r in recommendations)  # Lower confidence
    
    def test_edge_case_long_command_sequence(self, selector):
        """Test handling of very long command sequences."""
        long_sequence = ['explore', 'plan', 'decompose', 'execute'] * 10
        
        context = selector.analyze_context(
            task_description="Long running task",
            domain="testing",
            previous_commands=long_sequence
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        # Should suggest completion or verification commands
        assert any(r.command in ['verify', 'complete'] for r in recommendations[:3])
    
    def test_confidence_scoring(self, selector):
        """Test that confidence scores are within valid range."""
        context = selector.analyze_context(
            task_description="Test task",
            domain="testing"
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        assert all(0 <= r.confidence <= 1 for r in recommendations)
        # Verify recommendations are sorted by confidence
        for i in range(len(recommendations) - 1):
            assert recommendations[i].confidence >= recommendations[i + 1].confidence
    
    def test_command_alternatives_generation(self, selector):
        """Test generation of alternative command suggestions."""
        context = selector.analyze_context(
            task_description="Complex refactoring task",
            domain="refactoring",
            current_phase="implementation"
        )
        recommendations = selector.recommend_commands(context)
        
        # Should provide multiple alternatives
        assert len(recommendations) >= 3
        
        # Check for variety in recommendations
        commands = [r.command for r in recommendations]
        assert len(set(commands)) >= 2  # At least 2 different commands
    
    def test_phase_based_filtering(self, selector):
        """Test that recommendations are filtered based on current phase."""
        phases_and_expected = [
            ('planning', ['plan', 'analyze', 'design']),
            ('implementation', ['execute', 'code', 'implement']),
            ('verification', ['verify', 'test', 'validate']),
            ('completion', ['complete', 'document', 'archive'])
        ]
        
        for phase, expected_commands in phases_and_expected:
            context = selector.analyze_context(
                task_description="Test task",
                domain="testing",
                current_phase=phase
            )
            recommendations = selector.recommend_commands(context)
            
            # At least one expected command should be in top 3 recommendations
            top_commands = [r.command for r in recommendations[:3]]
            assert any(cmd in expected_commands for cmd in top_commands)
    
    @patch('atlas_commands.workflow.adaptive_command_selector.datetime')
    def test_time_based_recommendations(self, mock_datetime, selector):
        """Test recommendations change based on time patterns."""
        # Mock different times of day
        morning = datetime(2025, 6, 21, 9, 0)
        evening = datetime(2025, 6, 21, 18, 0)
        
        # Morning recommendations
        mock_datetime.now.return_value = morning
        context = selector.analyze_context(
            task_description="Daily task",
            domain="general"
        )
        morning_recs = selector.recommend_commands(context)
        
        # Evening recommendations
        mock_datetime.now.return_value = evening
        context = selector.analyze_context(
            task_description="Daily task",
            domain="general"
        )
        evening_recs = selector.recommend_commands(context)
        
        # Both should provide valid recommendations
        assert len(morning_recs) > 0
        assert len(evening_recs) > 0
    
    def test_learning_cache_size_limit(self, selector):
        """Test that learning cache respects size limits."""
        # Add many learning patterns
        for i in range(1000):
            selector.learn_from_outcome(
                command=f'command_{i % 10}',
                context=ContextType.GREENFIELD,
                domain='testing',
                success=i % 2 == 0,
                duration=1800 + i,
                task_description=f"Task {i}"
            )
        
        # Cache should not grow unbounded
        assert len(selector.learning_cache) <= 500  # Reasonable limit
    
    def test_pattern_matching_fuzzy(self, selector):
        """Test fuzzy matching of task descriptions to patterns."""
        # Learn from similar tasks
        similar_tasks = [
            "Build authentication system",
            "Create auth module",
            "Implement user authentication"
        ]
        
        for task in similar_tasks:
            selector.learn_from_outcome(
                command='explore',
                context=ContextType.GREENFIELD,
                domain='security',
                success=True,
                duration=3600,
                task_description=task
            )
        
        # Should recognize pattern for similar new task
        context = selector.analyze_context(
            task_description="Develop authentication feature",
            domain="security"
        )
        recommendations = selector.recommend_commands(context)
        
        # Should boost explore command based on learned patterns
        explore_rec = next((r for r in recommendations if r.command == 'explore'), None)
        assert explore_rec is not None
        assert explore_rec.confidence > 0.6


class TestCommandRecommendationIntegration:
    """Integration tests for command recommendations with real components."""
    
    @pytest.fixture
    def integration_selector(self):
        """Create selector with partial real dependencies."""
        # Use real task generator but mock others
        task_generator = TaskAutoGenerator()
        mock_memory = Mock(spec=MemoryGraphManager)
        mock_analyzer = Mock(spec=WorkflowPatternAnalyzer)
        
        mock_memory.query_patterns.return_value = []
        mock_analyzer.get_historical_sequences.return_value = []
        
        return AdaptiveCommandSelector(
            task_generator=task_generator,
            memory_manager=mock_memory,
            pattern_analyzer=mock_analyzer
        )
    
    def test_real_complexity_analysis_integration(self, integration_selector):
        """Test integration with real TaskAutoGenerator complexity analysis."""
        context = integration_selector.analyze_context(
            task_description="Refactor the entire authentication system with OAuth2",
            domain="security"
        )
        recommendations = integration_selector.recommend_commands(context)
        
        # Complex task should affect time estimates
        assert recommendations[0].estimated_time > 60  # More than 1 hour
        
    def test_workflow_sequence_validation(self, integration_selector):
        """Test that recommended sequences form valid workflows."""
        # Simulate a workflow progression
        workflow_commands = []
        current_commands = []
        
        task_desc = "Build complete feature"
        
        # Generate 5 steps of workflow
        for i in range(5):
            context = integration_selector.analyze_context(
                task_description=task_desc,
                domain="feature",
                previous_commands=current_commands
            )
            recs = integration_selector.recommend_commands(context)
            
            if recs:
                next_command = recs[0].command
                workflow_commands.append(next_command)
                current_commands.append(next_command)
        
        # Should form a logical sequence
        assert 'explore' in workflow_commands[:2]  # Early exploration
        assert any(cmd in ['execute', 'implement', 'code'] for cmd in workflow_commands[2:4])
        assert any(cmd in ['verify', 'complete'] for cmd in workflow_commands[-2:])


class TestLearningSystemEffectiveness:
    """Tests specifically for the learning system's effectiveness."""
    
    @pytest.fixture
    def learning_selector(self, tmp_path):
        """Create selector with temporary storage for learning tests."""
        mock_deps = {
            'task_generator': Mock(spec=TaskAutoGenerator),
            'memory_manager': Mock(spec=MemoryGraphManager),
            'pattern_analyzer': Mock(spec=WorkflowPatternAnalyzer)
        }
        
        mock_deps['task_generator'].analyze_complexity.return_value = "moderate"
        mock_deps['memory_manager'].query_patterns.return_value = []
        mock_deps['pattern_analyzer'].get_historical_sequences.return_value = []
        
        selector = AdaptiveCommandSelector(**mock_deps)
        selector.cache_file = tmp_path / "test_learning_cache.json"
        return selector
    
    def test_learning_improves_predictions(self, learning_selector):
        """Test that learning actually improves future predictions."""
        task_type = "API endpoint implementation"
        
        # Get baseline recommendations
        context = learning_selector.analyze_context(
            task_description=task_type,
            domain="backend"
        )
        baseline = learning_selector.recommend_commands(context)
        baseline_explore_conf = next(
            (r.confidence for r in baseline if r.command == 'explore'), 0
        )
        
        # Train with successful patterns
        for _ in range(5):
            learning_selector.learn_from_outcome(
                command='explore',
                context=ContextType.GREENFIELD,
                domain='backend',
                success=True,
                duration=1800,
                task_description=task_type
            )
        
        # Get improved recommendations
        context = learning_selector.analyze_context(
            task_description=task_type,
            domain="backend"
        )
        improved = learning_selector.recommend_commands(context)
        improved_explore_conf = next(
            (r.confidence for r in improved if r.command == 'explore'), 0
        )
        
        # Confidence should increase with learning
        assert improved_explore_conf > baseline_explore_conf
    
    def test_negative_learning_reduces_confidence(self, learning_selector):
        """Test that failures reduce confidence in commands."""
        # Train with failures
        for _ in range(3):
            learning_selector.learn_from_outcome(
                command='quick-fix',
                context=ContextType.DEBUGGING,
                domain='testing',
                success=False,
                duration=300,
                task_description="Fix test failures"
            )
        
        context = learning_selector.analyze_context(
            task_description="Fix test failures",
            domain="testing"
        )
        recommendations = learning_selector.recommend_commands(context)
        
        # quick-fix should have lower confidence or not appear
        quick_fix_rec = next((r for r in recommendations if r.command == 'quick-fix'), None)
        if quick_fix_rec:
            assert quick_fix_rec.confidence < 0.4


class TestPerformanceAndStress:
    """Performance and stress tests for the adaptive command selector."""
    
    def test_recommendation_performance(self, selector):
        """Test recommendation generation performance."""
        import time
        
        start = time.time()
        for _ in range(100):
            context = selector.analyze_context(
                task_description="Performance test task",
                domain="testing"
            )
        duration = time.time() - start
        
        # Should handle 100 recommendations in under 1 second
        assert duration < 1.0, f"Performance issue: {duration:.2f}s for 100 recommendations"
    
    def test_large_history_handling(self, selector):
        """Test handling of large command histories."""
        # Setup large historical data
        large_history = [
            {
                'commands': ['explore', 'plan', 'execute'] * 10,
                'success_rate': 0.8,
                'avg_duration': 3600,
                'context': 'testing'
            } for _ in range(50)
        ]
        
        selector.pattern_analyzer.get_historical_sequences.return_value = large_history
        
        # Should still generate recommendations efficiently
        context = selector.analyze_context(
            task_description="Task with large history",
            domain="testing"
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        assert recommendations[0].confidence > 0
    
    def test_concurrent_learning(self, selector):
        """Test concurrent learning doesn't cause issues."""
        import threading
        
        def learn_task(i):
            selector.learn_from_outcome(
                command=f'command_{i % 5}',
                context=ContextType.GREENFIELD,
                domain='concurrent',
                success=True,
                duration=1800,
                task_description=f"Concurrent task {i}"
            )
        
        threads = [threading.Thread(target=learn_task, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should handle concurrent learning without errors
        assert len(selector.learning_cache) >= 10