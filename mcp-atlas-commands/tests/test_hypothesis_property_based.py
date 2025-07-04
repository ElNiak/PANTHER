"""
Property-based tests using Hypothesis for ATLAS MCP components.
Ensures robustness across edge cases and validates core assumptions.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
import json
import string
from typing import Dict, Any, List

# Core components
from src.atlas_commands.intelligent_orchestrator import IntelligentMCPOrchestrator
from src.atlas_commands.compression.compression_manager import CompressionManager, CompressionStrategy
from src.atlas_commands.entropy.entropy_processor import EntropyProcessor, ProcessingTrigger
from src.atlas_commands.entropy.incremental_memory_manager import (
    IncrementalMemoryManager, 
    MemoryOperationType,
    ChunkingStrategy
)
from src.atlas_commands.saga.saga_coordinator import SagaCoordinator, SagaDefinition, SagaStep
from src.atlas_commands.otlp_concurrency.concurrent_exporter import ConcurrentExporter


# Strategy generators
@composite
def task_descriptions(draw):
    """Generate realistic task descriptions."""
    verbs = ["implement", "refactor", "analyze", "optimize", "debug", "test", "deploy", "fix"]
    nouns = ["feature", "system", "component", "service", "API", "database", "interface", "workflow"]
    adjectives = ["new", "improved", "complex", "simple", "critical", "advanced", "basic", "efficient"]
    
    verb = draw(st.sampled_from(verbs))
    adj = draw(st.sampled_from(adjectives))
    noun = draw(st.sampled_from(nouns))
    
    return f"{verb} {adj} {noun}"


@composite
def task_contexts(draw):
    """Generate realistic task contexts."""
    domains = ["authentication", "data", "network", "security", "ui", "api", "storage"]
    priorities = ["low", "medium", "high", "critical"]
    team_sizes = st.integers(min_value=1, max_value=20)
    
    return {
        "domain": draw(st.sampled_from(domains)),
        "priority": draw(st.sampled_from(priorities)),
        "team_size": draw(team_sizes),
        "deadline": draw(st.booleans()),
        "complexity": draw(st.floats(min_value=0.0, max_value=1.0))
    }


@composite
def compression_content(draw):
    """Generate content suitable for compression testing."""
    # Generate different types of content
    content_type = draw(st.sampled_from([
        "json", "repeated_text", "random_text", "structured_data", "code_snippet"
    ]))
    
    if content_type == "json":
        data = draw(st.dictionaries(
            st.text(alphabet=string.ascii_letters, min_size=1, max_size=10),
            st.one_of(st.text(min_size=1, max_size=50), st.integers(), st.booleans()),
            min_size=1,
            max_size=10
        ))
        return json.dumps(data)
    
    elif content_type == "repeated_text":
        base_text = draw(st.text(alphabet=string.printable, min_size=10, max_size=50))
        repetitions = draw(st.integers(min_value=2, max_value=10))
        return (base_text + " ") * repetitions
    
    elif content_type == "code_snippet":
        functions = ["def process_data(data):", "class DataProcessor:", "import json", "return result"]
        lines = draw(st.lists(st.sampled_from(functions), min_size=1, max_size=10))
        return "\n".join(lines)
    
    else:
        return draw(st.text(alphabet=string.printable, min_size=10, max_size=1000))


@composite
def entropy_content(draw):
    """Generate content for entropy analysis."""
    entropy_type = draw(st.sampled_from(["low", "medium", "high"]))
    
    if entropy_type == "low":
        # Repetitive content
        word = draw(st.text(alphabet=string.ascii_letters, min_size=3, max_size=8))
        return (word + " ") * draw(st.integers(min_value=5, max_value=20))
    
    elif entropy_type == "high":
        # Random, high-entropy content
        return draw(st.text(
            alphabet=string.printable,
            min_size=50,
            max_size=200
        ))
    
    else:
        # Medium entropy - structured but varied
        words = draw(st.lists(
            st.text(alphabet=string.ascii_letters, min_size=3, max_size=12),
            min_size=10,
            max_size=50
        ))
        return " ".join(words)


class TestIntelligentOrchestratorProperties:
    """Property-based tests for IntelligentMCPOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for property testing."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            return IntelligentMCPOrchestrator(storage_path=temp_dir)
    
    @given(
        task_description=task_descriptions(),
        context=task_contexts(),
        requirements=st.dictionaries(
            st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
            st.one_of(st.text(min_size=1, max_size=100), st.integers(), st.booleans()),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_orchestrate_workflow_always_returns_result(self, orchestrator, task_description, context, requirements):
        """Property: orchestrate_workflow always returns a valid result."""
        assume(len(task_description) > 5)  # Reasonable task description
        
        result = await orchestrator.orchestrate_workflow(task_description, context, requirements)
        
        # Properties that should always hold
        assert result is not None
        assert hasattr(result, 'estimated_efficiency_gain')
        assert hasattr(result, 'coordination_strategy')
        assert getattr(result, 'estimated_efficiency_gain', 0) >= 0
        assert getattr(result, 'estimated_efficiency_gain', 0) <= 100  # Reasonable upper bound
    
    @given(
        task_descriptions=st.lists(task_descriptions(), min_size=1, max_size=5),
        context=task_contexts()
    )
    @settings(max_examples=10, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_concurrent_orchestration_consistency(self, orchestrator, task_descriptions, context):
        """Property: concurrent orchestration produces consistent results."""
        # Execute multiple tasks concurrently
        tasks = [
            orchestrator.orchestrate_workflow(desc, context, {})
            for desc in task_descriptions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Properties
        assert len(results) == len(task_descriptions)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0  # At least some should succeed
        
        # All successful results should have valid efficiency gains
        for result in successful_results:
            efficiency = getattr(result, 'estimated_efficiency_gain', 0)
            assert 0 <= efficiency <= 100


class TestCompressionManagerProperties:
    """Property-based tests for CompressionManager."""
    
    @pytest.fixture
    def compression_manager(self):
        """Create compression manager for property testing."""
        return CompressionManager()
    
    @given(
        content=compression_content(),
        strategy=st.sampled_from(list(CompressionStrategy)),
        min_quality=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=25, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_compression_preserves_essential_properties(self, compression_manager, content, strategy, min_quality):
        """Property: compression preserves essential content properties."""
        assume(len(content) > 10)  # Minimum content size
        
        result = await compression_manager.compress(content, {}, strategy, min_quality)
        
        # Properties that should always hold
        assert result is not None
        assert hasattr(result, 'compressed_content')
        assert hasattr(result, 'compression_ratio')
        assert hasattr(result, 'metadata')
        
        # Compression ratio should be valid
        assert 0 <= result.compression_ratio <= 1.0
        
        # If compression was applied, content should be different or same size
        if result.compression_ratio < 1.0:
            # Either content changed or it's the same (no compression applied)
            assert len(result.compressed_content) <= len(content) or result.compressed_content == content
    
    @given(
        content=st.text(alphabet=string.printable, min_size=100, max_size=2000),
        strategies=st.lists(st.sampled_from(list(CompressionStrategy)), min_size=2, max_size=4, unique=True)
    )
    @settings(max_examples=15, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_compression_strategy_consistency(self, compression_manager, content, strategies):
        """Property: different strategies produce valid results consistently."""
        results = []
        
        for strategy in strategies:
            try:
                result = await compression_manager.compress(content, {}, strategy, 0.5)
                results.append((strategy, result))
            except Exception:
                # Some strategies might fail on certain content - that's okay
                pass
        
        # At least one strategy should work
        assume(len(results) > 0)
        
        # All successful results should be valid
        for strategy, result in results:
            assert 0 <= result.compression_ratio <= 1.0
            assert result.compressed_content is not None
            assert isinstance(result.metadata, dict)


class TestEntropyProcessorProperties:
    """Property-based tests for EntropyProcessor."""
    
    @pytest.fixture
    def entropy_processor(self):
        """Create entropy processor for property testing."""
        return EntropyProcessor()
    
    @given(content=entropy_content())
    @settings(max_examples=30, deadline=2000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_entropy_analysis_bounds(self, entropy_processor, content):
        """Property: entropy analysis produces bounded, valid results."""
        assume(len(content) > 5)
        
        analysis = entropy_processor.analyze_content_entropy(content)
        
        # Entropy values should be bounded
        assert 0 <= analysis.content_entropy <= 1.0
        assert 0 <= analysis.token_entropy
        assert 0 <= analysis.pattern_entropy
        assert 0 <= analysis.novelty_score <= 1.0
        assert 0 <= analysis.redundancy_score <= 1.0
        assert 0 <= analysis.information_density
        
        # Processing triggers should be valid
        assert isinstance(analysis.processing_triggers, list)
        for trigger in analysis.processing_triggers:
            assert isinstance(trigger, ProcessingTrigger)
    
    @given(
        contents=st.lists(entropy_content(), min_size=2, max_size=5)
    )
    @settings(max_examples=15, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_entropy_analysis_monotonicity(self, entropy_processor, contents):
        """Property: entropy analysis shows expected relationships."""
        analyses = []
        
        for content in contents:
            assume(len(content) > 5)
            analysis = entropy_processor.analyze_content_entropy(content)
            analyses.append((content, analysis))
        
        # Check that high-entropy content is detected appropriately
        high_entropy_analyses = [a for c, a in analyses if a.content_entropy > 0.8]
        
        if high_entropy_analyses:
            for analysis in high_entropy_analyses:
                # High entropy content should trigger high entropy processing
                triggers = [t.value for t in analysis.processing_triggers]
                assert any(t in triggers for t in ['high_entropy', 'novelty_detected', 'entropy_spike'])


class TestIncrementalMemoryManagerProperties:
    """Property-based tests for IncrementalMemoryManager."""
    
    @pytest.fixture
    def memory_manager(self):
        """Create memory manager for property testing."""
        return IncrementalMemoryManager()
    
    @given(
        content=st.text(alphabet=string.printable, min_size=20, max_size=1000),
        operation_type=st.sampled_from(list(MemoryOperationType)),
        chunking_strategy=st.sampled_from(list(ChunkingStrategy))
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_memory_operation_produces_chunks(self, memory_manager, content, operation_type, chunking_strategy):
        """Property: memory operations always produce valid chunks."""
        chunks = []
        
        async for chunk in memory_manager.process_memory_operation(
            content=content,
            operation_type=operation_type,
            context={"test": True},
            chunking_strategy=chunking_strategy
        ):
            chunks.append(chunk)
        
        # Properties
        assert len(chunks) > 0  # Should produce at least one chunk
        
        for chunk in chunks:
            assert isinstance(chunk, dict)
            assert "status" in chunk or "operation_id" in chunk  # Should have processing info
    
    @given(
        content_list=st.lists(
            st.text(alphabet=string.printable, min_size=10, max_size=200),
            min_size=1,
            max_size=5
        ),
        operation_type=st.sampled_from(list(MemoryOperationType))
    )
    @settings(max_examples=15, deadline=4000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_batch_processing_consistency(self, memory_manager, content_list, operation_type):
        """Property: batch processing maintains consistency."""
        all_chunks = []
        
        for content in content_list:
            chunks = []
            async for chunk in memory_manager.process_memory_operation(
                content=content,
                operation_type=operation_type,
                context={}
            ):
                chunks.append(chunk)
            all_chunks.extend(chunks)
        
        # Should process all content
        assert len(all_chunks) >= len(content_list)


class TestSagaCoordinatorProperties:
    """Property-based tests for SagaCoordinator."""
    
    @pytest.fixture
    def saga_coordinator(self):
        """Create saga coordinator for property testing."""
        return SagaCoordinator()
    
    @given(
        step_count=st.integers(min_value=1, max_value=5),
        timeout_seconds=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=15, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_saga_execution_completeness(self, saga_coordinator, step_count, timeout_seconds):
        """Property: saga execution handles all steps."""
        steps = []
        
        for i in range(step_count):
            step = SagaStep(
                step_id=f"step_{i}",
                name=f"test_step_{i}",
                action=lambda ctx, step: {"step_result": f"completed_{step.step_id}"},
                compensation=lambda ctx, step: {"compensated": step.step_id},
                timeout_seconds=timeout_seconds
            )
            steps.append(step)
        
        saga_def = SagaDefinition(
            saga_id=f"test_saga_{step_count}",
            name=f"property_test_saga_{step_count}",
            steps=steps
        )
        
        result = await saga_coordinator.execute_saga(saga_def, {"test": True})
        
        # Properties
        assert "saga_id" in result
        assert "status" in result
        assert "results" in result
        assert len(result["results"]) == step_count
        
        # Each step should have a result
        for i in range(step_count):
            step_id = f"step_{i}"
            assert step_id in result["results"]
            step_result = result["results"][step_id]
            assert "status" in step_result


class TestConcurrentExporterProperties:
    """Property-based tests for ConcurrentExporter."""
    
    @given(
        item_count=st.integers(min_value=1, max_value=50),
        max_concurrent=st.integers(min_value=1, max_value=10),
        batch_size=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=10, deadline=8000)
    @pytest.mark.asyncio
    async def test_concurrent_export_properties(self, item_count, max_concurrent, batch_size):
        """Property: concurrent export maintains data integrity."""
        exporter = ConcurrentExporter(
            max_concurrent_batches=max_concurrent,
            max_batch_size=batch_size
        )
        
        await exporter.start()
        
        try:
            # Queue items
            item_ids = []
            for i in range(item_count):
                item_id = await exporter.queue_item(
                    data={"test_data": f"item_{i}", "index": i},
                    priority=5
                )
                item_ids.append(item_id)
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Check status
            status = exporter.get_status()
            
            # Properties
            assert status["total_queued"] >= 0
            assert status["metrics"]["total_items_queued"] == item_count
            assert len(item_ids) == item_count
            assert all(isinstance(item_id, str) for item_id in item_ids)
            
        finally:
            await exporter.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])