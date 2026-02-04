# PANTHER Codebase Structure

## Root Directory
```
PANTHER/
├── panther/                 # Main package
├── tests/                   # Test suite
├── experiment-config/       # Example experiment configurations
├── outputs/                 # Generated outputs (gitignored)
├── build/                   # Build artifacts (gitignored)
├── .venv/                   # Virtual environment (gitignored)
├── pyproject.toml           # Project configuration (source of truth)
├── panther_builder.py       # Build system
├── CLAUDE.md                # Claude Code instructions
└── workflow.md              # Execution architecture docs
```

## Main Package Structure
```
panther/
├── __init__.py              # Package init, version
├── __main__.py              # Entry point
├── banner.py                # ASCII banner display
├── cli_click/               # NEW Click-based CLI (USE THIS)
│   ├── core/
│   │   ├── main.py          # CLI entry point
│   │   └── base.py          # Base CLI classes
│   └── commands/            # CLI subcommands
│       ├── run.py           # panther run
│       ├── config.py        # panther config
│       ├── plugins.py       # panther plugins
│       ├── tools.py         # panther tools
│       └── ...
├── config/                  # Configuration system
│   ├── core/                # Core config classes
│   │   ├── manager.py       # ConfigManager
│   │   ├── components/      # Component configs
│   │   └── mixins/          # Config mixins
│   └── README.md
├── core/                    # Core framework
│   ├── experiment_manager.py    # Central orchestrator
│   ├── experiment_strategy.py   # Strategy pattern
│   ├── test_cases/              # Test execution
│   │   ├── base/                # Base test case
│   │   ├── mixins/              # Mixin classes
│   │   └── test_case_impl.py    # Implementation
│   ├── events/                  # Event system
│   │   ├── base/                # Event base classes
│   │   └── emitter_registry.py  # Event registry
│   ├── observer/                # Observer pattern
│   │   ├── impl/                # Observer implementations
│   │   └── management/          # Event manager
│   ├── docker_builder/          # Docker orchestration
│   │   ├── docker_builder.py    # Main builder
│   │   ├── caching/             # Build caching
│   │   ├── plugin_mixin/        # Service manager mixin
│   │   └── utils/               # Utilities
│   ├── command_processor/       # Command generation
│   ├── reporting/               # Report generation
│   ├── outputs/                 # Output handling
│   ├── results/                 # Result collection
│   ├── metrics/                 # Metrics collection
│   └── utils/                   # Utilities
│       └── logger_factory.py    # Logging
├── plugins/                 # Plugin system
│   ├── core/                # Plugin infrastructure
│   │   ├── plugin_factory.py    # Factory
│   │   ├── plugin_decorators.py # @service_plugin, etc.
│   │   └── structures/          # Data structures
│   ├── plugin_manager.py    # Plugin discovery/loading
│   ├── services/            # Service plugins
│   │   ├── services_interface.py    # Base interface
│   │   ├── iut/                     # Implementation Under Test
│   │   │   └── quic/                # QUIC implementations
│   │   │       ├── picoquic/
│   │   │       ├── aioquic/
│   │   │       └── ...
│   │   └── testers/                 # Test tools
│   │       └── panther_ivy/         # Ivy (SUBMODULE)
│   ├── environments/        # Environment plugins
│   │   ├── environment_interface.py
│   │   ├── network_environment/     # Network setup
│   │   │   ├── docker_compose/
│   │   │   ├── localhost_single_container/
│   │   │   └── shadow_ns/
│   │   └── execution_environment/   # Execution setup
│   └── protocols/           # Protocol plugins
│       ├── protocol_interface.py
│       └── client_server/
│           └── quic/
├── webapp/                  # Flask web interface
│   └── web_app.py
└── tools/                   # Development tools
    ├── config/              # Config validation
    └── docs_gen/            # Documentation generation
```

## Test Structure
```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_core/           # Core module tests
│   └── test_plugins/        # Plugin tests
├── integration/             # Integration tests
└── cli/                     # CLI tests
    └── test_cli_commands_automated.py
```

## Important Entry Points
1. **CLI**: `panther/cli_click/core/main.py:main()`
2. **Experiment**: `panther/core/experiment_manager.py:ExperimentManager`
3. **Plugin Discovery**: `panther/plugins/plugin_manager.py:PluginManager`
4. **Docker Build**: `panther/core/docker_builder/docker_builder.py:DockerBuilder`
