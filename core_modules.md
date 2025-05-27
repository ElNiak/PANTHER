# Core Modules 🧠

> **Purpose:** Comprehensive guide to PANTHER's core modules that power the framework  
> **Target:** PANTHER framework developers; plugin developers; researchers extending the framework  

The core modules in PANTHER form the **foundation of the framework**, providing essential services for experiment management, event handling, result processing, and exception management. They define the architecture that enables PANTHER's extensibility and modularity.

---

## Architecture Overview

PANTHER's core system uses **modular components** that work together to provide:

1. **Experiment Management**: Orchestration of test cases, configurations, and executions
2. **Observer Pattern**: Event-based communication between components
3. **Results Handling**: Collection, processing, and storage of test results
4. **Exception Management**: Standardized error handling and reporting
5. **Utility Functions**: Common functionality for plugins and services

### Core System Components

| Component | Purpose | Key Features |
|-----------|---------|------------|
| **ExperimentManager** | Orchestrates test execution | Configuration loading, test lifecycle management |
| **Observer Pattern** | Event-based communication | Decoupled components, extensible event system |
| **Results Handling** | Test artifact management | Collection, validation, and storage of results |
| **Exceptions** | Error management | Custom exceptions for specific failure modes |
| **Test Cases** | Test execution framework | Standard interfaces for test definition and execution |
| **Utilities** | Common functionality | Template rendering, Docker management, sequence diagrams |

---

## Core Components

### 1. Experiment Management

**Purpose:** Orchestrates the lifecycle of experiments, including initialization, execution, and cleanup.

**Key Classes:**
- **`ExperimentManager`**: The central coordinator that manages test execution
- **`TestCase`**: Base implementation of test cases
- **`ITestCase`**: Interface for test case implementations

**Configuration:**
```yaml
experiment:
  name: "quic_interoperability"
  description: "Testing interoperability between QUIC implementations"
  author: "PANTHER Team"
  output_dir: "outputs"
  log_level: "INFO"
  tests:
    - name: "quiche_server_lsquic_client"
      description: "Testing Cloudflare Quiche server with lsquic client"
      # Test-specific configuration follows...
```

**Features:**
- Dynamic plugin loading and configuration
- Test case initialization and execution
- Environment setup and teardown
- Results collection and reporting
- Logging and progress tracking

**Example Usage:**
```python
from panther.config.config_experiment_schema import ExperimentConfig
from panther.core.experiment_manager import ExperimentManager

# Load experiment configuration
config_path = "experiment_config.yaml"
experiment = ExperimentManager(config_path)

# Initialize and run the experiment
experiment.initialize_experiments()
experiment.run_tests()
```

### 2. Observer Pattern

**Purpose:** Provides an event-driven architecture for communication between components.

**Key Classes:**
- **`Event`**: Base class for events in the system
- **`EventManager`**: Manages event registration and notification
- **`IObserver`**: Interface for observer implementations
- **`ExperimentObserver`**, **`LoggerObserver`**, **`ResultObserver`**: Specific observers for different aspects of the system

**Example Event Definition:**
```python
from panther.core.observer.event import Event

class TestStartEvent(Event):
    """Event fired when a test starts."""
    def __init__(self, test_name, test_config):
        super().__init__("test_start", {
            "test_name": test_name,
            "test_config": test_config
        })
```

**Observer Registration:**
```python
from panther.core.observer.event_manager import EventManager
from my_module import CustomObserver

event_manager = EventManager()
observer = CustomObserver()
event_manager.register_observer(observer)
```

**Event Notification:**
```python
from panther.core.observer.event import Event

# Create and send an event
event = Event("experiment_complete", {"status": "success"})
event_manager.notify(event)
```

**Features:**
- Decoupled components through event-based communication
- Extensible observer system
- Standardized event format
- Debug capabilities for event flow

### 3. Results Handling

**Purpose:** Collects, processes, and stores test results.

**Key Classes:**
- **`ResultCollector`**: Aggregates results from different sources
- **`ResultHandler`**: Base class for result processing
- **`StorageHandler`**: Handles persistent storage of results

