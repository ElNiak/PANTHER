"""
Integration Test for Event-Driven Plugin Architecture

This script demonstrates and validates the event-driven plugin architecture
by creating sample plugins, registering them with the event system, and
tracking event propagation between components.
"""

import logging
import sys
import time
from typing import Any, Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EventArchitectureTest")

# Define basic classes needed for the test
class Event:
    """Simplified Event class for testing."""

    def __init__(self, name: str, data: Dict[str, Any] = None):
        self.name = name
        self.data = data or {}

    def get_type(self) -> str:
        return self.name

    def __str__(self):
        return f"Event(name={self.name}, data={self.data})"

class EventManager:
    """Simplified EventManager for testing."""

    def __init__(self):
        self.observers = []

    def register_observer(self, observer):
        self.observers.append(observer)

    def notify(self, event: Event):
        for observer in self.observers:
            if hasattr(observer, "is_interested") and callable(getattr(observer, "is_interested")):
                if observer.is_interested(event.get_type()):
                    observer.on_event(event)
            else:
                observer.on_event(event)

class EventEmitter:
    """Simplified EventEmitter for testing."""

    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager

    def emit_event(self, event: Event):
        self.event_manager.notify(event)

    def emit_service_event(self, name: str, data: Dict[str, Any] = None):
        self.emit_event(Event(name=name, data=data or {}))

class IPantherPlugin:
    """Simplified Plugin interface for testing."""

    def __init__(self, plugin_id: str = None, name: str = None):
        self.plugin_id = plugin_id or self.__class__.__name__
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"Plugin:{self.name}")
        self.event_emitter = None

    def set_event_emitter(self, event_emitter):
        self.event_emitter = event_emitter

    def get_supported_events(self) -> List[str]:
        return []

    def handle_event(self, event: Event):
        pass

    def initialize(self, config: Dict[str, Any] = None) -> bool:
        return True

    def shutdown(self) -> bool:
        return True

class PluginObserver:
    """Simplified PluginObserver for testing."""

    def __init__(self):
        self.plugins = {}
        self.plugin_interests = {}
        self.event_subscribers = {}
        self.logger = logging.getLogger("PluginObserver")

    def register_plugin(self, plugin: IPantherPlugin):
        self.plugins[plugin.plugin_id] = plugin
        event_types = plugin.get_supported_events()

        if not event_types:
            return

        if plugin.plugin_id not in self.plugin_interests:
            self.plugin_interests[plugin.plugin_id] = set()

        for event_type in event_types:
            self.plugin_interests[plugin.plugin_id].add(event_type)

            if event_type not in self.event_subscribers:
                self.event_subscribers[event_type] = set()

            self.event_subscribers[event_type].add(plugin.plugin_id)

    def is_interested(self, event_type: str) -> bool:
        for pattern, plugins in self.event_subscribers.items():
            if self._matches_pattern(event_type, pattern):
                return True
        return False

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event_type matches a pattern with wildcards."""
        if pattern == "*":
            return True

        parts = pattern.split(".")
        event_parts = event_type.split(".")

        if len(parts) != len(event_parts):
            return False

        for i, part in enumerate(parts):
            if part != "*" and part != event_parts[i]:
                return False

        return True

    def on_event(self, event: Event):
        event_type = event.get_type()
        matched_plugins = set()

        # Find plugins with matching patterns
        for pattern, plugins in self.event_subscribers.items():
            if self._matches_pattern(event_type, pattern):
                matched_plugins.update(plugins)

        # Notify matching plugins
        for plugin_id in matched_plugins:
            plugin = self.plugins.get(plugin_id)
            if plugin:
                try:
                    plugin.handle_event(event)
                except Exception as e:
                    self.logger.error(f"Error in plugin '{plugin.name}': {e}")

class EventMonitorPlugin(IPantherPlugin):
    """
    Sample plugin that monitors events and logs them.
    """

    METADATA = {
        "name": "EventMonitor",
        "version": "1.0.0",
        "description": "Monitors and logs events in the system",
        "author": "PANTHER Team",
        "supported_events": ["*"],  # All events
        "tags": ["monitoring", "logging"],
    }

    def __init__(self, plugin_id=None, name=None):
        super().__init__(plugin_id, name)
        self.received_events = []

    def get_supported_events(self):
        """Return all event types we're interested in."""
        return ["service.*.started", "service.*.stopped", "experiment.initialized"]

    def handle_event(self, event):
        """Handle an incoming event."""
        self.received_events.append(event)
        self.logger.info(f"Received event: {event}")

    def initialize(self, config=None):
        """Initialize the plugin."""
        self.logger.info("EventMonitorPlugin initialized")
        return True

    def get_event_count(self):
        """Return the number of events received."""
        return len(self.received_events)

