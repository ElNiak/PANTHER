# PANTHER Core API Reference

## ExperimentManager

Central orchestration class managing experiment lifecycle with event-driven coordination.

### Class Definition

```python
class ExperimentManager(ErrorHandlerMixin, ExperimentObserverMixin, ExperimentAnalysisMixin):
    """Orchestrate experiment lifecycle with event-driven coordination."""
```

### Constructor

```python
def __init__(
    self,
    global_config: GlobalConfig,
    experiment_name: Optional[str] = None,
    plugin_dir: Optional[Path] = None,
    logger: Optional[logging.Logger] = None,
    metrics_collector: Optional[MetricsCollector] = None,
    fast_fail_enabled: bool = True,
    dry_run: bool = False
) -> None
```

**Parameters:**
- `global_config` (GlobalConfig): Global configuration containing paths and defaults
- `experiment_name` (Optional[str]): Optional name for the experiment (sanitized automatically)
- `plugin_dir` (Optional[Path]): Directory containing plugin implementations
- `logger` (Optional[logging.Logger]): Optional logger instance (creates default if None)
- `metrics_collector` (Optional[MetricsCollector]): Optional metrics collection system
- `fast_fail_enabled` (bool): Whether to terminate on critical errors
- `dry_run` (bool): Execute in validation mode without running actual tests

**Raises:**
- `ExperimentInitializationError`: When configuration validation fails
- `PluginValidationError`: When required plugins cannot be loaded

### Public Methods

#### initialize_experiments

```python
def initialize_experiments(self, experiment_config: ExperimentConfig) -> None:
    """Initialize experiments from configuration.

    Args:
        experiment_config: Validated experiment configuration.

    Raises:
        TestCaseInitializationError: When test cases cannot be created.
    """
```

#### run_tests

```python
def run_tests(self) -> Dict[str, Any]:
    """Execute all configured test cases.

    Returns:
        dict: Execution results with test outcomes and metrics.

    Raises:
        TestExecutionError: When test execution fails.
    """
```

#### cleanup

```python
def cleanup(self) -> None:
    """Clean up resources and finalize experiment.

    Performs teardown of Docker containers, temporary files,
    and finalizes metric collection.
    """
```

#### add_observer

```python
def add_observer(self, observer: Observer) -> None:
    """Add observer for experiment events.

    Args:
        observer: Observer instance to receive events.
    """
```

### Properties

```python
@property
def experiment_dir(self) -> Path:
    """Get experiment output directory."""

@property
def test_cases(self) -> List[ITestCase]:
    """Get configured test cases."""

@property
def plugin_manager(self) -> PluginManager:
    """Get plugin management system."""

@property
def event_manager(self) -> EventManager:
    """Get event coordination system."""
```

### Context Manager Support

```python
def __enter__(self) -> "ExperimentManager":
    """Enter experiment context."""

def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
    """Exit experiment context with cleanup."""
```

**Example Usage:**
```python
with ExperimentManager(config) as manager:
    manager.initialize_experiments(exp_config)
    results = manager.run_tests()
    # Automatic cleanup on exit
```

## TestCase

Test execution engine with mixin-composed capabilities.

### Class Definition

```python
class TestCase(
    TestCaseConfigurationMixin,
    TestCaseExecutionMixin,
    TestCaseAnalysisMixin,
    TestCaseObserverMixin,
    TestCaseReportingMixin,
    TestCaseDockerMixin
):
    """Mixin-composed test execution engine."""
```

### Constructor

```python
def __init__(
    self,
    test_case_config: TestCaseConfig,
    global_config: GlobalConfig,
    plugin_manager: PluginManager,
    event_manager: EventManager,
    metrics_collector: MetricsCollector
) -> None
```

### Public Methods

#### run

```python
def run(self) -> TestResult:
    """Execute test case with full lifecycle management.

    Returns:
        TestResult: Comprehensive test execution results.

    Raises:
        TestExecutionError: When test execution fails.
    """
```

#### validate_configuration

```python
def validate_configuration(self) -> bool:
    """Validate test case configuration.

    Returns:
        bool: True if configuration is valid.

    Raises:
        ConfigurationException: When validation fails.
    """
```

### State Management

```python
@property
def state(self) -> TestCaseState:
    """Get current test case state."""

def transition_to(self, new_state: TestCaseState) -> None:
    """Transition to new state with validation."""
```

## Event System

### EventManager

Central event coordination system for component communication.

```python
class EventManager:
    """Central event coordination system."""

    def emit(self, event: Event) -> None:
        """Emit event to all subscribers."""

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to specific event type."""

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from event type."""
```

### Event Types

#### ExperimentEvent

```python
@dataclass
class ExperimentEvent(Event):
    """Experiment lifecycle events."""
    experiment_id: str
    phase: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

#### TestEvent

```python
@dataclass
class TestEvent(Event):
    """Test execution events."""
    test_case_id: str
    action: str
    status: str
    duration_ms: Optional[int] = None
```

#### ServiceEvent

```python
@dataclass
class ServiceEvent(Event):
    """Service management events."""
    service_name: str
    operation: str
    container_id: Optional[str] = None
    exit_code: Optional[int] = None
```

## Observer Pattern

### Observer Interface

```python
class Observer(ABC):
    """Base observer interface."""

    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """Handle incoming event."""
```

### Built-in Observers

#### MetricsObserver

```python
class MetricsObserver(Observer):
    """Observer for metrics collection."""

    def handle_event(self, event: Event) -> None:
        """Collect metrics from events."""
```

#### LoggingObserver

```python
class LoggingObserver(Observer):
    """Observer for structured logging."""

    def handle_event(self, event: Event) -> None:
        """Log events with structured format."""
