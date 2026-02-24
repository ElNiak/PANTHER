# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PANTHER (Protocol Analysis and Testing Harness for Extensible Research) is a plugin-based, research-grade test harness for designing, reproducing, and analyzing network protocol experiments. It uses Docker-based isolation, event-driven architecture, and a four-phase execution model.

**Current Status**: Active development. CLI uses Click (`panther/cli_click/`). Dead code and legacy features remain. ARM support incomplete.

## Essential Commands

### Installation & Development

Always activate the virtual environment before running any commands.

Always activate Serena project environment when working on this repo. (Regular index project with `uvx --from git+https://github.com/oraios/serena serena project index`)

**IMPORTANT**: PANTHER must always be installed and run inside a virtual environment.

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/ElNiak/PANTHER.git
cd PANTHER

# Create and activate virtual environment (REQUIRED)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Development install (recommended)
python panther_builder.py package-dev

# Run tests
pytest tests/ -n auto -m unit             # Fast unit tests
pytest tests/ -n auto -m integration     # Requires Docker
pytest tests/unit/test_core/test_docker_builder_tag_generation.py -v  # Single test file

# Code quality
black panther/                           # Format
isort panther/                           # Sort imports
flake8 panther/                          # Lint
mypy panther/                            # Type check
```

### Build System (`panther_builder.py`)
```bash
python panther_builder.py package-dev    # Editable install with all deps
python panther_builder.py docs           # Build documentation
python panther_builder.py clean          # Remove build artifacts
python panther_builder.py serve-docs     # Local docs server
```

### CLI Commands (after `package-dev`)
```bash
panther run --config experiment-config/base/experiment_config_example_minimal.yaml     # Execute experiment
panther config validate --config x.yaml  # Validate config
panther plugins list                     # List plugins
panther tools doctor                     # System check
```


### Experiment Execution

#### Experiment Configuration

Example minimal config: `experiment-config/base/experiment_config_example_minimal.yaml`

Those are YAML files defining experiments, network environments, services, protocols, and test scenarios.

The parser uses OmegaConf with Pydantic for validation.

You can see the implementation of each config section in the corresponding plugin's `config_schema.py`.

You can see the parser and validator in `panther/config/`.

```yaml
logging:
  level: INFO
tests:
  - name: "Test Name"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
```

#### Run an Experiment

```bash
panther run --config experiment-config/base/experiment_config_example_minimal.yaml
```

All the experiment execution logic is in `panther/core/experiment_manager.py`, which orchestrates the four-phase execution model.

#### Checkout experiments output

When running an experiment for the config `experiment-config/base/experiment_config_example_minimal.yaml`, outputs are stored in `outputs/<experiment_date>/<experiment_id>/` where `<experiment_date>` is the date and time when the experiment was run, and `<experiment_id>` are experiment identifier defined in the config file.

At the end of an experiment run, outputs are stored in `outputs/<experiment_date>/<experiment_id>/`.

The outputs are managed by the reporting module located in `panther/core/reporting/`, `panther/core/results/` and `panther/core/outputs/` and also in plugins that implement custom reporters.

```bash
cd outputs/<experiment_date>/<experiment_id>/
ls -la  # View generated reports and logs
```

## Architecture

### Four-Phase Execution Model
1. **Initialization**: Load configs, validate, initialize plugins
2. **Plugin Loading**: Discover plugins, create service managers, generate commands
3. **Environment Deployment**: Setup network (Docker Compose/Shadow NS), build containers
4. **Test Execution**: Run scenarios, collect metrics, teardown, report

### Key Components
```
panther/
├── cli_click/          # Click-based CLI
├── core/
│   ├── experiment_manager.py    # Central orchestrator
│   ├── test_cases/              # Test execution (mixin-based)
│   ├── events/                  # Event-driven coordination
│   ├── observer/                # Observer pattern
│   ├── docker_builder/          # Docker orchestration
│   ├── command_processor/       # Safe command generation
│   └── reporting/               # Report generation
├── config/             # OmegaConf + Pydantic hybrid
└── plugins/
    ├── services/       # IUT implementations (picoquic, aioquic, etc.)
│   └── testers/    # Ivy formal verification
    ├── environments/   # Docker Compose, Shadow NS, localhost
    └── protocols/      # QUIC, HTTP, etc.
```

### Plugin System
- Decorator-based registration (`@register_plugin()`, `@register_protocol()`)
- Inheritance-based with template method pattern
- Each plugin contributes config schema via `config_schema.py`

## Configuration

Source of truth: `pyproject.toml` (v1.1.5)
Dependencies frozen in `requirements.txt` (do not edit)


## Testing

```bash
pytest tests/ -n auto --cov=panther --cov-fail-under=70  # Coverage required: 70%
```

**Test Markers**:
- `@pytest.mark.unit` - Fast, no external deps
- `@pytest.mark.integration` - Requires Docker
- `@pytest.mark.requires_docker` - Docker dependency
- `@pytest.mark.slow` - Takes >10 seconds

## Code Style

- **Line length**: 88 (Black default)
- **Python**: 3.10+
- **Formatting**: Black, isort
- **Excluded from linting**: `panther/plugins/services/testers/panther_ivy/` (submodule)

## Known Issues

1. **ARM**: Z3 math errors, use `development-scp-refactor` branch for stability
2. **Ivy tester**: First build ~30 minutes (slow compilation)
3. **Docker BuildKit**: May need `force_build_docker_image: true` in config
4. **Submodules**: Run `git submodule update --init --recursive` if panther_ivy missing

## Key Files to Understand

- `workflow.md` - Detailed execution architecture
- `panther/core/README.md` - Core framework
- `panther/config/README.md` - Configuration system
- `panther/plugins/development.md` - Plugin development guide

## Git Workflow

- Main branch: `production`
- Current dev branch: `panther-fix`
- PR target: `production`
