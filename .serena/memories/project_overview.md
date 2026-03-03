# PANTHER Project Overview

## Purpose
PANTHER (Protocol Analysis and Testing Harness for Extensible Research) is a plugin-based, research-grade test harness for designing, reproducing, and analyzing network protocol experiments. It uses Docker-based isolation, event-driven architecture, and a four-phase execution model.

## Current Status
- Version: 1.2.1
- Active refactoring in progress: CLI migrating from argparse (`panther/cli/`) to Click (`panther/cli_click/`)
- Main branch: `production`
- Current dev branch: `panther-fix`

## Tech Stack
- **Language**: Python 3.10+
- **CLI Framework**: Click (new) / argparse (deprecated)
- **Configuration**: OmegaConf + Pydantic hybrid
- **Containerization**: Docker, Docker Compose
- **Web Framework**: Flask (web interface)
- **Testing**: pytest with markers
- **Documentation**: MkDocs with Material theme
- **Formal Verification**: Ivy (via panther_ivy submodule)

## Four-Phase Execution Model
1. **Initialization**: Load configs, validate, initialize plugins
2. **Plugin Loading**: Discover plugins, create service managers, generate commands
3. **Environment Deployment**: Setup network (Docker Compose/Shadow NS), build containers
4. **Test Execution**: Run scenarios, collect metrics, teardown, report

## Key Components
```
panther/
├── cli_click/          # NEW Click-based CLI (use this)
├── cli/                # OLD argparse CLI (deprecated, being removed)
├── core/
│   ├── experiment_manager.py    # Central orchestrator
│   ├── test_cases/              # Test execution (mixin-based)
│   ├── events/                  # Event-driven coordination
│   ├── observer/                # Observer pattern
│   ├── docker_builder/          # Docker orchestration
│   ├── command_processor/       # Safe command generation
│   └── reporting/               # Report generation
├── config/             # OmegaConf + Pydantic hybrid
├── plugins/
│   ├── services/       # IUT implementations (picoquic, aioquic, etc.)
│   │   └── testers/    # Ivy formal verification
│   ├── environments/   # Docker Compose, Shadow NS, localhost
│   └── protocols/      # QUIC, HTTP, etc.
└── webapp/             # Flask web interface
```

## Plugin System
- Decorator-based registration (`@service_plugin`, `@protocol_plugin`)
- Inheritance-based with template method pattern
- Each plugin contributes config schema via `config_schema.py`

## Known Issues
1. ARM: Z3 math errors, use `development-scp-refactor` branch for stability
2. Ivy tester: First build ~30 minutes (slow compilation)
3. Docker BuildKit: May need `force_build_docker_image: true` in config
4. Submodules: Run `git submodule update --init --recursive` if panther_ivy missing
