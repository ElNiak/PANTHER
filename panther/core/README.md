# PANTHER Core Framework

**Foundation modules for experiment management and testing infrastructure**

The core modules provide the essential functionality that powers the PANTHER framework, including experiment orchestration, configuration management, event-driven communication, and command-line operations.

!!! info "For Framework Developers"
    This documentation is intended for developers working on PANTHER's core framework or those needing to understand the internal architecture. For plugin development, see the [Plugin Development Guide](../plugins/development.md).

---

## Core Functional Groups

PANTHER's core is organized into focused functional groups, each with comprehensive documentation:

| Functional Group | Purpose | Documentation |
|------------------|---------|---------------|
| **[Experiment Engine](panther/core/EXPERIMENT_ENGINE.md)** | Test execution orchestration and lifecycle management | Core experiment coordination |
| **[Configuration System](panther/config/README.md)** | Schema-driven configuration loading and validation | Type-safe YAML configuration |
| **[Observer Pattern](panther/core/observer/README.md)** | Event-driven component communication | Decoupled architecture |
| **[CLI Interface](panther/README.md)** | Command-line operations and user interaction | Primary user interface |S

---

## Module Organization

### Core Components by Directory

!!! note "Modular Architecture"
    Each core component is designed to be independent and replaceable. This modular design allows for future enhancements without breaking existing functionality.

```text
panther/core/
├── experiment_manager.py      # Central experiment orchestration
├── experiment_strategy.py     # Test execution strategies
├── test_cases/               # Test framework interfaces
├── observer/                 # Event-driven communication
├── results/                  # Result collection and processing
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
4. **Observer Pattern** coordinates component communication through events
5. **Results System** collects and processes test outputs (event-driven)

### Component Interaction

```text
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Experiment      │───▶│ Event        │───▶│ Observers   │
│ Manager         │    │ Manager      │    │             │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │                 │
         ▼                       ▼                 ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Plugin          │    │ Test Cases   │    │ Results     │
│ Manager         │    │              │    │ Manager     │
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

- [Configuration Guide](panther/config/README.md) — Complete YAML configuration reference
- [Plugin Development](panther/plugins/development.md) — Creating framework extensions
- [Quick Start](QUICK_START.md) — Getting started with PANTHER
