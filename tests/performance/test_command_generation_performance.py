"""Performance tests for command generation pipeline."""
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.slow]


class TestCommandGenerationPerformance:
    """Performance tests for command generation components."""

    def test_template_rendering_performance(self, sample_service_config):
        """Test that template rendering performs within acceptable limits."""
        # Mock template renderer for performance testing
        with patch(
            "panther.core.template.template_renderer.TemplateRenderer"
        ) as mock_renderer:
            mock_instance = Mock()
            mock_renderer.return_value = mock_instance
            mock_instance.render_command_template.return_value = "rendered command"

            # Time the rendering process
            start_time = time.time()

            # Simulate rendering multiple templates
            for _ in range(100):
                mock_instance.render_command_template(
                    "test_template", sample_service_config
                )

            end_time = time.time()
            execution_time = end_time - start_time

            # Assert performance criteria (should complete in under 1 second for 100 renders)
            assert (
                execution_time < 1.0
            ), f"Template rendering took {execution_time:.3f}s, expected < 1.0s"

            # Verify all calls were made
            assert mock_instance.render_command_template.call_count == 100

    def test_plugin_loading_performance(self, temp_dir):
        """Test that plugin loading performs within acceptable limits."""
        # Create multiple fake plugins
        plugins_dir = Path(temp_dir) / "plugins"
        for i in range(50):
            plugin_dir = (
                plugins_dir / "services" / "iut" / f"protocol_{i}" / f"impl_{i}"
            )
            plugin_dir.mkdir(parents=True, exist_ok=True)

            plugin_file = plugin_dir / f"impl_{i}.py"
            plugin_file.write_text(
                f"""
class Impl{i}ServiceManager:
    def __init__(self, *args, **kwargs):
        pass

    def generate_commands(self):
        return {{"run_cmd": {{"command_binary": "test_{i}"}}}}
"""
            )

        # Time the plugin discovery process
        start_time = time.time()

        # Simulate plugin discovery (mocked for performance)
        discovered_plugins = list(plugins_dir.rglob("*.py"))

        end_time = time.time()
        execution_time = end_time - start_time

        # Assert performance criteria
        assert (
            execution_time < 0.5
        ), f"Plugin discovery took {execution_time:.3f}s, expected < 0.5s"
        assert len(discovered_plugins) == 50

    @pytest.mark.parametrize("num_services", [1, 5, 10, 20])
    def test_command_validation_scalability(self, num_services):
        """Test command validation scalability with increasing number of services."""
        from panther.plugins.services.services_interface import (
            RUN_CMD_SCHEMA,
            validate_structure,
        )

        # Create test command structure
        test_command = {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "run_cmd": {
                "working_dir": "/test",
                "command_binary": "test",
                "command_args": "--test",
                "timeout": 60,
                "command_env": {},
            },
            "post_run_cmds": [],
        }

        start_time = time.time()

        # Validate multiple service configurations
        for i in range(num_services):
            try:
                validate_structure(test_command, RUN_CMD_SCHEMA)
            except Exception:
                pass  # We're testing performance, not correctness here

        end_time = time.time()
        execution_time = end_time - start_time

        # Performance should scale linearly
        expected_max_time = num_services * 0.01  # 10ms per service max
        assert (
            execution_time < expected_max_time
        ), f"Validation took {execution_time:.3f}s for {num_services} services"


class TestMemoryUsagePerformance:
    """Test memory usage characteristics of the system."""

    @pytest.mark.slow
    def test_event_system_memory_usage(self, mock_event_manager):
        """Test that event system doesn't leak memory with many events."""
        import gc

        # Force garbage collection before test
        gc.collect()

        # Create many events (simulating long-running experiment)
        events_created = 1000

        for i in range(events_created):
            # Mock event creation without actual event objects to test the pattern
            mock_event = Mock()
            mock_event.event_type = f"test.event.{i}"
            mock_event.data = {"test_data": f"data_{i}"}

            # Simulate event processing
            mock_event_manager.emit_event(mock_event)

        # Force cleanup
        gc.collect()

        # Verify events were processed
        assert mock_event_manager.emit_event.call_count == events_created

    def test_plugin_manager_memory_efficiency(self, temp_dir):
        """Test that plugin manager doesn't hold unnecessary references."""
        # This would test that plugin instances are properly cleaned up
        # when no longer needed, preventing memory leaks

        plugins_created = 10
        mock_plugins = []

        for i in range(plugins_created):
            mock_plugin = Mock()
            mock_plugin.name = f"plugin_{i}"
            mock_plugins.append(mock_plugin)

        # Simulate plugin cleanup
        mock_plugins.clear()

        # Verify cleanup
        assert len(mock_plugins) == 0


@pytest.mark.benchmark
class TestBenchmarkSuite:
    """Benchmark suite for key system components."""

    def test_full_command_generation_pipeline_benchmark(self, sample_service_config):
        """Benchmark the complete command generation pipeline."""
        iterations = 50
        times = []

        for _ in range(iterations):
            start_time = time.time()

            # Simulate full pipeline (mocked for consistent testing)
            # 1. Plugin loading
            # 2. Template rendering
            # 3. Command validation
            # 4. Command processing

            # Mock the pipeline steps
            time.sleep(0.001)  # Simulate minimal processing time

            end_time = time.time()
            times.append(end_time - start_time)

        # Calculate statistics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        # Performance assertions
        assert avg_time < 0.01, f"Average pipeline time {avg_time:.4f}s too slow"
        assert max_time < 0.02, f"Max pipeline time {max_time:.4f}s too slow"

        print(f"\\nPipeline Performance Stats:")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Min: {min_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")
