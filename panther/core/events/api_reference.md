# Events Module API Reference

## Core Classes

### BaseEvent
<!-- src: panther/core/events/base/event_base.py -->

```python
class BaseEvent(ABC)
```

Foundation class for all events in the PANTHER framework.

**Description:** Provides event identification with content-based UUID generation for deduplication, timestamp tracking, and entity identification. **Not a dataclass** -- uses a standard `__init__` constructor. **Not frozen/immutable** -- `add_data()` mutates data and regenerates the UUID.

**Constructor:**

```python
BaseEvent(
    name: str,
    entity_type: EventType,
    entity_id: str,
    data: Optional[Dict[str, Any]] = None,
    use_content_uuid: bool = True,
)
```

**Attributes:**
- `id: str` - UUID4 or content-based UUID5
- `name: str` - Event name/identifier
- `entity_type: EventType` - Type of entity (from `EventType` enum)
- `entity_id: str` - Unique identifier for the entity
- `timestamp: datetime` - Event creation timestamp
- `data: Dict[str, Any]` - Additional event data
- `content_signature: Optional[str]` - Deterministic content signature for deduplication

**Methods:**

#### `get_type() -> str`
Get the event type identifier string (e.g., `"test.execution_started"`).

#### `get_entity_id() -> str`
Get the entity identifier this event relates to.

#### `get_timestamp() -> datetime`
Get the event timestamp.

#### `get_data() -> Dict[str, Any]`
Get a copy of the event data.

#### `add_data(key: str, value: Any) -> None`
Add additional data to the event. Regenerates the content-based UUID if applicable.

#### `is_duplicate_of(other_event: BaseEvent) -> bool`
Check if this event is a duplicate of another event using content signatures.

#### `get_content_signature() -> Optional[str]`
Get the content signature for duplicate detection.

#### `to_dict() -> Dict[str, Any]`
Convert event to dictionary representation with keys: `id`, `name`, `type`, `entity_type`, `entity_id`, `timestamp`, `data`.

#### `validate() -> bool`
Validate event data. Base implementation checks that `name`, `entity_type`, `entity_id`, and `timestamp` are not None.

---

### EventEmitterBase
<!-- src: panther/core/events/base/event_emitter_base.py -->

```python
class EventEmitterBase(ABC)
```

Abstract base class for domain-specific event emitters.

**Description:** Provides event emission coordination through the EventManager.

**Constructor:**

```python
EventEmitterBase(event_manager: EventManager, entity_id: str = None)
```

**Attributes:**
- `event_manager: EventManager` - Event manager to emit events through
- `entity_id: Optional[str]` - Optional entity identifier for emitted events

**Methods:**

#### `_emit_event(event: BaseEvent) -> None`
Emit an event through the event manager (calls `event_manager.notify(event)`).

#### `_create_and_emit_event(event_class: Type, **kwargs) -> None`
Create an event from the given class with kwargs and emit it. Automatically injects `entity_id` into the appropriate ID field name (e.g., `experiment_id`, `service_id`) if not already provided.

#### `_validate_required_fields(**kwargs) -> None`
Validate that no required fields are None. Raises `ValueError` if any are missing.

### EntityEventEmitterBase
<!-- src: panther/core/events/base/event_emitter_base.py -->

```python
class EntityEventEmitterBase(EventEmitterBase)
```

Base class for entity-specific event emitters.

**Constructor:**

```python
EntityEventEmitterBase(event_manager: EventManager, entity_id: str, entity_type: str)
```

**Methods:**

#### `_create_and_emit_entity_event(event_class: Type, **kwargs) -> None`
Create and emit an entity-specific event, ensuring the entity ID field (e.g., `{entity_type}_id`) is always included in kwargs.

---

### EventEmitter
<!-- src: panther/core/events/base/event_emitter.py -->

```python
class EventEmitter
```

Simple event emitter that uses `EventManager.get_instance()` as default.

**Constructor:**

```python
EventEmitter(event_manager: Optional[EventManager] = None)
```

**Methods:**

#### `emit_event(event: BaseEvent) -> None`
Emit a typed event via `event_manager.publish(event)`.

---

### StateManager
<!-- src: panther/core/events/base/state_base.py -->

```python
class StateManager(ABC)
```

Abstract base state manager for managing entity state transitions.

**Constructor:**

```python
StateManager(entity_id: str, initial_state: BaseState)
```

