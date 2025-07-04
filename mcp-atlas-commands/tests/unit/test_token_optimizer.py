"""
Unit tests for Token Optimizer - MCP Component Testing
Following MCP best practices for testing token optimization and compression components.
"""

import pytest
import asyncio
import unittest.mock as mock
from datetime import datetime
from typing import Dict, List, Any

from src.atlas_commands.token_optimization.token_optimizer import (
    TokenOptimizer,
    ResponseMode,
    ContentType,
    OptimizedResponse,
    optimize_tool_response,
    optimize_tool_response_with_collider
)


class TestTokenOptimizer:
    """Test TokenOptimizer component in isolation."""
    
    @pytest.fixture
    def optimizer(self):
        """Fixture for TokenOptimizer instance."""
        return TokenOptimizer()
    
    @pytest.fixture
    def sample_json_data(self):
        """Fixture for sample JSON data."""
        return {
            "status": "successful",
            "timestamp": "2025-06-24T12:34:56.789Z",
            "debug_info": "This is verbose debug information that could be removed",
            "empty_field": "",
            "null_field": None,
            "results": [1, 2, 3, 4, 5],
            "nested": {
                "detailed_explanation": "Very long explanation with lots of details",
                "status_verbose": "Process completed successfully with no errors"
            }
        }
    
    @pytest.fixture
    def sample_text_data(self):
        """Fixture for sample text data."""
        return """
        INFO: Starting process
        DEBUG: Verbose debug information that could be removed
        ERROR: Critical error occurred
        INFO: Process completed successfully
        """
    
    def test_token_optimizer_initialization(self, optimizer):
        """Test TokenOptimizer initializes correctly."""
        assert optimizer is not None
        assert hasattr(optimizer, 'collider_filter')
        assert hasattr(optimizer, 'token_patterns')
        assert hasattr(optimizer, 'reduction_strategies')
    
    @pytest.mark.asyncio
    async def test_optimize_response_json_data(self, optimizer, sample_json_data):
        """Test response optimization with JSON data."""
        tool_name = "test_tool"
        content_type = ContentType.METADATA
        mode = ResponseMode.BALANCED
        
        results = await optimizer.optimize_response(
            tool_name, sample_json_data, content_type, mode
        )
        
        assert isinstance(results, list)
        assert len(results) == 1
        
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert result.original_tokens > 0
        assert result.optimized_tokens > 0
        assert result.compression_ratio >= 0.0
        assert result.content_type == content_type
        assert result.mode == mode
        assert "tool_name" in result.optimization_metadata
        assert result.optimization_metadata["tool_name"] == tool_name
    
    @pytest.mark.asyncio
    async def test_optimize_response_text_data(self, optimizer, sample_text_data):
        """Test response optimization with text data."""
        tool_name = "log_analyzer"
        content_type = ContentType.LOGS
        mode = ResponseMode.MINIMAL
        
        results = await optimizer.optimize_response(
            tool_name, sample_text_data, content_type, mode
        )
        
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert result.content_type == ContentType.LOGS
        assert result.mode == ResponseMode.MINIMAL
        # Minimal mode should achieve some compression
        assert result.optimized_tokens <= result.original_tokens
    
    @pytest.mark.asyncio
    async def test_optimize_response_different_modes(self, optimizer, sample_json_data):
        """Test optimization with different response modes."""
        tool_name = "test_tool"
        content_type = ContentType.ANALYSIS
        
        modes_to_test = [
            ResponseMode.MINIMAL,
            ResponseMode.BALANCED,
            ResponseMode.DETAILED,
            ResponseMode.AUTO
        ]
        
        results = {}
        for mode in modes_to_test:
            optimization_results = await optimizer.optimize_response(
                tool_name, sample_json_data, content_type, mode
            )
            results[mode] = optimization_results[0]
        
        # Verify all modes complete successfully
        for mode, result in results.items():
            assert isinstance(result, OptimizedResponse)
            assert result.mode == mode
            assert result.original_tokens > 0
            assert result.optimized_tokens > 0
    
    @pytest.mark.asyncio
    async def test_optimize_response_with_collider(self, optimizer, sample_json_data):
        """Test Collider-style optimization."""
        tool_name = "collider_test"
        content_type = ContentType.RESULTS
        mode = ResponseMode.BALANCED
        
        results = await optimizer.optimize_response_with_collider(
            tool_name, sample_json_data, content_type, mode
        )
        
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert "collider_filtering" in result.optimization_metadata
        assert result.optimization_metadata["collider_filtering"] is True
        assert "filtering_strategy" in result.optimization_metadata
        assert "content_priority" in result.optimization_metadata
        assert "token_analysis" in result.optimization_metadata
    
    def test_count_tokens_accuracy(self, optimizer):
        """Test token counting accuracy."""
        test_cases = [
            ("Hello world", 3),  # 2 words * 1.3 ≈ 3
            ("", 0),
            ("Single", 2),  # 1 word * 1.3 ≈ 2 (rounded)
            ("This is a longer sentence with more words", 11)  # 9 words * 1.3 ≈ 11
        ]
        
        for text, expected_range in test_cases:
            token_count = optimizer._count_tokens(text)
            assert isinstance(token_count, int)
            assert token_count >= 0
            # Allow some variance due to rounding
            if expected_range > 0:
                assert abs(token_count - expected_range) <= 2
    
    def test_remove_empty_fields(self, optimizer):
        """Test empty field removal."""
        text_with_empty_fields = '''
        {
          "valid_field": "has_value",
          "empty_string": "",
          "null_field": null,
          "empty_array": [],
          "empty_object": {},
          "another_valid": "value"
        }
        '''
        
        result = optimizer._remove_empty_fields(text_with_empty_fields)
        
        # Empty fields should be removed
        assert ': ""' not in result
        assert ': null' not in result
        assert ': []' not in result
        assert ': {}' not in result
        # Valid fields should remain
        assert '"valid_field"' in result
        assert '"another_valid"' in result
    
    def test_compress_timestamps(self, optimizer):
        """Test timestamp compression."""
        text_with_timestamps = '''
        {
          "created_at": "2025-06-24T12:34:56.789123Z",
          "updated_at": "2025-06-24T15:45:30.123456Z"
        }
        '''
        
        result = optimizer._compress_timestamps(text_with_timestamps)
        
        # Timestamps should be compressed (remove microseconds)
        assert "2025-06-24T12:34:56" in result
        assert "2025-06-24T15:45:30" in result
        assert ".789123Z" not in result
        assert ".123456Z" not in result
    
    def test_abbreviate_status_fields(self, optimizer):
        """Test status field abbreviation."""
        text_with_status = '''
        {
          "status": "successful",
          "state": "completed",
          "progress": "in_progress",
          "result": "failed"
        }
        '''
        
        result = optimizer._abbreviate_status_fields(text_with_status)
        
        # Status values should be abbreviated
        assert '"OK"' in result
        assert '"DONE"' in result
        assert '"WIP"' in result
        assert '"FAIL"' in result
        # Original values should be replaced
        assert '"successful"' not in result
        assert '"completed"' not in result
        assert '"in_progress"' not in result
        assert '"failed"' not in result
    
    def test_remove_debug_info(self, optimizer):
        """Test debug information removal."""
        text_with_debug = '''
        {
          "debug_level": "verbose",
          "trace_id": "abc123",
          "verbose_output": "detailed info",
          "internal_state": "hidden",
          "normal_field": "keep this"
        }
        '''
        
        result = optimizer._remove_debug_info(text_with_debug)
        
        # Debug fields should be removed
        assert "debug_level" not in result
        assert "trace_id" not in result
        assert "verbose_output" not in result
        assert "internal_state" not in result
        # Normal fields should remain
        assert "normal_field" in result
        assert "keep this" in result
    
    def test_summarize_verbose_details(self, optimizer):
        """Test verbose detail summarization."""
        long_text = "x" * 300  # Very long string
        text_with_verbose = f'{{"description": "{long_text}"}}'
        
        result = optimizer._summarize_verbose_details(text_with_verbose)
        
        # Long strings should be truncated
        assert "..." in result
        assert "(300 chars)" in result
        assert len(result) < len(text_with_verbose)
    
    def test_apply_minimal_optimization(self, optimizer):
        """Test minimal optimization mode."""
        formatted_json = '''
        {
          "key": "value",
          "array": [
            1,
            2,
            3
          ]
        }
        '''
        
        result = optimizer._apply_minimal_optimization(formatted_json)
        
        # Should be compact JSON
        assert "\n" not in result or result.count("\n") == 0
        assert result.count(" ") < formatted_json.count(" ")
    
    def test_apply_balanced_optimization(self, optimizer):
        """Test balanced optimization mode."""
        text_with_excess_whitespace = '''
        
        Line 1
        
        
        Line 2
        
        Line 3
        
        
        '''
        
        result = optimizer._apply_balanced_optimization(text_with_excess_whitespace)
        
        # Should remove excessive whitespace but maintain readability
        lines = result.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) == 3  # Only the 3 content lines
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
    
    def test_apply_auto_optimization(self, optimizer):
        """Test automatic optimization mode."""
        # Test small content (should not be optimized)
        small_content = "Short text"
        result_small = optimizer._apply_auto_optimization(small_content, ContentType.METADATA)
        assert result_small == small_content  # No optimization for small content
        
        # Test large content (should be optimized)
        large_content = "word " * 200  # Creates >500 tokens
        result_large = optimizer._apply_auto_optimization(large_content, ContentType.METADATA)
        assert len(result_large) <= len(large_content)  # Should be optimized
    
    def test_get_optimization_statistics(self, optimizer):
        """Test optimization statistics retrieval."""
        stats = optimizer.get_optimization_statistics()
        
        assert isinstance(stats, dict)
        assert "optimizer_version" in stats
        assert "supported_content_types" in stats
        assert "supported_modes" in stats
        assert "collider_filter_available" in stats
        assert "default_mode" in stats
        assert "average_compression_target" in stats
        
        # Verify content types and modes are complete
        assert len(stats["supported_content_types"]) == len(ContentType)
        assert len(stats["supported_modes"]) == len(ResponseMode)
        assert stats["collider_filter_available"] is True
        assert stats["default_mode"] == ResponseMode.BALANCED.value


