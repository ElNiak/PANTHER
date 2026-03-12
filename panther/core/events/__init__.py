"""Events Module - Event-Driven Architecture for PANTHER.

Provides a comprehensive, type-safe, hierarchical event system that enables
real-time monitoring, logging, and coordination across all testing components.
Events and states are organized by entity type (domain-driven design) for
clear separation of concerns.

Architecture::

    Event Producer --> BaseEvent --> EventEmitter --> EventManager --> Observers

    events/
    +-- base/                    # Foundation classes and interfaces
    |   +-- event_base.py       # BaseEvent, EventType, UUID generation
    |   +-- event_emitter_base.py  # EventEmitterBase, EntityEventEmitterBase
    |   +-- state_base.py       # BaseState, StateManager, StateTransition
    +-- {domain}/               # Domain-specific event implementations
    |   +-- events.py           # Event type definitions
    |   +-- states.py           # State management
    |   +-- emitter.py          # Event emission logic
    +-- emitter_registry.py     # Centralized emitter coordination + state validation
    +-- event_summarizer.py     # Log verbosity reduction via importance filtering

Event Categories:
    - **Test Events** -- Test lifecycle, execution, and result events
    - **Experiment Events** -- Experiment-level execution coordination
    - **Service Events** -- Service deployment, health, and lifecycle management
    - **Environment Events** -- Network and execution environment state changes
    - **Step Events** -- Individual test step execution tracking
    - **Assertion Events** -- Test assertion validation and results
    - **Plugin Events** -- Plugin loading, initialization, and lifecycle
    - **Metrics Events** -- Performance metrics collection and aggregation

Key Design Principles:
    - **Content-based UUID5** for deterministic event deduplication across
      distributed test environments (see `create_content_based_uuid()`)
    - **Entity-type partitioning** (test, service, environment, etc.)
    - **Mutable event data with UUID regeneration** -- ``add_data()`` mutates
      the data dict and regenerates the content-based UUID
    - **State tracking** -- Each domain maintains state managers that track
      entity lifecycle and enable workflow coordination
    - **Memory efficiency** -- ``__slots__`` in event classes, enum-based
      event types for O(1) filtering

Event Lifecycle:
    1. **Creation** -- Events created with deterministic UUIDs and timestamps
    2. **Emission** -- Domain emitters broadcast events to registered observers
    3. **Processing** -- Observers filter and handle relevant events
    4. **State Updates** -- State managers update entity status based on events
    5. **Persistence** -- Events stored for audit, debugging, and analytics

Example:
    Create and emit a custom event::

        from panther.core.events import BaseEvent, EventType

        event = BaseEvent(
            name="test.started",
            entity_type=EventType.TEST,
            entity_id="t1",
            data={"scenario": "handshake"},
        )
        assert event.id  # content-based UUID5
        assert event.validate()

    Use the EmitterRegistry for state-validated service events::

        from panther.core.events.emitter_registry import EmitterRegistry
        from panther.core.observer.management.event_manager import EventManager

        registry = EmitterRegistry(EventManager.get_instance())

        # Emit with state-machine validation (returns False if transition invalid).
        # Services start in CREATED state; transitions must follow the lifecycle.
        registry.emit_service_created_with_validation(
            service_id="svc-1", service_name="picoquic",
            service_type="iut", implementation="picoquic",
        )

        # Cleanup after service teardown
        registry.cleanup_service_state("svc-1")

    Creating custom event types (how-to)::

        from dataclasses import dataclass, field
        from enum import Enum
        from panther.core.events.base.event_base import BaseEvent

        class MyEventType(Enum):
            STARTED = "my_domain.started"
            COMPLETED = "my_domain.completed"
            FAILED = "my_domain.failed"

        @dataclass(frozen=True)
        class MyEvent(BaseEvent):
            context: dict = field(default_factory=dict)

            def __post_init__(self):
                object.__setattr__(self, 'event_type', MyEventType.STARTED)
                super().__post_init__()

See Also:
    `panther.core.observer` -- Observer pattern implementation
    `panther.core.events.emitter_registry` -- Centralized emitter coordination
"""