**Attributes:**
- `entity_id: str` - Unique identifier for the entity
- `current_state: BaseState` - Current entity state
- `state_history: List[StateTransition]` - Full transition history
- `allowed_transitions: Dict[BaseState, Set[BaseState]]` - Allowed state transitions (populated by `setup_transitions()`)
- `logger: logging.Logger` - Logger instance

**Abstract Methods:**

#### `_define_allowed_transitions() -> Dict[BaseState, Set[BaseState]]`
Define allowed state transitions for this entity type. Must be implemented by subclasses.

**Methods:**

#### `setup_transitions() -> None`
Call `_define_allowed_transitions()` and store the result.

#### `get_current_state() -> BaseState`
Get the current state.

#### `get_state_history() -> List[StateTransition]`
Get a copy of the complete state transition history.

#### `can_transition_to(target_state: BaseState) -> bool`
Check if transition to target state is allowed from current state.

#### `transition_to(target_state: BaseState, trigger: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool`
Attempt to transition to a new state. Returns True if successful, False if the transition is not allowed.

#### `is_in_state(state: BaseState) -> bool`
Check if currently in the specified state.

#### `is_in_any_state(states: Set[BaseState]) -> bool`
Check if currently in any of the specified states.

#### `get_time_in_current_state() -> Optional[float]`
Get time spent in current state in seconds.

#### `get_last_transition() -> Optional[StateTransition]`
Get the most recent state transition.

#### `reset_to_initial_state(initial_state: BaseState) -> None`
Reset to initial state and clear history.

### BaseState
<!-- src: panther/core/events/base/state_base.py -->

```python
class BaseState(Enum)
```

Base state enumeration. Entity-specific states should inherit from this.

### StateTransition
<!-- src: panther/core/events/base/state_base.py -->

```python
class StateTransition
```

Represents a state transition with metadata.

**Attributes:**
- `from_state: BaseState` - State transitioned from
- `to_state: BaseState` - State transitioned to
- `timestamp: datetime` - When the transition occurred
- `trigger: Optional[str]` - What triggered the transition
- `metadata: Dict[str, Any]` - Additional transition metadata

---

### EmitterRegistry
<!-- src: panther/core/events/emitter_registry.py -->

```python
class EmitterRegistry
```

Centralized registry for all event emitters with state validation.

**Constructor:**

```python
EmitterRegistry(event_manager: EventManager)
```

**Emitter Instances (created in `__init__`):**
- `experiment_emitter: ExperimentEventEmitter`
- `service_emitter: ServiceEventEmitter`
- `environment_emitter: EnvironmentEventEmitter`
- `step_emitter: StepEventEmitter`
- `plugin_emitter: PluginEventEmitter`
- `assertion_emitter: AssertionEventEmitter`
- `metrics_emitter: MetricsEventEmitter`
- `test_emitters: Dict[str, TestEventEmitter]` - Created on demand per test

**State Manager Instances:**
- `experiment_state: Optional[ExperimentStateManager]` - Created on demand
- `plugin_state: PluginStateManager`
- `environment_states: Dict[str, EnvironmentStateManager]` - Per environment
- `service_states: Dict[str, ServiceStateManager]` - Per service
- `test_states: Dict[str, TestStateManager]` - Per test

**Key Methods:**

#### `get_emitter(emitter_type: str, test_name: str = "default_test")`
Get an emitter by type string: `"experiment"`, `"service"`, `"environment"`, `"step"`, `"plugin"`, `"assertion"`, `"metrics"`, `"test"`.

#### `get_test_emitter(test_name: str) -> TestEventEmitter`
Get or create a test-specific emitter.

#### `get_experiment_state(experiment_id: str) -> ExperimentStateManager`
Get or create the experiment state manager.

#### `get_service_state(service_id: str) -> ServiceStateManager`
Get or create a service-specific state manager.

#### `get_test_state(test_id: str) -> TestStateManager`
Get or create a test-specific state manager.

#### `get_environment_state(env_id: str) -> EnvironmentStateManager`
Get or create an environment-specific state manager.

#### `emit_service_created_with_validation(service_id, service_name, service_type, implementation, config=None) -> bool`
Emit service created event with state validation.

#### `emit_test_started_with_validation(test_id, test_name, test_description=None, expected_duration=None) -> bool`
Emit test started event with state validation.

