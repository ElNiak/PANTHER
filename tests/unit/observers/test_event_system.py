"""
Unit tests for the enhanced event system.

This module contains tests for the core components of the
enhanced event system including plugins, async processing,
and result handling.
"""

import os
import unittest
import time
import tempfile
import shutil
from threading import Event as ThreadingEvent

from panther.core.events.base.event_emitter import Event
from panther.core.events.test.events import TestEvent, TestResultEvent
from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.management.results_manager import ResultsManager
from panther.core.observer.plugins.plugin_interface import IPluginObserver
from panther.core.observer.base.observer_interface import IObserver
from panther.core.observer.plugins.plugin_registry import PluginRegistry


class TestObserver(IObserver):
    """Test observer for event system testing."""

    def __init__(self):
        self.events = []
        self.event_received = ThreadingEvent()
        self.interested_types = None
        self.priority = 0

    def on_event(self, event: Event):
        """Record the event."""
        self.events.append(event)
        self.event_received.set()
        return True

    def is_interested(self, event_type: str) -> bool:
        """Check interest in an event type."""
        if self.interested_types is None:
            return True
        return event_type in self.interested_types or any(
            event_type.startswith(t) for t in self.interested_types
        )

    def get_priority(self) -> int:
        """Get observer priority."""
        return self.priority

    def clear(self):
        """Clear recorded events."""
        self.events = []
        self.event_received.clear()


class TestPlugin(IPluginObserver):
    """Test plugin for plugin system testing."""

    VERSION = "0.1.0"
    AUTHOR = "Test"
    EVENTS = ["test.plugin"]

    def __init__(self):
        self.events = []
        self.initialized = False

    def on_event(self, event: Event):
        """Record the event."""
        self.events.append(event)
        return True

    def initialize(self):
        """Initialize the plugin."""
        self.initialized = True
        return True


class EventManagerTests(unittest.TestCase):
    """Tests for EventManager functionality."""

    def setUp(self):
        # Create an event manager
        self.manager = EventManager()

        # Create test observers
        self.observer1 = TestObserver()
        self.observer2 = TestObserver()
        self.observer2.priority = 10  # Higher priority

        # Register observers
        self.manager.register_observer(self.observer1)
        self.manager.register_observer(self.observer2, ["test"])

    def tearDown(self):
        # Clear observers
        self.manager.observers.clear()

    def test_basic_notification(self):
        """Test basic event notification."""
        # Create and notify an event
        event = TestEvent("basic", {"value": 42})
        self.manager.publish(event)

        # Verify observers received the event
        self.assertEqual(len(self.observer1.events), 1)
        self.assertEqual(self.observer1.events[0].data["value"], 42)
        self.assertEqual(len(self.observer2.events), 1)

    def test_prioritization(self):
        """Test observer prioritization."""
        # Create event manager with test observers in reversed priority order
        manager = EventManager()

        # Create test observers with different priorities
        observer_low = TestObserver()
        observer_low.priority = 1

        observer_high = TestObserver()
        observer_high.priority = 10

        observer_mid = TestObserver()
        observer_mid.priority = 5

        # Register in reverse priority order
        manager.register_observer(observer_low)
        manager.register_observer(observer_mid)
        manager.register_observer(observer_high)

        # Create test event with a shared list to track notification order
        notification_order = []

        def add_to_order(obs_name):
            notification_order.append(obs_name)
            return True

        # Override on_event to track notification order
        observer_low.on_event = lambda e: add_to_order("low")
        observer_mid.on_event = lambda e: add_to_order("mid")
        observer_high.on_event = lambda e: add_to_order("high")

        # Notify the event
        event = Event(event_id="test1", event_type="test.priority", timestamp=time.time(), data={})
        manager.publish(event)

        # Verify notification order (highest priority first)
        self.assertEqual(notification_order, ["high", "mid", "low"])