```

#### StorageObserver

```python
class StorageObserver(Observer):
    """Observer for event persistence."""

    def handle_event(self, event: Event) -> None:
        """Store events to persistent storage."""
```

## Configuration Models

### GlobalConfig

```python
@dataclass
class GlobalConfig:
    """Global configuration model."""
    paths: Dict[str, str]
    plugins: Dict[str, Any]
    logging: Dict[str, Any]
    docker: Dict[str, Any]

    @classmethod
    def load(cls, config_path: str) -> "GlobalConfig":
        """Load configuration from file."""
```

### ExperimentConfig

```python
@dataclass
class ExperimentConfig:
    """Experiment configuration model."""
    name: str
    protocol: str
    test_cases: List[TestCaseConfig]
    network_environment: NetworkEnvironmentConfig
    execution_environment: ExecutionEnvironmentConfig

    def validate(self) -> bool:
        """Validate experiment configuration."""
```

### TestCaseConfig

```python
@dataclass
class TestCaseConfig:
    """Test case configuration model."""
    name: str
    implementation: str
    parameters: Dict[str, Any]
    timeout: int
    retry_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
```

## Metrics System

### MetricsCollector

```python
class MetricsCollector:
    """Central metrics collection system."""

    def record_timing(
        self,
        metric_name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record timing metric."""

    def record_counter(
        self,
        metric_name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record counter metric."""

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record gauge metric."""

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
```

## Plugin System Integration

### Plugin Interfaces

#### IPlugin

```python
class IPlugin(ABC):
    """Base plugin interface."""

    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name."""

    @abstractmethod
    def get_version(self) -> str:
        """Get plugin version."""

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
```

#### IProtocolPlugin

```python
class IProtocolPlugin(IPlugin):
    """Protocol plugin interface."""

    @abstractmethod
    def get_protocol_name(self) -> str:
        """Get protocol name."""

    @abstractmethod
    def create_test_scenario(self, config: Dict[str, Any]) -> TestScenario:
        """Create test scenario."""
```

#### IServicePlugin

```python
class IServicePlugin(IPlugin):
    """Service plugin interface."""

    @abstractmethod
    def create_service_manager(self, config: Dict[str, Any]) -> ServiceManager:
        """Create service manager."""

    @abstractmethod
    def get_docker_image(self) -> str:
        """Get Docker image name."""
```

## Exception Hierarchy

### Core Exceptions

```python
class PantherExperimentError(Exception):
    """Base exception for experiment errors."""

class ExperimentInitializationError(PantherExperimentError):
    """Exception raised during experiment initialization."""

class TestCaseInitializationError(PantherExperimentError):
    """Exception raised during test case initialization."""

class TestExecutionError(PantherExperimentError):
    """Exception raised during test execution."""

class PluginValidationError(PantherExperimentError):
    """Exception raised during plugin validation."""
```

### Fast-Fail Exceptions

```python
class ConfigurationException(Exception):
    """Configuration validation errors."""

class DockerComposeException(Exception):
    """Docker Compose operation errors."""

class ResourceExhaustionException(Exception):
    """System resource exhaustion errors."""

class TimeoutCascadeException(Exception):
    """Cascading timeout errors."""
```

## Usage Examples

### Basic Experiment

```python
from panther.core.experiment_manager import ExperimentManager
from panther.config.core.models import GlobalConfig

# Load configuration
config = GlobalConfig.load("global_config.yaml")

# Create experiment manager
manager = ExperimentManager(
    global_config=config,
    experiment_name="quic_performance_test"
)

# Initialize and run
manager.initialize_experiments(experiment_config)
results = manager.run_tests()
manager.cleanup()

print(f"Test success rate: {results['success_rate']}")
```

### With Custom Observer

```python
from panther.core.observer.base import Observer

class CustomMetricsObserver(Observer):
    def handle_event(self, event):
        if isinstance(event, TestEvent):
            # Custom metrics collection
            self.collect_custom_metrics(event)

# Add custom observer
manager = ExperimentManager(config)
manager.add_observer(CustomMetricsObserver())
manager.run_tests()
```

### Event-Driven Monitoring

```python
from panther.core.events.test import TestEvent

def test_completion_handler(event: TestEvent):
    if event.action == "completed":
        print(f"Test {event.test_case_id} completed: {event.status}")

# Subscribe to test events
manager.event_manager.subscribe("test.completed", test_completion_handler)
```

### Configuration Validation

```python
from panther.config.core.models import ExperimentConfig

# Validate configuration
try:
    config = ExperimentConfig.load("experiment.yaml")
    config.validate()
    print("Configuration is valid")
except ConfigurationException as e:
    print(f"Configuration error: {e}")
```

## Type Definitions

### Common Types

```python
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from datetime import datetime

# Result types
TestResult = Dict[str, Any]
ExperimentResult = Dict[str, Any]
MetricValue = Union[int, float, str]

# Configuration types
ConfigDict = Dict[str, Any]
ParameterDict = Dict[str, Union[str, int, float, bool]]

# Plugin types
PluginName = str
PluginVersion = str
PluginMetadata = Dict[str, Any]
```

### State Enums

```python
from enum import Enum

class TestCaseState(Enum):
    """Test case execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExperimentPhase(Enum):
    """Experiment execution phases."""
    INITIALIZATION = "initialization"
    PLUGIN_LOADING = "plugin_loading"
    SERVICE_SETUP = "service_setup"
    TEST_EXECUTION = "test_execution"
    CLEANUP = "cleanup"
```

---

**Related Documentation:**
- [Core Module README](README.md) — Architecture overview and design patterns
- [Developer Guide](DEVELOPER_GUIDE.md) — Development and debugging guide
- [Configuration Guide](../config/README.md) — Complete configuration reference
