# Enhanced Plugin Architecture for PANTHER

This directory contains the implementation of an enhanced plugin architecture for the PANTHER framework, focusing on complete separation of concerns and event-driven communication between plugins.

## Overview

The enhanced plugin architecture replaces direct method calls with event-based communication, allowing plugins to operate autonomously and focus solely on their specific domains. This promotes loose coupling between components and makes the system more maintainable and extensible.

## Key Components

### Core Interfaces

- `IPantherPlugin`: Base interface for all plugins with standardized lifecycle methods
- `IPluginRegistry`: Interface for the plugin registry

### Plugin Registry

- `EnhancedPluginRegistry`: Central registry for plugin event handling and lifecycle management

### Plugin Manager

- `EnhancedPluginManager`: Manager for discovering, initializing, and managing plugins

### Base Plugin Classes

- `BaseServicePlugin`: Base class for all service plugins
- `BaseEnvironmentPlugin`: Base class for all environment plugins
- `BaseTesterPlugin`: Base class for all tester plugins

### Event Mixins

- `ServicePluginEventMixin`: Event methods for service plugins
- `EnhancedEnvironmentPluginEventMixin`: Event methods for environment plugins
- `TesterPluginEventMixin`: Event methods for tester plugins

### Plugin Events

- Domain-specific event classes for different plugin types
- Events for service lifecycle, environment resources, and test execution

### Communication

- `PluginCommunicator`: Helper class for plugin-to-plugin communication

### Test Case Implementation

- `EventDrivenTestCase`: Test case implementation using event-driven communication

## Usage

### Creating a Service Plugin

```python
from panther.plugins.services.base_service_plugin import BaseServicePlugin

class MyServicePlugin(BaseServicePlugin):
    """My custom service plugin."""

    def _initialize_service(self):
        # Initialize your service
        return True

    def _start_service(self):
        # Start your service
        # Emit events for service state changes
        return True

    def _stop_service(self):
        # Stop your service
        return True

    # Implement other required methods
```

### Creating an Environment Plugin

```python
from panther.plugins.environments.base_environment_plugin import BaseEnvironmentPlugin

class MyEnvironmentPlugin(BaseEnvironmentPlugin):
    """My custom environment plugin."""

    def _initialize_environment(self):
        # Initialize your environment
        return True

    def _setup_environment(self):
        # Set up your environment
        # Allocate resources and emit events
        return True

    def _teardown_environment(self):
        # Tear down your environment
        # Release resources and emit events
        return True

    # Implement other required methods
```

### Creating a Tester Plugin

```python
from panther.plugins.testers.base_tester_plugin import BaseTesterPlugin

class MyTesterPlugin(BaseTesterPlugin):
    """My custom tester plugin."""

    def _initialize_tester(self):
        # Initialize your tester
        return True

    def _run_test(self, test_id, test_config):
        # Run a test and return results
        return True, {"output": "Test passed"}

    # Implement other required methods
```

### Running a Test

```python
from panther.core.observer.event_manager import EventManager
from panther.plugins.enhanced_plugin_manager import EnhancedPluginManager
from panther.core.test_cases.event_driven_test_case import EventDrivenTestCase

# Set up the event manager
event_manager = EventManager()

# Create the plugin manager
plugin_manager = EnhancedPluginManager(
    event_manager=event_manager,
    discovery_paths=["path/to/plugins"]
)

# Discover plugins
plugin_manager.discover_plugins()

# Create an event-driven test case
test_case = EventDrivenTestCase(
    plugin_registry=plugin_manager.plugin_registry,
    test_config={
        "id": "my-test",
        "environment": {"type": "my-env-type"},
        "services": [{"type": "my-service-type"}],
        "test_type": "my-test-type",
    }
)

# Run the test
result = test_case.run()
print(f"Test result: {result['success']}")
```

## Benefits

1. **Separation of Concerns**: Each plugin focuses solely on its specific domain
2. **Loose Coupling**: Plugins communicate through events, not direct method calls
3. **Extensibility**: New plugin types can be added without modifying existing code
4. **Testability**: Components can be tested in isolation with mock events
5. **Visibility**: Event-driven architecture makes system behavior more transparent

## Event Flow Example

1. Test case emits "environment.setup.request" event
2. Environment plugin handles the event, sets up the environment
3. Environment plugin emits "environment.setup.completed" event
4. Test case observer handles the event, requests services to start
5. Service plugins start and emit "service.ready" events
6. Test case observer tracks service readiness, requests test execution
7. Tester plugin runs the test and emits "test.completed" event
8. Test case observer handles completion, requests teardown
9. Environment and service plugins handle teardown events