**Configuration:**
```yaml
results:
  storage:
    type: "file_storage"
    path: "outputs/results"
  formats:
    - json
    - csv
  metrics:
    - throughput
    - latency
    - packet_loss
```

**Example Result Processing:**
```python
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler

# Set up result collection
collector = ResultCollector()
storage_handler = StorageHandler("/path/to/output", "experiment_name")
collector.register_handler("performance", storage_handler)

# Collect a result
result = {
    "type": "performance",
    "timestamp": "2025-05-26T12:00:00",
    "metrics": {
        "throughput": 120.5,
        "latency": 45.2,
        "packet_loss": 0.02
    }
}
collector.collect(result)
```

**Features:**
- Chain-of-responsibility pattern for result processing
- Multiple output format support
- Structured result storage
- Integration with the observer pattern

### 4. Exception Management

**Purpose:** Provides standardized error handling throughout the framework.

**Key Exceptions:**
- **`EnvironmentPluginNotFound`**: Raised when a required environment plugin is missing
- **`ServicePluginNotFound`**: Raised when a required service plugin is missing
- **`TesterPluginNotFound`**: Raised when a required tester plugin is missing
- **`ConfigurationError`**: Raised when there's an issue with the configuration

**Example Exception Handling:**
```python
from panther.core.exceptions.ServicePluginNotFound import ServicePluginNotFound

try:
    service = plugin_manager.load_service_plugin("quiche")
except ServicePluginNotFound as e:
    logger.error(f"Failed to load service plugin: {e}")
    # Handle the error, e.g., by falling back to a default plugin
    service = plugin_manager.load_service_plugin("default")
```

**Features:**
- Custom exception types for specific errors
- Detailed error messages
- Integration with logging system
- Consistent error handling patterns

### 5. Test Cases

**Purpose:** Provides a framework for defining and executing test cases.

**Key Classes:**
- **`ITestCase`**: Interface defining the test case contract
- **`TestCase`**: Base implementation of test cases

**Test Case Interface:**
```python
class ITestCase(ABC):
    @abstractmethod
    def run(self):
        """Runs the test case."""
        pass

    @abstractmethod
    def deploy_services(self):
        """Starts the services defined in the test configuration."""
        pass

    @abstractmethod
    def execute_steps(self):
        """Executes steps defined in the test configuration."""
        pass

    @abstractmethod
    def validate_assertions(self):
        """Validates assertions defined in the test configuration."""
        pass
```

**Example TestCase Usage:**
```python
from panther.core.test_cases.test_case import TestCase

class QuicInteropTest(TestCase):
    def execute_steps(self):
        # Custom steps for QUIC interoperability testing
        self.logger.info("Starting client connection")
        # ... implementation details ...
```

**Features:**
- Standard interface for all test cases
- Lifecycle methods for setup, execution, and teardown
- Integration with the observer pattern
- Result collection and validation

### 6. Utilities

**Purpose:** Provides common functionality used across the framework.

**Key Utilities:**
- **`JinjaManager`**: Template rendering for configurations and reports
- **`SequenceDiagram`**: Generation of sequence diagrams for documentation
- **`DockerBuilder`**: Utility for building Docker images

**Example Jinja Template Usage:**
```python
from panther.core.utils.jinja_manager import JinjaManager

# Initialize Jinja environment
jinja = JinjaManager("/path/to/templates")

# Render a template
context = {
    "test_name": "quic_interop",
    "implementations": ["quiche", "lsquic", "picoquic"]
}
rendered = jinja.render("report_template.md", context)
```

**Features:**
- Standardized template rendering
- Docker interaction utilities
- Visualization tools
- Common helper functions

---

## Extension Points

PANTHER's core modules are designed to be **extended** in various ways:

1. **Custom Observers**: Create new observers by implementing the `IObserver` interface.
   ```python
   from panther.core.observer.observer_interface import IObserver
   from panther.core.observer.event import Event
   
   class PerformanceObserver(IObserver):
       def on_event(self, event: Event):
           if event.name == "test_complete":
               # Process performance metrics
               metrics = event.data.get("metrics", {})
               # ... implementation details ...
   ```

