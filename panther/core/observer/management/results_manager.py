from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union

"""
Results manager for handling test results in the event system.

This module provides a comprehensive solution for collecting, aggregating,
and exporting test results from the event system.
"""

import csv
import datetime
import json
import logging
import os
import threading
from collections.abc import Callable
from datetime import datetime

from panther.core.events.base.event_base import BaseEvent as Event
from panther.core.events.test.events import EnhancedResultEvent, TestResultEvent
from panther.core.observer.base.observer_interface import IObserver

# Type variable for generic result data
T = TypeVar("T")


class ResultAggregator:
    """

    Aggregates test results from multiple test runs.

    This class provides functionality for collecting, tracking, and
    aggregating test results across multiple test runs or sessions.
    """

    def __init__(self):
        """Initialize a new ResultAggregator."""
        self.results: List[Dict[str, Any]] = []
        self.result_by_test: Dict[str, List[Dict[str, Any]]] = {}
        self.result_by_category: Dict[str, List[Dict[str, Any]]] = {}
        self.success_count = 0
        self.failure_count = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.tags: Dict[str, Set[str]] = {}  # Maps test names to their tags
        self.tag_stats: Dict[
            str, Dict[str, int]
        ] = {}  # Statistics by tag: {tag: {"success": 0, "failure": 0}}
        self.category_stats: Dict[str, Dict[str, int]] = {}  # Statistics by category
        self.lock = threading.RLock()

    def _ensure_iso_format(self, timestamp_str: str) -> str:
        """
        Ensures a timestamp string is in ISO format.

        Args:
            timestamp_str: The timestamp string to check/convert

        Returns:
            str: ISO formatted timestamp string
        """
        try:
            if not timestamp_str:
                return datetime.now().isoformat()

            # Try parsing as ISO format
            datetime.fromisoformat(timestamp_str)
            return timestamp_str
        except (ValueError, TypeError):
            # If not ISO format, try to parse with different formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"]:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue

            # If all parsing fails, return current time
            return datetime.now().isoformat()

    def _extract_result_data(
        self, result: Union[TestResultEvent, EnhancedResultEvent, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract standardized result data from various result sources.

        Args:
            result: The result source (event or dictionary)

        Returns:
            Dict[str, Any]: Standardized result data
        """
        if isinstance(result, EnhancedResultEvent):
            # Handle EnhancedResultEvent
            result_data = {
                "test_name": result.test_name,
                "result": result.result,
                "timestamp": result.data.get("timestamp", datetime.now().isoformat()),
                "data": result.data,
                "metadata": result.metadata,
                "category": result.category,
                "tags": result.tags,
                "result_data": result.get_result_data(),
            }
        elif isinstance(result, TestResultEvent):
            # Handle TestResultEvent
            result_data = {
                "test_name": result.test_name,
                "result": result.result,
                "timestamp": result.data.get("timestamp", datetime.now().isoformat()),
                "data": result.data,
                "metadata": result.metadata,
                "category": result.metadata.get("category", "default"),
                "tags": result.metadata.get("tags", []),
            }
        else:
            # Handle dictionary
            result_data = result.copy() if result else {}

            # Ensure standard fields exist
            if "test_name" not in result_data:
                result_data["test_name"] = "unknown_test"
            if "timestamp" not in result_data:
                result_data["timestamp"] = datetime.now().isoformat()
            if "category" not in result_data:
                result_data["category"] = "default"
            if "tags" not in result_data:
                result_data["tags"] = []
            if "metadata" not in result_data:
                result_data["metadata"] = {}
            if "data" not in result_data and "result_data" in result_data:
                result_data["data"] = {"result_data": result_data["result_data"]}
            elif "data" not in result_data:
                result_data["data"] = {}

        # Ensure timestamp is in ISO format
        result_data["timestamp"] = self._ensure_iso_format(result_data["timestamp"])

        return result_data

    def add_result(
        self, result: Union[TestResultEvent, EnhancedResultEvent, Dict[str, Any]]
    ):
        """
        Add a test result to the aggregator.

        Args:
            result: Test result event or result data dictionary
        """
        with self.lock:
            # Extract standardized data
            result_data = self._extract_result_data(result)

            # Update success/failure counts
            if result_data.get("result", False):
                self.success_count += 1
            else:
                self.failure_count += 1

            # Add to results list
            self.results.append(result_data)

            # Group by test name
            test_name = result_data.get("test_name", "unknown")
            if test_name not in self.result_by_test:
                self.result_by_test[test_name] = []
            self.result_by_test[test_name].append(result_data)

            # Group by category
            category = result_data.get("category", "default")
            if category not in self.result_by_category:
                self.result_by_category[category] = []
                self.category_stats[category] = {"success": 0, "failure": 0}

            self.result_by_category[category].append(result_data)

            # Update category stats
            if result_data.get("result", False):
                self.category_stats[category]["success"] += 1
            else:
                self.category_stats[category]["failure"] += 1

            # Update tags
            test_tags = result_data.get("tags", [])
            if test_name not in self.tags:
                self.tags[test_name] = set()

            # Add tags and update tag stats
            for tag in test_tags:
                self.tags[test_name].add(tag)

                if tag not in self.tag_stats:
                    self.tag_stats[tag] = {"success": 0, "failure": 0}

                if result_data.get("result", False):
                    self.tag_stats[tag]["success"] += 1
                else:
                    self.tag_stats[tag]["failure"] += 1

            # Update timing
            try:
                timestamp = datetime.fromisoformat(result_data["timestamp"])
                if self.start_time is None or timestamp < self.start_time:
                    self.start_time = timestamp
                if self.end_time is None or timestamp > self.end_time:
                    self.end_time = timestamp
            except (ValueError, TypeError):
                # If timestamp parsing fails, use current time
                now = datetime.now()
                if self.start_time is None:
                    self.start_time = now
                self.end_time = now

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all test results.

        Returns:
            Dict[str, Any]: Result summary
        """
        total = self.success_count + self.failure_count

        return {
            "total_tests": total,
            "successful": self.success_count,
            "failed": self.failure_count,
            "success_rate": self.success_count / total if total > 0 else 0,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time
                else None
            ),
            "tests": list(self.result_by_test.keys()),
        }

    def get_results_by_test(self, test_name: str) -> List[Dict[str, Any]]:
        """
        Get all results for a specific test.

        Args:
            test_name: Name of the test

        Returns:
            List[Dict[str, Any]]: All results for the specified test
        """
        return self.result_by_test.get(test_name, [])

    def get_all_results(self) -> List[Dict[str, Any]]:
        """
        Get all collected test results.

        Returns:
            List[Dict[str, Any]]: All test results
        """
        return self.results

    def clear(self):
        """Clear all collected results."""
        self.results = []
        self.result_by_test = {}
        self.success_count = 0
        self.failure_count = 0
        self.start_time = None
        self.end_time = None


class ResultsExporter:
    """
    Exports test results in various formats.

    This class provides functionality for exporting test results
    to different file formats for reporting and analysis.
    """

    SUPPORTED_FORMATS = ["json", "csv", "html", "md"]

    def __init__(self, results_aggregator: ResultAggregator):
        """
        Initialize a new ResultsExporter.

        Args:
            results_aggregator: The aggregator with results to export
        """
        self.aggregator = results_aggregator
        self.logger = logging.getLogger("ResultsExporter")

    def export_to_json(self, output_path: str, pretty: bool = True) -> bool:
        """
        Export results to JSON format.

        Args:
            output_path: Path to write the JSON file
            pretty: Whether to format the JSON for readability

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            data = {
                "summary": self.aggregator.get_summary(),
                "results": self.aggregator.get_all_results(),
            }

            with open(output_path, "w", encoding="utf-8") as f:
                if pretty:
                    json.dump(data, f, indent=2)
                else:
                    json.dump(data, f)

            self.logger.info("Exported test results to JSON: %s", output_path)
            return True
        except (OSError, ValueError, TypeError) as e:
            self.logger.error("Error exporting results to JSON: %s", e)
            return False

    def export_to_csv(self, output_path: str) -> bool:
        """
        Export results to CSV format.

        Args:
            output_path: Path to write the CSV file

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            results = self.aggregator.get_all_results()
            if not results:
                self.logger.warning("No results to export to CSV")
                return False

            # Collect all possible fields
            fieldnames = {"test_name", "result", "timestamp"}
            for result in results:
                fieldnames.update(result.get("data", {}).keys())

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                writer.writeheader()

                for result in results:
                    # Flatten the result structure for CSV
                    row = {
                        "test_name": result.get("test_name", ""),
                        "result": str(result.get("result", "")),
                        "timestamp": result.get("timestamp", ""),
                    }

                    # Add data fields
                    for key, value in result.get("data", {}).items():
                        row[key] = str(value) if value is not None else ""

                    writer.writerow(row)

            self.logger.info("Exported test results to CSV: %s", output_path)
            return True
        except (OSError, ValueError, TypeError) as e:
            self.logger.error("Error exporting results to CSV: %s", e)
            return False

    def export_to_html(self, output_path: str) -> bool:
        """
        Export results to HTML format.
        # TODO: use jinja

        Args:
            output_path: Path to write the HTML file

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            summary = self.aggregator.get_summary()
            results = self.aggregator.get_all_results()

            html = [
                "<!DOCTYPE html>",
                "<html>",
                "<head>",
                "  <title>Test Results</title>",
                "  <style>",
                "    body { font-family: Arial, sans-serif; margin: 20px; }",
                "    table { border-collapse: collapse; width: 100%; }",
                "    th, td { text-align: left; padding: 8px; }",
                "    tr:nth-child(even) { background-color: #f2f2f2; }",
                "    th { background-color: #4CAF50; color: white; }",
                "    .success { color: green; }",
                "    .failure { color: red; }",
                "    .summary { margin-bottom: 20px; }",
                "  </style>",
                "</head>",
                "<body>",
                "  <h1>Test Results Summary</h1>",
                '  <div class="summary">',
                f"    <p>Total Tests: {summary['total_tests']}</p>",
                f"    <p>Successful: <span class=\"success\">{summary['successful']}</span></p>",
                f"    <p>Failed: <span class=\"failure\">{summary['failed']}</span></p>",
                f"    <p>Success Rate: {summary['success_rate'] * 100:.2f}%</p>",
                f"    <p>Start Time: {summary['start_time']}</p>",
                f"    <p>End Time: {summary['end_time']}</p>",
                f"    <p>Duration: {summary['duration']} seconds</p>",
                "  </div>",
                "  <h2>Test Results</h2>",
                "  <table>",
                "    <tr>",
                "      <th>Test Name</th>",
                "      <th>Result</th>",
                "      <th>Timestamp</th>",
                "    </tr>",
            ]

            for result in results:
                result_class = "success" if result.get("result", False) else "failure"
                result_text = "Pass" if result.get("result", False) else "Fail"

                html.append("    <tr>")
                html.append(f"      <td>{result.get('test_name', '')}</td>")
                html.append(f'      <td class="{result_class}">{result_text}</td>')
                html.append(f"      <td>{result.get('timestamp', '')}</td>")
                html.append("    </tr>")

            html.extend(["  </table>", "</body>", "</html>"])

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(html))

            self.logger.info("Exported test results to HTML: %s", output_path)
            return True
        except (OSError, ValueError, TypeError) as e:
            self.logger.error("Error exporting results to HTML: %s", e)
            return False

    def export_to_markdown(self, output_path: str) -> bool:
        """
        Export results to Markdown format.

        Args:
            output_path: Path to write the Markdown file

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            summary = self.aggregator.get_summary()
            results = self.aggregator.get_all_results()

            md = [
                "# Test Results Summary\n",
                f"- Total Tests: {summary['total_tests']}",
                f"- Successful: {summary['successful']}",
                f"- Failed: {summary['failed']}",
                f"- Success Rate: {summary['success_rate'] * 100:.2f}%",
                f"- Start Time: {summary['start_time']}",
                f"- End Time: {summary['end_time']}",
                f"- Duration: {summary['duration']} seconds\n",
                "## Test Results\n",
                "| Union[Test Name, Result, Timestamp]|",
                "| --------- | ------ | --------- |",
            ]

            for result in results:
                result_text = "✅ Pass" if result.get("result", False) else "❌ Fail"
                md.append(
                    f"| {result.get('test_name', '')} | {result_text} | {result.get('timestamp', '')} |"
                )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md))

            self.logger.info("Exported test results to Markdown: %s", output_path)
            return True
        except Exception as e:
            self.logger.error("Error exporting results to Markdown: %s", e)
            return False

    def export(self, format_type: str, output_path: str) -> bool:
        """
        Export results to the specified format.

        Args:
            format_type: Format to export to ('json', 'csv', 'html', 'md')
            output_path: Path to write the output file

        Returns:
            bool: True if export successful, False otherwise

        Raises:
            ValueError: If format_type is not supported
        """
        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported export format: {format_type}")

        if format_type == "json":
            return self.export_to_json(output_path)
        elif format_type == "csv":
            return self.export_to_csv(output_path)
        elif format_type == "html":
            return self.export_to_html(output_path)
        elif format_type == "md":
            return self.export_to_markdown(output_path)

        return False


