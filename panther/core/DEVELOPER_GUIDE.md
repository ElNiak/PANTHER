# PANTHER Core Developer Guide

Complete guide for developing, debugging, and contributing to the PANTHER core framework.

## Development Environment Setup

### Prerequisites

```bash
# System requirements
python >= 3.9
docker >= 20.10
docker-compose >= 2.0

# Optional but recommended
git >= 2.30
```

### Project Setup

```bash
# Clone and navigate to project
git clone <repository_url>
cd PANTHER

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate.bat  # Windows

# Install development dependencies
pip install -e ".[dev]"
```

### Development Dependencies

Core development packages installed with `pip install -e ".[dev]"`:

```python
# Testing
pytest >= 7.0
pytest-asyncio >= 0.21
pytest-cov >= 4.0
hypothesis >= 6.75  # Property-based testing

# Code Quality
black >= 23.0       # Code formatting
flake8 >= 6.0       # Linting
mypy >= 1.0         # Type checking
isort >= 5.12       # Import sorting

# Documentation
sphinx >= 6.0      # API documentation
sphinx-rtd-theme    # Documentation theme

# Development Tools
pre-commit >= 3.0   # Git hooks
tox >= 4.0          # Multi-environment testing
```

### IDE Configuration

#### VS Code Settings
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.associations": {
        "*.yaml": "yaml",
        "*.yml": "yaml"
    }
}
```

#### PyCharm Configuration
- Enable pytest as test runner
- Configure Black as code formatter
- Set pylint as primary linter
- Add `panther/` as source root

## Running and Debugging

### Local Testing

```bash
# Run core module tests
python -m pytest tests/core/ -v

# Run with coverage
python -m pytest tests/core/ --cov=panther.core --cov-report=html

# Run specific test categories
python -m pytest tests/core/test_experiment_manager.py -v
python -m pytest tests/integration/ -k "experiment" -v

# Performance testing
python -m pytest tests/performance/ --benchmark-only
```

### Debug Mode Execution

```bash
# Enable debug logging
export PANTHER_LOG_LEVEL=DEBUG

# Run with debug mode
python -m panther run --debug --config test_config.yaml

# Interactive debugging with pdb
python -c "
import pdb; pdb.set_trace()
from panther.core.experiment_manager import ExperimentManager
# Debug session starts here
"
```

### Docker Development

```bash
# Build development image
docker build -t panther:dev -f Dockerfile.dev .

# Run tests in container
docker run --rm -v $(pwd):/workspace panther:dev pytest tests/core/

# Interactive development shell
docker run -it --rm -v $(pwd):/workspace panther:dev bash
```

## Testing Guidelines

### Test Structure

The core module follows a comprehensive testing strategy:

```
tests/
├── core/                     # Unit tests for core components
│   ├── test_experiment_manager.py
│   ├── test_events/          # Event system tests
│   ├── test_observer/        # Observer pattern tests
│   └── test_utils/          # Utility function tests
├── integration/             # Integration tests
│   ├── test_full_experiment.py
│   └── test_plugin_integration.py
├── performance/             # Performance benchmarks
│   └── test_experiment_throughput.py
└── fixtures/               # Test data and mock objects
    ├── configs/            # Test configurations
    └── plugins/            # Mock plugins for testing
```

### Writing Tests

#### Unit Test Example
```python
import pytest
from unittest.mock import Mock, patch
from panther.core.experiment_manager import ExperimentManager
from panther.config.core.models import GlobalConfig

class TestExperimentManager:
    """Test suite for ExperimentManager core functionality."""

    @pytest.fixture
    def global_config(self):
        """Create test global configuration."""
        return GlobalConfig(
            paths={"output_dir": "/tmp/test_output"},
            plugins={"discovery_paths": ["tests/fixtures/plugins"]}
        )

    @pytest.fixture
    def experiment_manager(self, global_config):
        """Create test experiment manager instance."""
        return ExperimentManager(global_config=global_config)

    def test_initialization_creates_required_components(self, experiment_manager):
        """Verify proper component initialization."""
        assert experiment_manager.event_manager is not None
        assert experiment_manager.plugin_manager is not None
        assert experiment_manager.workflow_tracker is not None

    def test_experiment_lifecycle_emits_events(self, experiment_manager):
        """Verify event emission during experiment lifecycle."""
        event_handler = Mock()
        experiment_manager.event_manager.subscribe(
            "experiment.started", event_handler
        )

        # Execute experiment
        with experiment_manager.initialize_experiments(mock_config):
            pass

        # Verify events were emitted
        event_handler.assert_called_once()
```

#### Integration Test Example
```python
import tempfile
from pathlib import Path
from panther.core.experiment_manager import ExperimentManager

