# PANTHER Python Package

The `panther/` directory is the main Python package for the PANTHER framework
(Protocol Analysis and Testing Harness for Extensible Research).

## Package Structure

```text
panther/
├── __init__.py
├── __main__.py            # Entry point: delegates to cli_click

├── banner.py              # CLI banner display
├── cli_click/             # Click-based CLI (primary interface)
│   ├── core/              #   CLI entry point and base utilities
│   └── commands/          #   Command implementations (run, config, plugins, ...)
├── config/                # Configuration system
│   ├── core/              #   ConfigurationManager, models, mixins, validators
│   └── tutorial/          #   Config tutorial helpers
├── core/                  # Experiment engine
│   ├── experiment_manager.py   # Central orchestrator
│   ├── test_cases/             # Mixin-composed test execution
│   ├── events/                 # Typed event-driven architecture
│   ├── observer/               # Observer pattern implementation
│   ├── metrics/                # Performance monitoring
│   ├── command_processor/      # Safe command generation
│   ├── docker_builder/         # Container build system
│   ├── reporting/              # Report generation
│   ├── results/                # Result collection
│   └── outputs/                # Output aggregation
├── plugins/               # Plugin system
│   ├── services/          #   IUT implementations and testers
│   ├── environments/      #   Docker Compose, Shadow NS, localhost
│   └── protocols/         #   QUIC, HTTP, MinIP protocol definitions
├── tools/                 # Development and diagnostic tools
├── tutorial/              # Interactive tutorials
└── webapp/                # Web dashboard
```

## Entry Point

The CLI entry point is defined in `pyproject.toml`:

```toml
[project.scripts]
panther = "panther.cli_click.core.main:main"
```

`__main__.py` simply imports and calls `main()` from `panther.cli_click.core.main`,
making `python -m panther` equivalent to the `panther` command.

For full CLI documentation, see [cli_click/README.md](cli_click/README.md).

## Key Subsystems

### Configuration (`config/`)

Hierarchical YAML configuration with OmegaConf + Pydantic validation.
The primary interface is `ConfigurationManager` in `panther.config.core.manager`.

See [config/README.md](config/README.md) for the full configuration guide.

### Core Engine (`core/`)

Four-phase experiment execution: initialization, plugin loading,
environment deployment, and test execution. Orchestrated by
`ExperimentManager` in `panther.core.experiment_manager`.

See [core/README.md](core/README.md) for architecture details.

### Plugins (`plugins/`)

Decorator-based plugin registration with template method pattern.
Supports service plugins (IUT implementations, testers), environment
plugins (Docker Compose, Shadow NS), and protocol plugins (QUIC, HTTP).

See [plugins/README.md](plugins/README.md) for the plugin development guide.

## Quick Reference

```bash
# Run an experiment
panther run --config experiment-config/base/experiment_config_example_minimal.yaml

# Validate configuration
panther config validate --config experiment.yaml

# List available plugins
panther plugins list

# System diagnostics
panther tools doctor
```
