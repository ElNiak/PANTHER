# PANTHER Core Framework

Central orchestration engine for PANTHER network protocol testing framework, implementing sophisticated experiment lifecycle management through event-driven architecture and plugin-based extensibility.

## Architecture Overview

The core module implements a multi-layered architecture combining several design patterns for enterprise-grade scalability and maintainability.

### Primary Components

**ExperimentManager** - Central facade orchestrating experiment lifecycle
- Event-driven coordination using EventManager + EmitterRegistry
- Observer pattern for pluggable monitoring and analysis
- Strategy pattern delegating to PluginManager for extensible execution
- Context manager pattern for automatic resource cleanup

**TestCase** - Mixin-composed test execution engine
- Six specialized mixins providing modular capability composition
- State machine with explicit transitions (PENDING → RUNNING → DONE)
- Docker orchestration for multi-service container management
- Comprehensive performance metrics and timing collection

**Plugin System** - Extensible execution backend
- Singleton PluginManager with thread-safe initialization
- Multi-level caching with TTL for performance optimization
- Protocol, service, and environment plugin types
- Docker integration with automated container building

### Design Philosophy

The core architecture employs enterprise-grade patterns for scalability and maintainability:

- **Event-Driven Architecture**: Central event bus coordinates all subsystem communication
- **Observer Pattern**: Pluggable observers for metrics, logging, and analysis
- **Strategy Pattern**: Pluggable algorithms for experiment execution strategies
- **Facade Pattern**: ExperimentManager provides unified interface to complex subsystems
- **Mixin Composition**: Modular capabilities through multiple inheritance

---

## Core Functional Groups

PANTHER's core is organized into focused functional groups, each with comprehensive documentation:

| Functional Group | Purpose | Documentation |
|------------------|---------|---------------|
| **Experiment Engine** | Test execution orchestration and lifecycle management | Core experiment coordination |
| **[Configuration System](../config/README.md)** | Schema-driven configuration loading and validation | Type-safe YAML configuration |
| **[Event System](events/README.md)** | Event-driven architecture with typed events | Entity-specific event management |
| **[Observer Pattern](observer/README.md)** | Event-driven component communication | Decoupled architecture |
| **[Metrics System](metrics/README.md)** | Performance monitoring and data collection | Comprehensive experiment analysis |
| **[Command Processor](command_processor/README.md)** | Structured command generation and processing | Safe command execution |
| **Reporting System** | Automatic experiment report generation | Status summaries and failure analysis |
| **[Configuration Validation](../config/README.md)** | Advanced configuration validation and auto-fixing | Protocol-aware port management |
| **[CLI Interface](../README.md)** | Command-line operations and user interaction | Primary user interface |

---

## Module Organization

### Core Components by Directory

!!! note "Modular Architecture"
    Each core component is designed to be independent and replaceable. This modular design allows for future enhancements without breaking existing functionality.

```text
panther/core/
├── experiment_manager.py      # Central experiment orchestration
├── experiment_strategy.py     # Test execution strategies
├── events/                   # Event-driven architecture with typed events
│   ├── base/                 # Base event classes and emitters
│   ├── experiment/           # Experiment lifecycle events
│   ├── test/                 # Test execution events
│   ├── service/              # Service management events
│   ├── environment/          # Environment setup/teardown events
│   ├── metrics/              # Metrics collection events
│   ├── step/                 # Test step events
│   ├── assertion/            # Test assertion events
│   └── plugin/               # Plugin lifecycle events
├── metrics/                  # Performance monitoring and data collection
│   ├── metrics_collector.py  # Central metrics collection
│   ├── metrics_exporter.py   # Export to various formats
│   ├── metrics_reporter.py   # Analysis and reporting
│   └── resource_monitor.py   # System resource monitoring
├── command_processor/        # Structured command generation and processing
│   ├── command.py            # Command objects and validation
│   ├── command_builder.py    # Command construction utilities
│   ├── command_processor.py  # Main processing engine
│   └── command_utils.py      # Command utilities and helpers
├── observer/                 # Event-driven communication
│   ├── base/                 # Observer interfaces
│   ├── impl/                 # Observer implementations
│   ├── factory/              # Observer factory pattern
│   ├── management/           # Event and results management
│   └── plugins/              # Observer plugin system
├── docker_builder/           # Container build system (see [Docker Builder README](docker_builder/README.md))
├── test_cases/               # Test framework interfaces
├── results/                  # Result collection and processing
├── reporting/                # Experiment report generation
│   ├── status_collector.py   # Test result aggregation
│   ├── experiment_reporter.py # Report generation engine
│   └── templates/            # Report templates
├── storage/                  # Event and data storage
├── state/                    # State management
├── template/                 # Template rendering system
├── workflow/                 # Workflow tracking
├── outputs/                  # Output aggregation and collection
├── exceptions/               # Framework-specific errors
└── utils/                    # Supporting utilities
```