#### `emit_test_completed_with_validation(test_id, test_name, success, duration=None, results=None) -> bool`
Emit test completed event with state validation.

#### `cleanup_test_emitter(test_name: str)`
Remove a test-specific emitter after test completion to prevent memory leaks.

#### `cleanup_service_state(service_id: str)`
Remove a service-specific state manager after cleanup.

#### `cleanup_environment_state(env_id: str)`
Remove an environment-specific state manager after cleanup.

#### `get_all_emitters() -> Dict[str, object]`
Get all emitters for debugging or inspection.

#### `get_all_state_managers() -> Dict[str, object]`
Get all state managers for debugging or inspection.

---

## Domain Event Classes

### EventType Enum
<!-- src: panther/core/events/base/event_base.py -->

```python
class EventType(Enum):
    EXPERIMENT = "experiment"
    TEST = "test"
    SERVICE = "service"
    ENVIRONMENT = "environment"
    SYSTEM = "system"
    METRICS = "metrics"
    STEP = "step"
    ASSERTION = "assertion"
    PLUGIN = "plugin"
```

---

### Test Events
<!-- src: panther/core/events/test/events.py -->

#### TestEventType

```python
class TestEventType(Enum):
    CREATED = "created"
    SETUP_STARTED = "setup_started"
    SETUP_COMPLETED = "setup_completed"
    SETUP_FAILED = "setup_failed"
    ENVIRONMENT_SETUP_STARTED = "environment_setup_started"
    ENVIRONMENT_SETUP_COMPLETED = "environment_setup_completed"
    ENVIRONMENT_SETUP_FAILED = "environment_setup_failed"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    EXECUTION_STARTED = "execution_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    ASSERTIONS_STARTED = "assertions_started"
    ASSERTION_CHECKED = "assertion_checked"
    ASSERTIONS_COMPLETED = "assertions_completed"
    ASSERTIONS_FAILED = "assertions_failed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    TEARDOWN_STARTED = "teardown_started"
    TEARDOWN_COMPLETED = "teardown_completed"
    COMPLETED = "completed"
    FAILED = "failed"
```

#### TestEvent

Base class for all test events. Constructor: `TestEvent(event_type: TestEventType, test_id: str, data=None)`.

#### Concrete Test Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `TestCreatedEvent` | `test_id, test_name, description=None, config=None` |
| `TestSetupStartedEvent` | `test_id, service_count=None, service_names=None` |
| `TestSetupCompletedEvent` | `test_id, services=None, duration_seconds=None` |
| `TestSetupFailedEvent` | `test_id, error_message, error_type=None, failed_component=None` |
| `TestEnvironmentSetupStartedEvent` | `test_id, environment_type, environment_config=None` |
| `TestEnvironmentSetupCompletedEvent` | `test_id, environment_type, environment_details=None` |
| `TestEnvironmentSetupFailedEvent` | `test_id, environment_type, error_message, error_type=None` |
| `TestDeploymentStartedEvent` | `test_id, services_to_deploy=None` |
| `TestDeploymentCompletedEvent` | `test_id, deployed_services=None, deployment_details=None` |
| `TestDeploymentFailedEvent` | `test_id, error_message, failed_services=None, error_type=None` |
| `TestExecutionStartedEvent` | `test_id, steps=None, expected_duration=None` |
| `TestStepStartedEvent` | `test_id, step_name, step_type=None, step_config=None` |
| `TestStepCompletedEvent` | `test_id, step_name, duration_seconds=None, result=None` |
| `TestStepFailedEvent` | `test_id, step_name, error_message, error_type=None` |
| `TestAssertionsStartedEvent` | `test_id, assertions=None` |
| `TestAssertionCheckedEvent` | `test_id, assertion_type, assertion_config, passed, result=None` |
| `TestAssertionsCompletedEvent` | `test_id, total_assertions, passed_assertions, failed_assertions, all_passed` |
| `TestAssertionsFailedEvent` | `test_id, error_message, error_type=None` |
| `TestExecutionCompletedEvent` | `test_id, duration_seconds=None, steps_completed=None, assertions_passed=None` |
| `TestExecutionFailedEvent` | `test_id, error_message, error_type=None, phase=None` |
| `TestTeardownStartedEvent` | `test_id` |
| `TestTeardownCompletedEvent` | `test_id, duration_seconds=None` |
| `TestCompletedEvent` | `test_id, test_name=None, total_duration_seconds=None, summary=None` |
| `TestFailedEvent` | `test_id, test_name=None, error_message="", error_type=None, phase=None, summary=None` |
| `TestResultEvent` | `name, test_name, result: bool, data=None, metadata=None` |
| `EnhancedResultEvent` | `name, test_name, result: bool, result_data=None, metadata=None, tags=None, category="default"` |

