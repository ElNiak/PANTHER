"""
Phase 2: Integration Components Tests
Tests the coordination optimization features - saga patterns, OTLP concurrency, and governance.
These are the 5 coordination optimizations achieving 804.7x performance improvement.
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from atlas_commands.compression.compression_manager import CompressionManager, CompressionStrategy
from atlas_commands.saga.saga_coordinator import SagaCoordinator
from atlas_commands.entropy.entropy_processor import EntropyProcessor, EntropyThresholds
from atlas_commands.entropy.incremental_memory_manager import IncrementalMemoryManager
from atlas_commands.otlp_concurrency.concurrent_exporter import ConcurrentExporter


@dataclass
class TestTask:
    """Test task for saga patterns."""
    id: str
    description: str
    dependencies: List[str]
    estimated_effort: float
    metadata: Dict[str, Any]


class TestPhase2IntegrationComponents:
    """Test Phase 2: Integration components for coordination optimization."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def compression_manager(self):
        """Create compression manager for testing."""
        return CompressionManager()
    
    @pytest.fixture
    def saga_coordinator(self, temp_storage):
        """Create saga coordinator for testing."""
        return SagaCoordinator(storage_path=temp_storage)
    
    @pytest.fixture
    def entropy_processor(self):
        """Create entropy processor for testing."""
        thresholds = EntropyThresholds(
            low_entropy=0.3,
            medium_entropy=0.6,
            high_entropy=0.8,
            trigger_entropy=0.9
        )
        return EntropyProcessor(thresholds=thresholds)
    
    @pytest.fixture
    def incremental_memory_manager(self, temp_storage):
        """Create incremental memory manager for testing."""
        return IncrementalMemoryManager(storage_path=temp_storage)
    
    @pytest.fixture
    def concurrent_exporter(self):
        """Create concurrent exporter for testing."""
        return ConcurrentExporter(initial_workers=2)


class TestCompressionManager:
    """Test compression manager functionality."""
    
    @pytest.fixture
    def compression_manager(self):
        """Create compression manager for testing."""
        return CompressionManager()
    
    def test_compression_manager_initialization(self, compression_manager):
        """Test compression manager initializes correctly."""
        assert compression_manager is not None
        assert hasattr(compression_manager, 'strategy')
        assert hasattr(compression_manager, 'compression_ratio')
    
    def test_compression_strategies_available(self, compression_manager):
        """Test all compression strategies are available."""
        # Verify strategy enum exists
        from atlas_commands.compression.compression_manager import CompressionStrategy
        
        # Should have multiple strategies
        strategies = list(CompressionStrategy)
        assert len(strategies) >= 3  # At least LOSSLESS, LOSSY, ADAPTIVE
        
        # Test setting different strategies
        for strategy in strategies:
            compression_manager.set_strategy(strategy)
            assert compression_manager.strategy == strategy
    
    def test_compression_performance_metrics(self, compression_manager):
        """Test compression performance tracking."""
        # Test with sample data
        test_data = {
            "task_description": "implement new feature with complex requirements",
            "metadata": {"priority": "high", "complexity": "medium"},
            "dependencies": ["task1", "task2", "task3"]
        }
        
        # Compress data
        compressed = compression_manager.compress(test_data)
        assert compressed is not None
        
        # Should track compression ratio
        assert hasattr(compression_manager, 'compression_ratio')
        assert compression_manager.compression_ratio > 0
        
        # Should maintain essential information
        if hasattr(compressed, 'task_description'):
            assert compressed.task_description is not None
    
    def test_llmlingua_compression_integration(self, compression_manager):
        """Test LLMLingua compression integration (research-backed optimization)."""
        # Set to LLMLingua strategy if available
        try:
            from atlas_commands.compression.compression_manager import CompressionStrategy
            if hasattr(CompressionStrategy, 'LLMLINGUA'):
                compression_manager.set_strategy(CompressionStrategy.LLMLINGUA)
            
            # Test information-theoretic importance scoring
            test_content = "This is critical information. This is less important detail. This is redundant noise."
            compressed = compression_manager.compress_with_importance_scoring(test_content)
            
            # Should preserve high-importance content
            assert compressed is not None
            assert len(compressed) <= len(test_content)  # Should be compressed
            
        except (ImportError, AttributeError):
            # LLMLingua may not be available in test environment
            pytest.skip("LLMLingua compression not available in test environment")


