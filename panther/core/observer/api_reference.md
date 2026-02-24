# Observer Module API Reference

## Core Interfaces

### IObserver
<!-- src: panther/core/observer/base/observer_interface.py -->

```python
class IObserver(ABC)
```

Core interface for all observer implementations in PANTHER.

**Description:** Defines the contract for event processing with deduplication protection and interest-based filtering.

**Constructor:** `IObserver()` - initializes `processed_events_uuids` list.

**Attributes:**
- `processed_events_uuids: List[str]` - UUIDs of previously processed events

**Methods:**

#### `on_event(event: BaseEvent) -> None` (abstract)
Handle an incoming event. Must be implemented by subclasses.

#### `is_interested(event_type: str) -> bool`
Check if this observer should process events of the given type. Default returns `True` (interested in all events).

#### `get_priority() -> int`
Get the priority for this observer. Higher values mean higher priority. Default returns `0`.

#### `_setup_logging(logger_name, log_level, enable_colors=True, output_file=None, structured_output=False)`
Set up logging for an observer using `LoggerFactory`. Supports lazy file handler creation (files are only created when content is first written).

---

### ITypedObserver
<!-- src: panther/core/observer/base/typed_observer_interface.py -->

```python
class ITypedObserver(IObserver)
```

Enhanced observer interface with typed event handlers for automatic event routing.

**Description:** Extends IObserver to provide specific `on_*` handler methods for each event type. The `on_event()` method automatically routes events to their typed handler based on `type(event)`. Observers can override only the handlers they need.

**Constructor:** `ITypedObserver()` - initializes `_event_handlers` dict mapping event classes to handler methods.

**Methods:**

#### `on_event(event: BaseEvent)`
Main event handler that routes to specific typed handlers by looking up `type(event)` in `_event_handlers`. Falls back to `on_unknown_event()` for unregistered event types. Catches exceptions per handler to prevent cascading failures.

#### `on_unknown_event(event: BaseEvent) -> bool`
Handle unknown event types. Default logs a debug warning and returns True.

#### `is_interested(event_type: str) -> bool`
Checks if any handler class name contains the event_type string (partial string matching). Returns True if a match is found.

**Typed Handler Methods (all return `bool`, default `True`):**

Experiment: `on_experiment_initialized`, `on_experiment_plugin_loading_started`, `on_experiment_plugin_loading_completed`, `on_experiment_plugin_loading_failed`, `on_experiment_test_cases_initialized`, `on_experiment_execution_started`, `on_experiment_execution_completed`, `on_experiment_execution_failed`, `on_experiment_finished_early`, `on_experiment_completed`, `on_experiment_failed`

Test: `on_test_created`, `on_test_setup_started`, `on_test_setup_completed`, `on_test_setup_failed`, `on_test_environment_setup_started`, `on_test_environment_setup_completed`, `on_test_environment_setup_failed`, `on_test_deployment_started`, `on_test_deployment_completed`, `on_test_deployment_failed`, `on_test_execution_started`, `on_test_step_started`, `on_test_step_completed`, `on_test_step_failed`, `on_test_assertions_started`, `on_test_assertion_checked`, `on_test_assertions_completed`, `on_test_assertions_failed`, `on_test_execution_completed`, `on_test_execution_failed`, `on_test_teardown_started`, `on_test_teardown_completed`, `on_test_completed`, `on_test_failed`

Service: `on_service_created`, `on_service_preparation_started`, `on_service_preparation_completed`, `on_service_preparation_failed`, `on_service_deployment_started`, `on_service_deployment_completed`, `on_service_deployment_failed`, `on_service_started`, `on_service_ready`, `on_service_health_check_passed`, `on_service_health_check_failed`, `on_service_stopped`, `on_service_error`, `on_service_destroyed`, `on_service_test_results`, `on_command_generation_started`, `on_command_generated`, `on_docker_build_started`, `on_docker_build_completed`, `on_tester_analysis_started`, `on_tester_analysis_completed`

Environment: `on_environment_created`, `on_environment_setup_started`, `on_environment_setup_completed`, `on_environment_setup_failed`, `on_environment_teardown_started`, `on_environment_teardown_completed`, `on_environment_error`, `on_network_setup_started`, `on_network_setup_completed`, `on_network_setup_failed`, `on_network_teardown_started`, `on_network_teardown_completed`, `on_execution_environment_setup_started`, `on_execution_environment_setup_completed`, `on_execution_environment_resource_monitoring`, `on_execution_environment_limit_exceeded`