2. **Custom Result Handlers**: Extend result processing by implementing custom handlers.
   ```python
   from panther.core.results.result_handler import ResultHandler
   
   class MetricAnalyzer(ResultHandler):
       def handle(self, result):
           if "metrics" in result:
               # Analyze metrics
               # ... implementation details ...
           
           # Pass to next handler
           super().handle(result)
   ```

3. **Custom Test Cases**: Create specialized test cases for specific testing needs.
   ```python
   from panther.core.test_cases.test_case import TestCase
   
   class ProtocolFuzzingTest(TestCase):
       def deploy_services(self):
           # Custom deployment logic
           # ... implementation details ...
       
       def execute_steps(self):
           # Fuzzing-specific test steps
           # ... implementation details ...
   ```

---

## Best Practices

1. **Observer Registration**:
   - Register observers early in the application lifecycle.
   - Use meaningful event names and consistent data structures.

2. **Error Handling**:
   - Use the provided exception classes for specific error types.
   - Include detailed error messages that help with troubleshooting.

3. **Test Case Development**:
   - Follow the lifecycle methods (deploy, execute, validate).
   - Use the observer pattern for progress reporting.
   - Store results using the result collector.

4. **Extension Development**:
   - Implement the appropriate interfaces.
   - Follow PANTHER's coding standards and documentation practices.
   - Include unit tests for new components.

---

## Core Module Dependencies

The core module has the following dependencies:

1. **Configuration Module**: For loading and validating experiment configurations
2. **Plugin System**: For dynamically loading and managing plugins
3. **Logging**: For consistent logging across the framework

---

## Troubleshooting

### Common Issues

1. **Plugin Loading Issues**:
   - **Symptom**: `PluginNotFound` exceptions
   - **Solution**: Check plugin paths and ensure all dependencies are installed

2. **Observer Notification Issues**:
   - **Symptom**: Events not being processed
   - **Solution**: Verify observer registration and event names

3. **Result Collection Issues**:
   - **Symptom**: Missing or incomplete results
   - **Solution**: Check result handler registration and data formats

### Debugging Techniques

1. **Enable Debug Logging**:
   ```yaml
   logging:
     level: DEBUG
   ```

2. **Event Tracing**:
   ```python
   # Add a debug observer
   from panther.core.observer.debug_observer import DebugObserver
   event_manager.register_observer(DebugObserver())
   ```

3. **Result Validation**:
   ```python
   # Add validation to result collection
   from panther.core.results.result_handlers.validation_handler import ValidationHandler
   collector.register_handler("all", ValidationHandler(schema_path))
   ```

---

## Future Directions

The core module is continuously evolving with the following enhancements planned:

1. **Advanced Event Filtering**: Allow observers to filter events based on patterns and criteria
2. **Parallel Test Execution**: Support for running test cases in parallel
3. **Enhanced Result Analysis**: Built-in statistical analysis of test results
4. **Integration with External Systems**: Connectors for CI/CD pipelines and external monitoring systems

---

## API Reference

Complete API documentation is available in the code and can be generated using tools like Sphinx.

### Key APIs

1. **Experiment Management**:
   - `ExperimentManager`: Main class for experiment orchestration
   - `TestCase`: Base implementation for test cases

2. **Observer Pattern**:
   - `EventManager`: Manager for event registration and notification
   - `IObserver`: Interface for observer implementations
   - `Event`: Base class for events

3. **Results Handling**:
   - `ResultCollector`: Aggregator for test results
   - `ResultHandler`: Base class for result processors

---

## Contributing

Contributions to the core module are welcome! Please follow these guidelines:

1. Follow the project's coding standards
2. Write unit tests for all new functionality
3. Update documentation to reflect changes
4. Submit a pull request with a clear description of the changes

---

## Additional Resources

- [Developer Guide](/DEV_GUIDE.md): Comprehensive development guide for PANTHER
- [Configuration Guide](/panther/config/README.md): Guide to configuring PANTHER experiments
- [Plugin Development](/docs/plugin_development.md): Guide to developing plugins for PANTHER
