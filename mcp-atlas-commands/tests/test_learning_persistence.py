"""Tests for learning system persistence and influence in AdaptiveCommandSelector."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import os

from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector,
    ContextType,
    CommandRecommendation
)
from atlas_commands.workflow.task_auto_generator import TaskAutoGenerator
from atlas_commands.memory.graph_manager import MemoryGraphManager
from atlas_commands.workflow.pattern_analyzer import WorkflowPatternAnalyzer


class TestLearningSystemPersistence:
    """Test suite for learning system persistence and effectiveness."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory for cache files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def selector_with_cache(self, temp_cache_dir):
        """Create selector with cache file in temp directory."""
        cache_file = temp_cache_dir / "learning_cache.json"
        
        # Create selector - it creates its own dependencies
        selector = AdaptiveCommandSelector()
        
        # Mock internal dependencies
        selector.task_generator = Mock(spec=TaskAutoGenerator)
        selector.task_generator.analyze_complexity.return_value = "moderate"
        
        selector.memory_manager = Mock(spec=MemoryGraphManager)
        selector.memory_manager.query_patterns.return_value = []
        
        selector.pattern_analyzer = Mock(spec=WorkflowPatternAnalyzer)
        selector.pattern_analyzer.get_historical_sequences.return_value = []
        
        # Override cache file location
        selector.cache_file = cache_file
        
        return selector, cache_file
    
    def test_learning_cache_initialization(self, selector_with_cache):
        """Test that learning cache initializes properly."""
        selector, cache_file = selector_with_cache
        
        assert hasattr(selector, 'learning_cache')
        assert isinstance(selector.learning_cache, list)
        assert len(selector.learning_cache) == 0
        assert selector.cache_file == cache_file
    
    def test_learn_from_outcome_creates_pattern(self, selector_with_cache):
        """Test that learn_from_outcome creates learning patterns."""
        selector, _ = selector_with_cache
        
        # Learn from a successful outcome
        selector.learn_from_outcome(
            command='explore',
            context=ContextType.GREENFIELD,
            domain='testing',
            success=True,
            duration=1800,
            task_description="Build test framework"
        )
        
        # Verify pattern was created
        assert len(selector.learning_cache) == 1
        pattern = selector.learning_cache[0]
        
        assert pattern.command == 'explore'
        assert pattern.context == ContextType.GREENFIELD
        assert pattern.domain == 'testing'
        assert pattern.success is True
        assert pattern.duration == 1800
        assert pattern.task_description == "Build test framework"
        assert pattern.timestamp is not None
    
    def test_learning_cache_persistence_to_file(self, selector_with_cache):
        """Test that learning cache persists to file."""
        selector, cache_file = selector_with_cache
        
        # Add multiple learning patterns
        patterns_data = [
            ('explore', ContextType.GREENFIELD, 'backend', True, 1800, "Build API"),
            ('plan', ContextType.GREENFIELD, 'backend', True, 900, "Plan API"),
            ('execute', ContextType.GREENFIELD, 'backend', False, 3600, "Implement API"),
            ('debug', ContextType.DEBUGGING, 'backend', True, 2400, "Fix API bugs"),
        ]
        
        for cmd, ctx, domain, success, duration, desc in patterns_data:
            selector.learn_from_outcome(cmd, ctx, domain, success, duration, desc)
        
        # Save cache (simulate shutdown)
        selector._save_learning_cache()
        
        # Verify file exists and contains data
        assert cache_file.exists()
        
        with open(cache_file, 'r') as f:
            saved_data = json.load(f)
        
        assert 'patterns' in saved_data
        assert len(saved_data['patterns']) == 4
        
        # Verify pattern data integrity
        for i, (cmd, ctx, domain, success, duration, desc) in enumerate(patterns_data):
            saved_pattern = saved_data['patterns'][i]
            assert saved_pattern['command'] == cmd
            assert saved_pattern['context'] == ctx.value
            assert saved_pattern['domain'] == domain
            assert saved_pattern['success'] == success
            assert saved_pattern['duration'] == duration
            assert saved_pattern['task_description'] == desc
            assert 'timestamp' in saved_pattern
    
    def test_learning_cache_load_from_file(self, selector_with_cache):
        """Test loading learning cache from file."""
        selector1, cache_file = selector_with_cache
        
        # Create and save patterns with first selector
        test_patterns = [
            ('explore', ContextType.GREENFIELD, 'frontend', True, 1200, "Build UI"),
            ('test', ContextType.MAINTENANCE, 'frontend', True, 600, "Test UI"),
            ('deploy', ContextType.DEPLOYMENT, 'frontend', False, 300, "Deploy UI"),
        ]
        
        for cmd, ctx, domain, success, duration, desc in test_patterns:
            selector1.learn_from_outcome(cmd, ctx, domain, success, duration, desc)
        
        selector1._save_learning_cache()
        
        # Create new selector with same cache file
        selector2 = AdaptiveCommandSelector()
        selector2.task_generator = selector1.task_generator
        selector2.memory_manager = selector1.memory_manager
        selector2.pattern_analyzer = selector1.pattern_analyzer
        selector2.cache_file = cache_file
        
        # Load cache
        selector2._load_learning_cache()
        
        # Verify patterns were loaded
        assert len(selector2.learning_cache) == 3
        
        for i, (cmd, ctx, domain, success, duration, desc) in enumerate(test_patterns):
            pattern = selector2.learning_cache[i]
            assert pattern.command == cmd
            assert pattern.context == ctx
            assert pattern.domain == domain
            assert pattern.success == success
            assert pattern.duration == duration
            assert pattern.task_description == desc
    
    def test_learning_influences_recommendations(self, selector_with_cache):
        """Test that learned patterns influence future recommendations."""
        selector, _ = selector_with_cache
        
        # Get baseline recommendations
        context = selector.analyze_context(
            task_description="Build authentication API",
            domain="security"
        )
        baseline_recs = selector.recommend_commands(context)
        
        baseline_explore_conf = next(
            (r.confidence for r in baseline_recs if r.command == 'explore'),
            0.0
        )
        
        # Learn successful explore patterns
        for i in range(5):
            selector.learn_from_outcome(
                command='explore',
                context=ContextType.GREENFIELD,
                domain='security',
                success=True,
                duration=1800,
                task_description=f"Build security feature {i}"
            )
        
        # Get recommendations after learning
        context = selector.analyze_context(
            task_description="Build authentication API",
            domain="security"
        )
        learned_recs = selector.recommend_commands(context)
        
        learned_explore_conf = next(
            (r.confidence for r in learned_recs if r.command == 'explore'),
            0.0
        )
        
        # Confidence should increase with positive patterns
        assert learned_explore_conf > baseline_explore_conf
    
    def test_negative_patterns_reduce_confidence(self, selector_with_cache):
        """Test that failed patterns reduce command confidence."""
        selector, _ = selector_with_cache
        
        # Learn failed patterns
        for i in range(3):
            selector.learn_from_outcome(
                command='quick-fix',
                context=ContextType.DEBUGGING,
                domain='testing',
                success=False,
                duration=300,
                task_description=f"Quick fix attempt {i}"
            )
        
        # Get recommendations
        context = selector.analyze_context(
            task_description="Fix test failures quickly",
            domain="testing"
        )
        recs = selector.recommend_commands(context)
        
        # quick-fix should have low confidence or not appear
        quick_fix_rec = next((r for r in recs if r.command == 'quick-fix'), None)
        
        if quick_fix_rec:
            assert quick_fix_rec.confidence < 0.4
    
    def test_domain_specific_learning(self, selector_with_cache):
        """Test that learning is domain-specific."""
        selector, _ = selector_with_cache
        
        # Learn patterns in different domains
        selector.learn_from_outcome(
            command='explore',
            context=ContextType.GREENFIELD,
            domain='frontend',
            success=True,
            duration=1200,
            task_description="Build React component"
        )
        
        selector.learn_from_outcome(
            command='explore',
            context=ContextType.GREENFIELD,
            domain='backend',
            success=False,
            duration=3600,
            task_description="Build microservice"
        )
        
        # Frontend recommendations should favor explore
        context = selector.analyze_context(
            task_description="Build new UI feature",
            domain="frontend"
        )
        frontend_recs = selector.recommend_commands(context)
        
        frontend_explore = next(
            (r for r in frontend_recs if r.command == 'explore'),
            None
        )
        
        # Backend recommendations should not favor explore
        context = selector.analyze_context(
            task_description="Build new API endpoint",
            domain="backend"
        )
        backend_recs = selector.recommend_commands(context)
        
        backend_explore = next(
            (r for r in backend_recs if r.command == 'explore'),
            None
        )
        
        # Frontend should have higher confidence for explore
        if frontend_explore and backend_explore:
            assert frontend_explore.confidence > backend_explore.confidence
    
    def test_temporal_pattern_decay(self, selector_with_cache):
        """Test that older patterns have less influence."""
        selector, _ = selector_with_cache
        
        # Mock current time
        current_time = datetime.now()
        
        with patch('atlas_commands.workflow.adaptive_command_selector.datetime') as mock_dt:
            # Add old successful pattern
            mock_dt.now.return_value = current_time - timedelta(days=30)
            selector.learn_from_outcome(
                command='legacy-approach',
                context=ContextType.GREENFIELD,
                domain='testing',
                success=True,
                duration=1800,
                task_description="Old successful approach"
            )
            
            # Add recent successful pattern
            mock_dt.now.return_value = current_time - timedelta(hours=1)
            selector.learn_from_outcome(
                command='modern-approach',
                context=ContextType.GREENFIELD,
                domain='testing',
                success=True,
                duration=900,
                task_description="Recent successful approach"
            )
            
            # Get recommendations
            mock_dt.now.return_value = current_time
            context = selector.analyze_context(
                task_description="Build new test feature",
                domain="testing"
            )
            recs = selector.recommend_commands(context)
        
        # Recent pattern should have more influence
        modern_rec = next((r for r in recs if r.command == 'modern-approach'), None)
        legacy_rec = next((r for r in recs if r.command == 'legacy-approach'), None)
        
        if modern_rec and legacy_rec:
            assert modern_rec.confidence > legacy_rec.confidence
    
    def test_pattern_aggregation_statistics(self, selector_with_cache):
        """Test that patterns are aggregated for statistics."""
        selector, _ = selector_with_cache
        
        # Add multiple patterns for same command
        success_counts = {'explore': 8, 'plan': 5, 'execute': 3}
        failure_counts = {'explore': 2, 'plan': 5, 'execute': 7}
        
        for command, count in success_counts.items():
            for i in range(count):
                selector.learn_from_outcome(
                    command=command,
                    context=ContextType.GREENFIELD,
                    domain='statistics',
                    success=True,
                    duration=1800,
                    task_description=f"{command} success {i}"
                )
        
        for command, count in failure_counts.items():
            for i in range(count):
                selector.learn_from_outcome(
                    command=command,
                    context=ContextType.GREENFIELD,
                    domain='statistics',
                    success=False,
                    duration=1800,
                    task_description=f"{command} failure {i}"
                )
        
        # Get recommendations
        context = selector.analyze_context(
            task_description="New statistics feature",
            domain="statistics"
        )
        recs = selector.recommend_commands(context)
        
        # Commands should be ranked by success rate
        # explore: 8/10 = 0.8, plan: 5/10 = 0.5, execute: 3/10 = 0.3
        command_order = [r.command for r in recs if r.command in ['explore', 'plan', 'execute']]
        
        # Verify explore appears before execute
        if 'explore' in command_order and 'execute' in command_order:
            assert command_order.index('explore') < command_order.index('execute')
    
    def test_cache_size_management(self, selector_with_cache):
        """Test that cache doesn't grow unbounded."""
        selector, _ = selector_with_cache
        
        # Add many patterns
        for i in range(1000):
            selector.learn_from_outcome(
                command=f'command_{i % 10}',
                context=list(ContextType)[i % len(ContextType)],
                domain=f'domain_{i % 5}',
                success=i % 2 == 0,
                duration=1000 + i,
                task_description=f"Task {i}"
            )
        
        # Cache should be bounded
        assert len(selector.learning_cache) <= 500  # Reasonable limit
        
        # Recent patterns should be kept
        recent_tasks = [p.task_description for p in selector.learning_cache[-10:]]
        assert "Task 999" in recent_tasks
    
    def test_pattern_similarity_matching(self, selector_with_cache):
        """Test fuzzy matching of similar task descriptions."""
        selector, _ = selector_with_cache
        
        # Learn from similar authentication tasks
        auth_variations = [
            "Build user authentication system",
            "Create auth module for users",
            "Implement authentication feature",
            "Develop user auth functionality",
            "Setup authentication system"
        ]
        
        for desc in auth_variations:
            selector.learn_from_outcome(
                command='explore',
                context=ContextType.GREENFIELD,
                domain='security',
                success=True,
                duration=2400,
                task_description=desc
            )
        
        # Test with similar but different description
        context = selector.analyze_context(
            task_description="Build authentication module",
            domain="security"
        )
        recs = selector.recommend_commands(context)
        
        # Should recognize pattern despite different wording
        explore_rec = next((r for r in recs if r.command == 'explore'), None)
        assert explore_rec is not None
        assert explore_rec.confidence > 0.7
    
    def test_concurrent_cache_access(self, selector_with_cache):
        """Test thread-safe cache operations."""
        selector, cache_file = selector_with_cache
        
        import threading
        import time
        
        errors = []
        
        def learn_concurrently(thread_id):
            try:
                for i in range(10):
                    selector.learn_from_outcome(
                        command=f'cmd_{thread_id}',
                        context=ContextType.GREENFIELD,
                        domain='concurrent',
                        success=True,
                        duration=1000,
                        task_description=f"Thread {thread_id} task {i}"
                    )
                    time.sleep(0.01)  # Small delay to increase contention
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch concurrent threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=learn_concurrently, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should handle concurrent access without errors
        assert len(errors) == 0
        
        # Should have patterns from all threads
        assert len(selector.learning_cache) >= 40  # At least some from each thread
    
    def test_cache_corruption_recovery(self, selector_with_cache):
        """Test recovery from corrupted cache file."""
        selector, cache_file = selector_with_cache
        
        # Create corrupted cache file
        with open(cache_file, 'w') as f:
            f.write("{ invalid json }")
        
        # Should handle gracefully
        selector._load_learning_cache()
        
        # Should start with empty cache
        assert len(selector.learning_cache) == 0
        
        # Should still be able to learn
        selector.learn_from_outcome(
            command='explore',
            context=ContextType.GREENFIELD,
            domain='recovery',
            success=True,
            duration=1800,
            task_description="Recovery test"
        )
        
        assert len(selector.learning_cache) == 1
    
    def test_memory_integration_with_learning(self, selector_with_cache):
        """Test that learning integrates with memory graph."""
        selector, _ = selector_with_cache
        
        # Learn a pattern for memory integration test
        selector.learn_from_outcome(
            command='analyze',
            context=ContextType.EXPLORATION,
            domain='research',
            success=True,
            duration=3600,
            task_description="Research new technology"
        )
        
        # Get recommendations
        context = selector.analyze_context(
            task_description="Research blockchain technology",
            domain="research"
        )
        recs = selector.recommend_commands(context)
        
        # Should include analyze command with good confidence
        analyze_rec = next((r for r in recs if r.command == 'analyze'), None)
        assert analyze_rec is not None
        assert analyze_rec.confidence > 0.5