class ResultsManager(IObserver):
    """
    Comprehensive manager for test results.

    This class combines result collection, aggregation, and export capabilities
    to provide a complete solution for managing test results in the event system.
    It supports both legacy TestResultEvents and EnhancedResultEvents with more
    advanced features like result categorization and tag-based filtering.
    """

    def __init__(self, output_dir: str = None):
        """
        Initialize a new ResultsManager.

        Args:
            output_dir: Directory for result exports (or None to use CWD)
        """
        self.logger = logging.getLogger("ResultsManager")
        self.output_dir = output_dir or os.getcwd()
        self.aggregator = ResultAggregator()
        self.exporter = ResultsExporter(self.aggregator)

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Set of event types to process
        self.result_event_types = {
            "test.result",
            "test.case.result",
            "test.suite.result",
            "enhanced.result",
        }

        # Registered callbacks for result events
        self.callbacks: Dict[str, List[Callable]] = {}

    def on_event(self, event: Event):
        """
        Handle an event, specifically looking for test result events.

        Supports both legacy TestResultEvent and enhanced EnhancedResultEvent
        types, as well as converting generic events to result events.

        Args:
            event: The event to handle
        """
        event_type = event.get_type()

        # Check if this is a result event
        if isinstance(event, (TestResultEvent, EnhancedResultEvent)):
            self.aggregator.add_result(event)
            if isinstance(event, EnhancedResultEvent):
                self.logger.debug(
                    "Collected enhanced test result for test: %s with %d tags in category %s",
                    event.test_name,
                    len(event.tags),
                    event.category,
                )
            else:
                self.logger.debug("Collected test result for test: %s", event.test_name)

            # Trigger callbacks
            self._trigger_callbacks(event_type, event)

        elif (
            event_type in self.result_event_types
            or event_type.startswith("test.result.")
            or event_type.startswith("enhanced.result.")
        ):
            # Try to convert generic event to result event
            try:
                data = event.data or {}
                test_name = data.get("test_name", "unknown")
                result = data.get("result", False)

                if event_type.startswith("enhanced.result."):
                    # Create an enhanced result event
                    category = data.get("category", "default")
                    tags = data.get("tags", [])
                    result_data = data.get("result_data")
                    metadata = data.get("metadata", {})

                    result_event = EnhancedResultEvent(
                        name=event_type.replace("enhanced.result.", ""),
                        test_name=test_name,
                        result=result,
                        result_data=result_data,
                        metadata=metadata,
                        tags=tags,
                        category=category,
                    )
                else:
                    # Create a standard test result event
                    result_event = TestResultEvent(
                        name=event_type.replace("test.result.", ""),
                        test_name=test_name,
                        result=result,
                        data=data,
                    )

                self.aggregator.add_result(result_event)
                self.logger.debug(
                    "Converted and collected result for test: %s", test_name
                )

                # Trigger callbacks
                self._trigger_callbacks(event_type, result_event)

            except (ValueError, KeyError, AttributeError) as e:
                self.logger.error("Error processing result event: %s", e)

    def is_interested(self, event_type: str) -> bool:
        """
        Check if this observer is interested in an event type.

        Args:
            event_type: Type of event to check interest for

        Returns:
            bool: True if the observer is interested in events of this type
        """
        return (
            event_type in self.result_event_types
            or event_type.startswith("test.result.")
            or event_type.startswith("enhanced.result.")
        )

    def get_priority(self) -> int:
        """
        Get the priority for this observer.

        Returns:
            int: Observer priority (default: 10 for early result processing)
        """
        return 10

    def register_callback(self, event_type: str, callback: Union[Callable, None]):
        """
        Register a callback for a specific result event type.

        Args:
            event_type: Event type to register for
            callback: Callback function that takes a TestResultEvent or EnhancedResultEvent
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []

        self.callbacks[event_type].append(callback)

    def _trigger_callbacks(
        self, event_type: str, event: Union[TestResultEvent, EnhancedResultEvent]
    ):
        """
        Trigger registered callbacks for an event type.

        Args:
            event_type: Type of event that occurred
            event: The event that occurred
        """
        # Call exact match callbacks
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                self.logger.error("Error in result callback: %s", e)

        # Call wildcard callbacks
        for callback in self.callbacks.get("*", []):
            try:
                callback(event)
            except Exception as e:
                self.logger.error("Error in wildcard result callback: %s", e)

    def export_results(self, format_type: str, filename: str = None) -> str:
        """
        Export collected results to a file.

        Args:
            format_type: Format to export to ('json', 'csv', 'html', 'md')
            filename: Filename to use (or None for auto-generated name)

        Returns:
            str: Path to the exported file, or empty string on failure
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.{format_type}"

        output_path = os.path.join(self.output_dir, filename)

        if self.exporter.export(format_type, output_path):
            return output_path
        return ""

    def export_all_formats(self, basename: str = None) -> Dict[str, str]:
        """
        Export results to all supported formats.

        Args:
            basename: Base filename to use (or None for auto-generated name)

        Returns:
            Dict[str, str]: Map of format types to exported file paths
        """
        if basename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            basename = f"test_results_{timestamp}"

        results = {}

        for fmt in self.exporter.SUPPORTED_FORMATS:
            filename = f"{basename}.{fmt}"
            path = self.export_results(fmt, filename)
            if path:
                results[fmt] = path

        return results

    def clear_results(self):
        """Clear all collected results."""
        self.aggregator.clear()

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all test results.

        Returns:
            Dict[str, Any]: Result summary
        """
        return self.aggregator.get_summary()

    def get_all_results(self) -> List[Dict[str, Any]]:
        """
        Get all collected test results.

        Returns:
            List[Dict[str, Any]]: All test results
        """
        return self.aggregator.get_all_results()

    def get_results_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all results for a specific category.

        Args:
            category: Category to filter results by

        Returns:
            List[Dict[str, Any]]: Results filtered by category
        """
        return self.aggregator.result_by_category.get(category, [])

    def get_results_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get all results that contain a specific tag.

        Args:
            tag: Tag to filter results by

        Returns:
            List[Dict[str, Any]]: Results that contain the specified tag
        """
        results = []
        for test_results in self.aggregator.results:
            if tag in test_results.get("tags", []):
                results.append(test_results)
        return results

    def get_category_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics by category.

        Returns:
            Dict[str, Dict[str, int]]: Map of categories to their success/failure counts
        """
        return self.aggregator.category_stats

    def get_tag_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics by tag.

        Returns:
            Dict[str, Dict[str, int]]: Map of tags to their success/failure counts
        """
        return self.aggregator.tag_stats