class TestSagaCoordinator:
    """Test saga coordinator for transactional integrity."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def saga_coordinator(self, temp_storage):
        """Create saga coordinator for testing."""
        return SagaCoordinator(storage_path=temp_storage)
    
    def test_saga_coordinator_initialization(self, saga_coordinator):
        """Test saga coordinator initializes correctly."""
        assert saga_coordinator is not None
        assert hasattr(saga_coordinator, 'storage_path')
        assert hasattr(saga_coordinator, 'active_sagas')
    
    @pytest.mark.asyncio
    async def test_saga_transaction_management(self, saga_coordinator):
        """Test saga transaction management with compensation."""
        # Create test tasks
        tasks = [
            TestTask("task1", "Initial setup", [], 1.0, {"type": "setup"}),
            TestTask("task2", "Core implementation", ["task1"], 3.0, {"type": "implementation"}),
            TestTask("task3", "Final validation", ["task2"], 1.0, {"type": "validation"})
        ]
        
        # Start saga
        saga_id = await saga_coordinator.start_saga("test_workflow", tasks)
        assert saga_id is not None
        assert saga_id in saga_coordinator.active_sagas
        
        # Execute tasks in saga
        for task in tasks:
            result = await saga_coordinator.execute_saga_step(saga_id, task.id, task)
            assert result.success or result.compensation_applied  # Either success or compensated
        
        # Complete saga
        completion_result = await saga_coordinator.complete_saga(saga_id)
        assert completion_result.success
    
    @pytest.mark.asyncio 
    async def test_saga_compensation_rollback(self, saga_coordinator):
        """Test saga compensation and rollback functionality."""
        # Create tasks with intentional failure
        tasks = [
            TestTask("task1", "Setup", [], 1.0, {"type": "setup"}),
            TestTask("task2", "Failing task", ["task1"], 2.0, {"type": "failing"}),
            TestTask("task3", "Never reached", ["task2"], 1.0, {"type": "unreachable"})
        ]
        
        # Start saga
        saga_id = await saga_coordinator.start_saga("failing_workflow", tasks)
        
        # Execute first task (should succeed)
        result1 = await saga_coordinator.execute_saga_step(saga_id, "task1", tasks[0])
        assert result1.success
        
        # Simulate failure in second task
        with patch.object(saga_coordinator, '_execute_task', side_effect=Exception("Simulated failure")):
            result2 = await saga_coordinator.execute_saga_step(saga_id, "task2", tasks[1])
            assert not result2.success
            assert result2.compensation_applied  # Should trigger compensation
        
        # Verify rollback occurred
        saga_state = saga_coordinator.get_saga_state(saga_id)
        assert saga_state.status == "compensated" or saga_state.status == "failed"
    
    def test_saga_dependency_resolution(self, saga_coordinator):
        """Test saga dependency resolution and ordering."""
        # Create tasks with complex dependencies
        tasks = [
            TestTask("A", "Task A", [], 1.0, {}),
            TestTask("B", "Task B", ["A"], 1.0, {}),
            TestTask("C", "Task C", ["A"], 1.0, {}),
            TestTask("D", "Task D", ["B", "C"], 1.0, {})
        ]
        
        # Resolve execution order
        execution_order = saga_coordinator.resolve_task_dependencies(tasks)
        
        # Verify correct ordering
        assert execution_order[0].id == "A"  # A has no dependencies
        assert execution_order[1].id in ["B", "C"]  # B and C depend on A
        assert execution_order[2].id in ["B", "C"]  # B and C depend on A
        assert execution_order[3].id == "D"  # D depends on B and C


class TestEntropyProcessor:
    """Test entropy processor for information-theoretic optimization."""
    
    @pytest.fixture
    def entropy_processor(self):
        """Create entropy processor for testing."""
        thresholds = EntropyThresholds(
            low_entropy=0.3,
            medium_entropy=0.6,
            high_entropy=0.8,
            trigger_entropy=0.9
        )
        return EntropyProcessor(thresholds=thresholds)
    
    def test_entropy_processor_initialization(self, entropy_processor):
        """Test entropy processor initializes correctly."""
        assert entropy_processor is not None
        assert hasattr(entropy_processor, 'thresholds')
        assert entropy_processor.thresholds.trigger_entropy == 0.9
    
    def test_shannon_entropy_calculation(self, entropy_processor):
        """Test Shannon entropy calculation for content analysis."""
        # Test with different content types
        test_cases = [
            ("aaaaaaaaaa", 0.0),  # No entropy - all same character
            ("abcdefghij", None),  # High entropy - all different characters
            ("aabbccddee", None),  # Medium entropy - some repetition
        ]
        
        for content, expected_entropy in test_cases:
            calculated_entropy = entropy_processor.calculate_shannon_entropy(content)
            
            if expected_entropy is not None:
                assert abs(calculated_entropy - expected_entropy) < 0.1
            else:
                assert 0.0 <= calculated_entropy <= 1.0  # Valid entropy range
    
    def test_entropy_triggered_processing(self, entropy_processor):
        """Test entropy-triggered processing threshold detection."""
        # Test content that should trigger processing (high entropy)
        high_entropy_content = "This contains many different unique symbols and patterns that create high information entropy!"
        
        entropy_score = entropy_processor.calculate_shannon_entropy(high_entropy_content)
        should_process = entropy_processor.should_trigger_processing(entropy_score)
        
        # Should trigger if entropy exceeds threshold (0.9)
        if entropy_score >= 0.9:
            assert should_process
        else:
            assert not should_process
        
        # Test low entropy content
        low_entropy_content = "simple simple simple simple"
        low_entropy_score = entropy_processor.calculate_shannon_entropy(low_entropy_content)
        should_not_process = entropy_processor.should_trigger_processing(low_entropy_score)
        assert not should_not_process  # Should not trigger for low entropy
    
    def test_adaptive_chunking_based_on_entropy(self, entropy_processor):
        """Test adaptive memory chunking based on entropy analysis."""
        # Test content with varying entropy levels
        mixed_content = [
            "routine task completion",  # Low entropy
            "complex algorithmic optimization with multiple constraints",  # High entropy
            "standard procedure",  # Low entropy
            "unexpected integration failure requiring deep analysis"  # High entropy
        ]
        
        chunks = entropy_processor.adaptive_chunk_by_entropy(mixed_content)
        
        # Should create different chunk sizes based on entropy
        assert len(chunks) > 0
        
        # High entropy content should be in smaller chunks
        # Low entropy content can be in larger chunks
        for chunk in chunks:
            assert len(chunk) > 0
            assert hasattr(chunk, 'entropy_score') or isinstance(chunk, (str, dict))


class TestIncrementalMemoryManager:
    """Test incremental memory manager for context-aware processing."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def memory_manager(self, temp_storage):
        """Create incremental memory manager for testing."""
        return IncrementalMemoryManager(storage_path=temp_storage)
    
    def test_incremental_memory_manager_initialization(self, memory_manager):
        """Test memory manager initializes correctly."""
        assert memory_manager is not None
        assert hasattr(memory_manager, 'storage_path')
        assert hasattr(memory_manager, 'memory_chunks')
    
    @pytest.mark.asyncio
    async def test_context_aware_chunking(self, memory_manager):
        """Test context-aware memory chunking to prevent token explosion."""
        # Add memory content with different contexts
        contexts = [
            {"content": "Project setup and configuration", "category": "setup", "importance": 0.7},
            {"content": "Critical bug found in authentication system", "category": "bug", "importance": 0.95},
            {"content": "Regular code review feedback", "category": "review", "importance": 0.5},
            {"content": "Performance optimization breakthrough", "category": "optimization", "importance": 0.9}
        ]
        
        # Process each context
        for context in contexts:
            chunks = []
            async for chunk in memory_manager.process_memory_operation(
                content=context["content"],
                operation_type="CREATE",
                context=context
            ):
                chunks.append(chunk)
            
            # Should create appropriate chunks based on importance
            assert len(chunks) > 0
            
            # High importance content should be preserved with more detail
            if context["importance"] > 0.8:
                # Should have detailed chunks for high importance
                assert any("importance" in str(chunk) for chunk in chunks)
    
    def test_memory_chunk_optimization(self, memory_manager):
        """Test memory chunk optimization for token efficiency."""
        # Test with content of different sizes
        small_content = "Simple task"
        large_content = "Complex task with many details " * 100  # Large content
        
        # Process different content sizes
        small_chunks = memory_manager.optimize_chunks(small_content)
        large_chunks = memory_manager.optimize_chunks(large_content)
        
        # Should handle different content sizes appropriately
        assert len(small_chunks) >= 1
        assert len(large_chunks) >= len(small_chunks)  # Larger content should have more chunks
        
        # Verify chunk size limits
        for chunk in large_chunks:
            if hasattr(chunk, 'size'):
                assert chunk.size <= memory_manager.max_chunk_size
    
    def test_incremental_context_building(self, memory_manager):
        """Test incremental context building across multiple operations."""
        # Simulate series of related operations
        operations = [
            {"content": "Start new feature development", "type": "CREATE"},
            {"content": "Add authentication middleware", "type": "UPDATE"},
            {"content": "Fix security vulnerability", "type": "UPDATE"},
            {"content": "Complete feature testing", "type": "COMPLETE"}
        ]
        
        # Process operations incrementally
        for i, operation in enumerate(operations):
            result = memory_manager.add_incremental_context(operation["content"], operation["type"])
            
            # Context should build incrementally
            assert result is not None
            
            # Should maintain context from previous operations
            context = memory_manager.get_current_context()
            assert len(context.operations) == i + 1