class PluginRegistryTests(unittest.TestCase):
    """Tests for the PluginRegistry."""

    def setUp(self):
        # Create a temporary directory for test plugins
        self.test_plugin_dir = tempfile.mkdtemp()

        # Create a test plugin file
        with open(os.path.join(self.test_plugin_dir, "test_plugin.py"), "w") as f:
            f.write(
                """
from panther.core.observer.plugins.plugin_interface import IPluginObserver
from panther.core.events.base.event_emitter import Event


class TestPlugin(IPluginObserver):
    VERSION = "1.0.0"
    AUTHOR = "Test Author"
    EVENTS = ["test.plugin"]

    def on_event(self, event: Event):
        return True


class AnotherPlugin(IObserverPlugin):
    VERSION = "0.5.0"
    AUTHOR = "Another Author"

    def on_event(self, event: Event):
        return True
"""
            )

        # Create the registry with the test plugins directory
        self.registry = PluginRegistry(plugin_paths=[self.test_plugin_dir])

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.test_plugin_dir)

    def test_discover_plugins(self):
        """Test plugin discovery."""
        # Discover plugins
        discovered = self.registry.discover_plugins()

        # Check that our test plugins were found
        self.assertIn("TestPlugin", discovered)
        self.assertIn("AnotherPlugin", discovered)
        self.assertEqual(len(discovered), 2)

        # Verify metadata was extracted
        self.assertEqual(self.registry.get_plugin_metadata("TestPlugin")["version"], "1.0.0")
        self.assertEqual(self.registry.get_plugin_metadata("TestPlugin")["author"], "Test Author")
        self.assertEqual(self.registry.get_plugin_metadata("AnotherPlugin")["version"], "0.5.0")

    def test_load_plugin(self):
        """Test plugin loading."""
        # Discover plugins first
        self.registry.discover_plugins()

        # Load a plugin
        plugin = self.registry.load_plugin("TestPlugin")

        # Verify plugin was loaded
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.__class__.__name__, "TestPlugin")

        # Verify plugin is in instances
        self.assertIn("TestPlugin", self.registry.instances)

        # Verify we can get the instance
        self.assertEqual(self.registry.get_plugin_instance("TestPlugin"), plugin)

    def test_load_plugins_by_event_type(self):
        """Test loading plugins by event type."""
        # Discover plugins first
        self.registry.discover_plugins()

        # Load plugins interested in a specific event type
        plugins = self.registry.load_plugins_by_event_type("test.plugin")

        # Should find TestPlugin but not AnotherPlugin
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].__class__.__name__, "TestPlugin")

        # Load plugins for a different event type (should include AnotherPlugin
        # since it doesn't specify any specific event types)
        plugins = self.registry.load_plugins_by_event_type("other.event")
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].__class__.__name__, "AnotherPlugin")


class ResultsManagerTests(unittest.TestCase):
    """Tests for the ResultsManager."""

    def setUp(self):
        # Create a temporary directory for result exports
        self.test_output_dir = tempfile.mkdtemp()

        # Create a results manager
        self.results_manager = ResultsManager(output_dir=self.test_output_dir)

        # Create some test result events
        self.result_events = [
            TestResultEvent("test_case_1", "passed", {"score": 100}),
            TestResultEvent("test_case_2", "failed", {"error": "Failed assertion"}),
            TestResultEvent("test_case_3", "passed", {"performance": "good"}),
        ]

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.test_output_dir)

    def test_result_collection(self):
        """Test result collection."""
        # Process result events
        for event in self.result_events:
            self.results_manager.on_event(event)

        # Verify results were collected
        summary = self.results_manager.get_summary()
        self.assertEqual(summary["total_tests"], 3)
        self.assertEqual(summary["successful"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertAlmostEqual(summary["success_rate"], 2 / 3)

        # Check all results are present
        results = self.results_manager.get_all_results()
        self.assertEqual(len(results), 3)

        # Verify result data
        test_names = [r["test_name"] for r in results]
        self.assertIn("test_case_1", test_names)
        self.assertIn("test_case_2", test_names)
        self.assertIn("test_case_3", test_names)

    def test_result_export(self):
        """Test result export functionality."""
        # Add results
        for event in self.result_events:
            self.results_manager.on_event(event)

        # Export to JSON
        json_path = self.results_manager.export_results("json", "test_results.json")
        self.assertTrue(os.path.exists(json_path))

        # Export to CSV
        csv_path = self.results_manager.export_results("csv", "test_results.csv")
        self.assertTrue(os.path.exists(csv_path))

        # Export to all formats
        all_exports = self.results_manager.export_all_formats("all_formats")
        self.assertEqual(len(all_exports), 4)  # json, csv, html, md

        # Verify all files exist
        for path in all_exports.values():
            self.assertTrue(os.path.exists(path))

    def test_result_callbacks(self):
        """Test result callbacks."""
        # Create a callback function
        callback_results = []

        def test_callback(event):
            callback_results.append(event.test_name)

        # Register the callback
        self.results_manager.register_callback("test.result", test_callback)

        # Process events
        for event in self.result_events:
            self.results_manager.on_event(event)

        # Verify callback was called for each event
        self.assertEqual(len(callback_results), 3)
        self.assertIn("test_case_1", callback_results)
        self.assertIn("test_case_2", callback_results)
        self.assertIn("test_case_3", callback_results)


if __name__ == "__main__":
    unittest.main()
