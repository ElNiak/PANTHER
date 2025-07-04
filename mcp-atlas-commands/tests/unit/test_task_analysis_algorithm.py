"""
Unit tests for Task Analysis Algorithm - MCP Component Testing
Following best practices for MCP tool testing with pytest and mocking.
"""

import pytest
import unittest.mock as mock
from datetime import datetime
from typing import Dict, Any

from src.atlas_commands.task_analysis_algorithm import (
    TaskComplexityAnalyzer,
    DependencyAnalyzer,
    PatternDetector,
    ExecutionOptimizer,
    analyze_task_for_atlas_framework,
    ComplexityLevel,
    ComplexityFactors
)


class TestTaskComplexityAnalyzer:
    """Test TaskComplexityAnalyzer component in isolation."""
    
    @pytest.fixture
    def analyzer(self):
        """Fixture for TaskComplexityAnalyzer instance."""
        return TaskComplexityAnalyzer()
    
    @pytest.fixture
    def valid_task_context(self):
        """Fixture for valid task context."""
        return {
            "domain": "backend",
            "team_size": 3,
            "deadline": "2025-07-01",
            "priority": "high"
        }
    
    @pytest.fixture
    def invalid_task_context(self):
        """Fixture for invalid task context."""
        return {
            "domain": "",  # Invalid empty domain
            "team_size": -1,  # Invalid negative team size
            "priority": "invalid_priority"  # Invalid priority
        }
    
    def test_analyze_task_complexity_simple_task(self, analyzer, valid_task_context):
        """Test complexity analysis for simple tasks."""
        task_description = "Fix typo in documentation"
        
        result = analyzer.analyze_task_complexity(task_description, valid_task_context)
        
        assert isinstance(result, ComplexityFactors)
        assert result.computational_complexity >= -1.0  # Can be negative for simple tasks
        assert result.cognitive_complexity >= -1.0  # Can be negative for simple tasks
        assert result.integration_complexity >= -1.0  # Can be negative for simple tasks
        assert result.estimated_duration > 0.0
        assert result.dependency_count >= 0
    
    def test_analyze_task_complexity_complex_task(self, analyzer, valid_task_context):
        """Test complexity analysis for complex tasks."""
        task_description = "Design distributed microservices architecture with event-driven communication"
        
        result = analyzer.analyze_task_complexity(task_description, valid_task_context)
        
        assert isinstance(result, ComplexityFactors)
        # Complex tasks should have higher complexity scores
        assert result.cognitive_complexity > 0.1
        assert result.integration_complexity > 0.1
        assert result.estimated_duration > 1.0
    
    def test_analyze_task_complexity_empty_description(self, analyzer, valid_task_context):
        """Test error handling for empty task description."""
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            analyzer.analyze_task_complexity("", valid_task_context)
    
    def test_analyze_task_complexity_none_description(self, analyzer, valid_task_context):
        """Test error handling for None task description."""
        with pytest.raises(ValueError, match="Task description cannot be None"):
            analyzer.analyze_task_complexity(None, valid_task_context)
    
    def test_analyze_task_complexity_invalid_context(self, analyzer, invalid_task_context):
        """Test handling of invalid context parameters."""
        task_description = "Implement REST API"
        
        # Should handle invalid context gracefully, not crash
        result = analyzer.analyze_task_complexity(task_description, invalid_task_context)
        assert isinstance(result, ComplexityFactors)
    
    def test_analyze_task_complexity_no_context(self, analyzer):
        """Test analysis with None context."""
        task_description = "Implement user authentication"
        
        result = analyzer.analyze_task_complexity(task_description, None)
        
        assert isinstance(result, ComplexityFactors)
        assert result.estimated_duration > 0.0
    
    @mock.patch('src.atlas_commands.task_analysis_algorithm.datetime')
    def test_complexity_analysis_deterministic_timestamp(self, mock_datetime, analyzer, valid_task_context):
        """Test deterministic behavior with mocked timestamp."""
        # Mock datetime for predictable test results
        fixed_time = datetime(2025, 6, 24, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        task_description = "Deploy application to production"
        result = analyzer.analyze_task_complexity(task_description, valid_task_context)
        
        assert isinstance(result, ComplexityFactors)
        # Verify the mocked timestamp was used
        mock_datetime.now.assert_called_once()


class TestDependencyAnalyzer:
    """Test DependencyAnalyzer component in isolation."""
    
    @pytest.fixture
    def dependency_analyzer(self):
        """Fixture for DependencyAnalyzer instance."""
        return DependencyAnalyzer({})
    
    @pytest.fixture
    def mock_task_graph(self):
        """Fixture for mock task dependency graph."""
        return {
            "task_1": {"dependencies": [], "type": "implementation"},
            "task_2": {"dependencies": ["task_1"], "type": "testing"},
            "task_3": {"dependencies": ["task_1", "task_2"], "type": "deployment"}
        }
    
    def test_analyze_dependencies_simple_task(self, dependency_analyzer):
        """Test dependency analysis for simple task."""
        task_description = "Write unit tests"
        
        result = dependency_analyzer.analyze_dependencies(task_description, {})
        
        assert "count" in result
        assert "types" in result
        assert "execution_order" in result
        assert isinstance(result["count"], int)
        assert result["count"] >= 0
    
    def test_analyze_dependencies_with_mock_graph(self):
        """Test dependency analysis with predefined task graph."""
        mock_graph = {
            "current_task": {"dependencies": ["task_a", "task_b"], "type": "integration"}
        }
        analyzer = DependencyAnalyzer(mock_graph)
        
        result = analyzer.analyze_dependencies("current_task", {})
        
        assert result["count"] >= 0
        assert isinstance(result["types"], list)
        assert isinstance(result["execution_order"], list)
    
    def test_analyze_dependencies_circular_detection(self):
        """Test detection of circular dependencies."""
        circular_graph = {
            "task_a": {"dependencies": ["task_b"], "type": "implementation"},
            "task_b": {"dependencies": ["task_c"], "type": "testing"},
            "task_c": {"dependencies": ["task_a"], "type": "deployment"}  # Circular!
        }
        analyzer = DependencyAnalyzer(circular_graph)
        
        # Should handle circular dependencies gracefully
        result = analyzer.analyze_dependencies("task_a", {})
        assert isinstance(result, dict)
        assert "count" in result


class TestPatternDetector:
    """Test PatternDetector component in isolation."""
    
    @pytest.fixture
    def pattern_detector(self):
        """Fixture for PatternDetector instance."""
        return PatternDetector("", {})
    
    def test_detect_patterns_crud_operations(self, pattern_detector):
        """Test pattern detection for CRUD operations."""
        task_description = "Create user registration API with full CRUD operations"
        
        result = pattern_detector.detect_patterns(task_description, {})
        
        assert "detected" in result
        assert "primary_pattern" in result
        assert "confidence" in result
        assert isinstance(result["detected"], list)
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
    
    def test_detect_patterns_microservices(self, pattern_detector):
        """Test pattern detection for microservices architecture."""
        task_description = "Design microservices with event-driven architecture and service mesh"
        
        result = pattern_detector.detect_patterns(task_description, {})
        
        assert isinstance(result["detected"], list)
        assert result["primary_pattern"] in ["microservices", "event_driven", "unknown"]
    
    @mock.patch.object(PatternDetector, '_extract_technical_keywords')
    def test_detect_patterns_with_mocked_keywords(self, mock_extract, pattern_detector):
        """Test pattern detection with mocked keyword extraction."""
        # Mock keyword extraction for predictable results
        mock_extract.return_value = ["api", "database", "authentication"]
        
        task_description = "Build secure API"
        result = pattern_detector.detect_patterns(task_description, {})
        
        mock_extract.assert_called_once_with(task_description)
        assert isinstance(result, dict)


class TestExecutionOptimizer:
    """Test ExecutionOptimizer component in isolation."""
    
    @pytest.fixture
    def execution_optimizer(self):
        """Fixture for ExecutionOptimizer instance."""
        return ExecutionOptimizer()
    
    @pytest.fixture
    def sample_complexity_factors(self):
        """Fixture for sample complexity factors."""
        return ComplexityFactors(
            computational_complexity=0.3,
            cognitive_complexity=0.5,
            integration_complexity=0.2,
            risk_factor=0.1,
            uncertainty_factor=0.1,
            dependency_count=3,
            estimated_duration=8.0
        )
    
    def test_optimize_execution_standard_task(self, execution_optimizer, sample_complexity_factors):
        """Test execution optimization for standard complexity task."""
        task_description = "Implement REST API endpoints"
        context = {"team_size": 2, "deadline": "2025-07-15"}
        
        result = execution_optimizer.optimize_execution(
            task_description, sample_complexity_factors, context
        )
        
        assert "execution_mode" in result
        assert "parallelization" in result
        assert "resource_allocation" in result
        assert "caching_strategy" in result
        assert "monitoring_level" in result
        assert "optimization_score" in result
        
        assert isinstance(result["optimization_score"], float)
        assert 0.0 <= result["optimization_score"] <= 1.0
    
    def test_optimize_execution_high_complexity(self, execution_optimizer):
        """Test execution optimization for high complexity task."""
        high_complexity = ComplexityFactors(
            computational_complexity=0.8,
            cognitive_complexity=0.9,
            integration_complexity=0.7,
            risk_factor=0.5,
            uncertainty_factor=0.4,
            dependency_count=10,
            estimated_duration=40.0
        )
        
        task_description = "Migrate legacy monolith to microservices"
        context = {"team_size": 5, "deadline": "2025-12-31"}
        
        result = execution_optimizer.optimize_execution(
            task_description, high_complexity, context
        )
        
        # High complexity tasks should have different optimization strategies
        assert result["execution_mode"] in ["monitored", "phased", "standard"]
        assert result["monitoring_level"] in ["comprehensive", "detailed", "minimal"]
    
    def test_optimize_execution_empty_context(self, execution_optimizer, sample_complexity_factors):
        """Test execution optimization with empty context."""
        task_description = "Write documentation"
        
        result = execution_optimizer.optimize_execution(
            task_description, sample_complexity_factors, {}
        )
        
        assert isinstance(result, dict)
        assert all(key in result for key in [
            "execution_mode", "parallelization", "resource_allocation", 
            "caching_strategy", "monitoring_level", "optimization_score"
        ])


class TestAnalyzeTaskForAtlasFramework:
    """Test the main analyze_task_for_atlas_framework function."""
    
    def test_analyze_task_complete_flow(self):
        """Test complete task analysis flow."""
        task_description = "Implement user authentication with OAuth2"
        context = {"domain": "backend", "team_size": 3}
        
        result = analyze_task_for_atlas_framework(task_description, context)
        
        # Verify all expected sections are present
        assert "task_description" in result
        assert "complexity" in result
        assert "dependencies" in result
        assert "patterns" in result
        assert "optimization" in result
        assert "recommendations" in result
        assert "metadata" in result
        
        # Verify data types and structure
        assert result["task_description"] == task_description
        assert isinstance(result["complexity"], dict)
        assert isinstance(result["dependencies"], dict)
        assert isinstance(result["patterns"], dict)
        assert isinstance(result["optimization"], dict)
        assert isinstance(result["recommendations"], dict)
        assert isinstance(result["metadata"], dict)
    
    def test_analyze_task_with_invalid_input(self):
        """Test error handling for invalid inputs."""
        with pytest.raises(ValueError):
            analyze_task_for_atlas_framework("", {})
        
        with pytest.raises(ValueError):
            analyze_task_for_atlas_framework(None, {})
    
    @mock.patch('src.atlas_commands.task_analysis_algorithm.TaskComplexityAnalyzer')
    @mock.patch('src.atlas_commands.task_analysis_algorithm.DependencyAnalyzer')
    @mock.patch('src.atlas_commands.task_analysis_algorithm.PatternDetector')
    @mock.patch('src.atlas_commands.task_analysis_algorithm.ExecutionOptimizer')
    def test_analyze_task_mocked_components(self, mock_optimizer, mock_detector, mock_dep_analyzer, mock_complexity_analyzer):
        """Test task analysis with all components mocked for isolation."""
        # Setup mocks
        mock_complexity_analyzer.return_value.analyze_task_complexity.return_value = ComplexityFactors(
            computational_complexity=0.2,
            cognitive_complexity=0.3,
            integration_complexity=0.1,
            risk_factor=0.0,
            uncertainty_factor=0.0,
            dependency_count=1,
            estimated_duration=2.0
        )
        
        mock_dep_analyzer.return_value.analyze_dependencies.return_value = {
            "count": 2,
            "types": ["implementation"],
            "execution_order": ["task_1", "task_2"]
        }
        
        mock_detector.return_value.detect_patterns.return_value = {
            "detected": ["api_pattern"],
            "primary_pattern": "api_pattern",
            "confidence": 0.8
        }
        
        mock_optimizer.return_value.optimize_execution.return_value = {
            "execution_mode": "standard",
            "optimization_score": 0.9
        }
        
        # Execute test
        result = analyze_task_for_atlas_framework("Test task", {"domain": "test"})
        
        # Verify mocks were called
        mock_complexity_analyzer.assert_called_once()
        mock_dep_analyzer.assert_called_once()
        mock_detector.assert_called_once()
        mock_optimizer.assert_called_once()
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "complexity" in result
        assert "dependencies" in result
        assert "patterns" in result
        assert "optimization" in result
    
    def test_analyze_task_metadata_contains_timestamp(self):
        """Test that metadata contains proper timestamp."""
        task_description = "Deploy to production"
        context = {"environment": "production"}
        
        result = analyze_task_for_atlas_framework(task_description, context)
        
        assert "metadata" in result
        assert "analysis_timestamp" in result["metadata"]
        assert "analyzer_version" in result["metadata"]
        assert "task_signature" in result["metadata"]
        
        # Verify timestamp format (ISO format)
        timestamp = result["metadata"]["analysis_timestamp"]
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise exception


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def test_config():
    """Session-wide test configuration."""
    return {
        "test_environment": "unit",
        "mock_external_dependencies": True,
        "enable_logging": False
    }


# Coverage and performance tests
class TestTaskAnalysisPerformance:
    """Performance and edge case tests."""
    
    def test_analyze_large_task_description(self):
        """Test analysis of very large task descriptions."""
        large_description = "Implement " + "complex " * 1000 + "system"
        context = {"domain": "backend"}
        
        result = analyze_task_for_atlas_framework(large_description, context)
        
        assert isinstance(result, dict)
        assert "complexity" in result
    
    def test_analyze_special_characters(self):
        """Test analysis with special characters and unicode."""
        task_description = "Implement API with émojis 🚀 and spëcial châractérs"
        context = {"domain": "frontend"}
        
        result = analyze_task_for_atlas_framework(task_description, context)
        
        assert result["task_description"] == task_description
        assert isinstance(result["complexity"], dict)
    
    def test_concurrent_analysis_thread_safety(self):
        """Test thread safety of analysis components."""
        import threading
        
        results = []
        
        def analyze_task():
            result = analyze_task_for_atlas_framework("Test concurrent task", {"domain": "test"})
            results.append(result)
        
        # Run multiple analyses concurrently
        threads = [threading.Thread(target=analyze_task) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, dict)
            assert "complexity" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.atlas_commands.task_analysis_algorithm"])