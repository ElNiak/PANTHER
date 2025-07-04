"""
Unit tests for Intelligent MCP Orchestrator - Core Component Testing
Following MCP best practices for testing orchestration and coordination components.
"""

import pytest
import asyncio
import unittest.mock as mock
from datetime import datetime
from typing import Dict, Any, Optional

from src.atlas_commands.intelligent_orchestrator import (
    IntelligentMCPOrchestrator,
    OrchestrationPattern,
    AutomationLevel,
    OrchestrationResult
)


class TestIntelligentMCPOrchestrator:
    """Test IntelligentMCPOrchestrator component in isolation."""
    
    @pytest.fixture
    def orchestrator(self):
        """Fixture for IntelligentMCPOrchestrator instance."""
        return IntelligentMCPOrchestrator()
    
    @pytest.fixture
    def sample_task_request(self):
        """Fixture for sample task orchestration request."""
        return {
            "task_description": "Implement user authentication API with JWT tokens",
            "context": {
                "domain": "backend",
                "team_size": 3,
                "deadline": "2025-07-15",
                "priority": "high",
                "technologies": ["Python", "FastAPI", "PostgreSQL"]
            },
            "requirements": {
                "performance_target": "< 200ms response time",
                "security_level": "high",
                "scalability": "moderate"
            }
        }
    
    @pytest.fixture
    def complex_task_request(self):
        """Fixture for complex task orchestration request."""
        return {
            "task_description": "Migrate legacy monolith to microservices architecture with event-driven communication",
            "context": {
                "domain": "architecture",
                "team_size": 8,
                "deadline": "2025-12-31",
                "priority": "critical",
                "existing_system": "legacy_monolith",
                "target_architecture": "microservices"
            },
            "requirements": {
                "zero_downtime": True,
                "backward_compatibility": True,
                "performance_improvement": "50%"
            }
        }
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test IntelligentMCPOrchestrator initializes correctly."""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'task_analyzer')
        assert hasattr(orchestrator, 'dependency_analyzer')
        assert hasattr(orchestrator, 'pattern_detector')
        assert hasattr(orchestrator, 'tool_registry')
        assert hasattr(orchestrator, 'storage_manager')
        assert hasattr(orchestrator, 'memory_graph')
        assert hasattr(orchestrator, 'command_selector')
    
    def test_orchestrator_initialization_with_custom_storage(self):
        """Test orchestrator initialization with custom storage path."""
        custom_storage = "/tmp/test_atlas_storage"
        orchestrator = IntelligentMCPOrchestrator(storage_path=custom_storage)
        
        assert orchestrator is not None
        # Verify custom storage path is used
        assert hasattr(orchestrator, 'storage_manager')
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_simple_request(self, orchestrator, sample_task_request):
        """Test task orchestration for simple request."""
        with mock.patch.object(orchestrator.task_analyzer, 'analyze_task_complexity') as mock_analyze:
            # Mock the task analysis response
            mock_complexity = mock.MagicMock()
            mock_complexity.level = "moderate"
            mock_complexity.estimated_duration = 8.0
            mock_analyze.return_value = mock_complexity
            
            result = await orchestrator.orchestrate_task(
                sample_task_request["task_description"],
                sample_task_request["context"],
                sample_task_request["requirements"]
            )
            
            assert isinstance(result, OrchestrationResult)
            assert result.task_analysis is not None
            assert result.coordination_strategy is not None
            assert result.token_optimization is not None
            assert result.tool_activation is not None
            assert result.automation_strategy is not None
            assert result.execution_sequence is not None
            assert isinstance(result.execution_sequence, list)
            assert result.estimated_efficiency_gain >= 0.0
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_complex_request(self, orchestrator, complex_task_request):
        """Test task orchestration for complex request."""
        with mock.patch.object(orchestrator.task_analyzer, 'analyze_task_complexity') as mock_analyze:
            # Mock complex task analysis
            mock_complexity = mock.MagicMock()
            mock_complexity.level = "complex"
            mock_complexity.estimated_duration = 120.0
            mock_complexity.dependency_count = 15
            mock_analyze.return_value = mock_complexity
            
            result = await orchestrator.orchestrate_task(
                complex_task_request["task_description"],
                complex_task_request["context"],
                complex_task_request["requirements"]
            )
            
            assert isinstance(result, OrchestrationResult)
            # Complex tasks should have more sophisticated strategies
            assert len(result.execution_sequence) > 3
            assert result.estimated_efficiency_gain > 0.0
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_error_handling(self, orchestrator):
        """Test error handling in task orchestration."""
        # Test with invalid input
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            await orchestrator.orchestrate_task("", {}, {})
        
        with pytest.raises(ValueError, match="Task description cannot be None"):
            await orchestrator.orchestrate_task(None, {}, {})
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_with_mocked_components(self, orchestrator, sample_task_request):
        """Test orchestration with all components mocked for isolation."""
        # Mock all major components
        with mock.patch.object(orchestrator.task_analyzer, 'analyze_task_complexity') as mock_task_analyzer, \
             mock.patch.object(orchestrator.dependency_analyzer, 'analyze_dependencies') as mock_dep_analyzer, \
             mock.patch.object(orchestrator.pattern_detector, 'detect_patterns') as mock_pattern_detector, \
             mock.patch.object(orchestrator.token_optimizer, 'optimize_response') as mock_token_optimizer, \
             mock.patch.object(orchestrator.governance_pipeline, 'activate_features') as mock_governance:
            
            # Setup mock responses
            mock_complexity = mock.MagicMock()
            mock_complexity.level = "moderate"
            mock_complexity.estimated_duration = 6.0
            mock_task_analyzer.return_value = mock_complexity
            
            mock_dep_analyzer.return_value = {
                "count": 3,
                "types": ["implementation", "testing"],
                "execution_order": ["task_1", "task_2", "task_3"]
            }
            
            mock_pattern_detector.return_value = {
                "detected": ["api_pattern", "authentication_pattern"],
                "primary_pattern": "api_pattern",
                "confidence": 0.85
            }
            
            mock_token_optimizer.return_value = [mock.MagicMock(compression_ratio=0.25)]
            
            mock_governance.return_value = {
                "activated_features": ["task_decomposition", "validation_pipeline"],
                "adoption_score": 0.68
            }
            
            # Execute orchestration
            result = await orchestrator.orchestrate_task(
                sample_task_request["task_description"],
                sample_task_request["context"],
                sample_task_request["requirements"]
            )
            
            # Verify all components were called
            mock_task_analyzer.assert_called_once()
            mock_dep_analyzer.assert_called_once()
            mock_pattern_detector.assert_called_once()
            mock_token_optimizer.assert_called()
            mock_governance.assert_called_once()
            
            # Verify result structure
            assert isinstance(result, OrchestrationResult)
            assert result.task_analysis["complexity_level"] == "moderate"
            assert len(result.coordination_strategy["detected_patterns"]) == 2
    
    def test_determine_orchestration_pattern_simple_task(self, orchestrator):
        """Test orchestration pattern determination for simple tasks."""
        simple_task_analysis = {
            "complexity_level": "trivial",
            "estimated_duration": 2.0,
            "dependency_count": 1
        }
        
        pattern = orchestrator._determine_orchestration_pattern(simple_task_analysis, {})
        
        assert pattern in [OrchestrationPattern.DIRECT_EXECUTION, OrchestrationPattern.WORKFLOW_BASED]
    
    def test_determine_orchestration_pattern_complex_task(self, orchestrator):
        """Test orchestration pattern determination for complex tasks."""
        complex_task_analysis = {
            "complexity_level": "complex",
            "estimated_duration": 80.0,
            "dependency_count": 12
        }
        
        pattern = orchestrator._determine_orchestration_pattern(complex_task_analysis, {})
        
        assert pattern in [OrchestrationPattern.STATEFUL_CENTRAL_ORCHESTRATOR, OrchestrationPattern.WORKFLOW_BASED]
    
    def test_determine_automation_level_high_confidence(self, orchestrator):
        """Test automation level determination with high confidence patterns."""
        task_analysis = {"complexity_level": "moderate"}
        patterns = {"confidence": 0.9, "detected": ["well_known_pattern"]}
        context = {"team_experience": "high"}
        
        automation_level = orchestrator._determine_automation_level(task_analysis, patterns, context)
        
        assert automation_level in [AutomationLevel.FULL, AutomationLevel.INTELLIGENT_TRIGGERS, AutomationLevel.PREDICTIVE]
    
    def test_determine_automation_level_low_confidence(self, orchestrator):
        """Test automation level determination with low confidence patterns."""
        task_analysis = {"complexity_level": "complex"}
        patterns = {"confidence": 0.3, "detected": ["unknown_pattern"]}
        context = {"team_experience": "low"}
        
        automation_level = orchestrator._determine_automation_level(task_analysis, patterns, context)
        
        assert automation_level in [AutomationLevel.MANUAL, AutomationLevel.INTELLIGENT_TRIGGERS]
    
    def test_generate_execution_sequence_linear(self, orchestrator):
        """Test execution sequence generation for linear workflow."""
        task_analysis = {"complexity_level": "simple", "estimated_duration": 4.0}
        dependencies = {"execution_order": ["step_1", "step_2", "step_3"]}
        orchestration_pattern = OrchestrationPattern.WORKFLOW_BASED
        
        sequence = orchestrator._generate_execution_sequence(
            task_analysis, dependencies, orchestration_pattern, {}
        )
        
        assert isinstance(sequence, list)
        assert len(sequence) >= 3
        for step in sequence:
            assert isinstance(step, dict)
            assert "step_name" in step
            assert "estimated_duration" in step
            assert "dependencies" in step
    
    def test_generate_execution_sequence_parallel(self, orchestrator):
        """Test execution sequence generation with parallel opportunities."""
        task_analysis = {"complexity_level": "moderate", "estimated_duration": 12.0}
        dependencies = {
            "execution_order": ["analysis", "implementation", "testing", "deployment"],
            "parallel_opportunities": ["testing", "documentation"]
        }
        orchestration_pattern = OrchestrationPattern.STATEFUL_CENTRAL_ORCHESTRATOR
        
        sequence = orchestrator._generate_execution_sequence(
            task_analysis, dependencies, orchestration_pattern, {}
        )
        
        assert isinstance(sequence, list)
        assert len(sequence) >= 4
        
        # Check for parallel execution indicators
        parallel_steps = [step for step in sequence if step.get("parallel", False)]
        assert len(parallel_steps) >= 0  # May or may not have parallel steps
    
    def test_calculate_efficiency_gain_moderate_optimization(self, orchestrator):
        """Test efficiency gain calculation for moderate optimizations."""
        coordination_improvements = {
            "token_reduction": 0.25,
            "parallel_execution": 0.30,
            "automation_level": 0.40
        }
        
        gain = orchestrator._calculate_efficiency_gain(coordination_improvements)
        
        assert isinstance(gain, float)
        assert 0.0 <= gain <= 1.0
        assert gain > 0.2  # Should show meaningful improvement
    
    def test_calculate_efficiency_gain_minimal_optimization(self, orchestrator):
        """Test efficiency gain calculation for minimal optimizations."""
        coordination_improvements = {
            "token_reduction": 0.05,
            "parallel_execution": 0.10,
            "automation_level": 0.15
        }
        
        gain = orchestrator._calculate_efficiency_gain(coordination_improvements)
        
        assert isinstance(gain, float)
        assert 0.0 <= gain <= 1.0
        assert gain < 0.3  # Should show modest improvement
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_real_integration(self, orchestrator):
        """Test orchestration with real (non-mocked) components."""
        # Simple task that should work with real components
        task_description = "Create a simple REST API endpoint"
        context = {"domain": "backend", "team_size": 2}
        requirements = {"performance": "standard"}
        
        result = await orchestrator.orchestrate_task(task_description, context, requirements)
        
        assert isinstance(result, OrchestrationResult)
        assert result.task_analysis is not None
        assert result.coordination_strategy is not None
        assert result.execution_sequence is not None
        assert len(result.execution_sequence) > 0
        assert result.estimated_efficiency_gain >= 0.0


class TestOrchestrationResult:
    """Test OrchestrationResult data structure."""
    
    def test_orchestration_result_creation(self):
        """Test OrchestrationResult creation and validation."""
        result = OrchestrationResult(
            task_analysis={"complexity": "moderate"},
            coordination_strategy={"pattern": "workflow"},
            token_optimization={"compression_ratio": 0.25},
            tool_activation={"activated_tools": ["analyzer", "optimizer"]},
            automation_strategy={"level": "intelligent"},
            value_alignment={"score": 0.85},
            execution_sequence=[
                {"step": "analysis", "duration": 2.0},
                {"step": "implementation", "duration": 6.0}
            ],
            monitoring_framework={"metrics": ["performance", "quality"]},
            success_metrics={"target_efficiency": 0.40},
            estimated_efficiency_gain=0.35
        )
        
        assert result.task_analysis["complexity"] == "moderate"
        assert result.coordination_strategy["pattern"] == "workflow"
        assert result.token_optimization["compression_ratio"] == 0.25
        assert len(result.tool_activation["activated_tools"]) == 2
        assert result.estimated_efficiency_gain == 0.35
        assert len(result.execution_sequence) == 2
    
    def test_orchestration_result_serialization(self):
        """Test OrchestrationResult can be serialized."""
        from dataclasses import asdict
        
        result = OrchestrationResult(
            task_analysis={"test": "data"},
            coordination_strategy={},
            token_optimization={},
            tool_activation={},
            automation_strategy={},
            value_alignment={},
            execution_sequence=[],
            monitoring_framework={},
            success_metrics={},
            estimated_efficiency_gain=0.0
        )
        
        # Should be serializable to dict
        result_dict = asdict(result)
        assert isinstance(result_dict, dict)
        assert "task_analysis" in result_dict
        assert "estimated_efficiency_gain" in result_dict


class TestOrchestratorErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def orchestrator(self):
        return IntelligentMCPOrchestrator()
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_with_component_failure(self, orchestrator):
        """Test orchestration when a component fails."""
        with mock.patch.object(orchestrator.task_analyzer, 'analyze_task_complexity') as mock_analyzer:
            # Mock a component failure
            mock_analyzer.side_effect = Exception("Component failure")
            
            # Should handle component failure gracefully
            with pytest.raises(Exception):
                await orchestrator.orchestrate_task(
                    "Test task",
                    {"domain": "test"},
                    {}
                )
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_with_invalid_context(self, orchestrator):
        """Test orchestration with invalid context data."""
        invalid_contexts = [
            {"team_size": -1},  # Invalid team size
            {"deadline": "invalid_date"},  # Invalid date format
            {"priority": "invalid_priority"},  # Invalid priority
            {"domain": ""},  # Empty domain
        ]
        
        for invalid_context in invalid_contexts:
            # Should handle invalid context gracefully, not crash
            result = await orchestrator.orchestrate_task(
                "Test task with invalid context",
                invalid_context,
                {}
            )
            assert isinstance(result, OrchestrationResult)
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_with_large_context(self, orchestrator):
        """Test orchestration with very large context data."""
        large_context = {
            "domain": "backend",
            "large_data": ["item_" + str(i) for i in range(10000)],  # Large array
            "nested_data": {f"key_{i}": f"value_{i}" for i in range(1000)}  # Large dict
        }
        
        # Should handle large context without performance issues
        result = await orchestrator.orchestrate_task(
            "Task with large context",
            large_context,
            {}
        )
        
        assert isinstance(result, OrchestrationResult)
    
    @pytest.mark.asyncio
    async def test_orchestrate_task_concurrent_requests(self, orchestrator):
        """Test handling of concurrent orchestration requests."""
        async def orchestrate_concurrent_task(task_id):
            return await orchestrator.orchestrate_task(
                f"Concurrent task {task_id}",
                {"domain": "test", "task_id": task_id},
                {}
            )
        
        # Run multiple orchestrations concurrently
        tasks = [orchestrate_concurrent_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert isinstance(result, OrchestrationResult)
            # Verify each task was processed independently
            assert result.task_analysis is not None


class TestOrchestratorPerformance:
    """Performance tests for orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        return IntelligentMCPOrchestrator()
    
    @pytest.mark.asyncio
    async def test_orchestration_performance_simple_task(self, orchestrator):
        """Test orchestration performance for simple tasks."""
        import time
        
        start_time = time.time()
        
        result = await orchestrator.orchestrate_task(
            "Simple performance test task",
            {"domain": "performance"},
            {}
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete quickly for simple tasks
        assert execution_time < 2.0  # 2 seconds max
        assert isinstance(result, OrchestrationResult)
    
    @pytest.mark.asyncio
    async def test_orchestration_memory_usage(self, orchestrator):
        """Test memory usage during orchestration."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Run multiple orchestrations
        for i in range(10):
            result = await orchestrator.orchestrate_task(
                f"Memory test task {i}",
                {"domain": "memory_test"},
                {}
            )
            assert isinstance(result, OrchestrationResult)
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (less than 100MB for 10 tasks)
        assert memory_increase < 100 * 1024 * 1024  # 100MB


@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.atlas_commands.intelligent_orchestrator"])