"""Performance and stress tests for AdaptiveCommandSelector."""

import pytest
import time
import threading
import multiprocessing
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import Mock
import json
import tempfile
from pathlib import Path

from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector,
    ContextType,
    LearningPattern
)
from atlas_commands.task_auto_generator import TaskAutoGenerator
from atlas_commands.memory_graph import MemoryGraphManager
from atlas_commands.workflow.workflow_pattern_analyzer import WorkflowPatternAnalyzer


class TestAdaptiveCommandPerformance:
    """Performance tests for AdaptiveCommandSelector."""
    
    @pytest.fixture
    def performance_selector(self):
        """Create selector optimized for performance testing."""
        mock_deps = {
            'task_generator': Mock(spec=TaskAutoGenerator),
            'memory_manager': Mock(spec=MemoryGraphManager),
            'pattern_analyzer': Mock(spec=WorkflowPatternAnalyzer)
        }
        
        # Minimal mock setup for speed
        mock_deps['task_generator'].analyze_complexity.return_value = "moderate"
        mock_deps['memory_manager'].query_patterns.return_value = []
        mock_deps['pattern_analyzer'].get_historical_sequences.return_value = []
        
        return AdaptiveCommandSelector(**mock_deps)
    
    def test_recommendation_speed_baseline(self, performance_selector):
        """Test baseline recommendation generation speed."""
        iterations = 1000
        
        start_time = time.perf_counter()
        
        for i in range(iterations):
            performance_selector.get_adaptive_recommendations(
                task_description=f"Test task {i}",
                domain="performance"
            )
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        print(f"\nBaseline Performance:")
        print(f"Total time for {iterations} recommendations: {total_time:.3f}s")
        print(f"Average time per recommendation: {avg_time*1000:.2f}ms")
        
        # Should be fast enough for interactive use
        assert avg_time < 0.01  # Less than 10ms per recommendation
    
    def test_recommendation_speed_with_large_history(self, performance_selector):
        """Test performance with large command history."""
        # Setup large historical data
        large_history = []
        for i in range(100):
            large_history.append({
                'commands': ['explore', 'plan', 'execute', 'verify'] * 5,
                'success_rate': 0.8,
                'avg_duration': 3600,
                'context': f'domain_{i % 10}'
            })
        
        performance_selector.pattern_analyzer.get_historical_sequences.return_value = large_history
        
        iterations = 100
        start_time = time.perf_counter()
        
        for i in range(iterations):
            performance_selector.get_adaptive_recommendations(
                task_description="Complex task with history",
                domain="performance",
                previous_commands=['explore', 'plan'] * 10
            )
        
        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / iterations
        
        print(f"\nLarge History Performance:")
        print(f"Average time with 100 historical patterns: {avg_time*1000:.2f}ms")
        
        # Should still be reasonably fast
        assert avg_time < 0.05  # Less than 50ms per recommendation
    
    def test_learning_performance(self, performance_selector):
        """Test performance of learning from outcomes."""
        iterations = 1000
        
        start_time = time.perf_counter()
        
        for i in range(iterations):
            performance_selector.learn_from_outcome(
                command=f'command_{i % 10}',
                context=list(ContextType)[i % len(ContextType)],
                domain=f'domain_{i % 5}',
                success=i % 2 == 0,
                duration=1000 + i,
                task_description=f"Task {i}"
            )
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        print(f"\nLearning Performance:")
        print(f"Total time for {iterations} learning operations: {total_time:.3f}s")
        print(f"Average time per learning: {avg_time*1000:.2f}ms")
        
        # Learning should be very fast
        assert avg_time < 0.001  # Less than 1ms per learning operation
    
    def test_memory_usage_under_load(self, performance_selector):
        """Test memory usage with large amounts of data."""
        process = psutil.Process()
        
        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Add many learning patterns
        for i in range(10000):
            performance_selector.learn_from_outcome(
                command=f'cmd_{i % 20}',
                context=list(ContextType)[i % len(ContextType)],
                domain=f'domain_{i % 10}',
                success=i % 3 != 0,
                duration=1000 + (i % 3600),
                task_description=f"Memory test task {i}"
            )
        
        # Get memory after load
        gc.collect()
        loaded_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = loaded_memory - baseline_memory
        
        print(f"\nMemory Usage:")
        print(f"Baseline memory: {baseline_memory:.1f} MB")
        print(f"Loaded memory: {loaded_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        
        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB increase
    
    def test_concurrent_recommendation_generation(self, performance_selector):
        """Test concurrent recommendation generation."""
        num_threads = 10
        recommendations_per_thread = 100
        results = []
        errors = []
        
        def generate_recommendations(thread_id):
            thread_results = []
            try:
                for i in range(recommendations_per_thread):
                    recs = performance_selector.get_adaptive_recommendations(
                        task_description=f"Thread {thread_id} task {i}",
                        domain=f"domain_{thread_id}"
                    )
                    thread_results.append(len(recs))
            except Exception as e:
                errors.append((thread_id, str(e)))
            return thread_results
        
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(generate_recommendations, i) 
                for i in range(num_threads)
            ]
            
            for future in futures:
                result = future.result()
                results.extend(result)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        total_recommendations = len(results)
        
        print(f"\nConcurrent Performance:")
        print(f"Total recommendations: {total_recommendations}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Throughput: {total_recommendations/total_time:.1f} recommendations/second")
        print(f"Errors: {len(errors)}")
        
        # Should handle concurrent access without errors
        assert len(errors) == 0
        assert total_recommendations == num_threads * recommendations_per_thread
    
    def test_pattern_matching_performance(self, performance_selector):
        """Test performance of pattern matching with many patterns."""
        # Pre-populate with many patterns
        for i in range(1000):
            performance_selector.learn_from_outcome(
                command=f'command_{i % 50}',
                context=list(ContextType)[i % len(ContextType)],
                domain=f'domain_{i % 20}',
                success=True,
                duration=1800,
                task_description=f"Pattern {i}: {['build', 'fix', 'refactor'][i % 3]} {['API', 'UI', 'database'][i % 3]}"
            )
        
        # Time pattern matching
        iterations = 100
        start_time = time.perf_counter()
        
        for i in range(iterations):
            performance_selector.get_adaptive_recommendations(
                task_description="Build new API endpoint for user management",
                domain="backend"
            )
        
        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / iterations
        
        print(f"\nPattern Matching Performance:")
        print(f"Patterns in cache: {len(performance_selector.learning_cache)}")
        print(f"Average recommendation time: {avg_time*1000:.2f}ms")
        
        # Should scale reasonably with pattern count
        assert avg_time < 0.02  # Less than 20ms even with 1000 patterns
    
    def test_classification_performance(self, performance_selector):
        """Test context classification performance."""
        test_descriptions = [
            "Build new authentication system with OAuth2 integration",
            "Debug memory leak in worker process causing crashes",
            "Refactor payment module to improve maintainability",
            "Optimize database queries for better performance",
            "Deploy application to production environment",
            "Migrate from MySQL to PostgreSQL database",
            "Fix broken login functionality for mobile users",
            "Investigate slow API response times"
        ] * 125  # 1000 total
        
        start_time = time.perf_counter()
        
        for desc in test_descriptions:
            performance_selector._classify_context_type(desc)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / len(test_descriptions)
        
        print(f"\nClassification Performance:")
        print(f"Classifications: {len(test_descriptions)}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average time: {avg_time*1000:.4f}ms")
        
        # Classification should be very fast
        assert avg_time < 0.0001  # Less than 0.1ms per classification
    
    def test_cache_persistence_performance(self, performance_selector):
        """Test performance of cache save/load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "perf_cache.json"
            performance_selector.cache_file = cache_file
            
            # Add many patterns
            pattern_count = 5000
            for i in range(pattern_count):
                performance_selector.learn_from_outcome(
                    command=f'cmd_{i % 100}',
                    context=list(ContextType)[i % len(ContextType)],
                    domain=f'domain_{i % 50}',
                    success=i % 3 != 0,
                    duration=1000 + i,
                    task_description=f"Cached task {i}"
                )
            
            # Time save operation
            start_save = time.perf_counter()
            performance_selector._save_learning_cache()
            save_time = time.perf_counter() - start_save
            
            # Check file size
            file_size = cache_file.stat().st_size / 1024 / 1024  # MB
            
            # Create new selector and time load operation
            new_selector = AdaptiveCommandSelector(
                task_generator=performance_selector.task_generator,
                memory_manager=performance_selector.memory_manager,
                pattern_analyzer=performance_selector.pattern_analyzer
            )
            new_selector.cache_file = cache_file
            
            start_load = time.perf_counter()
            new_selector._load_learning_cache()
            load_time = time.perf_counter() - start_load
            
            print(f"\nCache Persistence Performance:")
            print(f"Patterns: {pattern_count}")
            print(f"File size: {file_size:.2f} MB")
            print(f"Save time: {save_time:.3f}s")
            print(f"Load time: {load_time:.3f}s")
            
            # Should handle large caches efficiently
            assert save_time < 1.0  # Less than 1 second to save
            assert load_time < 0.5  # Less than 0.5 seconds to load
    
    def test_recommendation_consistency_under_load(self, performance_selector):
        """Test that recommendations remain consistent under load."""
        task_desc = "Build REST API for user management"
        domain = "backend"
        
        # Get baseline recommendations
        baseline = performance_selector.get_adaptive_recommendations(
            task_description=task_desc,
            domain=domain
        )
        baseline_commands = [r.command for r in baseline[:3]]
        
        # Generate many recommendations concurrently
        inconsistencies = []
        
        def check_consistency(iteration):
            recs = performance_selector.get_adaptive_recommendations(
                task_description=task_desc,
                domain=domain
            )
            rec_commands = [r.command for r in recs[:3]]
            
            if rec_commands != baseline_commands:
                inconsistencies.append({
                    'iteration': iteration,
                    'expected': baseline_commands,
                    'actual': rec_commands
                })
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_consistency, i) for i in range(1000)]
            for future in futures:
                future.result()
        
        print(f"\nConsistency Test:")
        print(f"Inconsistencies found: {len(inconsistencies)}")
        
        # Should be consistent
        assert len(inconsistencies) == 0
    
    def test_stress_maximum_load(self, performance_selector):
        """Stress test with maximum load."""
        # Warning: This test is intensive
        print("\nStress Test Starting...")
        
        start_time = time.perf_counter()
        operations = 0
        errors = []
        
        # Run for 10 seconds with maximum load
        end_time = start_time + 10
        
        while time.perf_counter() < end_time:
            try:
                # Mix of operations
                if operations % 3 == 0:
                    # Recommendation
                    performance_selector.get_adaptive_recommendations(
                        task_description=f"Stress test {operations}",
                        domain="stress"
                    )
                elif operations % 3 == 1:
                    # Learning
                    performance_selector.learn_from_outcome(
                        command='stress-cmd',
                        context=ContextType.GREENFIELD,
                        domain='stress',
                        success=True,
                        duration=1000,
                        task_description=f"Stress learn {operations}"
                    )
                else:
                    # Classification
                    performance_selector._classify_context_type(
                        f"Stress classify {operations}"
                    )
                
                operations += 1
                
            except Exception as e:
                errors.append((operations, str(e)))
        
        total_time = time.perf_counter() - start_time
        ops_per_second = operations / total_time
        
        print(f"\nStress Test Results:")
        print(f"Total operations: {operations}")
        print(f"Total time: {total_time:.1f}s")
        print(f"Operations/second: {ops_per_second:.1f}")
        print(f"Errors: {len(errors)}")
        
        # Should handle high load without errors
        assert len(errors) == 0
        assert ops_per_second > 1000  # Should handle >1000 ops/second


class TestAdaptiveCommandScalability:
    """Scalability tests for AdaptiveCommandSelector."""
    
    def test_scalability_with_domains(self, performance_selector):
        """Test scalability with increasing number of domains."""
        domain_counts = [10, 50, 100, 500]
        times = []
        
        for domain_count in domain_counts:
            # Add patterns for many domains
            for i in range(domain_count * 10):
                performance_selector.learn_from_outcome(
                    command='explore',
                    context=ContextType.GREENFIELD,
                    domain=f'domain_{i % domain_count}',
                    success=True,
                    duration=1800,
                    task_description=f"Task for domain {i % domain_count}"
                )
            
            # Time recommendations
            start = time.perf_counter()
            for i in range(100):
                performance_selector.get_adaptive_recommendations(
                    task_description="Test scalability",
                    domain=f"domain_{i % domain_count}"
                )
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            
            print(f"Domains: {domain_count}, Time: {elapsed:.3f}s")
        
        # Check that performance doesn't degrade too much
        # Time should grow sub-linearly with domain count
        time_ratio = times[-1] / times[0]
        domain_ratio = domain_counts[-1] / domain_counts[0]
        
        print(f"\nScalability Analysis:")
        print(f"Domain increase: {domain_ratio}x")
        print(f"Time increase: {time_ratio:.1f}x")
        
        # Should scale better than linear
        assert time_ratio < domain_ratio * 0.5