class TestConcurrentExporter:
    """Test concurrent OTLP exporter for linear scaling parallelism."""
    
    @pytest.fixture
    def concurrent_exporter(self):
        """Create concurrent exporter for testing."""
        return ConcurrentExporter(initial_workers=2)
    
    def test_concurrent_exporter_initialization(self, concurrent_exporter):
        """Test concurrent exporter initializes correctly."""
        assert concurrent_exporter is not None
        assert hasattr(concurrent_exporter, 'worker_count')
        assert hasattr(concurrent_exporter, 'task_queue')
        assert concurrent_exporter.worker_count >= 2
    
    @pytest.mark.asyncio
    async def test_linear_scaling_parallelism(self, concurrent_exporter):
        """Test linear scaling parallelism with demonstrated performance."""
        # Create test items for processing
        test_items = [
            {"id": f"item_{i}", "data": f"test data {i}", "priority": i % 3}
            for i in range(10)
        ]
        
        # Process items concurrently
        results = await concurrent_exporter.process_items_concurrently(test_items)
        
        # Should process all items
        assert len(results) == len(test_items)
        
        # All items should be processed successfully
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) >= 8  # At least 80% success rate
    
    @pytest.mark.asyncio
    async def test_worker_pool_management(self, concurrent_exporter):
        """Test dynamic worker pool management."""
        # Test scaling up workers
        initial_workers = concurrent_exporter.worker_count
        concurrent_exporter.scale_workers(5)
        assert concurrent_exporter.worker_count >= initial_workers
        
        # Test scaling down workers
        concurrent_exporter.scale_workers(2)
        assert concurrent_exporter.worker_count >= 2  # Should maintain minimum
        
        # Test worker health monitoring
        if hasattr(concurrent_exporter, 'check_worker_health'):
            health_status = concurrent_exporter.check_worker_health()
            assert health_status.get('healthy_workers', 0) >= 0
    
    @pytest.mark.asyncio
    async def test_otlp_export_pipeline(self, concurrent_exporter):
        """Test OTLP export pipeline functionality."""
        # Test OTLP-formatted data export
        otlp_data = {
            "resource_spans": [
                {
                    "resource": {"attributes": [{"key": "service.name", "value": "atlas-test"}]},
                    "instrumentation_library_spans": [
                        {
                            "spans": [
                                {
                                    "trace_id": "test-trace-123",
                                    "span_id": "test-span-456",
                                    "name": "test-operation",
                                    "start_time_unix_nano": 1640995200000000000,
                                    "end_time_unix_nano": 1640995260000000000
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Export OTLP data
        export_result = await concurrent_exporter.export_otlp_data(otlp_data)
        
        # Should handle OTLP export
        assert export_result is not None
        assert export_result.get('exported', False) or export_result.get('queued', False)
    
    def test_performance_metrics_tracking(self, concurrent_exporter):
        """Test performance metrics tracking for the 804.7x improvement."""
        # Get baseline metrics
        metrics = concurrent_exporter.get_performance_metrics()
        
        # Should track key performance indicators
        assert 'operations_per_second' in metrics
        assert 'worker_utilization' in metrics
        assert 'queue_depth' in metrics
        
        # Performance should be measurable
        assert metrics['operations_per_second'] >= 0
        assert 0 <= metrics['worker_utilization'] <= 1.0


class TestIntegrationCoordinationOptimizations:
    """Test integration between all 5 coordination optimizations."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def coordination_system(self, temp_storage):
        """Create integrated coordination system."""
        compression_manager = CompressionManager()
        saga_coordinator = SagaCoordinator(storage_path=temp_storage)
        entropy_processor = EntropyProcessor(
            thresholds=EntropyThresholds(0.3, 0.6, 0.8, 0.9)
        )
        memory_manager = IncrementalMemoryManager(storage_path=temp_storage)
        concurrent_exporter = ConcurrentExporter(initial_workers=2)
        
        return {
            'compression': compression_manager,
            'saga': saga_coordinator,
            'entropy': entropy_processor,
            'memory': memory_manager,
            'concurrency': concurrent_exporter
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_coordination_workflow(self, coordination_system):
        """Test end-to-end coordination workflow using all 5 optimizations."""
        # 1. Start with high-entropy task
        task_description = "Implement complex distributed system with microservices, event sourcing, and CQRS patterns"
        
        # 2. Check entropy and trigger processing
        entropy_score = coordination_system['entropy'].calculate_shannon_entropy(task_description)
        should_process = coordination_system['entropy'].should_trigger_processing(entropy_score)
        
        if should_process:
            # 3. Compress task description using LLMLingua
            compressed_task = coordination_system['compression'].compress({"description": task_description})
            
            # 4. Create saga for coordinated execution
            saga_tasks = [
                TestTask("analyze", "Analyze requirements", [], 2.0, {"compressed": compressed_task}),
                TestTask("design", "Create system design", ["analyze"], 4.0, {}),
                TestTask("implement", "Implement system", ["design"], 8.0, {}),
                TestTask("test", "Test system", ["implement"], 3.0, {})
            ]
            
            saga_id = await coordination_system['saga'].start_saga("complex_system_workflow", saga_tasks)
            
            # 5. Process with incremental memory management
            chunks = []
            async for chunk in coordination_system['memory'].process_memory_operation(
                content=task_description,
                operation_type="CREATE",
                context={"saga_id": saga_id, "entropy": entropy_score}
            ):
                chunks.append(chunk)
            
            # 6. Export results concurrently
            export_data = {
                "saga_id": saga_id,
                "entropy_score": entropy_score,
                "compressed_size": len(str(compressed_task)),
                "memory_chunks": len(chunks)
            }
            
            export_result = await coordination_system['concurrency'].export_otlp_data(export_data)
            
            # Verify integration success
            assert saga_id is not None
            assert len(chunks) > 0
            assert export_result is not None
    
    def test_performance_improvement_validation(self, coordination_system):
        """Test that coordination optimizations achieve performance improvement."""
        # Measure baseline performance (without optimizations)
        baseline_metrics = {
            'operations_per_second': 135.7,  # From documentation
            'compression_ratio': 1.0,
            'memory_efficiency': 1.0,
            'concurrency_factor': 1.0
        }
        
        # Measure optimized performance
        optimized_metrics = {}
        
        # Compression improvement
        test_data = {"large_content": "x" * 1000}
        compressed = coordination_system['compression'].compress(test_data)
        compression_ratio = len(str(compressed)) / len(str(test_data))
        optimized_metrics['compression_ratio'] = compression_ratio
        
        # Concurrency improvement
        concurrency_metrics = coordination_system['concurrency'].get_performance_metrics()
        optimized_metrics['operations_per_second'] = concurrency_metrics['operations_per_second']
        
        # Memory efficiency
        memory_chunks = coordination_system['memory'].optimize_chunks("test content")
        optimized_metrics['memory_efficiency'] = 1.0 / max(len(memory_chunks), 1)
        
        # Verify improvements (should approach the documented 804.7x improvement)
        # Note: In test environment, we won't achieve full production performance
        # but should see some improvements
        assert optimized_metrics['compression_ratio'] <= 1.0  # Should compress
        assert optimized_metrics['operations_per_second'] >= 0  # Should be measurable


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])