---

### Service Events
<!-- src: panther/core/events/service/events.py -->

#### ServiceEventType

```python
class ServiceEventType(Enum):
    CREATED = "created"
    PREPARATION_STARTED = "preparation_started"
    PREPARATION_COMPLETED = "preparation_completed"
    PREPARATION_FAILED = "preparation_failed"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    STARTED = "started"
    READY = "ready"
    HEALTH_CHECK_PASSED = "health_check_passed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"
    TEST_RESULTS = "test_results"
```

#### Concrete Service Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `ServiceCreatedEvent` | `service_id, service_name, service_type, implementation, config=None` |
| `ServicePreparationStartedEvent` | `service_id, service_name, preparation_steps=None` |
| `ServicePreparationCompletedEvent` | `service_id, service_name, duration_seconds=None, artifacts=None` |
| `ServicePreparationFailedEvent` | `service_id, service_name, error_message, error_type=None, failed_step=None` |
| `ServiceDeploymentStartedEvent` | `service_id, service_name, environment, deployment_config=None` |
| `ServiceDeploymentCompletedEvent` | `service_id, service_name, environment, endpoint=None, ports=None, deployment_details=None` |
| `ServiceDeploymentFailedEvent` | `service_id, service_name, environment, error_message, error_type=None` |
| `ServiceStartedEvent` | `service_id, service_name, pid=None, start_time=None` |
| `ServiceReadyEvent` | `service_id, service_name, readiness_checks=None` |
| `ServiceHealthCheckPassedEvent` | `service_id, service_name, check_type, endpoint=None, response_time_ms=None` |
| `ServiceHealthCheckFailedEvent` | `service_id, service_name, check_type, error_message, endpoint=None, status_code=None` |
| `ServiceStoppedEvent` | `service_id, service_name, exit_code=None, reason=None, uptime_seconds=None` |
| `ServiceErrorEvent` | `service_id, service_name, error_message, error_type=None, error_details=None` |
| `ServiceDestroyedEvent` | `service_id, service_name, cleanup_details=None` |
| `ServiceTestResultsEvent` | `service_id, service_name, test_results, overall_success, test_summary=None` |
| `CommandGenerationStartedEvent` | `service_id, service_name, phase, config=None` |
| `CommandGeneratedEvent` | `service_id, service_name, phase, command, command_type=None` |
| `CommandModifiedEvent` | `service_id, service_name, phase, original_command, modified_command, modifier, modification_details=None` |
| `DockerBuildStartedEvent` | `service_id, service_name, dockerfile_path, image_name=None` |
| `DockerBuildCompletedEvent` | `service_id, service_name, image_name, success, error_message=None, build_duration=None` |
| `DockerBuildFailedEvent` | `service_id, service_name, dockerfile_path, error_message, build_duration=None` |
| `ConfigGeneratedEvent` | `service_id, config_type, config_path, config_content=None, services_included=None` |
| `TesterAnalysisStartedEvent` | `service_id, tester_name, inputs, analysis_type` |
| `TesterAnalysisCompletedEvent` | `service_id, tester_name, passed, failed_checks, warnings=None, detailed_results=None` |

---

### Experiment Events
<!-- src: panther/core/events/experiment/events.py -->

#### ExperimentEventType

```python
class ExperimentEventType(Enum):
    INITIALIZED = "initialized"
    PLUGIN_LOADING_STARTED = "plugin_loading_started"
    PLUGIN_LOADING_COMPLETED = "plugin_loading_completed"
    PLUGIN_LOADING_FAILED = "plugin_loading_failed"
    TEST_CASES_INITIALIZED = "test_cases_initialized"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    FINISHED_EARLY = "finished_early"
    SERVICE_FAILURE = "service_failure"
    COMPLETED = "completed"
    FAILED = "failed"
```

