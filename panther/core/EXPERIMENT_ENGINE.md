# Core Engine — Experiment Orchestration 🔧

**Purpose:** Central experiment management and test execution coordination
**Components:** `ExperimentManager`, `ExperimentStrategy`, `TestCase` implementations
**Dependencies:** Configuration system, plugin loader, observer pattern

The PANTHER core engine orchestrates the complete testing lifecycle from configuration loading through test execution and result collection.

---

## Architecture Overview

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/experiment_manager.py
class ExperimentManager:
    """
    Manages the lifecycle of an experiment, including initialization, configuration,
    and execution of test cases.
    """
```

### Core Flow

1. **Configuration Loading** → Load and validate experiment configuration
2. **Plugin Initialization** → Discover and initialize required plugins
3. **Environment Setup** → Prepare network and execution environments
4. **Test Execution** → Run test cases with progress tracking
5. **Result Collection** → Gather and process test outputs

---

## Key Components

### ExperimentManager

**Location:** `panther/core/experiment_manager.py`

Central coordinator that manages the complete experiment lifecycle:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/experiment_manager.py
def initialize_experiments(self, experiment_config: ExperimentConfig):
    """Initializes plugins, environment, and validates configuration."""

def run_tests(self):
    """Runs the tests defined in the experiment configuration."""
```

**Key Responsibilities:**

- Experiment directory creation and management
- Plugin loading and dependency resolution
- Test case initialization from configuration
- Execution coordination with progress tracking
- Error handling and cleanup operations

### Test Case System

**Location:** `panther/core/test_cases/`

Provides the testing framework interface:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/test_cases/test_interface_impl.py
class ITestCase:
    """Interface for test case implementations"""

# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/test_cases/test_case_impl.py
class TestCase(ITestCase):
    """Concrete test case implementation with plugin integration"""
```

**Features:**

- Plugin-based service instantiation
- Environment setup and teardown
- Test execution with timeout handling
- Result collection and validation

---

## Usage Patterns

### Basic Experiment Execution

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Load configuration
config_loader = ConfigLoader(experiment_config_path, output_dir)
global_config = config_loader.load_and_validate_global_config()

# Create experiment manager
experiment_manager = ExperimentManager(
    global_config=global_config,
    experiment_name=experiment_name
)

# Initialize and run
experiment_config = config_loader.load_and_validate_experiment_config()
experiment_manager.initialize_experiments(experiment_config)
experiment_manager.run_tests()
```

### Custom Test Strategy

Experiments can use different execution strategies via `ExperimentStrategy`:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/experiment_strategy.py
# Custom strategies for different testing approaches
# - Sequential execution
# - Parallel execution
# - Conditional execution based on previous results
```

---

## Integration Points

### With Configuration System

- Validates experiment configuration schemas
- Resolves plugin dependencies and paths
- Manages output directory structure

### With Plugin System

- Dynamically loads required plugins
- Handles plugin lifecycle (setup/teardown)
- Manages plugin communication and data flow

### With Observer System

- Publishes experiment lifecycle events
- Coordinates between distributed components
- Enables real-time monitoring and logging

---

## Error Handling

The engine implements comprehensive error management:

- **Configuration Errors:** Invalid YAML, missing required fields
- **Plugin Errors:** Missing plugins, initialization failures
- **Runtime Errors:** Test timeouts, network failures, resource constraints
- **Cleanup Errors:** Environment teardown issues

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/exceptions/
# Custom exception hierarchy for different error types
```

---

## Extending the Engine

### Custom Test Cases

Implement `ITestCase` interface for specialized testing scenarios:

```python
from panther.core.test_cases.test_interface_impl import ITestCase

class CustomTestCase(ITestCase):
    def setup(self):
        # Custom setup logic

    def execute(self):
        # Custom test execution

    def teardown(self):
        # Custom cleanup
```

### Custom Execution Strategies

Extend `ExperimentStrategy` for specialized execution patterns.

### Debugging Tips

- Enable debug logging: `--log-level DEBUG`
- Use experiment validation: `panther --validate-config`
- Check plugin loading: Inspect experiment manager initialization logs

---

**Related Documentation:**

- [Configuration System](panther/config/README.md) — How configurations drive experiment behavior
- [CLI Interface](panther/README.md) — Command-line options and workflows
- [Observer Pattern](panther/core/observer/README.md) — Event-driven architecture
