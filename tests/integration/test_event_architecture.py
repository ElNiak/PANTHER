"""
Integration Test for Event-Driven Plugin Architecture

This script demonstrates and validates the event-driven plugin architecture
by creating sample plugins, registering them with the event system, and
tracking event propagation between components.
"""

import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EventArchitectureTest")

# Adjust Python path to include the project root directory
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import required components
from panther.core.observer.management.event_manager import EventManager
from panther.core.events.base.event_emitter import EventEmitter
from panther.core.events.service.events import ServiceEvent
from panther.core.events.experiment.events import ExperimentInitializedEvent
from panther.core.observer.impl.plugin_observer import PluginObserver
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.plugin_interface_enhanced import IPantherPlugin


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


def create_temp_plugin_file(plugin_class):
    """Create a temporary file containing the plugin class."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w+") as f:
        f.write(
            f"""
from panther.plugins.plugin_interface_enhanced import IPantherPlugin

class {plugin_class.__name__}(IPantherPlugin):
    # Use the same metadata as the original class
    METADATA = {plugin_class.METADATA}

    def __init__(self, plugin_id=None, name=None):
        super().__init__(plugin_id, name)
        self.received_events = []

    def get_supported_events(self):
        return {repr(plugin_class().get_supported_events())}

    def handle_event(self, event):
        self.received_events.append(event)

    def initialize(self, config=None):
        return True

    def shutdown(self):
        return True
"""
        )
        return f.name


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

    # Create plugin manager with temp directory for plugins
    plugin_dir = tempfile.mkdtemp()
    plugin_manager = PluginManager(plugin_directories=[plugin_dir], event_manager=event_manager)

    # Set event emitter on plugin manager
    plugin_manager.set_event_emitter(event_emitter)

    # Create temporary plugin files
    monitor_plugin_file = create_temp_plugin_file(EventMonitorPlugin)
    interactor_plugin_file = create_temp_plugin_file(ServiceInteractorPlugin)

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
        service_event = ServiceEvent(
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
        experiment_event = ExperimentInitializedEvent(
            experiment_id="test_experiment", config={"test_count": 3}
        )
        event_emitter.emit_event(experiment_event)
        time.sleep(0.1)  # Allow event processing

        # Verify only monitor plugin received this event
        assert (
            monitor_plugin.get_event_count() > 1
        ), "Monitor plugin didn't receive the experiment event"

        # Test 3: Emit a service stopped event
        logger.info("TEST 3: Emitting service stopped event")
        service_stopped_event = ServiceEvent(
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

    finally:
        # Cleanup
        if os.path.exists(monitor_plugin_file):
            os.unlink(monitor_plugin_file)
        if os.path.exists(interactor_plugin_file):
            os.unlink(interactor_plugin_file)

        if os.path.exists(plugin_dir):
            try:
                os.rmdir(plugin_dir)
            except:
                pass


if __name__ == "__main__":
    success = test_event_architecture()
    sys.exit(0 if success else 1)
