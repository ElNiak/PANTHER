"""
Test Output Recorder - Comprehensive test output capture and logging

This module provides utilities for recording test outputs, results, and metrics
to files for analysis and documentation purposes.
"""

import json
import logging
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest


class TestOutputRecorder:
    """Records test outputs, logs, and results to files."""

    def __init__(self, test_name: str, output_dir: Path = None):
        self.test_name = test_name
        self.output_dir = output_dir or Path("test_outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create test-specific directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_dir = self.output_dir / f"{test_name}_{timestamp}"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Initialize recording data
        self.start_time = time.time()
        self.logs = []
        self.outputs = []
        self.errors = []
        self.metrics = {}
        self.results = {}

        # Setup logging capture
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging to capture all log messages."""
        self.log_file = self.test_dir / "test.log"

        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(formatter)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG)

        self.file_handler = file_handler

    def record_output(self, output: str, output_type: str = "stdout"):
        """Record command or function output."""
        timestamp = datetime.now().isoformat()
        output_record = {"timestamp": timestamp, "type": output_type, "content": output}
        self.outputs.append(output_record)

        # Write to file immediately
        output_file = self.test_dir / f"{output_type}_output.txt"
        with open(output_file, "a") as f:
            f.write(f"[{timestamp}] {output}\n")

    def record_error(self, error: Exception, context: str = ""):
        """Record test errors and exceptions."""
        timestamp = datetime.now().isoformat()
        error_record = {
            "timestamp": timestamp,
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
        }
        self.errors.append(error_record)

        # Write to error file
        error_file = self.test_dir / "errors.json"
        with open(error_file, "w") as f:
            json.dump(self.errors, f, indent=2)

    def record_metric(self, name: str, value: Any, unit: str = ""):
        """Record test metrics."""
        self.metrics[name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        }

        # Write metrics to file
        metrics_file = self.test_dir / "metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def record_result(self, test_case: str, result: str, details: Dict = None):
        """Record test case results."""
        self.results[test_case] = {
            "result": result,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        # Write results to file
        results_file = self.test_dir / "results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

    @contextmanager
    def capture_subprocess_output(self):
        """Context manager to capture subprocess output."""
        captured_outputs = []

        def mock_run(*args, **kwargs):
            # Call original subprocess.run
            import subprocess

            result = subprocess.run(*args, **kwargs, capture_output=True, text=True)

            # Record the output
            self.record_output(f"Command: {args[0]}", "command")
            if result.stdout:
                self.record_output(result.stdout, "stdout")
            if result.stderr:
                self.record_output(result.stderr, "stderr")

            captured_outputs.append(
                {
                    "command": args[0],
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            )

            return result

        with patch("subprocess.run", side_effect=mock_run):
            yield captured_outputs

    @contextmanager
    def capture_function_calls(self, module_path: str, function_name: str):
        """Context manager to capture function calls and outputs."""
        captured_calls = []

        def mock_function(*args, **kwargs):
            # Record the call
            call_record = {
                "function": f"{module_path}.{function_name}",
                "args": str(args),
                "kwargs": str(kwargs),
                "timestamp": datetime.now().isoformat(),
            }
            captured_calls.append(call_record)

            # Call original function if it exists
            try:
                import importlib

                module = importlib.import_module(module_path)
                original_func = getattr(module, function_name)
                result = original_func(*args, **kwargs)

                # Record result
                call_record["result"] = str(result)
                self.record_output(
                    f"Function call: {module_path}.{function_name} -> {result}",
                    "function_call",
                )

                return result
            except Exception as e:
                call_record["error"] = str(e)
                self.record_error(e, f"Function call: {module_path}.{function_name}")
                raise

        with patch(f"{module_path}.{function_name}", side_effect=mock_function):
            yield captured_calls

    def finalize(self):
        """Finalize recording and generate summary."""
        end_time = time.time()
        duration = end_time - self.start_time

        # Record final metrics
        self.record_metric("test_duration", duration, "seconds")
        self.record_metric("total_outputs", len(self.outputs), "count")
        self.record_metric("total_errors", len(self.errors), "count")

        # Generate summary report
        summary = {
            "test_name": self.test_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "duration": duration,
            "outputs_count": len(self.outputs),
            "errors_count": len(self.errors),
            "metrics": self.metrics,
            "results_summary": {
                "total_tests": len(self.results),
                "passed": sum(
                    1 for r in self.results.values() if r["result"] == "PASS"
                ),
                "failed": sum(
                    1 for r in self.results.values() if r["result"] == "FAIL"
                ),
                "skipped": sum(
                    1 for r in self.results.values() if r["result"] == "SKIP"
                ),
            },
        }

        # Write summary
        summary_file = self.test_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Generate human-readable report
        self._generate_report(summary)

        # Cleanup logging
        if hasattr(self, "file_handler"):
            logging.getLogger().removeHandler(self.file_handler)

        return summary

    def _generate_report(self, summary: Dict):
        """Generate human-readable test report."""
        report_file = self.test_dir / "TEST_REPORT.md"

        with open(report_file, "w") as f:
            f.write(f"# Test Report: {self.test_name}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Duration:** {summary['duration']:.2f} seconds\n")
            f.write(f"- **Outputs Captured:** {summary['outputs_count']}\n")
            f.write(f"- **Errors:** {summary['errors_count']}\n")
            f.write(f"- **Test Cases:** {summary['results_summary']['total_tests']}\n")
            f.write(f"- **Passed:** {summary['results_summary']['passed']}\n")
            f.write(f"- **Failed:** {summary['results_summary']['failed']}\n")
            f.write(f"- **Skipped:** {summary['results_summary']['skipped']}\n\n")

            if self.metrics:
                f.write("## Metrics\n\n")
                for name, metric in self.metrics.items():
                    f.write(f"- **{name}:** {metric['value']} {metric['unit']}\n")
                f.write("\n")

            if self.results:
                f.write("## Test Results\n\n")
                for test_case, result in self.results.items():
                    status_emoji = (
                        "✅"
                        if result["result"] == "PASS"
                        else "❌"
                        if result["result"] == "FAIL"
                        else "⏭️"
                    )
                    f.write(f"### {status_emoji} {test_case}\n\n")
                    f.write(f"**Result:** {result['result']}\n\n")
                    if result.get("details"):
                        f.write("**Details:**\n")
                        for key, value in result["details"].items():
                            f.write(f"- {key}: {value}\n")
                        f.write("\n")

            if self.errors:
                f.write("## Errors\n\n")
                for error in self.errors:
                    f.write(f"### {error['type']}\n\n")
                    f.write(f"**Time:** {error['timestamp']}\n\n")
                    f.write(f"**Context:** {error['context']}\n\n")
                    f.write(f"**Message:** {error['message']}\n\n")

            f.write("## Files Generated\n\n")
            files = list(self.test_dir.glob("*"))
            for file_path in sorted(files):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    f.write(f"- `{file_path.name}` ({size} bytes)\n")


@pytest.fixture
def test_output_recorder(request):
    """Pytest fixture for test output recording."""
    test_name = request.node.name
    recorder = TestOutputRecorder(test_name)

    # Yield the recorder for use in tests
    yield recorder

    # Finalize recording after test
    summary = recorder.finalize()

    # Attach summary to test node for pytest reporting
    if hasattr(request.node, "user_properties"):
        request.node.user_properties.append(("test_output_dir", str(recorder.test_dir)))
        request.node.user_properties.append(("test_duration", summary["duration"]))


@pytest.fixture
def enhanced_cli_tester():
    """Enhanced CLI testing fixture with output recording."""

    class EnhancedCLITester:
        def __init__(self):
            self.outputs = []
            self.commands_run = []
            self.temp_files = []

        def create_temp_config(self, config_dict: Dict) -> str:
            """Create temporary config file and track it."""
            import yaml

            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            )
            yaml.dump(config_dict, temp_file)
            temp_file.close()
            self.temp_files.append(temp_file.name)
            return temp_file.name

        def create_namespace(self, **kwargs):
            """Create argument namespace with tracking."""

            class Namespace:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)

            ns = Namespace(**kwargs)
            self.commands_run.append({"type": "namespace", "args": kwargs})
            return ns

        def run_command_with_recording(
            self, command_class, method_name: str, args, recorder: TestOutputRecorder
        ):
            """Run CLI command with comprehensive recording."""
            start_time = time.time()

            try:
                # Record command execution start
                recorder.record_output(
                    f"Starting {command_class.__name__}.{method_name}", "command_start"
                )

                # Execute command
                if hasattr(command_class, method_name):
                    method = getattr(command_class, method_name)
                    result = method(args)
                else:
                    result = command_class.handle(args)

                # Record success
                end_time = time.time()
                duration = end_time - start_time

                recorder.record_metric(f"{method_name}_duration", duration, "seconds")
                recorder.record_result(
                    f"{command_class.__name__}.{method_name}",
                    "PASS" if result == 0 else "FAIL",
                    {"return_code": result, "duration": duration},
                )

                recorder.record_output(
                    f"Completed {command_class.__name__}.{method_name} with result {result}",
                    "command_end",
                )

                return result

            except Exception as e:
                # Record failure
                end_time = time.time()
                duration = end_time - start_time

                recorder.record_error(e, f"{command_class.__name__}.{method_name}")
                recorder.record_result(
                    f"{command_class.__name__}.{method_name}",
                    "FAIL",
                    {"exception": str(e), "duration": duration},
                )

                raise

        def cleanup(self):
            """Clean up temporary files."""
            for temp_file in self.temp_files:
                try:
                    Path(temp_file).unlink()
                except FileNotFoundError:
                    pass

    tester = EnhancedCLITester()
    yield tester
    tester.cleanup()


@pytest.fixture(scope="session")
def test_session_recorder():
    """Session-wide test recording for aggregate analysis."""
    session_recorder = TestOutputRecorder(
        "test_session", Path("test_outputs") / "session"
    )
    yield session_recorder

    # Generate session summary
    summary = session_recorder.finalize()

    # Create aggregate report
    aggregate_file = session_recorder.test_dir / "AGGREGATE_TEST_REPORT.md"
    with open(aggregate_file, "w") as f:
        f.write("# Aggregate Test Session Report\n\n")
        f.write(f"**Session Duration:** {summary['duration']:.2f} seconds\n\n")
        f.write(f"**Total Test Outputs:** {summary['outputs_count']}\n\n")
        f.write(f"**Total Errors:** {summary['errors_count']}\n\n")

        # List all individual test directories
        f.write("## Individual Test Reports\n\n")
        test_dirs = list(Path("test_outputs").glob("test_*"))
        for test_dir in sorted(test_dirs):
            if test_dir.is_dir() and test_dir != session_recorder.test_dir:
                f.write(f"- [{test_dir.name}](./{test_dir.name}/TEST_REPORT.md)\n")


class TestMetricsCollector:
    """Collect and analyze test metrics across multiple test runs."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("test_outputs") / "metrics"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = {}

    def collect_from_test_dir(self, test_dir: Path):
        """Collect metrics from a test directory."""
        metrics_file = test_dir / "metrics.json"
        if metrics_file.exists():
            with open(metrics_file) as f:
                test_metrics = json.load(f)
                test_name = test_dir.name
                self.metrics[test_name] = test_metrics

    def collect_all_metrics(self):
        """Collect metrics from all test directories."""
        test_dirs = Path("test_outputs").glob("test_*")
        for test_dir in test_dirs:
            if test_dir.is_dir():
                self.collect_from_test_dir(test_dir)

    def generate_analysis(self):
        """Generate comprehensive metrics analysis."""
        if not self.metrics:
            return

        analysis = {
            "total_tests": len(self.metrics),
            "avg_duration": 0,
            "total_duration": 0,
            "performance_summary": {},
            "test_efficiency": {},
        }

        # Calculate averages and totals
        durations = []
        for test_name, metrics in self.metrics.items():
            if "test_duration" in metrics:
                duration = metrics["test_duration"]["value"]
                durations.append(duration)
                analysis["total_duration"] += duration

        if durations:
            analysis["avg_duration"] = sum(durations) / len(durations)
            analysis["min_duration"] = min(durations)
            analysis["max_duration"] = max(durations)

        # Save analysis
        analysis_file = self.output_dir / "test_metrics_analysis.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)

        # Generate report
        self._generate_metrics_report(analysis)

        return analysis

    def _generate_metrics_report(self, analysis: Dict):
        """Generate human-readable metrics report."""
        report_file = self.output_dir / "METRICS_REPORT.md"

        with open(report_file, "w") as f:
            f.write("# Test Metrics Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Total Tests Analyzed:** {analysis['total_tests']}\n")
            f.write(f"- **Total Duration:** {analysis['total_duration']:.2f} seconds\n")
            f.write(f"- **Average Duration:** {analysis['avg_duration']:.2f} seconds\n")

            if "min_duration" in analysis:
                f.write(f"- **Fastest Test:** {analysis['min_duration']:.2f} seconds\n")
                f.write(f"- **Slowest Test:** {analysis['max_duration']:.2f} seconds\n")

            f.write("\n## Individual Test Metrics\n\n")
            for test_name, metrics in self.metrics.items():
                f.write(f"### {test_name}\n\n")
                for metric_name, metric_data in metrics.items():
                    f.write(
                        f"- **{metric_name}:** {metric_data['value']} {metric_data['unit']}\n"
                    )
                f.write("\n")
