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

from panther.core.observer.events import Event, TestEvent, SystemEvent, TestResultEvent
from panther.core.observer.async_event_manager import AsyncEventManager, TypeBasedBufferingStrategy
from panther.core.observer.storage.results_manager import ResultsManager
from panther.core.observer.plugin.plugin_interface import IObserverPlugin
from panther.core.observer.core.observer_interface import IObserver
from panther.core.observer.plugin.plugin_registry import PluginRegistry


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


class TestPlugin(IObserverPlugin):
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


class AsyncEventManagerTests(unittest.TestCase):
    """Tests for AsyncEventManager functionality."""

    def setUp(self):
        # Create a buffering strategy for testing
        self.buffer_strategy = TypeBasedBufferingStrategy(
            buffer_types=["test.buffered"], max_buffer_size=3, max_buffer_time=0.5
        )

        # Create an event manager with the buffering strategy
        self.manager = AsyncEventManager(
            max_workers=2, queue_size=100, buffering_strategy=self.buffer_strategy
        )

        # Create test observers
        self.observer1 = TestObserver()
        self.observer2 = TestObserver()
        self.observer2.priority = 10  # Higher priority

        # Register observers
        self.manager.register_observer(self.observer1)
        self.manager.register_observer(self.observer2, ["test"])

    def tearDown(self):
        # Shutdown the event manager
        self.manager.shutdown(wait=True)

    def test_basic_notification(self):
        """Test basic event notification."""
        # Create and notify an event
        event = TestEvent("basic", {"value": 42})
        future = self.manager.notify(event)

        # Wait for the event to be processed
        self.assertTrue(self.observer1.event_received.wait(timeout=1.0))
        self.assertTrue(future.done())

        # Verify observers received the event
        self.assertEqual(len(self.observer1.events), 1)
        self.assertEqual(self.observer1.events[0].data["value"], 42)
        self.assertEqual(len(self.observer2.events), 1)

    def test_prioritization(self):
        """Test observer prioritization."""
        # Create event manager with test observers in reversed priority order
        manager = AsyncEventManager()

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

        # Override on_event to track notification order
        observer_low.on_event = lambda e: add_to_order("low")
        observer_mid.on_event = lambda e: add_to_order("mid")
        observer_high.on_event = lambda e: add_to_order("high")

        # Notify the event and wait for processing
        event = Event("test.priority")
        future = manager.notify(event)
        future.result(timeout=1.0)

        # Verify notification order (highest priority first)
        self.assertEqual(notification_order, ["high", "mid", "low"])

        # Clean up
        manager.shutdown()

    def test_buffering(self):
        """Test event buffering."""
        # Create buffered events
        event1 = Event("test.buffered.type1", {"seq": 1})
        event2 = Event("test.buffered.type1", {"seq": 2})  # Same type, should replace event1
        event3 = Event("test.buffered.type2", {"seq": 3})  # Different type

        # Notify events
        self.manager.notify(event1)
        self.manager.notify(event2)
        self.manager.notify(event3)

        # Wait for buffer flush (max size reached)
        time.sleep(0.1)

        # Verify observer received the consolidated events (only event2 and event3)
        self.observer1.event_received.wait(timeout=1.0)

        # Give time for all events to be processed
        time.sleep(0.2)

        # Should have 2 events (event2 and event3), as event1 was replaced by event2
        self.assertEqual(len(self.observer1.events), 2)

        # Verify event2 (seq 2) was kept and event1 (seq 1) was discarded
        event_seqs = [e.data["seq"] for e in self.observer1.events]
        self.assertIn(2, event_seqs)
        self.assertIn(3, event_seqs)
        self.assertNotIn(1, event_seqs)

    def test_time_based_buffer_flush(self):
        """Test time-based buffer flushing."""
        # Create a buffered event
        event = Event("test.buffered.timeout", {"value": "timeout_test"})

        # Notify the event
        self.manager.notify(event)

        # Wait for time-based flush
        time.sleep(0.6)  # Buffer time is 0.5s

        # Verify observer received the event
        self.assertEqual(len(self.observer1.events), 1)
        self.assertEqual(self.observer1.events[0].data["value"], "timeout_test")

    def test_error_handling_and_retry(self):
        """Test error handling and retry mechanism."""
        # Create an observer that fails initially then succeeds
        fail_count = [0]  # Use list for mutable state in closure

        class FailingObserver(IObserver):
            def on_event(self, event: Event):
                if fail_count[0] < 2:  # Fail twice
                    fail_count[0] += 1
                    raise ValueError("Intentional failure")
                return True  # Succeed on third try

            def is_interested(self, event_type: str) -> bool:
                return True

        # Register the failing observer
        failing_observer = FailingObserver()
        self.manager.register_observer(failing_observer)

        # Create and notify an event
        event = Event("test.retry")
        future = self.manager.notify(event)

        # Wait for the event to be processed (including retries)
        try:
            result = future.result(timeout=3.0)
            self.assertTrue(result)
            self.assertEqual(fail_count[0], 2)  # Should have failed twice before success
        except Exception as e:
            self.fail(f"Event processing failed after retries: {e}")

    def test_metrics(self):
        """Test metrics collection."""
        # Clear existing events
        self.observer1.clear()

        # Create and notify several events
        events = [
            Event("test.metric.1", {"value": 1}),
            Event("test.metric.2", {"value": 2}),
            SystemEvent("status", {"status": "ready"}),
        ]

        for event in events:
            self.manager.notify(event)

        # Wait for events to be processed
        time.sleep(0.5)

        # Get metrics
        metrics = self.manager.get_metrics()

        # Verify basic metrics
        self.assertGreaterEqual(metrics["processed"], 3)
        self.assertEqual(metrics["errors"], 0)

        # Verify event type metrics
        self.assertIn("test.metric.1", metrics["by_type"])
        self.assertIn("test.metric.2", metrics["by_type"])
        self.assertIn("system.status", metrics["by_type"])


class PluginRegistryTests(unittest.TestCase):
    """Tests for the PluginRegistry."""

    def setUp(self):
        # Create a temporary directory for test plugins
        self.test_plugin_dir = tempfile.mkdtemp()

        # Create a test plugin file
        with open(os.path.join(self.test_plugin_dir, "test_plugin.py"), "w") as f:
            f.write(
                """
from panther.core.observer.plugin.plugin_interface import IObserverPlugin
from panther.core.observer.events import Event

class TestPlugin(IObserverPlugin):
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
            TestResultEvent("result1", "test_case_1", True, {"score": 100}),
            TestResultEvent("result2", "test_case_2", False, {"error": "Failed assertion"}),
            TestResultEvent("result3", "test_case_3", True, {"performance": "good"}),
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
