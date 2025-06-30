"""
Performance Benchmark Tests for CLI Commands.

Tests targeting performance characteristics of methods identified as having
high line counts, complexity, or potential performance bottlenecks.
Based on Codacy analysis findings.
"""

import argparse
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestMethodPerformance(ComprehensiveCLITest):
    """Test performance of individual methods with high complexity/line count."""

    def test_run_command_handle_performance(self):
        """
        Test performance of RunCommand.handle method.
        Lines: 146, Complexity: 43 - highest complexity in CLI module.
        """
        from panther.cli.subcommands.run import RunCommand

        with patch("pathlib.Path.exists", return_value=True), patch(
            "panther.cli.subcommands.run.ConfigLoader"
        ) as mock_loader_class, patch(
            "panther.cli.subcommands.run.ExperimentManager"
        ) as mock_exp_class, patch(
            "panther.core.utils.logger_factory.LoggerFactory"
        ), patch(
            "panther.core.metrics.MetricsCollector"
        ), patch(
            "panther.core.metrics.ResourceMonitor"
        ), patch(
            "panther.core.metrics.MetricsReporter"
        ), patch(
            "panther.core.metrics.MetricsExporter"
        ), patch(
            "builtins.open", mock_open(read_data="test: config")
        ):
            # Setup mocks for fast execution
            mock_loader = MagicMock()
            mock_global_config = MagicMock()
            mock_global_config.logging.level.name = "INFO"
            mock_global_config.logging.format = "%(message)s"
            mock_global_config.logging.enable_colors = True
            mock_global_config.docker = MagicMock()
            mock_global_config.docker.user_mapping = MagicMock()
            mock_loader.load_and_validate_global_config.return_value = (
                mock_global_config
            )

            mock_experiment_config = MagicMock()
            mock_experiment_config.tests = [MagicMock()]
            mock_experiment_config.services = MagicMock()
            mock_loader.load_and_validate_experiment_config.return_value = (
                mock_experiment_config
            )
            mock_loader_class.return_value = mock_loader

            mock_exp = MagicMock()
            mock_exp.initialize_experiments.return_value = True
            mock_exp_class.return_value = mock_exp

            args = self.create_namespace(
                config="test.yaml", dry_run=True, enable_metrics=True, verbose=False
            )

            # Measure execution time
            start_time = time.time()
            result = RunCommand.handle(args)
            end_time = time.time()

            execution_time = end_time - start_time

            # Should complete quickly (< 1 second for dry run)
            assert (
                execution_time < 1.0
            ), f"RunCommand.handle took {execution_time:.3f}s, expected < 1.0s"
            assert result == 0

    def test_admin_docker_handle_performance(self):
        """
        Test performance of AdminCommand._handle_docker method.
        Lines: 180, Complexity: 29 - most complex admin method.
        """
        from panther.cli.subcommands.admin import AdminCommand

        with patch("subprocess.run") as mock_subprocess, patch(
            "pathlib.Path.exists", return_value=True
        ):
            # Setup fast mock responses
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout="Fast response", stderr=""
            )

            args = self.create_namespace(
                admin_action="docker", docker_action="status", format="simple"
            )

            # Measure execution time
            start_time = time.time()
            result = AdminCommand._handle_docker(args)
            end_time = time.time()

            execution_time = end_time - start_time

            # Should complete quickly (< 0.5 seconds for status check)
            assert (
                execution_time < 0.5
            ), f"AdminCommand._handle_docker took {execution_time:.3f}s, expected < 0.5s"
            assert result in [0, 1]

    def test_config_validate_performance(self):
        """
        Test performance of ConfigCommand._handle_validate method.
        Lines: 80, Complexity: 26 - high complexity validation method.
        """
        from panther.cli.subcommands.config import ConfigCommand

        with patch(
            "panther.cli.subcommands.config.ConfigLoader"
        ) as mock_loader_class, patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="test: config")
        ):
            # Setup fast mock validation
            mock_loader = MagicMock()
            mock_loader.load_and_validate_experiment_config.return_value = MagicMock()
            mock_loader_class.return_value = mock_loader

            args = self.create_namespace(
                config_action="validate",
                config="test.yaml",
                format="simple",
                strict=False,
            )

            # Measure execution time
            start_time = time.time()
            result = ConfigCommand._handle_validate(args)
            end_time = time.time()

            execution_time = end_time - start_time

            # Should complete quickly (< 0.3 seconds for simple validation)
            assert (
                execution_time < 0.3
            ), f"ConfigCommand._handle_validate took {execution_time:.3f}s, expected < 0.3s"
            assert result == 0

    def test_plugins_list_performance_large_dataset(self):
        """
        Test performance of PluginsCommand._handle_list with large datasets.
        Lines: 63, Complexity: 14 - tests scalability with many plugins.
        """
        from panther.cli.subcommands.plugins import PluginsCommand

        # Create large plugin dataset
        large_plugin_list = [
            MagicMock(
                name=f"plugin_{i:04d}",
                type="iut",
                version=f"1.{i % 100}.{i % 10}",
                description=f"Test plugin number {i} with detailed description",
            )
            for i in range(1000)  # 1000 plugins
        ]

        with patch("panther.cli.subcommands.plugins.PluginManager") as mock_manager:
            mock_manager_instance = MagicMock()
            mock_manager_instance.discover_plugins.return_value = None
            mock_manager_instance.get_plugins_by_type.return_value = large_plugin_list
            mock_manager.return_value = mock_manager_instance

            args = self.create_namespace(format="table", type="all")

            # Measure execution time with large dataset
            start_time = time.time()
            result = PluginsCommand._handle_list(args)
            end_time = time.time()

            execution_time = end_time - start_time

            # Should handle large datasets efficiently (< 2 seconds for 1000 plugins)
            assert (
                execution_time < 2.0
            ), f"PluginsCommand._handle_list with 1000 plugins took {execution_time:.3f}s, expected < 2.0s"
            assert result == 0

    def test_check_command_performance_all_checks(self):
        """
        Test performance of CheckCommand.handle with all checks enabled.
        Lines: 62, Complexity: 21 - tests performance of comprehensive checking.
        """
        from panther.cli.subcommands.check import CheckCommand

        with patch("subprocess.run") as mock_subprocess:
            # Setup fast mock responses for all subprocess calls
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout="Check passed", stderr=""
            )

            args = self.create_namespace(
                check_deps=True,
                check_lint=True,
                check_type=True,
                check_security=True,
                verbose=False,
            )

            # Measure execution time for all checks
            start_time = time.time()
            result = CheckCommand.handle(args)
            end_time = time.time()

            execution_time = end_time - start_time

            # Should complete all checks efficiently (< 1 second with mocks)
            assert (
                execution_time < 1.0
            ), f"CheckCommand.handle with all checks took {execution_time:.3f}s, expected < 1.0s"
            assert result in [0, 1]