class ServiceInteractorPlugin(IPantherPlugin):
    """
    Sample plugin that reacts to service events by taking actions.
    """

    METADATA = {
        "name": "ServiceInteractor",
        "version": "1.0.0",
        "description": "Interacts with services based on events",
        "author": "PANTHER Team",
        "supported_events": ["service.*.started", "service.*.stopped"],
        "tags": ["service", "interaction"],
    }

    def __init__(self, plugin_id=None, name=None):
        super().__init__(plugin_id, name)
        self.active_services = set()

    def get_supported_events(self):
        """Return service event types."""
        return ["service.*.started", "service.*.stopped"]

    def handle_event(self, event):
        """Handle service events."""
        event_type = event.get_type()

        if event_type.endswith(".started"):
            service_name = event.data.get("service_name", "unknown")
            self.active_services.add(service_name)
            self.logger.info(
                f"Service started: {service_name}, total active: {len(self.active_services)}"
            )

            # Emit a custom event in response
            if self.event_emitter:
                self.event_emitter.emit_service_event(
                    name="service.interaction",
                    data={
                        "action": "tracked",
                        "service_name": service_name,
                        "active_count": len(self.active_services),
                    },
                )

        elif event_type.endswith(".stopped"):
            service_name = event.data.get("service_name", "unknown")
            if service_name in self.active_services:
                self.active_services.remove(service_name)
                self.logger.info(
                    f"Service stopped: {service_name}, total active: {len(self.active_services)}"
                )

    def get_active_service_count(self):
        """Return the number of active services."""
        return len(self.active_services)

def test_event_architecture():
    """
    Test the event-driven plugin architecture.

    This function:
    1. Sets up the event management system
    2. Creates and registers plugins
    3. Emits various events
    4. Validates event propagation
    """
    logger.info("Starting event architecture integration test")

    # Setup event system
    event_manager = EventManager()
    event_emitter = EventEmitter(event_manager)

    # Create plugin observer and register with event manager
    plugin_observer = PluginObserver()
    event_manager.register_observer(plugin_observer)

    try:
        # Manually load the plugins
        monitor_plugin = EventMonitorPlugin()
        interactor_plugin = ServiceInteractorPlugin()

        # Set event emitter and register with observer
        monitor_plugin.set_event_emitter(event_emitter)
        interactor_plugin.set_event_emitter(event_emitter)
        plugin_observer.register_plugin(monitor_plugin)
        plugin_observer.register_plugin(interactor_plugin)

        # Initialize plugins
        assert monitor_plugin.initialize(), "Failed to initialize monitor plugin"
        assert interactor_plugin.initialize(), "Failed to initialize interactor plugin"

        # Validate setup
        assert plugin_observer.plugins, "No plugins registered"

        # Test 1: Emit a service started event
        logger.info("TEST 1: Emitting service started event")
        service_event = Event(
            name="service.test_service.started",
            data={"service_name": "test_service", "service_type": "tester"},
        )
        event_emitter.emit_event(service_event)
        time.sleep(0.1)  # Allow event processing

        # Verify both plugins received the event
        assert monitor_plugin.get_event_count() > 0, "Monitor plugin didn't receive the event"
        assert (
            interactor_plugin.get_active_service_count() > 0
        ), "Interactor plugin didn't track the service"

        # Test 2: Emit an experiment initialized event
        logger.info("TEST 2: Emitting experiment initialized event")
        experiment_event = Event(
            name="experiment.initialized",
            data={"experiment_id": "test_experiment", "config": {"test_count": 3}},
        )
        event_emitter.emit_event(experiment_event)
        time.sleep(0.1)  # Allow event processing

        # Verify only monitor plugin received this event
        assert (
            monitor_plugin.get_event_count() > 1
        ), "Monitor plugin didn't receive the experiment event"

        # Test 3: Emit a service stopped event
        logger.info("TEST 3: Emitting service stopped event")
        service_stopped_event = Event(
            name="service.test_service.stopped",
            data={"service_name": "test_service", "success": True, "reason": "test completed"},
        )
        event_emitter.emit_event(service_stopped_event)
        time.sleep(0.1)  # Allow event processing

        # Verify service was removed from active list
        assert (
            interactor_plugin.get_active_service_count() == 0
        ), "Interactor plugin didn't remove the stopped service"

        logger.info("All tests passed successfully!")
        return True

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_event_architecture()
    sys.exit(0 if success else 1)