Step: `on_step_execution_started`, `on_step_execution_completed`, `on_step_execution_failed`, `on_step_progress`, `on_step_unsupported`, `on_step_skipped`

Assertion: `on_assertions_validation_started`, `on_assertions_validation_completed`, `on_assertion_progress`, `on_assertion_result`, `on_assertion_error`, `on_assertion_unknown`

Metrics: `on_metric_collected`, `on_resource_metric`, `on_timing_metric`, `on_counter_metric`, `on_metrics_summary`

Plugin: `on_plugin_loading_started`, `on_plugin_loading_completed`, `on_plugin_loading_failed`, `on_plugin_initialized`, `on_plugin_started`, `on_plugin_stopped`, `on_plugin_error`, `on_plugin_service_created`, `on_plugin_service_started`, `on_plugin_service_stopped`

---

### IPluginObserver
<!-- src: panther/core/observer/base/observer_plugin_interface.py -->

```python
class IPluginObserver(IObserver)
```

Interface for plugin-based observers with bidirectional event-plugin mapping.

**Constructor:** `IPluginObserver()` - initializes `plugin_events` and `event_plugins` defaultdicts.

**Attributes:**
- `plugin_events: Dict[str, Set[str]]` - Maps plugin IDs to their interested event types
- `event_plugins: Dict[str, Set[str]]` - Maps event types to interested plugin IDs

**Abstract Methods:**

#### `register_plugin_events(plugin_id: str, event_types: List[str]) -> None`
Register event types that a plugin is interested in.

#### `unregister_plugin(plugin_id: str) -> None`
Unregister a plugin and its event interests.

#### `get_plugin_events(plugin_id: str) -> List[str]`
Get the event types a plugin is interested in.

#### `get_plugins_for_event(event_type: str) -> List[str]`
Get plugins interested in a specific event type.

### PluginObserver (concrete implementation)
<!-- src: panther/core/observer/base/observer_plugin_interface.py -->

```python
class PluginObserver(IPluginObserver)
```

Concrete implementation of plugin-based observer. Implements all abstract methods.

**Additional Methods:**

#### `on_event(event: Event) -> None`
Handle an event by notifying interested plugins via `_notify_plugins()`.

#### `_notify_plugins(event: Event, plugin_ids: List[str]) -> None`
Notify specific plugins about an event. Default implementation logs notifications.

#### `get_registered_plugins() -> List[str]`
Get a list of all registered plugin IDs.

#### `get_event_types() -> List[str]`
Get a list of all event types that have interested plugins.

---

## Management Classes

### EventManager
<!-- src: panther/core/observer/management/event_manager.py -->

```python
class EventManager(LoggerMixin)
```

Central event coordination system. Implements singleton pattern.

**Constructor:** `EventManager()` - initializes observer registry, event history, metrics, and deduplication systems. Guarded by `_initialized` flag to prevent re-initialization.

**Attributes:**
- `observers: Dict[str, List[Tuple[int, IObserver]]]` - Map of event types to prioritized observers
- `global_observers: List[Tuple[int, IObserver]]` - Global observers that receive all events
- `event_history: List[Tuple[datetime, BaseEvent]]` - Recent events for debugging (max 1000)
- `metrics: Dict` - Processing metrics (`processed`, `errors`, `by_type`)
- `duplicate_detection_enabled: bool` - Content-based duplicate detection flag (default True)

**Class Methods:**

#### `get_instance() -> EventManager`
Get the singleton instance.

#### `ensure_instance() -> EventManager`
Alias for `get_instance()` with a clearer name.

#### `reset_instance() -> None`
Reset the singleton instance (for testing).

**Public Methods:**

#### `register_observer(observer: IObserver, event_types: List[str] = None, priority: int = 0) -> None`
Register an observer. If `event_types` is None, registers as a global observer. Higher priority (larger number) observers are notified first. Skips duplicate registrations.

#### `register_observer_once(observer, observer_id, scope="global", event_types=None, priority=0)`
Register an observer only if not already registered, with scope tracking. Returns the observer (existing or new).

#### `unregister_observer(observer: IObserver, event_types: List[str] = None) -> None`
Unregister an observer from specific or all event types.

#### `notify(event: BaseEvent) -> bool`
Main event distribution method. Performs content-based and time-based duplicate detection, validates the event, records it in history, and notifies matching observers. Returns True if event was processed.

#### `get_event_history(event_type: str = None, limit: int = None) -> List[Tuple[datetime, BaseEvent]]`
Get recent events, optionally filtered by type.

#### `get_metrics() -> Dict[str, Any]`
Get event processing metrics.