from panther.core.events.assertion import (
    AssertionErrorEvent,
    AssertionEvent,
    AssertionEventEmitter,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionState,
    AssertionsValidationCompletedEvent,
    AssertionsValidationStartedEvent,
    AssertionUnknownEvent,
)
from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.events.base.state_base import BaseState, StateManager
from panther.core.events.environment import (  # Deployment Events; Network Environment Events; Execution Environment Events; Output Collection Events
    EnvironmentConfigurationEvent,
    EnvironmentCreatedEvent,
    EnvironmentDeploymentCompletedEvent,
    EnvironmentDeploymentFailedEvent,
    EnvironmentDeploymentStartedEvent,
    EnvironmentDestroyedEvent,
    EnvironmentErrorEvent,
    EnvironmentEvent,
    EnvironmentEventEmitter,
    EnvironmentInitializationCompletedEvent,
    EnvironmentInitializationFailedEvent,
    EnvironmentInitializationStartedEvent,
    EnvironmentMonitoringEvent,
    EnvironmentReadyEvent,
    EnvironmentResourceEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentSetupFailedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentState,
    EnvironmentTeardownCompletedEvent,
    EnvironmentTeardownFailedEvent,
    EnvironmentTeardownStartedEvent,
    ExecutionEnvironmentEvent,
    ExecutionEnvironmentLimitExceededEvent,
    ExecutionEnvironmentResourceMonitoringEvent,
    ExecutionEnvironmentSetupCompletedEvent,
    ExecutionEnvironmentSetupStartedEvent,
    NetworkEnvironmentEvent,
    NetworkSetupCompletedEvent,
    NetworkSetupFailedEvent,
    NetworkSetupStartedEvent,
    NetworkTeardownCompletedEvent,
    NetworkTeardownStartedEvent,
    OutputCollectedEvent,
    OutputCollectionCompletedEvent,
    OutputCollectionStartedEvent,
)

# Entity-specific imports
from panther.core.events.experiment import (
    ExperimentCompletedEvent,
    ExperimentEvent,
    ExperimentEventEmitter,
    ExperimentExecutionCompletedEvent,
    ExperimentExecutionFailedEvent,
    ExperimentExecutionStartedEvent,
    ExperimentFailedEvent,
    ExperimentFinishedEarlyEvent,
    ExperimentInitializedEvent,
    ExperimentPluginLoadingCompletedEvent,
    ExperimentPluginLoadingFailedEvent,
    ExperimentPluginLoadingStartedEvent,
    ExperimentState,
    ExperimentTestCasesInitializedEvent,
)
from panther.core.events.metrics import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsEvent,
    MetricsEventEmitter,
    MetricsState,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)
from panther.core.events.plugin import (
    PluginErrorEvent,
    PluginEvent,
    PluginEventEmitter,
    PluginInitializedEvent,
    PluginLoadingCompletedEvent,
    PluginLoadingFailedEvent,
    PluginLoadingStartedEvent,
    PluginServiceCreatedEvent,
    PluginServiceStartedEvent,
    PluginServiceStoppedEvent,
    PluginStartedEvent,
    PluginState,
    PluginStoppedEvent,
)
from panther.core.events.service import (
    CommandGeneratedEvent,
    CommandGenerationStartedEvent,
    DockerBuildCompletedEvent,
    DockerBuildStartedEvent,
    ServiceCreatedEvent,
    ServiceDeploymentCompletedEvent,
    ServiceDeploymentFailedEvent,
    ServiceDeploymentStartedEvent,
    ServiceDestroyedEvent,
    ServiceErrorEvent,
    ServiceEvent,
    ServiceEventEmitter,
    ServiceHealthCheckFailedEvent,
    ServiceHealthCheckPassedEvent,
    ServicePreparationCompletedEvent,
    ServicePreparationFailedEvent,
    ServicePreparationStartedEvent,
    ServiceReadyEvent,
    ServiceStartedEvent,
    ServiceState,
    ServiceStoppedEvent,
    ServiceTestResultsEvent,
    TesterAnalysisCompletedEvent,
    TesterAnalysisStartedEvent,
)
from panther.core.events.step import (
    StepEvent,
    StepEventEmitter,
    StepExecutionCompletedEvent,
    StepExecutionFailedEvent,
    StepExecutionStartedEvent,
    StepProgressEvent,
    StepSkippedEvent,
    StepState,
    StepUnsupportedEvent,
)
from panther.core.events.test import (
    EnhancedResultEvent,
    TestAssertionCheckedEvent,
    TestAssertionsCompletedEvent,
    TestAssertionsFailedEvent,
    TestAssertionsStartedEvent,
    TestCompletedEvent,
    TestCreatedEvent,
    TestDeploymentCompletedEvent,
    TestDeploymentFailedEvent,
    TestDeploymentStartedEvent,
    TestEnvironmentSetupCompletedEvent,
    TestEnvironmentSetupFailedEvent,
    TestEnvironmentSetupStartedEvent,
    TestEvent,
    TestEventEmitter,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    TestExecutionStartedEvent,
    TestFailedEvent,
    TestResultEvent,
    TestSetupCompletedEvent,
    TestSetupFailedEvent,
    TestSetupStartedEvent,
    TestState,
    TestStepCompletedEvent,
    TestStepFailedEvent,
    TestStepStartedEvent,
    TestTeardownCompletedEvent,
    TestTeardownStartedEvent,
)