#### Concrete Experiment Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `ExperimentInitializedEvent` | `experiment_id, config=None` |
| `ExperimentPluginLoadingStartedEvent` | `experiment_id, plugin_count=None` |
| `ExperimentPluginLoadingCompletedEvent` | `experiment_id, loaded_plugins=None, plugin_count=None` |
| `ExperimentPluginLoadingFailedEvent` | `experiment_id, error_message, error_type=None, failed_plugins=None` |
| `ExperimentTestCasesInitializedEvent` | `experiment_id, test_count, test_names=None` |
| `ExperimentExecutionStartedEvent` | `experiment_id, test_count=None` |
| `ExperimentExecutionCompletedEvent` | `experiment_id, success_count, failure_count, total_count, duration_seconds=None` |
| `ExperimentExecutionFailedEvent` | `experiment_id, error_message, error_type=None, phase=None` |
| `ExperimentFinishedEarlyEvent` | `experiment_id, reason, details=None` |
| `ExperimentCompletedEvent` | `experiment_id, summary=None` |
| `ExperimentFailedEvent` | `experiment_id, error_message, error_type=None, summary=None` |
| `ExperimentServiceFailureEvent` | `experiment_id, failed_service, reason, details=None` |

---

### Metrics Events
<!-- src: panther/core/events/metrics/events.py -->

#### MetricsEventType

```python
class MetricsEventType(Enum):
    COLLECTED = "collected"
    RESOURCE = "resource"
    TIMING = "timing"
    COUNTER = "counter"
    SUMMARY = "summary"
```

#### Concrete Metrics Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `MetricCollectedEvent` | `metric_name, metric_type, value, phase=None, test_case=None, component=None, labels=None, metadata=None` |
| `ResourceMetricEvent` | `resource_type, usage_value, component=None, test_case=None, metadata=None` |
| `TimingMetricEvent` | `operation_name, duration, phase=None, test_case=None, component=None, metadata=None` |
| `CounterMetricEvent` | `counter_name, value, increment=True, test_case=None, component=None, metadata=None` |
| `MetricsSummaryEvent` | `metrics, test_case=None, period=None, metadata=None` |

---

### Environment Events
<!-- src: panther/core/events/environment/events.py -->

Environment events use a different constructor pattern. The base `EnvironmentEvent` takes `(name, environment_id, environment_name, environment_type, data=None)` directly.

#### Concrete Environment Event Classes (partial list of key classes)

| Class | Constructor Params |
|-------|-------------------|
| `EnvironmentCreatedEvent` | `environment_id, environment_name, environment_type, config=None` |
| `EnvironmentSetupStartedEvent` | `environment_id, environment_name, environment_type, setup_config=None` |
| `EnvironmentSetupCompletedEvent` | `environment_id, environment_name, environment_type, duration, resources_allocated=None` |
| `EnvironmentSetupFailedEvent` | `environment_id, environment_name, environment_type, error_message, error_details=None` |
| `EnvironmentTeardownStartedEvent` | `environment_id, environment_name, environment_type, teardown_reason="test_completed"` |
| `EnvironmentTeardownCompletedEvent` | `environment_id, environment_name, environment_type, duration, resources_released=None` |
| `EnvironmentErrorEvent` | `environment_id, environment_name, environment_type, error_message, error_type="unknown", error_details=None, recovery_possible=False` |
| `NetworkSetupStartedEvent` | `environment_id, environment_name, environment_type, network_config=None, interfaces=None` |
| `NetworkSetupCompletedEvent` | `environment_id, environment_name, environment_type, network_config=None, allocated_resources=None, duration=None` |

---

### Step Events
<!-- src: panther/core/events/step/events.py -->

#### StepEventType

```python
class StepEventType(Enum):
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    PROGRESS = "progress"
    UNSUPPORTED = "unsupported"
    SKIPPED = "skipped"
```

#### Concrete Step Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `StepExecutionStartedEvent` | `step_id, step_name, test_case_id=None, step_config=None, prerequisites=None` |
| `StepExecutionCompletedEvent` | `step_id, step_name, test_case_id=None, duration=None, result=None, output=None` |
| `StepExecutionFailedEvent` | `step_id, step_name, test_case_id=None, error_message="", error_details=None, duration=None, retry_count=0` |
| `StepProgressEvent` | `step_id, step_name, test_case_id=None, progress_percentage=None, progress_message="", current_operation=None` |
| `StepUnsupportedEvent` | `step_id, step_name, test_case_id=None, reason="", alternative_steps=None` |
| `StepSkippedEvent` | `step_id, step_name, test_case_id=None, skip_reason="", skip_condition=None` |