def test_full_experiment_execution():
    """Test complete experiment execution flow."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup test environment
        config_path = Path(temp_dir) / "test_config.yaml"
        config_path.write_text("""
        experiment:
          name: "integration_test"
          protocol: "quic"
          test_cases:
            - name: "basic_connection"
              implementation: "picoquic"
        """)

        # Run experiment
        manager = ExperimentManager.from_config(str(config_path))
        results = manager.run_experiment()

        # Verify results
        assert results.success_rate > 0.8
        assert len(results.test_cases) > 0
```

### Performance Testing

```bash
# Memory profiling
python -m memory_profiler scripts/profile_experiment.py

# CPU profiling
python -m cProfile -o profile.stats scripts/run_experiment.py
python -c "
import pstats
stats = pstats.Stats('profile.stats')
stats.sort_stats('cumulative').print_stats(20)
"

# Benchmark with pytest-benchmark
python -m pytest tests/performance/ --benchmark-compare
```

## Debugging Common Issues

### Event System Debugging

```python
# Enable event tracing
import logging
logging.getLogger('panther.core.events').setLevel(logging.DEBUG)

# Subscribe to all events for debugging
from panther.core.events.base import EventBase

def debug_handler(event: EventBase):
    print(f"Event: {event.__class__.__name__} - {event}")

event_manager.subscribe_all(debug_handler)
```

### Plugin Loading Issues

```bash
# Debug plugin discovery
export PANTHER_PLUGIN_DEBUG=1
python -c "
from panther.plugins.plugin_manager import PluginManager
manager = PluginManager()
print(manager.discover_plugins())
"

# Validate plugin configuration
python -m panther plugins validate --plugin-dir custom_plugins/
```

### Configuration Problems

```bash
# Validate configuration schema
python -m panther config validate --config problematic_config.yaml

# Debug configuration loading
python -c "
from panther.config.core.manager import ConfigManager
manager = ConfigManager()
config = manager.load_config('config.yaml', debug=True)
"
```

### Docker Build Issues

```bash
# Debug BuildKit cache
export DOCKER_BUILDKIT_DEBUG=1
docker build --progress=plain --no-cache .

# Check container resource limits
docker stats panther_experiment

# Inspect container filesystem
docker run --rm -it panther:latest ls -la /opt/panther/
```

## Code Quality Standards

### Linting and Formatting

```bash
# Format code with Black
black panther/core/

# Sort imports with isort
isort panther/core/

# Lint with pylint
pylint panther/core/

# Type checking with mypy
mypy panther/core/

# Security scanning
bandit -r panther/core/
```

### Pre-commit Hooks

The project uses pre-commit hooks for automated quality checks:

```yaml
# .pre-commit-config.yaml (relevant sections)
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/pylint
    rev: v2.13.9
    hooks:
      - id: pylint
        args: [--rcfile=.pylintrc]
```

### Documentation Standards

- All public classes and functions require docstrings
- Use Google-style docstring format
- Include type hints for all function parameters and return values
- Add usage examples for complex APIs
- Update API documentation when changing interfaces

## Pull Request Workflow

### Before Submitting

1. **Run full test suite**: `python -m pytest tests/`
2. **Check code coverage**: Maintain >90% coverage for core modules
3. **Validate formatting**: `pre-commit run --all-files`
4. **Update documentation**: Add/update docstrings and guides
5. **Test integration**: Verify changes work with existing plugins

### Pull Request Template

```markdown
## Summary
Brief description of changes and motivation.

## Changes Made
- [ ] Core functionality changes
- [ ] API modifications
- [ ] Documentation updates
- [ ] Test additions/modifications

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Performance tests pass (if applicable)
- [ ] Manual testing completed

## Breaking Changes
List any breaking changes and migration instructions.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
```

### Review Process

1. **Automated checks**: CI runs linting, testing, and security scans
2. **Peer review**: At least one core maintainer review required
3. **Integration testing**: Changes tested against plugin ecosystem
4. **Documentation review**: Technical writing team reviews docs
5. **Final approval**: Project maintainer approval for merge

## Advanced Development Topics

### Event System Extension

```python
# Creating custom event types
from panther.core.events.base import EventBase
from dataclasses import dataclass

@dataclass
class CustomExperimentEvent(EventBase):
    """Custom event for specialized experiment tracking."""
    experiment_id: str
    custom_data: dict

    def __post_init__(self):
        super().__post_init__()
        self.event_type = "experiment.custom"
```

### Plugin Interface Development

```python
# Implementing new plugin interfaces
from abc import ABC, abstractmethod
from panther.plugins.core.interfaces import IPlugin

class ICustomPlugin(IPlugin, ABC):
    """Interface for custom plugin functionality."""

    @abstractmethod
    def custom_operation(self, data: dict) -> bool:
        """Perform custom plugin operation."""
        pass
```

### Performance Optimization

```python
# Adding performance monitoring
from panther.core.metrics import MetricsCollector
from contextlib import contextmanager

@contextmanager
def performance_tracking(operation_name: str):
    """Context manager for performance tracking."""
    metrics = MetricsCollector.get_instance()
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        metrics.record_timing(operation_name, duration)
```

## Troubleshooting

### Common Error Patterns

**Import Errors**:
- Check PYTHONPATH includes project root
- Verify all dependencies installed with correct versions
- Ensure no circular imports in module structure

**Configuration Errors**:
- Validate YAML syntax with `yamllint`
- Check schema validation with `python -m panther config validate`
- Verify plugin parameters match expected schema

**Docker Issues**:
- Check Docker daemon is running
- Verify BuildKit is enabled
- Clear Docker cache if builds hang: `docker builder prune`

**Test Failures**:
- Run tests with `-vvv` for detailed output
- Check for test isolation issues
- Verify test fixtures and mock data

### Getting Help

- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share ideas
- **Wiki**: Detailed technical documentation
- **Slack**: Real-time community support (#panther-dev)

## Contributing Guidelines

### Code Style
- Follow PEP 8 with Black formatting
- Use type hints consistently
- Prefer composition over inheritance
- Keep functions focused and testable

### Documentation
- Update README files for significant changes
- Add docstring examples for complex APIs
- Include migration guides for breaking changes
- Keep documentation up-to-date with code changes

### Testing
- Write tests for all new functionality
- Maintain test coverage above 90%
- Include both positive and negative test cases
- Test error conditions and edge cases

### Performance
- Profile performance-critical code paths
- Use appropriate data structures and algorithms
- Implement caching where beneficial
- Monitor memory usage in long-running operations
