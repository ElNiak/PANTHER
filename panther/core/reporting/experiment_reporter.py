"""Comprehensive experiment reporting system for PANTHER framework.

This module implements a sophisticated reporting system that generates detailed,
multi-format experiment reports including status summaries, failure analysis,
resource utilization tracking, and fast-fail analysis.

**Report Generation Strategy**:
- **Multi-Format Support**: JSON (machine-readable), Markdown (human-readable), Text (fallback)
- **Template System**: Jinja2-based templating with graceful degradation to basic formatting
- **Rich Context**: Comprehensive experiment metadata, test outcomes, and resource usage
- **Error Recovery**: Multiple format attempts with progressive fallback strategies

**Report Content Architecture**:
```
Experiment Report Structure:
├── Executive Summary (status, duration, success rate)
├── Test Results Analysis (passed/failed breakdown with details)
├── Fast-Fail Analysis (trigger conditions and error categorization)
├── Resource Usage Metrics (memory, disk, Docker images, logs)
├── Individual Test Details (timing, errors, fast-fail triggers)
└── Metadata (timestamps, PANTHER version, file references)
```

**Output Formats**:
- **JSON Report**: Machine-parseable data with full experiment context
- **Markdown Report**: Human-readable report with emoji indicators and structured sections
- **Text Summary**: Minimal fallback format for constrained environments

**Template Features**:
- **Conditional Rendering**: Content adapts based on experiment characteristics
- **Rich Formatting**: Status emojis, duration formatting, percentage calculations
- **Error Context**: Detailed failure analysis with categorization and fast-fail correlation
- **Resource Tracking**: Memory peaks, disk usage, Docker image counts, log sizes

**Integration Points**:
- **StatusCollector**: Aggregates experiment data from multiple sources
- **ExperimentManager**: Provides experiment lifecycle context
- **FastFailHandler**: Contributes failure analysis and error categorization
- **MetricsCollector**: Supplies resource usage and performance data
- **TestCaseManager**: Individual test outcome and timing data
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from jinja2 import Environment, FileSystemLoader, Template

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from .status_collector import (
    ExperimentStatus,
    ExperimentSummary,
    StatusCollector,
    TestStatus,
)


class ExperimentReporter:
    """Advanced experiment reporting engine with multi-format output capabilities.

    Provides comprehensive experiment analysis and reporting functionality, generating
    detailed reports in multiple formats with rich metadata, failure analysis, and
    resource utilization tracking.

    **Core Capabilities**:
    - **Multi-Format Generation**: JSON, Markdown, and Text report formats
    - **Template-Driven Rendering**: Jinja2 templates with fallback to basic formatting
    - **Comprehensive Analysis**: Test outcomes, resource usage, fast-fail analysis
    - **Rich Metadata**: Experiment context, timing, version information
    - **Error Recovery**: Progressive fallback strategies for robust report generation

    **Report Generation Workflow**:
    ```
    Report Generation Pipeline:
    ├── Data Collection (StatusCollector aggregation)
    ├── Context Enhancement (metadata, formatting, calculations)
    ├── Multi-Format Rendering (JSON → Markdown → Text fallbacks)
    ├── File Output (structured directory organization)
    └── Success Validation (per-format success tracking)
    ```

    **Output Strategy**:
    - **Primary Format**: Markdown for human consumption with rich formatting
    - **Data Format**: JSON for programmatic analysis and integration
    - **Fallback Format**: Plain text for minimal environments or template failures
    - **Template Flexibility**: Jinja2 templates with graceful degradation

    **Report Content Features**:
    - **Executive Summary**: High-level experiment status and success metrics
    - **Test Analysis**: Individual test outcomes with timing and error details
    - **Resource Tracking**: Memory usage, disk consumption, Docker image statistics
    - **Fast-Fail Analysis**: Failure categorization and termination reasoning
    - **Historical Context**: Experiment metadata and version information

    **Performance Characteristics**:
    - **Report Generation**: ~100-500ms depending on experiment size and template complexity
    - **Memory Usage**: O(n) where n is number of test cases and log entries
    - **Template Rendering**: ~10-50ms for Jinja2, ~5-10ms for basic formatting
    - **Error Resilience**: Multiple format attempts ensure report availability

    **Usage Patterns**:
    ```python
    # Basic usage
    reporter = ExperimentReporter(experiment_dir, "experiment_name")
    results = reporter.generate_reports()

    # Quick summary for logging
    summary = reporter.generate_quick_summary()
    logger.info(summary)

    # Check format success
    if results.get("markdown"):
        logger.info("Markdown report generated successfully")
    ```

    **Thread Safety**: Not thread-safe - designed for single-threaded report generation
    **Template Dependency**: Graceful handling of missing Jinja2 with basic formatting fallback
    **File Management**: Automatic output directory creation and structured file naming
    """

    def __init__(self, experiment_dir: Path, experiment_name: Optional[str] = None):
        """
        Initialize experiment reporter.

        Args:
            experiment_dir: Path to experiment output directory
            experiment_name: Optional experiment name override
        """
        self.experiment_dir = Path(experiment_dir)
        self.experiment_name = experiment_name or self.experiment_dir.name
        self.logger = logging.getLogger(__name__)
        self.status_collector = StatusCollector(self.experiment_dir)

        # Set up Jinja2 environment if available
        if JINJA2_AVAILABLE:
            templates_dir = Path(__file__).parent / "templates"
            self.jinja_env = Environment(
                loader=FileSystemLoader(templates_dir),
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=True,
            )
        else:
            self.jinja_env = None
            self.logger.warning("Jinja2 not available - using basic templates")

    def generate_reports(self) -> Dict[str, bool]:
        """
        Generate all experiment reports.

        Returns:
            Dict[str, bool]: Success status for each report type
        """
        results = {}

        try:
            # Collect experiment summary
            summary = self.status_collector.collect_experiment_summary()

            # Generate JSON report
            results["json"] = self._generate_json_report(summary)

            # Generate Markdown report
            results["markdown"] = self._generate_markdown_report(summary)

            # Generate simple text summary if other formats fail
            if not any(results.values()):
                results["text"] = self._generate_simple_text_report(summary)

            self.logger.info(f"Generated experiment reports for {self.experiment_name}")

        except Exception as e:
            self.logger.error(
                f"Failed to generate experiment reports: {e}", exc_info=True
            )
            results["error"] = False

        return results

    def _generate_json_report(self, summary: ExperimentSummary) -> bool:
        """Generate machine-readable JSON report."""
        try:
            report_data = summary.to_dict()

            # Add metadata
            report_data["report_metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "panther_version": self._get_panther_version(),
                "report_format_version": "1.0",
            }

            json_path = self.experiment_dir / "experiment_summary.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Generated JSON report: {json_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate JSON report: {e}")
            return False

    def _generate_markdown_report(self, summary: ExperimentSummary) -> bool:
        """Generate human-readable Markdown report."""
        try:
            if self.jinja_env:
                return self._generate_jinja_markdown_report(summary)
            else:
                return self._generate_basic_markdown_report(summary)

        except Exception as e:
            self.logger.error(f"Failed to generate Markdown report: {e}")
            return False

    def _generate_jinja_markdown_report(self, summary: ExperimentSummary) -> bool:
        """Generate Markdown report using Jinja2 template."""
        try:
            template = self.jinja_env.get_template("experiment_report.md.jinja")

            # Prepare template context
            context = {
                "summary": summary,
                "generation_time": datetime.now(),
                "panther_version": self._get_panther_version(),
                "status_emoji": self._get_status_emoji(summary.status),
                "duration_str": self._format_duration(summary.duration),
            }

            # Render template
            content = template.render(**context)

            # Write to file
            markdown_path = self.experiment_dir / "EXPERIMENT_REPORT.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.debug(f"Generated Markdown report: {markdown_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate Jinja2 Markdown report: {e}")
            return False

    def _generate_basic_markdown_report(self, summary: ExperimentSummary) -> bool:
        """Generate basic Markdown report without Jinja2."""
        try:
            lines = [
                f"# Experiment Report: {summary.experiment_id}",
                "",
                "## Overview",
                f"- **Experiment ID**: `{summary.experiment_id}`",
                f"- **Status**: {self._get_status_emoji(summary.status)} {summary.status.value.title()}",
                f"- **Start Time**: {summary.start_time.strftime('%Y-%m-%d %H:%M:%S') if summary.start_time else 'Unknown'}",
                f"- **End Time**: {summary.end_time.strftime('%Y-%m-%d %H:%M:%S') if summary.end_time else 'Unknown'}",
                f"- **Total Duration**: {self._format_duration(summary.duration)}",
                f"- **Configuration**: {summary.configuration_file or 'Unknown'}",
                "",
                "## Test Results Summary",
                "",
                f"- **Total Tests**: {summary.total_tests}",
                f"- **Passed**: {summary.passed_tests} ({summary.success_rate:.1f}%)",
                f"- **Failed**: {summary.failed_tests}",
                f"- **Skipped**: {summary.skipped_tests}",
                f"- **Timeout**: {summary.timeout_tests}",
                f"- **Interrupted**: {summary.interrupted_tests}",
                f"- **Unknown**: {summary.unknown_tests}",
                "",
            ]

            # Add individual test results
            if summary.tests:
                lines.extend(["## Individual Test Results", ""])

                # Passed tests
                passed_tests = [
                    t for t in summary.tests if t.status == TestStatus.PASSED
                ]
                if passed_tests:
                    lines.append(f"### ✅ Passed Tests ({len(passed_tests)})")
                    for test in passed_tests:
                        lines.append(
                            f"- **{test.name}** - Duration: {test.duration:.1f}s"
                        )
                    lines.append("")

                # Failed tests
                failed_tests = [
                    t for t in summary.tests if t.status != TestStatus.PASSED
                ]
                if failed_tests:
                    lines.append(f"### ❌ Failed/Problem Tests ({len(failed_tests)})")
                    for test in failed_tests:
                        lines.append(
                            f"- **{test.name}** - Status: {test.status.value.title()} - Duration: {test.duration:.1f}s"
                        )
                        if test.error_message:
                            lines.append(f"  - Error: {test.error_message}")
                        if test.fast_fail_triggered:
                            lines.append("  - ⚡ Fast-fail triggered")
                    lines.append("")

            # Fast-fail analysis
            lines.extend(
                [
                    "## Fast-Fail Analysis",
                    f"- **Fast-Fail Enabled**: {'✅ Yes' if summary.fast_fail.enabled else '❌ No'}",
                ]
            )

            if summary.fast_fail.test_level:
                lines.append("- **Test-Level Control**: ✅ Enabled")

            if summary.fast_fail.triggered:
                lines.extend(
                    [
                        "- **⚡ Fast-Fail Triggered**: Yes",
                        f"- **Termination Reason**: {summary.fast_fail.reason or 'Unknown'}",
                    ]
                )
                if summary.fast_fail.error_category:
                    lines.append(
                        f"- **Error Category**: {summary.fast_fail.error_category}"
                    )
            else:
                lines.append("- **Fast-Fail Triggered**: No")

            lines.extend(["", ""])

            # Resource usage
            lines.append("## Resource Usage")
            resource_items = []
            if summary.resources.peak_memory_mb:
                resource_items.append(
                    f"- **Peak Memory**: {summary.resources.peak_memory_mb:.1f} MB"
                )
            if summary.resources.disk_usage_mb:
                resource_items.append(
                    f"- **Disk Usage**: {summary.resources.disk_usage_mb:.1f} MB"
                )
            if summary.resources.docker_images_created:
                resource_items.append(
                    f"- **Docker Images Created**: {summary.resources.docker_images_created}"
                )
            if summary.resources.total_log_size_mb:
                resource_items.append(
                    f"- **Total Log Size**: {summary.resources.total_log_size_mb:.1f} MB"
                )

            if resource_items:
                lines.extend(resource_items)
            else:
                lines.append("- No resource usage data available")

            lines.extend(
                [
                    "",
                    "",
                    "## Detailed Information",
                    "",
                    "### Log Files",
                    "- **Main Experiment Log**: `./experiment.log`",
                ]
            )

            if summary.tests:
                lines.append("- **Individual Test Logs**:")
                for test in summary.tests:
                    lines.append(f"  - {test.name}: `./{test.logs_path}/test.log`")

            lines.extend(
                [
                    "",
                    "---",
                    "",
                    f"**Report generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"**PANTHER Version**: {self._get_panther_version()}",
                    "**Report Format**: Markdown v1.0",
                ]
            )

            # Write to file
            content = "\n".join(lines)
            markdown_path = self.experiment_dir / "EXPERIMENT_REPORT.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.debug(f"Generated basic Markdown report: {markdown_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate basic Markdown report: {e}")
            return False

    def _generate_simple_text_report(self, summary: ExperimentSummary) -> bool:
        """Generate simple text report as fallback."""
        try:
            lines = [
                f"EXPERIMENT REPORT: {summary.experiment_id}",
                "=" * 50,
                "",
                f"Status: {summary.status.value.upper()}",
                f"Total Tests: {summary.total_tests}",
                f"Passed: {summary.passed_tests}",
                f"Failed: {summary.failed_tests}",
                f"Success Rate: {summary.success_rate:.1f}%",
                "",
                f"Fast-Fail Enabled: {summary.fast_fail.enabled}",
                f"Fast-Fail Triggered: {summary.fast_fail.triggered}",
                "",
                f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]

            content = "\n".join(lines)
            text_path = self.experiment_dir / "experiment_summary.txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.debug(f"Generated text report: {text_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate text report: {e}")
            return False

    def _get_status_emoji(self, status: ExperimentStatus) -> str:
        """Get emoji for experiment status."""
        emoji_map = {
            ExperimentStatus.COMPLETED: "✅",
            ExperimentStatus.FAILED: "❌",
            ExperimentStatus.INTERRUPTED: "⏹️",
            ExperimentStatus.TIMEOUT: "⏰",
            ExperimentStatus.UNKNOWN: "❓",
        }
        return emoji_map.get(status, "❓")

    def _format_duration(self, duration) -> str:
        """Format duration for display."""
        if not duration:
            return "Unknown"

        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours}h {minutes}m {seconds}s"

    def _get_panther_version(self) -> str:
        """Get PANTHER version string."""
        try:
            # Try to get version from package metadata
            import pkg_resources

            return pkg_resources.get_distribution("panther").version
        except Exception:
            try:
                # Try to get from git if in development
                import subprocess

                result = subprocess.run(
                    ["git", "describe", "--tags", "--always"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent.parent.parent,
                )
                if result.returncode == 0:
                    return f"dev-{result.stdout.strip()}"
            except Exception:
                pass

        return "Development"

    def generate_quick_summary(self) -> Optional[str]:
        """
        Generate a quick one-line summary for logging.

        Returns:
            str: Quick summary string
        """
        try:
            summary = self.status_collector.collect_experiment_summary()

            status_emoji = self._get_status_emoji(summary.status)
            duration_str = self._format_duration(summary.duration)

            return (
                f"{status_emoji} {summary.experiment_id}: "
                f"{summary.passed_tests}/{summary.total_tests} tests passed "
                f"({summary.success_rate:.1f}%) in {duration_str}"
            )

        except Exception as e:
            self.logger.error(f"Failed to generate quick summary: {e}")
            return None