---

### Plugin Events
<!-- src: panther/core/events/plugin/events.py -->

#### PluginEventType

```python
class PluginEventType(Enum):
    LOADING_STARTED = "loading_started"
    LOADING_COMPLETED = "loading_completed"
    LOADING_FAILED = "loading_failed"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    SERVICE_CREATED = "service_created"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    ENVIRONMENT_CREATED = "environment_created"
    ENVIRONMENT_READY = "environment_ready"
    ENVIRONMENT_DESTROYED = "environment_destroyed"
```

#### Concrete Plugin Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `PluginLoadingStartedEvent` | `plugin_id, plugin_name, plugin_type, plugin_path=None, loading_config=None` |
| `PluginLoadingCompletedEvent` | `plugin_id, plugin_name, plugin_type, duration=None, capabilities=None, version=None` |
| `PluginLoadingFailedEvent` | `plugin_id, plugin_name, plugin_type, error_message="", error_details=None, duration=None` |
| `PluginInitializedEvent` | `plugin_id, plugin_name, plugin_type, initialization_config=None, dependencies=None` |
| `PluginStartedEvent` | `plugin_id, plugin_name, plugin_type, startup_duration=None, startup_details=None` |
| `PluginStoppedEvent` | `plugin_id, plugin_name, plugin_type, stop_reason="normal_shutdown", cleanup_duration=None, cleanup_details=None` |
| `PluginErrorEvent` | `plugin_id, plugin_name, plugin_type, error_message="", error_type="unknown", error_details=None, recoverable=False` |
| `PluginServiceCreatedEvent` | `plugin_id, plugin_name, plugin_type, service_id, service_name, service_type, service_config=None` |
| `PluginServiceStartedEvent` | `plugin_id, plugin_name, plugin_type, service_id, service_name, startup_duration=None` |
| `PluginServiceStoppedEvent` | `plugin_id, plugin_name, plugin_type, service_id, service_name, stop_reason="normal_shutdown"` |
| `PluginLoadedEvent` | `plugin_id, plugin_name, plugin_type, plugin_path, metadata=None` |
| `ServiceManagerCreatedEvent` | `plugin_id, plugin_name, plugin_type, service_name, implementation, protocol, service_config=None` |

---

### Assertion Events
<!-- src: panther/core/events/assertion/events.py -->

#### AssertionEventType

```python
class AssertionEventType(Enum):
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    UNKNOWN = "unknown"
```

#### Concrete Assertion Event Classes

| Class | Constructor Params |
|-------|-------------------|
| `AssertionsValidationStartedEvent` | `assertion_id, assertion_name, test_case_id=None, step_id=None, total_assertions=None, validation_config=None` |
| `AssertionsValidationCompletedEvent` | `assertion_id, assertion_name, test_case_id=None, step_id=None, duration=None, passed_count=0, failed_count=0, total_count=0, summary=None` |
| `AssertionProgressEvent` | `assertion_id, assertion_name, test_case_id=None, step_id=None, current_assertion=None, total_assertions=None, progress_message=""` |
| `AssertionResultEvent` | `assertion_id, assertion_name, test_case_id=None, step_id=None, assertion_passed=False, expected_value=None, actual_value=None, assertion_message="", assertion_details=None` |
| `AssertionErrorEvent` | `assertion_id, assertion_name, test_case_id=None, step_id=None, error_message="", error_type="unknown", error_details=None, recoverable=False` |
| `AssertionUnknownEvent` | `assertion_id, assertion_name, test_case_id=None, step_id=None, reason="", context=None` |

---

## Utility Functions

### create_content_based_uuid
<!-- src: panther/core/events/base/event_base.py -->

```python
def create_content_based_uuid(content: str) -> str
```

Generate deterministic UUID from content for deduplication. Uses UUID5 with the standard namespace OID.

### create_event_signature
<!-- src: panther/core/events/base/event_base.py -->

```python
def create_event_signature(
    name: str,
    entity_type: str,
    entity_id: str,
    data: Dict[str, Any] = None
) -> str
```

Create a deterministic signature string for event deduplication. Excludes timestamps to allow duplicate detection of identical events. Returns `"{entity_type}:{name}:{entity_id}:{sorted_data}"`.
