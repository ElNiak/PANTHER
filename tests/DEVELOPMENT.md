# PANTHER Development Guide

This document provides comprehensive information for developers working on PANTHER, including testing guidelines, development workflows, and contribution standards.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Testing Framework](#testing-framework)
- [Test Coverage Requirements](#test-coverage-requirements)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Code Quality](#code-quality)
- [Contribution Guidelines](#contribution-guidelines)

## Development Environment Setup

### Prerequisites

- Python 3.8+
- Docker
- Git

### Installing Development Dependencies

```bash
# Install development dependencies
pip install -e .[dev]

# Or install test dependencies separately
pip install pytest pytest-cov pytest-mock hypothesis
```

### Setting up Pre-commit Hooks

```bash
pre-commit install
```

## Testing Framework

PANTHER uses a comprehensive testing framework with multiple layers:

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── builder/                       # Builder script tests
│   ├── test_builder_unit.py      # Unit tests for BuildManager
│   ├── test_builder_edge_cases.py # Edge cases and error conditions
│   └── test_builder_hypothesis.py # Property-based testing
├── config/                        # Configuration layer tests
│   └── test_config_unit.py       # Config manager and schema tests
├── core/                          # Core functionality tests
│   └── test_core_unit.py         # ExperimentManager tests
└── integration/                   # Integration tests
    └── test_cli_integration.py   # End-to-end CLI testing
```

### Testing Libraries

- **pytest**: Main testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **hypothesis**: Property-based testing

## Test Coverage Requirements

PANTHER maintains strict coverage requirements:

- **Builder (`panther_builder.py`)**: ≥90% coverage
- **Config layer (`panther/config/*`)**: ≥85% coverage
- **Core layer (`panther/core/*`)**: ≥85% coverage

### Coverage Exclusions

The following are excluded from coverage requirements:
- Abstract base classes
- Exception handling for system-level failures
- Debug-only code paths
- Platform-specific fallbacks

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/builder/
pytest tests/config/
pytest tests/core/
pytest tests/integration/

# Run with verbose output
pytest -v

# Run only fast tests (skip slow tests)
pytest -m "not slow"

# Run only slow tests
pytest -m "slow"
```

### Coverage Analysis

```bash
# Run tests with coverage
pytest --cov=panther_builder --cov=panther.config --cov=panther.core

# Generate HTML coverage report
pytest --cov=panther_builder --cov=panther.config --cov=panther.core --cov-report=html

# Coverage with specific thresholds
pytest --cov=panther_builder --cov-fail-under=90 \
       --cov=panther.config --cov-fail-under=85 \
       --cov=panther.core --cov-fail-under=85
```

### Performance Testing

```bash
# Run performance benchmarks
pytest tests/integration/ -k "performance"

# Time all tests
pytest --durations=0
```

## Writing Tests

### Test Categories

#### 1. Unit Tests

**Purpose**: Test individual components in isolation with mocked dependencies.

**Characteristics**:
- Fast execution (< 1s per test)
- Deterministic behavior
- Extensive mocking of external dependencies
- High coverage of public methods

**Example**:
```python
def test_build_manager_initialization(mock_docker_client):
    """Test BuildManager initializes correctly with valid parameters."""
    with patch('panther_builder.docker.from_env', return_value=mock_docker_client):
        manager = BuildManager("/test/path")
        assert manager.project_path == Path("/test/path")
        assert manager.docker_client is not None
```

#### 2. Integration Tests

**Purpose**: Test component interactions and end-to-end workflows.

**Characteristics**:
- May take longer (marked with `@pytest.mark.slow`)
- Real CLI invocation
- Temporary file system usage
- Resource cleanup

**Example**:
```python
@pytest.mark.slow
def test_cli_build_command(integration_workspace):
    """Test complete build workflow through CLI."""
    result = subprocess.run([
        sys.executable, "panther_builder.py", "build",
        "--project-path", str(integration_workspace)
    ], capture_output=True, text=True, timeout=30)

    assert result.returncode == 0
```

#### 3. Property-Based Tests

**Purpose**: Test invariants across a wide range of inputs using Hypothesis.

**Characteristics**:
- Automatic test case generation
- Edge case discovery
- Invariant verification

**Example**:
```python
@given(project_path=st.text(min_size=1, max_size=100))
def test_build_manager_path_handling(project_path):
    """Test BuildManager handles various path inputs correctly."""
    # Test implementation
```

### Test Fixtures

PANTHER provides comprehensive fixtures in `conftest.py`:

#### Builder Fixtures
- `mock_docker_client`: Mocked Docker client
- `mock_subprocess`: Mocked subprocess operations
- `temp_project_dir`: Temporary project directory
- `builder_instance`: Configured BuildManager instance

#### Config Fixtures
- `temp_config_dir`: Temporary configuration directory
- `sample_global_config`: Sample global configuration
- `config_loader_instance`: Configured ConfigLoader

#### Core Fixtures
- `mock_experiment_manager`: Mocked ExperimentManager
- `mock_plugin_manager`: Mocked plugin system

#### Integration Fixtures
- `integration_workspace`: Complete temporary workspace
- `performance_timer`: Performance measurement utilities

### Mocking Guidelines

1. **Mock External Dependencies**: Always mock Docker, subprocess, file system operations
2. **Use Appropriate Mock Types**:
   - `Mock` for simple objects
   - `MagicMock` for complex objects with magic methods
   - `patch` for replacing imports
3. **Verify Mock Calls**: Use `assert_called_with()`, `assert_called_once()`, etc.
4. **Reset Mocks**: Use `reset_mock()` or fresh fixtures

### Error Testing

Test both expected and unexpected error conditions:

```python
def test_build_manager_docker_error(mock_docker_client):
    """Test BuildManager handles Docker connection errors."""
    mock_docker_client.ping.side_effect = docker.errors.APIError("Connection failed")

    with pytest.raises(RuntimeError, match="Docker connection failed"):
        BuildManager("/test/path")
```

### Performance Guidelines

- **Fast Tests**: Unit tests should complete in < 1s
- **Slow Tests**: Mark longer tests with `@pytest.mark.slow`
- **Timeouts**: Use `timeout` parameter for subprocess calls
- **Resource Cleanup**: Always clean up temporary resources

## Code Quality

### Linting and Formatting

```bash
# Run flake8
flake8 panther_builder.py panther/

# Run black formatter
black panther_builder.py panther/

# Run isort
isort panther_builder.py panther/
```

### Type Checking

```bash
# Run mypy
mypy panther_builder.py panther/
```

### Security Scanning

```bash
# Run bandit
bandit -r panther/

# Run safety
safety check
```

## Continuous Integration

### GitHub Actions

PANTHER uses GitHub Actions for CI/CD:

- **Unit Tests**: Run on every PR and push
- **Coverage**: Enforce coverage thresholds
- **Integration Tests**: Run on release branches
- **Code Quality**: Linting, formatting, security scans

### Local CI Simulation

```bash
# Run the full CI pipeline locally
make ci

# Or run individual stages
make test
make lint
make security
```

## Contribution Guidelines

### Pull Request Process

1. **Create Feature Branch**: `git checkout -b feature/your-feature`
2. **Write Tests**: Add comprehensive tests for new functionality
3. **Run Tests**: Ensure all tests pass locally
4. **Update Documentation**: Update relevant documentation
5. **Submit PR**: Create pull request with clear description

### Code Review Checklist

- [ ] Tests cover new functionality
- [ ] Coverage thresholds maintained
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] Security considerations addressed
- [ ] Performance impact assessed

### Testing Requirements for PRs

- All tests must pass
- Coverage thresholds must be maintained
- New features require comprehensive tests
- Bug fixes require regression tests

## Debugging Tests

### Common Issues

1. **Import Errors**: Check PYTHONPATH and package installation
2. **Mock Failures**: Verify mock setup and patch targets
3. **Flaky Tests**: Add proper setup/teardown and deterministic behavior
4. **Timeout Issues**: Increase timeouts or optimize test logic

### Debugging Tools

```bash
# Run with pdb debugger
pytest --pdb

# Show local variables on failure
pytest --tb=long -vv

# Disable output capture for debugging
pytest -s
```

### Test Isolation

Ensure tests are properly isolated:
- Use temporary directories for file operations
- Reset global state between tests
- Mock external dependencies consistently
- Clean up resources in teardown

## Performance Optimization

### Test Performance

- Keep unit tests under 1 second
- Use `@pytest.mark.slow` for longer tests
- Optimize fixture setup/teardown
- Minimize file I/O in fast tests

### CI Performance

- Parallelize test execution where possible
- Cache dependencies
- Optimize Docker operations
- Use appropriate timeout values

## Troubleshooting

### Common Test Failures

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError` | Install package in development mode: `pip install -e .` |
| `Docker connection failed` | Ensure Docker daemon is running |
| `Permission denied` | Check file/directory permissions |
| `Timeout` | Increase timeout values or optimize test logic |

### Getting Help

- Check existing issues on GitHub
- Review test documentation
- Ask questions in discussions
- Contact maintainers for complex issues

---

*This document is maintained by the PANTHER development team. For questions or suggestions, please open an issue or discussion on GitHub.*
