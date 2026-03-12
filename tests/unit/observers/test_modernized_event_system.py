"""Tests for the modernized event system's YAML configuration and metrics integration.

This module contains tests for the new observer configuration system
and metrics integration features.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.observer.factory import ObserverFactory
from panther.core.observer.impl.metrics_observer import MetricsObserver
from panther.core.observer.management.event_manager import EventManager


class TestObserverConfig(unittest.TestCase):
    """Test cases for the YAML-based observer configuration system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.event_manager = EventManager()
        self.factory = ObserverFactory()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_create_logger_observer(self):
        """Test creating a logger observer through factory."""
        config = {
            "logger": {
                "enabled": True,
                "log_level": "DEBUG",
                "correlation_tracking": True,
            }
        }

        observer = self.factory.create_observer(
            "logger", self.event_manager, config["logger"]
        )
        self.assertIsNotNone(observer)
        self.assertEqual(observer.__class__.__name__, "LoggerObserver")

    def test_create_metrics_observer(self):
        """Test creating a metrics observer through factory."""
        config = {
            "metrics": {
                "enabled": True,
                "collect_system_metrics": True,
                "publish_interval": 30,
            }
        }

        observer = self.factory.create_observer(
            "metrics", self.event_manager, config["metrics"]
        )
        self.assertIsNotNone(observer)
        self.assertEqual(observer.__class__.__name__, "MetricsObserver")

    def test_invalid_observer_type(self):
        """Test creating an observer with invalid type."""
        config = {"unknown": {"enabled": True}}

        # Should raise ValueError for invalid observer type
        with self.assertRaises(ValueError) as context:
            self.factory.create_observer(
                "unknown_type", self.event_manager, config["unknown"]
            )
        self.assertIn("Unknown observer type", str(context.exception))


class MockMetricsCollector(MetricsCollector):
    """Mock metrics collector for testing."""

    def __init__(self):
        self.recorded_metrics = []
        super().__init__("test_experiment", Path("/tmp/test_metrics"))

    def record_metric(self, name, metric_type, value, **kwargs):
        """Record a metric."""
        self.recorded_metrics.append(
            {"name": name, "type": metric_type, "value": value, **kwargs}
        )


class TestMetricsIntegration(unittest.TestCase):
    """Test cases for metrics integration with the event system."""

    def setUp(self):
        """Set up test environment."""
        self.metrics_collector = MockMetricsCollector()
        self.event_manager = EventManager()
        self.metrics_observer = MetricsObserver(
            metrics_collector=self.metrics_collector,
            publish_metrics=True,
            collect_system_metrics=True,
        )
        self.event_manager.register_observer(self.metrics_observer)

    def test_metrics_event_to_metric(self):
        """Test conversion from metrics events to metrics."""
        # Import the correct ResourceMetricEvent
        from panther.core.events.metrics.events import ResourceMetricEvent

        # Create and notify a resource metric event
        resource_event = ResourceMetricEvent(
            resource_type="memory", usage_value=512.0, component="test_component"
        )
        self.event_manager.notify(resource_event)

        # Check that the metric was recorded
        self.assertGreaterEqual(len(self.metrics_collector.recorded_metrics), 1)

        # Find the resource metric
        resource_metric = None
        for metric in self.metrics_collector.recorded_metrics:
            if metric["name"] == "resource.memory":
                resource_metric = metric
                break

        self.assertIsNotNone(resource_metric)
        self.assertEqual(resource_metric["value"], 512.0)
        self.assertEqual(resource_metric["component"], "test_component")

    def test_timing_metric_event(self):
        """Test handling timing metric events."""
        from panther.core.events.metrics.events import TimingMetricEvent

        timing_event = TimingMetricEvent(
            operation_name="function_call", duration=1.25, component="test_module"
        )
        self.event_manager.notify(timing_event)

        # Check that the metric was recorded
        timing_metric = None
        for metric in self.metrics_collector.recorded_metrics:
            if metric["name"] == "timing.function_call":
                timing_metric = metric
                break

        self.assertIsNotNone(timing_metric)
        self.assertEqual(timing_metric["value"], 1.25)
        self.assertEqual(timing_metric["component"], "test_module")

    def test_counter_metric_event(self):
        """Test handling counter metric events."""
        from panther.core.events.metrics.events import CounterMetricEvent

        counter_event = CounterMetricEvent(
            counter_name="api_calls", value=5, increment=True, component="api_client"
        )
        self.event_manager.notify(counter_event)

        # Since we're using a mock, we don't have the actual counter value,
        # but we can check that a metric was recorded with the right name
        counter_metric = None
        for metric in self.metrics_collector.recorded_metrics:
            if "name" in metric and metric["name"] == "api_calls":
                counter_metric = metric
                break

        self.assertIsNotNone(counter_metric)
        self.assertEqual(counter_metric["value"], 5)
        self.assertEqual(counter_metric["component"], "api_client")


if __name__ == "__main__":
    unittest.main()