#### `cleanup_scoped_observers(scope: str) -> None`
Remove all observers from a specific scope.

#### `get_scoped_observer_count(scope: str = None) -> Dict[str, int]`
Get count of observers by scope.

#### `has_observer(observer_id: str) -> bool`
Check if an observer with the given ID is already registered.

#### `get_registered_observer(observer_id: str) -> Optional[Tuple[IObserver, str]]`
Get a registered observer by its ID. Returns `(observer, scope)` or None.

#### `get_observer_by_type(observer_type) -> Optional[IObserver]`
Find and return an observer by its class type. Searches global and event-specific observers.

#### `enable_duplicate_detection(enabled: bool = True) -> None`
Enable or disable content-based duplicate detection.

#### `clear_signature_cache() -> None`
Clear the content signature cache for duplicate detection.

#### `set_event_context(context_id: str, context_data: Dict[str, Any]) -> None`
Set context data for event correlation.

#### `clear_event_context(context_id: str) -> None`
Clear context data.

#### `get_event_context(context_id: str) -> Dict[str, Any]`
Get context data for event correlation.

#### `cleanup_none_observers() -> int`
Remove any None observers from all observer lists. Returns count of cleaned observers.

**Module-Level Convenience Function:**

```python
def get_event_manager() -> EventManager
```

Get the EventManager singleton instance.

---

### ResultsManager
<!-- src: panther/core/observer/management/results_manager.py -->

```python
class ResultsManager(IObserver)
```

Comprehensive manager for test results. Combines result collection, aggregation, and export.

**Constructor:** `ResultsManager(output_dir: str = None)` - creates output directory if needed.

**Attributes:**
- `aggregator: ResultAggregator` - Result aggregation engine
- `exporter: ResultsExporter` - Export functionality

**Methods:**

#### `on_event(event: Event) -> None`
Handle events, specifically looking for `TestResultEvent` and `EnhancedResultEvent` types.

#### `is_interested(event_type: str) -> bool`
Returns True for `test.result`, `test.case.result`, `test.suite.result`, `enhanced.result` types and prefixes.

#### `get_priority() -> int`
Returns 10 for early result processing.

#### `register_callback(event_type: str, callback: Callable) -> None`
Register a callback for a specific result event type. Use `"*"` for wildcard.

#### `export_results(format_type: str, filename: str = None) -> str`
Export collected results to a file. Supports `"json"`, `"csv"`, `"html"`, `"md"`. Returns path or empty string.

#### `export_all_formats(basename: str = None) -> Dict[str, str]`
Export results to all supported formats. Returns map of format types to file paths.

#### `clear_results() -> None`
Clear all collected results.

#### `get_summary() -> Dict[str, Any]`
Get result summary: `total_tests`, `successful`, `failed`, `success_rate`, `start_time`, `end_time`, `duration`, `tests`.

#### `get_all_results() -> List[Dict[str, Any]]`
Get all collected test results.

#### `get_results_by_category(category: str) -> List[Dict[str, Any]]`
Get results filtered by category.

#### `get_results_by_tag(tag: str) -> List[Dict[str, Any]]`
Get results that contain a specific tag.

#### `get_category_stats() -> Dict[str, Dict[str, int]]`
Get statistics by category (`{category: {"success": n, "failure": n}}`).

#### `get_tag_stats() -> Dict[str, Dict[str, int]]`
Get statistics by tag (`{tag: {"success": n, "failure": n}}`).

### ResultAggregator
<!-- src: panther/core/observer/management/results_manager.py -->

```python
class ResultAggregator
```

Aggregates test results from multiple test runs with thread safety.

**Methods:** `add_result(result)`, `get_summary()`, `get_results_by_test(test_name)`, `get_all_results()`, `clear()`.

### ResultsExporter
<!-- src: panther/core/observer/management/results_manager.py -->

```python
class ResultsExporter
```

Exports test results in various formats.

**Supported Formats:** `json`, `csv`, `html`, `md`

**Methods:** `export(format_type, output_path)`, `export_to_json(output_path, pretty=True)`, `export_to_csv(output_path)`, `export_to_html(output_path)`, `export_to_markdown(output_path)`.

---

## Factory System

### ObserverFactory
<!-- src: panther/core/observer/factory/observer_factory.py -->

```python
class ObserverFactory
```

Factory for creating and configuring observer instances.

**Constructor:**

```python
ObserverFactory(
    event_manager: Optional[EventManager] = None,
    observer_config: Optional[BaseObserverConfig] = None,
)
```