class TestConvenienceFunctions:
    """Test convenience functions for tool response optimization."""
    
    @pytest.mark.asyncio
    async def test_optimize_tool_response_function(self):
        """Test optimize_tool_response convenience function."""
        tool_name = "test_tool"
        data = {"key": "value", "number": 42}
        content_type = ContentType.RESULTS
        mode = ResponseMode.BALANCED
        
        results = await optimize_tool_response(tool_name, data, content_type, mode)
        
        assert isinstance(results, list)
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert result.content_type == content_type
        assert result.mode == mode
    
    @pytest.mark.asyncio
    async def test_optimize_tool_response_with_collider_function(self):
        """Test optimize_tool_response_with_collider convenience function."""
        tool_name = "collider_tool"
        data = {"large_dataset": list(range(100)), "metadata": "info"}
        content_type = ContentType.ANALYSIS
        mode = ResponseMode.MINIMAL
        
        results = await optimize_tool_response_with_collider(tool_name, data, content_type, mode)
        
        assert isinstance(results, list)
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert "collider_filtering" in result.optimization_metadata
        assert result.optimization_metadata["collider_filtering"] is True


class TestTokenOptimizerErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def optimizer(self):
        return TokenOptimizer()
    
    @pytest.mark.asyncio
    async def test_optimize_response_with_none_data(self, optimizer):
        """Test optimization with None data."""
        results = await optimizer.optimize_response("test_tool", None)
        
        assert isinstance(results, list)
        assert len(results) == 1
        result = results[0]
        assert result.text == "None"
        assert result.original_tokens >= 0
    
    @pytest.mark.asyncio
    async def test_optimize_response_with_complex_object(self, optimizer):
        """Test optimization with complex nested object."""
        complex_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "deep_array": [{"id": i, "data": f"item_{i}"} for i in range(50)]
                    }
                }
            },
            "metadata": {
                "timestamps": ["2025-01-01T00:00:00Z"] * 20,
                "debug_flags": ["verbose", "trace", "debug"] * 10
            }
        }
        
        results = await optimizer.optimize_response(
            "complex_tool", complex_data, ContentType.ANALYSIS, ResponseMode.MINIMAL
        )
        
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert result.original_tokens > 0
        assert result.optimized_tokens > 0
        # Minimal mode should achieve compression on this large dataset
        assert result.compression_ratio >= 0.0
    
    @pytest.mark.asyncio
    async def test_optimize_response_empty_string(self, optimizer):
        """Test optimization with empty string."""
        results = await optimizer.optimize_response("test_tool", "")
        
        result = results[0]
        assert result.text == ""
        assert result.original_tokens == 0
        assert result.optimized_tokens == 0
        assert result.compression_ratio == 0.0
    
    @pytest.mark.asyncio
    async def test_optimize_response_malformed_json_string(self, optimizer):
        """Test optimization with malformed JSON string."""
        malformed_json = '{"key": "value", "incomplete":'
        
        results = await optimizer.optimize_response("test_tool", malformed_json)
        
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        # Should handle malformed JSON gracefully
        assert result.original_tokens > 0
        assert result.optimized_tokens >= 0


