# PANTHER Tester Services API Reference

## Overview

PANTHER Tester Services provide formal verification and protocol testing capabilities through a modular, mixin-based architecture. This API reference covers the core interfaces, implementations, and integration patterns for developing and using tester services.

## Core Interfaces

### ITesterManager

The primary interface for all tester service managers, extending the base `IServiceManager`.

```python
class ITesterManager(IServiceManager, ABC):
    """Interface for tester service managers with standardized test reporting."""

    def __init__(self, service_config_to_test: ServiceConfig, service_type: str,
                 protocol: ProtocolConfig, implementation_name: str,
                 event_manager: Optional[EventManager] = None,
                 test_case: Optional[Any] = None):
        """Initialize tester manager with configuration and context."""
```

#### Key Methods

**`run_tests() -> Dict[str, Any]`**

Execute tests with proper event notifications and error handling.

```python
def run_tests(self):
    """
    Run tests with proper event notifications.

    Returns:
        Dict: Test results containing success status and detailed outcomes

    Raises:
        Exception: Test execution failures are propagated after event emission
    """
```

**`_do_run_tests() -> Dict[str, Any]`** *(Abstract)*

Actual test implementation to be overridden by subclasses.

```python
@abstractmethod
def _do_run_tests(self):
    """
    Actual implementation of test running.

    Returns:
        Dict: Test results containing at minimum a 'success' key with boolean value
    """
```

**`set_collected_outputs(outputs: Dict[str, Dict[str, str]]) -> None`** *(Abstract)*

Set outputs collected from execution environments for analysis.

```python
@abstractmethod
def set_collected_outputs(self, outputs: Dict[str, Dict[str, str]]) -> None:
    """
    Set outputs collected from execution environments.

    Args:
        outputs: Dictionary organized by output type, then by environment
                Example: {
                    "trace": {"strace": "/path/to/trace.out"},
                    "cpu_profile": {"gperf_cpu": "/path/to/profile.data"}
                }
    """
```

**`analyze_outputs() -> Dict[str, Any]`** *(Abstract)*

Analyze collected outputs to determine test outcomes.

```python
@abstractmethod
def analyze_outputs(self) -> Dict[str, Any]:
    """
    Analyze collected outputs from execution environments.

    Returns:
        Dict[str, Any]: Analysis results including:
            - passed: bool - Whether analysis passed
            - failed_checks: List[str] - List of failed checks
            - warnings: List[str] - List of warnings
            - detailed_results: dict - Detailed analysis results
            - analysis_summary: str - Human-readable summary
    """
```

**`get_test_results() -> Dict[str, Any]`** *(Abstract)*

Get final test results after analysis.

```python
@abstractmethod
def get_test_results(self) -> Dict[str, Any]:
    """
    Get final test results after analysis.

    Returns:
        Dict[str, Any]: Complete test results including:
            - passed: bool - Overall test success
            - execution_results: dict - Results from test execution
            - analysis_results: dict - Results from output analysis
            - summary: str - Overall summary
    """
```

## Event System

### TesterManagerEventMixin

Provides standardized event emission for tester services.

```python
class TesterManagerEventMixin(ServiceManagerEventMixin):
    """Mixin providing standardized event emission methods for tester plugins."""

    def emit_test_starting(self, test_id: str, test_type: str,
                          details: Dict[str, Any] = None) -> None:
        """Emit test starting event."""

    def emit_test_completed(self, test_id: str, success: bool,
                           result: Dict[str, Any] = None,
                           error_message: Optional[str] = None,
                           details: Dict[str, Any] = None) -> None:
        """Emit test completion event."""
```

#### Event Types

**TestExecutionStartedEvent**
- Emitted when test execution begins
- Contains test ID and execution steps

**TestCompletedEvent**
- Emitted when test completes successfully
- Contains test results and summary

**TestFailedEvent**
- Emitted when test fails
- Contains error message and failure details

## PantherIvy Implementation

### PantherIvyServiceManager

Comprehensive formal verification tester using Microsoft Ivy framework.