__all__ = [
    # Base classes
    "BaseEvent",
    "EventType",
    "BaseState",
    "StateManager",
    # Experiment
    "ExperimentState",
    "ExperimentEvent",
    "ExperimentEventEmitter",
    # Test
    "TestState",
    "TestEvent",
    "TestEventEmitter",
    "TestCreatedEvent",
    "TestSetupStartedEvent",
    "TestSetupCompletedEvent",
    "TestSetupFailedEvent",
    "TestEnvironmentSetupStartedEvent",
    "TestEnvironmentSetupCompletedEvent",
    "TestEnvironmentSetupFailedEvent",
    "TestDeploymentStartedEvent",
    "TestDeploymentCompletedEvent",
    "TestDeploymentFailedEvent",
    "TestExecutionStartedEvent",
    "TestStepStartedEvent",
    "TestStepCompletedEvent",
    "TestStepFailedEvent",
    "TestAssertionsStartedEvent",
    "TestAssertionCheckedEvent",
    "TestAssertionsCompletedEvent",
    "TestAssertionsFailedEvent",
    "TestExecutionCompletedEvent",
    "TestExecutionFailedEvent",
    "TestTeardownStartedEvent",
    "TestTeardownCompletedEvent",
    "TestCompletedEvent",
    "TestFailedEvent",
    "TestResultEvent",
    "EnhancedResultEvent",
    # Service
    "ServiceState",
    "ServiceEvent",
    "ServiceEventEmitter",
    "ServiceCreatedEvent",
    "ServicePreparationStartedEvent",
    "ServicePreparationCompletedEvent",
    "ServicePreparationFailedEvent",
    "ServiceDeploymentStartedEvent",
    "ServiceDeploymentCompletedEvent",
    "ServiceDeploymentFailedEvent",
    "ServiceStartedEvent",
    "ServiceReadyEvent",
    "ServiceHealthCheckPassedEvent",
    "ServiceHealthCheckFailedEvent",
    "ServiceStoppedEvent",
    "ServiceErrorEvent",
    "ServiceDestroyedEvent",
    "ServiceTestResultsEvent",
    "CommandGenerationStartedEvent",
    "CommandGeneratedEvent",
    "DockerBuildStartedEvent",
    "DockerBuildCompletedEvent",
    "TesterAnalysisStartedEvent",
    "TesterAnalysisCompletedEvent",
    # Environment
    "EnvironmentState",
    "EnvironmentEvent",
    "EnvironmentEventEmitter",
    "EnvironmentCreatedEvent",
    "EnvironmentInitializationStartedEvent",
    "EnvironmentInitializationCompletedEvent",
    "EnvironmentInitializationFailedEvent",
    "EnvironmentSetupStartedEvent",
    "EnvironmentSetupCompletedEvent",
    "EnvironmentSetupFailedEvent",
    "EnvironmentReadyEvent",
    "EnvironmentTeardownStartedEvent",
    "EnvironmentTeardownCompletedEvent",
    "EnvironmentTeardownFailedEvent",
    "EnvironmentDestroyedEvent",
    "EnvironmentErrorEvent",
    "EnvironmentResourceEvent",
    "EnvironmentConfigurationEvent",
    "EnvironmentMonitoringEvent",
    # Deployment
    "EnvironmentDeploymentStartedEvent",
    "EnvironmentDeploymentCompletedEvent",
    "EnvironmentDeploymentFailedEvent",
    # Network Environment
    "NetworkEnvironmentEvent",
    "NetworkSetupStartedEvent",
    "NetworkSetupCompletedEvent",
    "NetworkSetupFailedEvent",
    "NetworkTeardownStartedEvent",
    "NetworkTeardownCompletedEvent",
    # Execution Environment
    "ExecutionEnvironmentEvent",
    "ExecutionEnvironmentSetupStartedEvent",
    "ExecutionEnvironmentSetupCompletedEvent",
    "ExecutionEnvironmentResourceMonitoringEvent",
    "ExecutionEnvironmentLimitExceededEvent",
    # Output Collection
    "OutputCollectionStartedEvent",
    "OutputCollectedEvent",
    "OutputCollectionCompletedEvent",
    # Metrics
    "MetricsState",
    "MetricsEvent",
    "MetricsEventEmitter",
    "MetricCollectedEvent",
    "ResourceMetricEvent",
    "TimingMetricEvent",
    "CounterMetricEvent",
    "MetricsSummaryEvent",
    # Step
    "StepState",
    "StepEvent",
    "StepEventEmitter",
    "StepExecutionStartedEvent",
    "StepExecutionCompletedEvent",
    "StepExecutionFailedEvent",
    "StepProgressEvent",
    "StepUnsupportedEvent",
    "StepSkippedEvent",
    # Assertion
    "AssertionState",
    "AssertionEvent",
    "AssertionEventEmitter",
    "AssertionsValidationStartedEvent",
    "AssertionsValidationCompletedEvent",
    "AssertionProgressEvent",
    "AssertionResultEvent",
    "AssertionErrorEvent",
    "AssertionUnknownEvent",
    # Plugin
    "PluginState",
    "PluginEvent",
    "PluginEventEmitter",
    "PluginLoadingStartedEvent",
    "PluginLoadingCompletedEvent",
    "PluginLoadingFailedEvent",
    "PluginInitializedEvent",
    "PluginStartedEvent",
    "PluginStoppedEvent",
    "PluginErrorEvent",
    "PluginServiceCreatedEvent",
    "PluginServiceStartedEvent",
    "PluginServiceStoppedEvent",
]