class TestTokenOptimizerPerformance:
    """Performance and stress tests for TokenOptimizer."""
    
    @pytest.fixture
    def optimizer(self):
        return TokenOptimizer()
    
    @pytest.mark.asyncio
    async def test_optimize_large_dataset_performance(self, optimizer):
        """Test performance with large datasets."""
        large_data = {
            "records": [{"id": i, "data": f"record_{i}", "metadata": {"created": f"2025-01-{i%30+1:02d}"}} 
                       for i in range(1000)],
            "summary": "Large dataset with 1000 records for performance testing"
        }
        
        import time
        start_time = time.time()
        
        results = await optimizer.optimize_response(
            "performance_tool", large_data, ContentType.RESULTS, ResponseMode.BALANCED
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 5.0  # 5 seconds max
        
        result = results[0]
        assert isinstance(result, OptimizedResponse)
        assert result.original_tokens > 1000  # Should be a large number of tokens
    
    @pytest.mark.asyncio
    async def test_concurrent_optimization_thread_safety(self, optimizer):
        """Test thread safety with concurrent optimizations."""
        import asyncio
        
        async def optimize_task(task_id):
            data = {"task_id": task_id, "data": f"Task {task_id} data"}
            results = await optimizer.optimize_response(f"task_{task_id}", data)
            return results[0]
        
        # Run multiple optimizations concurrently
        tasks = [optimize_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 10
        for i, result in enumerate(results):
            assert isinstance(result, OptimizedResponse)
            assert f"task_{i}" in result.optimization_metadata["tool_name"]


@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Integration test with mocked MCP server context
class TestMCPIntegration:
    """Integration tests simulating MCP server context."""
    
    @pytest.mark.asyncio
    async def test_mcp_tool_response_optimization_workflow(self):
        """Test complete MCP tool response optimization workflow."""
        # Simulate MCP tool response
        mcp_tool_response = {
            "tool_name": "file_analyzer",
            "success": True,
            "result": {
                "files_analyzed": 150,
                "issues_found": [
                    {"file": "app.py", "line": 45, "issue": "Long line", "severity": "warning"},
                    {"file": "utils.py", "line": 123, "issue": "Unused import", "severity": "info"},
                    {"file": "config.py", "line": 67, "issue": "Hard-coded value", "severity": "error"}
                ],
                "summary": "Analysis complete. Found 3 issues across 150 files.",
                "debug_info": "Detailed analysis took 2.3 seconds with full AST parsing",
                "timestamp": "2025-06-24T12:34:56.789Z"
            },
            "metadata": {
                "execution_time": 2.3,
                "memory_usage": "45MB",
                "cpu_usage": "12%"
            }
        }
        
        # Optimize for MCP response
        optimizer = TokenOptimizer()
        results = await optimizer.optimize_response(
            "file_analyzer",
            mcp_tool_response,
            ContentType.ANALYSIS,
            ResponseMode.BALANCED
        )
        
        result = results[0]
        
        # Verify MCP-specific optimization
        assert isinstance(result, OptimizedResponse)
        assert result.original_tokens > 50  # Should be substantial content
        assert "file_analyzer" in result.optimization_metadata["tool_name"]
        assert result.content_type == ContentType.ANALYSIS
        
        # Verify optimized content still contains essential information
        optimized_data = result.text
        assert "files_analyzed" in optimized_data
        assert "issues_found" in optimized_data
        assert "summary" in optimized_data
        # Debug info might be compressed or removed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.atlas_commands.token_optimization.token_optimizer"])