# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

### Python Virtual Environment
```bash
# Create virtual environment with Python 3.10+
python3.10 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
.\.venv\Scripts\activate  # On Windows

# Install in development mode
pip install -e .
```

### MCP Server Integration

This project integrates with the **Codacy MCP Server** for automated code quality analysis:

- **Always use**: provider: `gh`, organization: `ElNiak`, repository: `PANTHER`
- **After editing files**: Run `codacy_cli_analyze` with rootPath set to PANTHER project root
- **Security scanning**: Use Trivy for dependency changes in requirements.txt
- **Fix Critical/High issues**: Always address these before proceeding

See `.github/copilot-instructions.md` for detailed MCP server usage patterns.

## Common Development Commands

### Building and Installing
```bash
# Install in development mode
python panther_builder.py package-dev

# Build and install the package
python panther_builder.py package

# Build, install and run tests
python panther_builder.py package-test

# Clean build artifacts
python panther_builder.py clean
```

### Running PANTHER Experiments
```bash
# Run a basic experiment
python -m panther --experiment-config experiment-config/experiment_config_example_minimal.yaml

# Run with debug logging
python -m panther --experiment-config config.yaml --debug

# Validate configuration without running
python -m panther --experiment-config config.yaml --validate-config

# Run with metrics collection
python -m panther --experiment-config config.yaml --enable-metrics

# List plugin parameters
python -m panther --list-plugin-params picoquic --plugin-type iut --protocol quic
```

### Plugin Management
```bash
# Create a new plugin
python -m panther --create-plugin service my_service --dev-mode

# Create plugin with subplugins
python -m panther --create-plugin protocol my_protocol --with-subplugins

# Run interactive tutorial
python -m panther --interactive-tutorials

# Create a subplugin
python -m panther --create-subplugin service quic my_implementation
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/              # Integration tests
pytest tests/e2e/                     # End-to-end tests
pytest tests/property_based/          # Property-based tests

# Run tests with markers
pytest -m unit                        # Fast unit tests
pytest -m "not requires_docker"       # Skip Docker-dependent tests
pytest -m requires_ivy                # Only Ivy-related tests

# Run a single test file
pytest tests/unit/test_core/test_experiment_manager.py

# Run a specific test
pytest tests/unit/test_core/test_experiment_manager.py::TestExperimentManager::test_initialization

# Run with coverage
pytest --cov=panther --cov-report=html
```

### Documentation
```bash
# Build documentation
python panther_builder.py docs

# Serve documentation locally
python panther_builder.py serve-docs

# Deploy to GitHub Pages
python panther_builder.py deploy-docs
```

### Code Quality
```bash
# Run code quality checks
python panther_builder.py check

# Install pre-commit hooks
python panther_builder.py install-precommit

# Format code with black
black panther/

# Check imports with isort
isort panther/

# Lint with flake8
flake8 panther/
```

### Docker Management
```bash
# Remove all PANTHER Docker images
python panther_builder.py remove-images-all

# Remove service-specific images
python panther_builder.py remove-images-services

# Remove volumes
python panther_builder.py remove-volume
```

## High-Level Architecture

### Event-Driven Architecture

PANTHER uses a comprehensive event-driven architecture with entity-specific event modules:

1. **Event Types** (`panther/core/events/`):
   - `experiment/`: Experiment lifecycle events and states
   - `test/`: Test execution events and states
   - `service/`: Service management events and states
   - `environment/`: Environment setup/teardown events
   - `metrics/`, `step/`, `assertion/`, `plugin/`: Specialized event types

2. **Event Flow**:
   - Each entity type has its own `events.py`, `states.py`, and `emitter.py`
   - Events include UUID, timestamp, entity metadata, and state transitions
   - State machines enforce valid transitions (e.g., INITIALIZED → RUNNING → COMPLETED)

3. **Observer Pattern**:
   - `EventManager` coordinates all observers
   - Observers include: LoggerObserver, MetricsObserver, StorageObserver
   - Events are propagated asynchronously to avoid blocking

### Plugin System

The plugin architecture supports three main categories:

1. **Service Plugins** (`panther/plugins/services/`):
   - **IUT (Implementation Under Test)**: Protocol implementations (e.g., picoquic, aioquic)
   - **Testers**: Validation tools (e.g., panther_ivy for formal verification)
   - Each plugin provides a ServiceManager implementing command generation

2. **Environment Plugins** (`panther/plugins/environments/`):
   - **Network**: Docker Compose, localhost, Shadow NS
   - **Execution**: Performance profilers (strace, gperf, memcheck)
   - Handle deployment, monitoring, and teardown

3. **Protocol Plugins** (`panther/plugins/protocols/`):
   - Define protocol-specific configurations
   - Support client-server and peer-to-peer patterns

### Command Generation Pipeline

Commands are generated through a multi-phase template system:

1. **Command Processor** (`panther/core/command_processor/`):
   - Structured command objects with proper escaping
   - Command validation and error handling
   - Support for complex shell constructs

2. **Template Rendering**:
   - Jinja2 templates in each plugin's `templates/` directory
   - Parameters include certificates, network config, protocol settings
   - Five command phases: pre-compile, compile, post-compile, run, post-run

3. **Execution Flow**:
   ```
   Service Manager → Command Generation → Template Rendering →
   Command Processor → Environment Plugin → Container/Process Execution
   ```

### Experiment Workflow

The 4-phase execution model managed by `ExperimentManager`:

1. **Initialization**: Load configs, validate, create test cases
2. **Plugin Loading**: Discover plugins, create service managers, generate commands
3. **Environment Deployment**: Build containers, setup network, deploy services
4. **Test Execution**: Run services, monitor, collect results, teardown

### Key Integration Points

1. **Service Manager Creation** (`plugin_manager.py:229`):
   - Dynamic module loading from plugin directories
   - Class instantiation with naming convention
   - Event emitter injection for monitoring

2. **Docker Compose Orchestration** (`docker_compose.py`):
   - Multi-stage container builds with base + implementation layers
   - Volume management for logs, certs, and synchronization
   - Service coordination with wait conditions

3. **Result Collection**:
   - Automatic packet capture for all services
   - Centralized logging to experiment output directory
   - Metrics collection through observer pattern

### Development Patterns

1. **Adding a New Protocol Implementation**:
   - Create directory under `panther/plugins/services/iut/<protocol>/<implementation>/`
   - Implement ServiceManager with required command generation methods
   - Add Dockerfile and command templates
   - Register in plugin loader

2. **Creating Environment Plugins**:
   - Inherit from INetworkEnvironment or IExecutionEnvironment
   - Implement prepare(), deploy(), run(), teardown() lifecycle
   - Handle service coordination and monitoring

3. **Event System Extension**:
   - Create new event types in `panther/core/events/<entity>/`
   - Define states with valid transitions
   - Implement entity-specific emitter
   - Register observers for event handling

### Testing Considerations

- Unit tests mock plugin loading and command generation
- Integration tests use real Docker containers (mark with `@pytest.mark.requires_docker`)
- Property-based tests validate configuration schemas
- E2E tests run complete experiment workflows

### Common Debugging Points

1. **Plugin Loading Issues**: Check class naming convention (e.g., `PicoquicServiceManager`)
2. **Command Generation**: Enable debug logging to see rendered templates
3. **Container Failures**: Inspect generated docker-compose.yml and entrypoint scripts
4. **Event Propagation**: Use DebugObserver to trace event flow
5. **Service Coordination**: Check shared volumes and wait conditions in Docker Compose