```python
@register_plugin(
    plugin_type=PluginType.TESTER,
    name="panther_ivy",
    version="3.1.0",
    description="Ivy formal verification tester using mixin-based architecture",
    supported_protocols=["quic"],
    external_dependencies=["z3=4.8", "python=3.7"]
)
class PantherIvyServiceManager(
    TesterServiceManagerMixin,
    ServiceManagerDockerMixin,
    TesterManagerEventMixin,
    IvyCommandMixin,
    IvyAnalysisMixin,
    IvyOutputPatternMixin,
    IvyProtocolAwareMixin,
    IvyNetworkResolutionMixin,
    IvyBuildModeMixin,
    ErrorHandlerMixin
):
    """Mixin-based PantherIvy service manager with specialized functionality."""
```

#### Constructor

```python
def __init__(self, service_config_to_test: ServiceConfig, service_type: Any,
             protocol: ProtocolConfig, implementation_name: str,
             event_manager=None, global_config=None, test_case=None, **kwargs):
    """
    Initialize PantherIvy service manager with mixin-based architecture.

    Args:
        service_config_to_test: Ivy service configuration
        service_type: Type of service (should be 'TESTERS')
        protocol: Protocol configuration object
        implementation_name: Name of the implementation
        event_manager: Event manager instance (optional)
        global_config: Global configuration dictionary (optional)
        test_case: Reference to parent test case for execution environment access
    """
```

#### Key Methods

**`_do_run_tests() -> Dict[str, Any]`**

Execute Ivy formal verification tests.

```python
def _do_run_tests(self) -> Dict[str, Any]:
    """
    Execute Ivy tests and return results.

    Returns:
        Dict[str, Any]: Test execution results including:
            - success: bool - Test execution success
            - test_name: str - Name of executed test
            - role: str - Service role (client/server)
            - outputs: dict - Collected output files
            - analysis: dict - Analysis results
            - errors: list - Error messages if any
    """
```

**`analyze_outputs() -> Dict[str, Any]`**

Analyze Ivy test outputs using pattern matching.

```python
def analyze_outputs(self) -> Dict[str, Any]:
    """
    Analyze outputs using analysis mixin.

    Returns:
        Dict[str, Any]: Analysis results with success status and details
    """
```

**`collect_outputs() -> Dict[str, Any]`**

Collect service outputs using output pattern matching.

```python
def collect_outputs(self) -> Dict[str, Any]:
    """
    Collect service outputs using output pattern mixin.

    Returns:
        Dict[str, Any]: Collected outputs organized by pattern type
    """
```

#### Mixin Capabilities

**IvyCommandMixin**
- Command generation for Ivy compilation and execution
- Build mode management (debug, release, profiling)
- Parameter handling for optimization levels

**IvyAnalysisMixin**
- Output pattern matching for verification results
- Log analysis for error detection
- Success/failure determination based on Ivy output

**IvyOutputPatternMixin**
- Standardized output file collection
- Pattern-based file organization
- Protocol-specific output handling

**IvyProtocolAwareMixin**
- Protocol-specific configuration handling
- Model path resolution
- Version-aware protocol support

**IvyNetworkResolutionMixin**
- Network configuration for containerized testing
- Service discovery and resolution
- Protocol endpoint management

**IvyBuildModeMixin**
- Build mode configuration (standard, debug-asan, rel-lto, release-static-pgo)
- Optimization level management
- Compiler flag handling

## Configuration

### PantherIvyConfig

Configuration schema for Panther Ivy tester services.

```python
class PantherIvyConfig(ServicePluginConfig):
    """Configuration for Panther Ivy tester service."""

    name: str = Field(default="panther_ivy", description="Implementation name")
    type: ImplementationType = Field(default=ImplementationType.TESTERS)
    test: str = Field(default="", description="Test name for testers")
    use_system_models: bool = Field(default=False, description="Use system models")

    # Build and execution parameters
    tests_output_dir: str = Field(default="temp/")
    tests_build_dir: str = Field(default="build/")
    iterations_per_test: int = Field(default=1)
    internal_iterations_per_test: int = Field(default=300)
    timeout: int = Field(default=120)

    # Debugging and optimization
    build_mode: Optional[str] = Field(default=None)
    log_level_events: str = Field(default="DEBUG")
    log_level_binary: str = Field(default="DEBUG")
    optimization_level: str = Field(default=None)
```

