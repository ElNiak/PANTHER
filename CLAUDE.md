Notes:
- Dead code and legacy features remain. (MUST be removed in future refactor)
- ARM support incomplete.

## Essential Commands

**Prerequisites**: Python 3.10+, Docker

ALWAYS activate the virtual environment before running any commands.

Always activate Serena project environment when working on this repo.
Regular index project with `uvx --from git+https://github.com/oraios/serena serena project index`

**IMPORTANT**: PANTHER must always be installed and run inside a virtual environment.

```bash
# Create and activate virtual environment (REQUIRED)
python -m venv .venv
source .venv/bin/activate

# Development install (recommended — also installs panther_ivy if submodule is present)
python panther_builder.py package-dev

# If using the Ivy tester plugin (init submodule first):
git submodule update --init panther/plugins/services/testers/panther_ivy
# Then re-run package-dev, or install manually:
pip install -e panther/plugins/services/testers/panther_ivy/

# Run tests
pytest tests/ -n auto -m unit             # Fast unit tests
pytest tests/ -n auto -m integration     # Requires Docker

# Code quality
black panther/                           # Format
isort panther/                           # Sort imports
flake8 panther/                          # Lint
mypy panther/                            # Type check
```

### Build System
```bash
# Bootstrap (when PANTHER is not yet installed):
python panther_builder.py package-dev    # Editable install with all deps

# After installation, use CLI commands:
panther build dev                        # Editable install with all deps
panther build package                    # Build and install wheel
panther build test                       # Build + run tests
panther build clean                      # Remove build artifacts
panther docs build                       # Build documentation
panther docs serve                       # Build + serve locally
panther docs deploy                      # Deploy to GitHub Pages
```

### CLI Commands (after `package-dev`)
```bash
panther run --config experiment-config/base/experiment_config_example_minimal.yaml     # Execute experiment
panther config validate --config x.yaml  # Validate config
panther plugins list                     # List plugins
panther tools status                     # Show tool installation status
panther admin archive-outputs            # Archive outputs directory
```


### Experiment Execution

#### Experiment Configuration

Example minimal config: `experiment-config/base/experiment_config_example_minimal.yaml`

Define experiments in YAML files specifying network environments, services, protocols, and test scenarios.

The parser uses OmegaConf with Pydantic for validation.

Find each config section's implementation in the corresponding plugin's `config_schema.py`.

Find the parser and validator in `panther/config/`.

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

Outputs land in `outputs/<experiment_date>/<experiment_id>/`. The reporting module at `panther/core/reporting/`, `panther/core/results/`, and `panther/core/outputs/` manages outputs, along with plugins that implement custom reporters.

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
├── cli/          # CLI
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

Source of truth: `pyproject.toml` (v1.2.1)
Dependencies defined in `pyproject.toml`


## Testing

```bash
pytest tests/ -n auto --cov=panther --cov-fail-under=70  # Coverage required: 70%
```

**Test Markers**:
- `@pytest.mark.unit` - Fast, no external deps
- `@pytest.mark.integration` - Requires Docker
- `@pytest.mark.requires_docker` - Docker dependency
- `@pytest.mark.slow` - Takes >10 seconds
- Always run the full test suite after refactoring or multi-file changes. Do not consider a task complete until tests pass.

## Code Style

- **Line length**: 88 (Black default)
- **Python**: 3.10+
- **Formatting**: Black, isort
- **Excluded from linting**: `panther/plugins/services/testers/panther_ivy/` (submodule)

## Known Issues

1. **ARM**: Z3 4.7.1 (local build) hangs solver on ARM64; use `z3_source: pip` with z3-solver 4.13.0.0 and `target_platform: linux/arm64`
2. **Ivy tester**: First build ~30 minutes (slow compilation)

## Debugging

- When debugging MCP server issues, distinguish between MCP server crashes/drops and Claude-side errors. Never attribute MCP infrastructure failures to application logic without evidence.
- Avoid going down triage/exploration rabbit holes when the user asks a direct debugging question. Start with the specific issue before broadening scope.

## Skills & Tooling

- When scoping new skills or tools, start broad -- include debug logs, plans, tasks, and multi-project support from the beginning. Ask the user about scope before narrowing.

## Key Files to Understand

- `workflow.md` - Detailed execution architecture
- `panther/core/__init__.py` - Core framework (module docstring)
- `panther/config/__init__.py` - Configuration system (module docstring)
- `panther/plugins/__init__.py` - Plugin development guide (module docstring)

## Git Workflow

- Main branch: `production`
- PR target: `production`