### Related Systems

```text
panther/config/               # Configuration management
├── config_manager.py         # Configuration loading and validation
├── config_global_schema.py   # Global configuration schema
├── config_experiment_schema.py # Experiment configuration schema
└── plugin_params.py          # Plugin parameter discovery

panther/__main__.py           # CLI entry point and command routing
```

---

## Integration Overview

The core systems work together to provide a cohesive framework:

**Flow:**

1. **CLI** processes user commands and loads configurations
2. **Configuration System** validates and provides typed configuration
3. **Experiment Engine** orchestrates test execution using configuration
4. **Event System** provides typed events for all component interactions
5. **Observer Pattern** coordinates component communication through events
6. **Command Processor** generates and validates execution commands
7. **Metrics System** collects performance data throughout execution
8. **Results System** collects and processes test outputs (event-driven)
9. **Reporting System** generates comprehensive experiment reports automatically

### Component Interaction

```text
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Experiment      │───▶│ Event        │───▶│ Observers   │
│ Manager         │    │ System       │    │             │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │                 │
         ▼                       ▼                 ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Command         │    │ Test Cases   │    │ Metrics     │
│ Processor       │    │              │    │ System      │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │                 │
         ▼                       ▼                 ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Plugin          │    │ Docker       │    │ Results     │
│ Manager         │    │ Builder      │    │ Manager     │
└─────────────────┘    └──────────────┘    └─────────────┘
```

---

## Quick Start

### Basic Experiment Execution

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
from panther.config.config_manager import ConfigLoader
from panther.core.experiment_manager import ExperimentManager

# Load configuration
config_loader = ConfigLoader("experiment_config.yaml")
global_config = config_loader.load_and_validate_global_config()

# Create and run experiment
experiment_manager = ExperimentManager(global_config=global_config)
experiment_config = config_loader.load_and_validate_experiment_config()
experiment_manager.initialize_experiments(experiment_config)
experiment_manager.run_tests()
```

### Command Line Usage

```bash
# Run experiment
panther --experiment-config config.yaml

# Validate configuration
panther --validate-config --experiment-config config.yaml

# List plugin parameters
panther --list-plugin-params quiche
```

---

## Development Guidelines

### Extending Core Functionality

1. **Follow the Observer Pattern** — Use events for component communication
2. **Maintain Type Safety** — Use dataclasses and proper type annotations
3. **Plugin Integration** — Ensure new features work with the plugin system
4. **Documentation** — Update functional group docs for significant changes

### Code Organization

- **Single Responsibility** — Each module has a clear, focused purpose
- **Dependency Injection** — Components receive dependencies through constructors
- **Error Handling** — Use custom exceptions from `panther/core/exceptions/`
- **Testing** — Write tests that validate both success and error scenarios

---

**Related Documentation:**

- [Configuration Guide](../config/README.md) — Complete YAML configuration reference
- [Plugin Development](../plugins/development.md) — Creating framework extensions
- [Quick Start](../../QUICK_START.md) — Getting started with PANTHER