#### Build Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `""` (empty) | Original/Shadow compatible | Standard testing |
| `debug-asan` | Debug with AddressSanitizer | Memory debugging |
| `rel-lto` | Release with Link Time Optimization | Performance testing |
| `release-static-pgo` | Release with Profile Guided Optimization | Production benchmarks |

#### Environment Variables

Core environment variables automatically configured:

```python
DEFAULT_ENVIRONMENT_VARIABLES = {
    "PROTOCOL_TESTED": "",           # Target protocol name
    "IVY_DEBUG": "1",               # Enable Ivy debugging
    "SOURCE_DIR": "/opt/",          # Base source directory
    "IVY_DIR": "$SOURCE_DIR/panther_ivy",  # Ivy installation
    "PROTOCOL_PATH": "$PANTHER_IVY_BASE_PATH/$PROTOCOL_TESTED",
    # Certificate and key paths
    "PANTHER_IVY_CERT_PATH": "$PANTHER_IVY_BASE_PATH/$PROTOCOL_TESTED/leaf_cert.pem",
    "PANTHER_IVY_KEY_PATH": "$PANTHER_IVY_BASE_PATH/$PROTOCOL_TESTED/leaf_cert.key"
}
```

### AvailableTests

Dynamic test discovery from protocol testing directories.

```python
class AvailableTests(BaseModel):
    """Container for available Ivy tests with auto-discovery."""

    tests: List[Dict[str, str]] = Field(default_factory=list)

    @staticmethod
    def load_tests_from_directory(tests_dir: str) -> "AvailableTests":
        """
        Load all Ivy files from protocol-testing folders.

        Args:
            tests_dir: Directory to scan for .ivy test files

        Returns:
            AvailableTests: Discovered test definitions
        """
```

## Command Generation

### Command Methods

The PantherIvy service manager provides comprehensive command generation:

**Pre-compilation Commands**
```python
def generate_pre_compile_commands(self) -> List[Union[str, ShellCommand]]:
    """Generate environment setup and dependency installation commands."""
```

**Compilation Commands**
```python
def generate_compile_commands(self) -> List[Union[str, ShellCommand]]:
    """Generate Ivy test compilation commands with build mode support."""
```

**Runtime Commands**
```python
def generate_run_command(self) -> Dict[str, Any]:
    """
    Generate test execution command.

    Returns:
        Dict containing:
            - working_dir: str - Execution directory
            - command_binary: str - Test executable path
            - command_args: List[str] - Command arguments
            - timeout: int - Execution timeout
            - command_env: Dict - Additional environment variables
    """
```

**Post-execution Commands**
```python
def generate_post_run_commands(self) -> List[Union[str, ShellCommand]]:
    """Generate output collection and cleanup commands."""
```

## Usage Examples

### Basic Tester Usage

```python
from panther.plugins.services.testers.panther_ivy import PantherIvyServiceManager
from panther.config.core.models import ProtocolConfig
from panther.config.core.models.service import ServiceConfig

# Create protocol configuration
protocol = ProtocolConfig(name="quic", role="server")

# Create service configuration
service_config = ServiceConfig(
    name="ivy_quic_server_test",
    implementation="panther_ivy",
    plugin_config={
        "test": "quic_server_test_connect",
        "build_mode": "debug-asan",
        "log_level_binary": "DEBUG"
    }
)

# Initialize tester
tester = PantherIvyServiceManager(
    service_config_to_test=service_config,
    service_type="TESTERS",
    protocol=protocol,
    implementation_name="panther_ivy"
)

# Run tests
results = tester.run_tests()
print(f"Test success: {results['success']}")
```

### Advanced Configuration

