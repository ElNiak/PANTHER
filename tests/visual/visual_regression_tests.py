#!/usr/bin/env python3
"""
Visual Regression Testing for PANTHER CLI

This module implements visual regression testing to ensure CLI output
consistency across changes. It captures, compares, and validates CLI outputs.
"""

import difflib
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CLIOutputCapture:
    """Capture and normalize CLI output for comparison."""

    def __init__(self, baseline_dir: Path = None):
        self.baseline_dir = baseline_dir or Path("tests/visual/baselines")
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.captures_dir = Path("tests/visual/captures")
        self.captures_dir.mkdir(parents=True, exist_ok=True)

    def capture_output(self, command: List[str], name: str) -> Tuple[str, str]:
        """Capture stdout and stderr from a CLI command."""
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)

        # Save raw output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_file = self.captures_dir / f"{name}_{timestamp}.txt"

        with open(capture_file, "w") as f:
            f.write(f"Command: {' '.join(command)}\n")
            f.write(f"Return code: {result.returncode}\n")
            f.write(f"{'='*50}\nSTDOUT:\n{'='*50}\n")
            f.write(result.stdout)
            f.write(f"\n{'='*50}\nSTDERR:\n{'='*50}\n")
            f.write(result.stderr)

        return result.stdout, result.stderr

    def normalize_output(self, output: str) -> str:
        """Normalize output to remove variable elements."""
        # Remove timestamps
        output = re.sub(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", "<TIMESTAMP>", output)

        # Remove file paths that might vary
        output = re.sub(r"/[^\s]+/PANTHER/", "<PANTHER_ROOT>/", output)

        # Remove UUIDs
        output = re.sub(
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            "<UUID>",
            output,
        )

        # Remove process IDs
        output = re.sub(r"PID:\s*\d+", "PID: <PID>", output)

        # Remove duration values
        output = re.sub(r"\d+\.\d+\s*(seconds?|ms)", "<DURATION>", output)

        # Normalize line endings
        output = output.replace("\r\n", "\n").strip()

        return output

    def save_baseline(self, name: str, stdout: str, stderr: str):
        """Save output as baseline for future comparisons."""
        baseline_file = self.baseline_dir / f"{name}.json"

        baseline_data = {
            "name": name,
            "created": datetime.now().isoformat(),
            "stdout": self.normalize_output(stdout),
            "stderr": self.normalize_output(stderr),
            "checksum": self._calculate_checksum(stdout + stderr),
        }

        with open(baseline_file, "w") as f:
            json.dump(baseline_data, f, indent=2)

        print(f"✅ Baseline saved: {baseline_file}")

    def compare_with_baseline(
        self, name: str, stdout: str, stderr: str
    ) -> Dict[str, any]:
        """Compare current output with baseline."""
        baseline_file = self.baseline_dir / f"{name}.json"

        if not baseline_file.exists():
            return {"status": "no_baseline", "message": f"No baseline found for {name}"}

        with open(baseline_file, "r") as f:
            baseline = json.load(f)

        current_stdout = self.normalize_output(stdout)
        current_stderr = self.normalize_output(stderr)

        # Compare normalized outputs
        stdout_match = current_stdout == baseline["stdout"]
        stderr_match = current_stderr == baseline["stderr"]

        if stdout_match and stderr_match:
            return {"status": "pass", "message": "Output matches baseline"}

        # Generate diff
        stdout_diff = list(
            difflib.unified_diff(
                baseline["stdout"].splitlines(),
                current_stdout.splitlines(),
                fromfile=f"{name}_baseline_stdout",
                tofile=f"{name}_current_stdout",
                lineterm="",
            )
        )

        stderr_diff = list(
            difflib.unified_diff(
                baseline["stderr"].splitlines(),
                current_stderr.splitlines(),
                fromfile=f"{name}_baseline_stderr",
                tofile=f"{name}_current_stderr",
                lineterm="",
            )
        )

        return {
            "status": "fail",
            "message": "Output differs from baseline",
            "stdout_diff": stdout_diff,
            "stderr_diff": stderr_diff,
        }

    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum of content."""
        return hashlib.sha256(content.encode()).hexdigest()


class VisualRegressionTestSuite:
    """Suite of visual regression tests for PANTHER CLI."""

    def __init__(self):
        self.capture = CLIOutputCapture()
        self.test_cases = [
            {
                "name": "help_output",
                "command": ["python", "-m", "panther", "--help"],
                "description": "Main help text",
            },
            {
                "name": "version_output",
                "command": ["python", "-m", "panther", "--version"],
                "description": "Version information",
            },
            {
                "name": "list_plugins",
                "command": ["python", "-m", "panther", "--list-plugins"],
                "description": "Plugin listing output",
            },
            {
                "name": "validate_config",
                "command": [
                    "python",
                    "-m",
                    "panther",
                    "--validate-config",
                    "experiment-config/experiment_config_example_minimal.yaml",
                ],
                "description": "Configuration validation output",
            },
            {
                "name": "plugin_params",
                "command": [
                    "python",
                    "-m",
                    "panther",
                    "--list-plugin-params",
                    "picoquic",
                    "--plugin-type",
                    "iut",
                    "--protocol",
                    "quic",
                ],
                "description": "Plugin parameter listing",
            },
            {
                "name": "error_missing_config",
                "command": [
                    "python",
                    "-m",
                    "panther",
                    "--experiment-config",
                    "nonexistent.yaml",
                ],
                "description": "Error message for missing config",
            },
        ]
        self.results = []

    def run_all_tests(self, update_baselines: bool = False) -> Dict[str, any]:
        """Run all visual regression tests."""
        print("🎨 PANTHER Visual Regression Test Suite")
        print("=" * 50)

        total_tests = len(self.test_cases)
        passed = 0
        failed = 0
        no_baseline = 0

        for test in self.test_cases:
            print(f"\n📸 Testing: {test['name']} - {test['description']}")

            try:
                # Capture output
                stdout, stderr = self.capture.capture_output(
                    test["command"], test["name"]
                )

                if update_baselines:
                    # Update baseline
                    self.capture.save_baseline(test["name"], stdout, stderr)
                    result = {"status": "baseline_updated"}
                else:
                    # Compare with baseline
                    result = self.capture.compare_with_baseline(
                        test["name"], stdout, stderr
                    )

                # Track results
                if result["status"] == "pass":
                    print("   ✅ PASS - Output matches baseline")
                    passed += 1
                elif result["status"] == "fail":
                    print("   ❌ FAIL - Output differs from baseline")
                    failed += 1
                    if "stdout_diff" in result and result["stdout_diff"]:
                        print("   STDOUT differences:")
                        for line in result["stdout_diff"][:10]:  # Show first 10 lines
                            print(f"     {line}")
                elif result["status"] == "no_baseline":
                    print("   ⚠️  NO BASELINE - Run with --update-baselines")
                    no_baseline += 1
                elif result["status"] == "baseline_updated":
                    print("   📝 BASELINE UPDATED")

                self.results.append({"test": test, "result": result})

            except subprocess.TimeoutExpired:
                print("   ⏱️  TIMEOUT - Command took too long")
                failed += 1
            except Exception as e:
                print(f"   ⚠️  ERROR - {str(e)}")
                failed += 1

        # Summary
        print("\n" + "=" * 50)
        print("📊 VISUAL REGRESSION TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"No Baseline: {no_baseline} ⚠️")

        success_rate = (passed / max(1, total_tests - no_baseline)) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        return {
            "total": total_tests,
            "passed": passed,
            "failed": failed,
            "no_baseline": no_baseline,
            "success_rate": success_rate,
            "results": self.results,
        }

    def generate_report(self, output_file: Path = None):
        """Generate detailed HTML report of visual regression tests."""
        output_file = output_file or Path("tests/visual/visual_regression_report.html")

        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>PANTHER Visual Regression Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #333; color: white; padding: 20px; }
        .summary { background-color: #f0f0f0; padding: 15px; margin: 20px 0; }
        .test-case { border: 1px solid #ddd; margin: 10px 0; padding: 15px; }
        .pass { background-color: #d4edda; }
        .fail { background-color: #f8d7da; }
        .no-baseline { background-color: #fff3cd; }
        .diff { background-color: #f8f8f8; padding: 10px; font-family: monospace; overflow-x: auto; }
        .added { color: green; }
        .removed { color: red; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 PANTHER Visual Regression Test Report</h1>
        <p>Generated: {timestamp}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {total}</p>
        <p>Passed: {passed} ✅</p>
        <p>Failed: {failed} ❌</p>
        <p>No Baseline: {no_baseline} ⚠️</p>
        <p>Success Rate: {success_rate:.1f}%</p>
    </div>

    <h2>Test Results</h2>
    {test_results}
</body>
</html>
        """

        # Generate test result HTML
        test_results_html = ""
        for result in self.results:
            test = result["test"]
            test_result = result["result"]

            status_class = test_result["status"].replace("_", "-")
            test_results_html += f"""
    <div class="test-case {status_class}">
        <h3>{test['name']}</h3>
        <p><strong>Description:</strong> {test['description']}</p>
        <p><strong>Command:</strong> <code>{' '.join(test['command'])}</code></p>
        <p><strong>Status:</strong> {test_result['status'].upper()}</p>
        <p><strong>Message:</strong> {test_result.get('message', '')}</p>
    </div>
            """

        # Fill in template
        html_content = html_content.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total=len(self.results),
            passed=sum(1 for r in self.results if r["result"]["status"] == "pass"),
            failed=sum(1 for r in self.results if r["result"]["status"] == "fail"),
            no_baseline=sum(
                1 for r in self.results if r["result"]["status"] == "no_baseline"
            ),
            success_rate=(
                sum(1 for r in self.results if r["result"]["status"] == "pass")
                / max(
                    1,
                    len(
                        [
                            r
                            for r in self.results
                            if r["result"]["status"] != "no_baseline"
                        ]
                    ),
                )
            )
            * 100,
            test_results=test_results_html,
        )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content)
        print(f"\n📄 Report generated: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run PANTHER visual regression tests")
    parser.add_argument(
        "--update-baselines",
        action="store_true",
        help="Update baselines instead of comparing",
    )
    parser.add_argument(
        "--generate-report", action="store_true", help="Generate HTML report"
    )

    args = parser.parse_args()

    # Run tests
    suite = VisualRegressionTestSuite()
    results = suite.run_all_tests(update_baselines=args.update_baselines)

    # Generate report if requested
    if args.generate_report:
        suite.generate_report()