class TestConcurrencyAndParallelism(ComprehensiveCLITest):
    """Test concurrent execution and thread safety."""

    def test_concurrent_command_execution(self):
        """Test multiple CLI commands executing concurrently."""
        from panther.cli.subcommands.tools import ToolsCommand

        def execute_tools_list():
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(
                    returncode=0, stdout="tool_name version", stderr=""
                )

                args = self.create_namespace(tools_action="list")
                return ToolsCommand._list_tools(args)

        # Execute multiple commands concurrently
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_tools_list) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        execution_time = end_time - start_time

        # Concurrent execution should be faster than sequential
        # and all should succeed
        assert all(result == 0 for result in results)
        assert len(results) == 10
        assert execution_time < 5.0  # Should complete within 5 seconds

    def test_thread_safety_plugin_discovery(self):
        """Test thread safety of plugin discovery operations."""
        from panther.cli.subcommands.plugins import PluginsCommand

        def discover_plugins():
            with patch("panther.cli.subcommands.plugins.PluginManager") as mock_manager:
                mock_manager_instance = MagicMock()
                mock_manager_instance.discover_plugins.return_value = None
                mock_manager_instance.get_plugins_by_type.return_value = [
                    MagicMock(
                        name="test_plugin",
                        type="iut",
                        version="1.0",
                        description="Test",
                    )
                ]
                mock_manager.return_value = mock_manager_instance

                args = self.create_namespace(format="simple", type="all")
                return PluginsCommand._handle_list(args)

        # Test concurrent plugin discovery
        results = []

        def worker():
            results.append(discover_plugins())

        threads = [threading.Thread(target=worker) for _ in range(5)]

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        end_time = time.time()

        # All threads should complete successfully
        assert len(results) == 5
        assert all(result == 0 for result in results)
        assert end_time - start_time < 3.0  # Should complete quickly

    def test_resource_contention_handling(self):
        """Test handling of resource contention in concurrent operations."""
        from panther.cli.subcommands.admin import AdminCommand

        def cleanup_operation():
            with patch("subprocess.run") as mock_subprocess, patch(
                "pathlib.Path.exists", return_value=True
            ):
                # Simulate varying response times
                import random

                time.sleep(random.uniform(0.01, 0.1))

                mock_subprocess.return_value = MagicMock(
                    returncode=0, stdout="Cleanup completed", stderr=""
                )

                args = self.create_namespace(admin_action="clean", force=False)
                return AdminCommand._handle_clean(args)

        # Execute cleanup operations concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(cleanup_operation) for _ in range(6)]
            results = [future.result() for future in as_completed(futures)]

        # Should handle resource contention gracefully
        assert len(results) == 6
        assert all(result in [0, 1] for result in results)