Registers default observer types: `"logger"` (LoggerObserver), `"event_logger"` (LoggerObserver), `"metrics"` (MetricsObserver), `"storage"` (StorageObserver), `"experiment"` (ExperimentObserver).

**Methods:**

#### `create_observer(observer_type, name=None, auto_register=False, event_types=None, priority=0, **kwargs) -> IObserver`
Create an observer instance of the specified type. Raises `ValueError` for unknown types. Optionally auto-registers with the event manager.

#### `register_observer_type(name: str, observer_class: type[IObserver]) -> None`
Register a custom observer type.

#### `register_observer(name: str, observer: IObserver) -> None`
Register an existing observer instance with a name.

#### `unregister_observer(name: str) -> bool`
Unregister a named observer. Returns True if found and removed.

#### `get_observer(name: str) -> Optional[IObserver]`
Get a registered observer by name.

#### `get_all_observers() -> Dict[str, IObserver]`
Get all registered observers.

#### `get_available_types() -> List[str]`
Get list of available observer types.

#### `configure_observer_type(observer_type: str, config: Dict[str, Any]) -> None`
Configure default parameters for an observer type.

#### `set_event_manager(event_manager: EventManager) -> None`
Set the event manager for this factory.

#### `register_with_event_manager(observer, event_types=None, priority=0) -> None`
Register an observer with the event manager. Raises `RuntimeError` if no event manager set.

#### `unregister_from_event_manager(observer: IObserver) -> None`
Unregister an observer from the event manager. Raises `RuntimeError` if no event manager set.

#### `set_observer_config(observer_config: BaseObserverConfig) -> None`
Set the observer configuration for this factory.

#### `batch_register_with_event_manager(observers: list[tuple]) -> None`
Register multiple observers with the event manager. Tuples contain `(observer, event_types, priority)`.

**Module-Level Convenience Functions:**

```python
def get_observer_factory(global_config=None) -> ObserverFactory
def create_observer(observer_type: str, **kwargs) -> IObserver
def create_default_observers(config: Dict[str, Any]) -> List[IObserver]
```

---

## Workflow System

### WorkflowStateTracker
<!-- src: panther/core/observer/workflow/workflow_tracker.py -->

```python
class WorkflowStateTracker(LoggerMixin)
```

Lightweight tracker for experiment workflow states with validated transitions.

**Constructor:** `WorkflowStateTracker()` - initializes empty state and history tracking.

**Methods:**

#### `set_workflow_state(experiment_id: str, state: WorkflowState) -> bool`
Set the workflow state for an experiment. Validates transitions against `WORKFLOW_TRANSITIONS`. New experiments must start with `CREATED`. Returns True if successful.

#### `get_workflow_state(experiment_id: str) -> Optional[WorkflowState]`
Get the current workflow state for an experiment.

#### `force_fail_workflow(experiment_id: str, reason: str = "Forced failure") -> bool`
Force a workflow to FAILED state regardless of current state. Used for error recovery.

#### `clear_workflow_state(experiment_id: str) -> None`
Clear the state for a specific workflow.

#### `is_workflow_in_terminal_state(experiment_id: str) -> bool`
Check if a workflow is in a terminal state (COMPLETED or FAILED).

#### `get_all_workflow_states() -> Dict[str, str]`
Get all current workflow states as `{experiment_id: state_value}`.

#### `get_allowed_transitions(current_state_str: str) -> List[str]`
Get list of allowed state transitions from the given state string.

#### `get_state_history(experiment_id: str = None) -> List[dict]`
Get state transition history, optionally filtered by experiment ID.

### WorkflowState Enum
<!-- src: panther/core/observer/workflow/workflow_tracker.py -->

```python
class WorkflowState(Enum):
    CREATED = "created"
    LOADING_PLUGINS = "loading_plugins"
    GENERATING_COMMANDS = "generating_commands"
    BUILDING_DOCKER = "building_docker"
    DEPLOYING = "deploying"
    RUNNING = "running"
    COLLECTING_OUTPUTS = "collecting_outputs"
    ANALYZING_RESULTS = "analyzing_results"
    REPORTING_RESULTS = "reporting_results"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## Plugin System

### EventObserverPlugin
<!-- src: panther/core/observer/plugins/event_observer_plugin.py -->

Base class for plugin-based observer implementations. See source for details.

### PluginObserverFactory
<!-- src: panther/core/observer/plugins/plugin_observer_factory.py -->

Factory for dynamic plugin observer loading and management. See source for details.

---

## Utility Classes

### EventColors
<!-- src: panther/core/observer/utils/event_colors.py -->

Color mapping utilities for event display in terminal output.
