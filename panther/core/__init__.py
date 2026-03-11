"""PANTHER Core Framework.

Central orchestration engine for network protocol testing, implementing
experiment lifecycle management through event-driven architecture and
plugin-based extensibility.

Architecture::

    ┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
    │ Experiment      │───>│ Event        │───>│ Observers   │
    │ Manager         │    │ System       │    │             │
    └─────────────────┘    └──────────────┘    └─────────────┘
             │                       │                 │
             v                       v                 v
    ┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
    │ Command         │    │ Test Cases   │    │ Metrics     │
    │ Processor       │    │              │    │ System      │
    └─────────────────┘    └──────────────┘    └─────────────┘
             │                       │                 │
             v                       v                 v
    ┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
    │ Plugin          │    │ Docker       │    │ Results     │
    │ Manager         │    │ Builder      │    │ Manager     │
    └─────────────────┘    └──────────────┘    └─────────────┘

Primary Components:

    ExperimentManager
        Central facade orchestrating experiment lifecycle. Uses
        event-driven coordination (EventManager + EmitterRegistry),
        observer pattern for pluggable monitoring, and facade
        pattern delegating to PluginManager.

    TestCase
        Mixin-composed test execution engine with six specialized
        mixins, state machine transitions (PENDING -> RUNNING -> DONE),
        Docker orchestration, and performance metrics collection.

    Plugin System
        Singleton PluginManager with thread-safe initialization,
        multi-level caching with TTL, protocol/service/environment
        plugin types, and Docker integration.

Design Patterns:
    - Event-Driven Architecture: central event bus for subsystem communication
    - Observer Pattern: pluggable observers for metrics, logging, analysis
    - Facade Pattern: ExperimentManager as unified interface
    - Mixin Composition: modular capabilities through multiple inheritance

Module Organization::

    core/
    ├── experiment_manager.py      # Central orchestration
    ├── events/                    # Typed event system
    ├── observer/                  # Observer pattern implementation
    ├── command_processor/         # Structured command generation
    ├── docker_builder/            # Container build system
    ├── test_cases/                # Mixin-based test execution
    ├── metrics/                   # Performance monitoring
    ├── results/                   # Result collection
    ├── reporting/                 # Report generation
    ├── exceptions/                # Framework-specific errors
    └── utils/                     # Supporting utilities

Example::

    from panther.config.core.manager import ConfigurationManager
    from panther.core.experiment_manager import ExperimentManager

    config_manager = ConfigurationManager()
    config = config_manager.load_and_validate_config("config.yaml")
    experiment = ExperimentManager(global_config=config)
    experiment.run_tests()
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "experiment_manager",
    "observer",
    "results",
    "test_cases",
    "utils",
    "exceptions",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    if name == "experiment_manager":
        from . import experiment_manager  # pylint: disable=import-outside-toplevel

        return experiment_manager
    elif name == "observer":
        from . import observer  # pylint: disable=import-outside-toplevel

        return observer
    elif name == "results":
        from . import results  # pylint: disable=import-outside-toplevel

        return results
    elif name == "test_cases":
        from . import test_cases  # pylint: disable=import-outside-toplevel

        return test_cases
    elif name == "utils":
        from . import utils  # pylint: disable=import-outside-toplevel

        return utils
    elif name == "exceptions":
        from . import exceptions  # pylint: disable=import-outside-toplevel

        return exceptions
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
