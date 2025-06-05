"""
Tests for the modernized event system's YAML configuration and metrics integration.

This module contains tests for the new observer configuration system
and metrics integration features.
"""

import os
import unittest
import tempfile
import shutil

from panther.core.observer.event_manager import EventManager
from panther.core.observer.observer_config import ObserverRegistry
from panther.core.observer.events import ResourceMetricEvent, TimingMetricEvent, CounterMetricEvent
from panther.core.observer.metrics.metrics_observer import MetricsObserver
from panther.core.metrics.metrics_collector import MetricsCollector


class TestObserverConfig(unittest.TestCase):
    """Test cases for the YAML-based observer configuration system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.event_manager = EventManager()
        self.registry = ObserverRegistry(self.event_manager)

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_load_config_dict(self):
        """Test loading configuration from a dictionary."""
        config = {
            "observers": [
                {
                    "id": "test_observer",
                    "class_path": "panther.core.observer.logger_observer.LoggerObserver",
                    "enabled": True,
                    "priority": 10,
                    "params": {"log_level": "DEBUG"},
                }
            ]
        }

        success = self.registry.load_config_dict(config)
        self.assertTrue(success)
        self.assertEqual(len(self.registry.configs), 1)

        observer_config = self.registry.configs["test_observer"]
        self.assertEqual(
            observer_config.class_path, "panther.core.observer.logger_observer.LoggerObserver"
        )
        self.assertEqual(observer_config.priority, 10)
        self.assertEqual(observer_config.params["log_level"], "DEBUG")

    def test_load_config_file(self):
        """Test loading configuration from a YAML file."""
        config_path = os.path.join(self.temp_dir, "test_config.yaml")
        with open(config_path, "w") as f:
            f.write(
                """
observers:
  - id: test_observer
    class_path: panther.core.observer.logger_observer.LoggerObserver
    enabled: true
    priority: 20
    params:
      log_level: INFO
      include_data: true
"""
            )

        success = self.registry.load_config_file(config_path)
        self.assertTrue(success)
        self.assertEqual(len(self.registry.configs), 1)

        observer_config = self.registry.configs["test_observer"]
        self.assertEqual(observer_config.priority, 20)
        self.assertEqual(observer_config.params["log_level"], "INFO")
        self.assertTrue(observer_config.params["include_data"])

    def test_load_invalid_config(self):
        """Test loading an invalid configuration."""
        # Missing observers key
        config = {"not_observers": []}
        success = self.registry.load_config_dict(config)
        self.assertFalse(success)

        # Missing class_path
        config = {"observers": [{"id": "bad_observer", "enabled": True}]}
        success = self.registry.load_config_dict(config)
        self.assertFalse(success)

    def test_load_config_directory(self):
        """Test loading configurations from a directory."""
        # Create multiple config files
        os.makedirs(os.path.join(self.temp_dir, "config"))

        with open(os.path.join(self.temp_dir, "config", "observers1.yaml"), "w") as f:
            f.write(
                """
observers:
  - id: observer1
    class_path: panther.core.observer.logger_observer.LoggerObserver
"""
            )

        with open(os.path.join(self.temp_dir, "config", "observers2.yaml"), "w") as f:
            f.write(
                """
observers:
  - id: observer2
    class_path: panther.core.observer.result_observer.ResultObserver
"""
            )

        count = self.registry.load_config_directory(os.path.join(self.temp_dir, "config"))
        self.assertEqual(count, 2)
        self.assertEqual(len(self.registry.configs), 2)
        self.assertIn("observer1", self.registry.configs)
        self.assertIn("observer2", self.registry.configs)


class MockMetricsCollector(MetricsCollector):
    """Mock metrics collector for testing."""

    def __init__(self):
        super().__init__()
        self.recorded_metrics = []

    def record_metric(self, name, metric_type, value, **kwargs):
        """Record a metric."""
        self.recorded_metrics.append({"name": name, "type": metric_type, "value": value, **kwargs})


class TestMetricsIntegration(unittest.TestCase):
    """Test cases for metrics integration with the event system."""

    def setUp(self):
        """Set up test environment."""
        self.metrics_collector = MockMetricsCollector()
        self.event_manager = EventManager()
        self.metrics_observer = MetricsObserver(
            metrics_collector=self.metrics_collector,
            publish_metrics_as_events=True,
            record_events_as_metrics=True,
        )
        self.event_manager.register_observer(self.metrics_observer)

    def test_metrics_event_to_metric(self):
        """Test conversion from metrics events to metrics."""
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
        timing_event = TimingMetricEvent(
            operation="function_call", duration=1.25, component="test_module"
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