```python
# Advanced configuration with custom parameters
service_config = ServiceConfig(
    name="ivy_performance_test",
    implementation="panther_ivy",
    plugin_config={
        "test": "quic_performance_test",
        "build_mode": "rel-lto",
        "optimization_level": "O3",
        "iterations_per_test": 5,
        "internal_iterations_per_test": 500,
        "timeout": 300,
        "use_system_models": False
    }
)

tester = PantherIvyServiceManager(
    service_config_to_test=service_config,
    service_type="TESTERS",
    protocol=protocol,
    implementation_name="panther_ivy"
)

# Set up external output collection
external_outputs = {
    "trace": {"strace": "/path/to/strace.out"},
    "cpu_profile": {"gperf_cpu": "/path/to/cpu.prof"}
}
tester.set_collected_outputs(external_outputs)

# Run with external outputs
results = tester.run_tests()
analysis = tester.get_test_results()
```

### Event-Driven Testing

```python
from panther.core.observer.base import Observer

class TestProgressObserver(Observer):
    def handle_event(self, event):
        if hasattr(event, 'test_id'):
            print(f"Test event: {event.__class__.__name__} for {event.test_id}")

# Set up event monitoring
observer = TestProgressObserver()
tester.event_manager.add_observer(observer)

# Events will be automatically emitted during test execution
results = tester.run_tests()
```

## Error Handling

### Exception Types

**Configuration Errors**
- Invalid test names
- Missing protocol models
- Incorrect build modes

**Execution Errors**
- Compilation failures
- Runtime timeouts
- Analysis parsing errors

**Environment Errors**
- Missing dependencies
- Docker setup issues
- File permission problems

### Error Recovery

```python
try:
    results = tester.run_tests()
except Exception as e:
    # Check if results are available despite error
    if hasattr(tester, 'final_analysis_res') and tester.final_analysis_res:
        partial_results = tester.get_test_results()
        print(f"Partial results available: {partial_results}")
    else:
        print(f"Test execution failed: {e}")
```

## Integration Patterns

### Output Collection Integration

```python
class OutputAggregator:
    def collect_all_outputs(self, testers: List[ITesterManager]):
        for tester in testers:
            outputs = self.collect_from_environments()
            tester.set_collected_outputs(outputs)

    def collect_from_environments(self) -> Dict[str, Any]:
        # Collect from execution environments
        return collected_outputs
```

### Multi-Protocol Testing

```python
protocols = ["quic", "tcp", "http3"]
results = {}

for protocol_name in protocols:
    protocol = ProtocolConfig(name=protocol_name)
    tester = PantherIvyServiceManager(
        service_config_to_test=service_config,
        service_type="TESTERS",
        protocol=protocol,
        implementation_name="panther_ivy"
    )
    results[protocol_name] = tester.run_tests()
```

## Best Practices

### Configuration Management
- Use version-specific configurations for protocol testing
- Specify build modes appropriate for testing goals
- Set appropriate timeouts for complex formal verification

### Performance Optimization
- Use `rel-lto` build mode for performance testing
- Adjust `internal_iterations_per_test` based on verification depth
- Monitor resource usage with execution environment profilers

### Debugging
- Enable `debug-asan` build mode for memory issue detection
- Use `DEBUG` log levels for detailed execution tracing
- Collect comprehensive outputs for post-mortem analysis

### Event Management
- Subscribe to relevant test events for progress monitoring
- Implement custom observers for metrics collection
- Use event-driven patterns for reactive test orchestration

## Related Documentation

- [Tester Services Overview](README.md) — General tester plugin architecture
- [Service Plugin Development](../development.md) — Creating custom tester plugins
- [Event System](../../../core/events/README.md) — Event-driven programming patterns
- [Configuration Management](../../../config/README.md) — Advanced configuration options

## References

- [Microsoft Ivy Framework](https://github.com/microsoft/ivy) — Formal verification framework
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/) — Configuration validation
- [Docker Compose](https://docs.docker.com/compose/) — Container orchestration
- [QUIC Protocol Specification](https://tools.ietf.org/html/rfc9000) — Protocol testing reference