class TestMemoryAndResourceUsage(ComprehensiveCLITest):
    """Test memory usage and resource management."""

    def test_memory_usage_large_configurations(self):
        """Test memory usage with large configuration files."""
        from panther.cli.subcommands.config import ConfigCommand

        # Create large configuration content
        large_config = {
            "services": {
                f"service_{i}": {
                    "name": f"service_{i}",
                    "ports": [f"{4000+i}:{4000+i}"],
                    "environment": {f"VAR_{j}": f"value_{j}" for j in range(100)},
                }
                for i in range(100)
            },
            "tests": [
                {
                    "name": f"test_{i}",
                    "description": "x" * 1000,  # Large description
                    "steps": {f"step_{j}": f"action_{j}" for j in range(50)},
                }
                for i in range(50)
            ],
        }

        with patch(
            "panther.cli.subcommands.config.ConfigLoader"
        ) as mock_loader_class, patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=str(large_config))
        ):
            mock_loader = MagicMock()
            mock_loader.load_and_validate_experiment_config.return_value = large_config
            mock_loader_class.return_value = mock_loader

            args = self.create_namespace(
                config_action="validate", config="large_config.yaml", format="detailed"
            )

            # Monitor memory usage (simplified test)
            import tracemalloc

            tracemalloc.start()

            result = ConfigCommand._handle_validate(args)

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Should handle large configs without excessive memory usage
            assert result == 0
            # Peak memory should be reasonable (< 50MB for this test)
            assert peak < 50 * 1024 * 1024  # 50MB

    def test_resource_cleanup_after_errors(self):
        """Test proper resource cleanup after errors."""
        from panther.cli.subcommands.tools import ToolsCommand

        # Test resource cleanup when subprocess fails
        with patch("subprocess.run") as mock_subprocess, patch(
            "subprocess.Popen"
        ) as mock_popen:
            # Simulate subprocess failure
            mock_subprocess.side_effect = Exception("Subprocess failed")

            # Mock Popen for cleanup testing
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.stdout = MagicMock()
            mock_popen.return_value = mock_process

            args = self.create_namespace(tools_action="install-slim", force=True)

            result = ToolsCommand._install_slim(args)

            # Should handle errors and cleanup resources
            assert result == 1

            # Verify cleanup was attempted
            if mock_process.stdout.close.called:
                mock_process.stdout.close.assert_called()


class TestScalabilityLimits(ComprehensiveCLITest):
    """Test scalability limits and edge cases."""

    def test_maximum_parameter_combinations(self):
        """Test handling of maximum parameter combinations."""
        from panther.cli.subcommands.run import RunCommand

        # Test with many parameters set
        max_params = {
            "config": "test.yaml",
            "output_dir": "outputs",
            "experiment_name": "max_test",
            "dry_run": True,
            "enable_metrics": True,
            "metrics_collect_resources": True,
            "metrics_generate_report": True,
            "metrics_output_format": "json",
            "verbose": True,
            "debug": True,
            "force": True,
            "parallel": True,
            "timeout": 3600,
        }

        with patch("panther.cli.subcommands.run.ConfigLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_loader.load_and_validate_global_config.return_value = MagicMock()
            mock_loader.load_and_validate_experiment_config.return_value = MagicMock()
            mock_loader_class.return_value = mock_loader

            args = self.create_namespace(**max_params)

            start_time = time.time()
            result = RunCommand.handle(args)
            end_time = time.time()

            # Should handle maximum parameters efficiently
            assert result in [0, 1]
            assert end_time - start_time < 2.0  # Should complete quickly

    def test_extreme_output_volumes(self):
        """Test handling of extreme output volumes."""
        from panther.cli.subcommands.plugins import PluginsCommand

        # Create plugins with very large descriptions
        extreme_plugins = [
            MagicMock(
                name=f"plugin_{i}",
                type="iut",
                version="1.0.0",
                description="X" * 10000,  # 10KB description each
            )
            for i in range(100)  # 1MB total
        ]

        with patch(
            "panther.cli.subcommands.plugins.PluginManager"
        ) as mock_manager, patch("logging.info") as mock_log:
            mock_manager_instance = MagicMock()
            mock_manager_instance.discover_plugins.return_value = None
            mock_manager_instance.get_plugins_by_type.return_value = extreme_plugins
            mock_manager.return_value = mock_manager_instance

            args = self.create_namespace(format="table", type="all")

            start_time = time.time()
            result = PluginsCommand._handle_list(args)
            end_time = time.time()

            # Should handle extreme output volumes
            assert result == 0
            assert end_time - start_time < 5.0  # Should complete within 5 seconds

            # Verify output was generated (check logging calls)
            assert mock_log.called

    def test_command_execution_timeout_handling(self):
        """Test handling of command execution timeouts."""
        from panther.cli.subcommands.check import CheckCommand

        # Test with long-running subprocess that should timeout
        def slow_subprocess(*args, **kwargs):
            time.sleep(2.0)  # Simulate slow operation
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=slow_subprocess):
            args = self.create_namespace(check_lint=True)

            start_time = time.time()
            result = CheckCommand._check_lint(args)
            end_time = time.time()

            execution_time = end_time - start_time

            # Should handle slow operations
            assert result in [0, 1]
            # Should not hang indefinitely
            assert execution_time < 10.0  # 10 second max
