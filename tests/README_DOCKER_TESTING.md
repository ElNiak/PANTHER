# Docker Testing with pytest-docker

This document explains how to use `pytest-docker` for Docker integration testing in PANTHER.

## Overview

PANTHER now includes comprehensive Docker integration testing using the `pytest-docker` plugin. This enables testing of real Docker containers, services, and workflows without mocking.

## Installation

pytest-docker is included in the project dependencies:

```bash
# Install with test dependencies
pip install -e ".[tests]"

# Or install directly
pip install pytest-docker
```

## Configuration

### pyproject.toml
```toml
[project.optional-dependencies]
tests = [
    "pytest-docker>=3.1.0,<4.0",
    # ... other test dependencies
]
```

### pytest.ini
```ini
markers =
    requires_docker: Tests that require Docker daemon
    docker_integration: Tests using pytest-docker for real Docker integration
```

## Test Structure

### Basic Docker Client Test
```python
import pytest
import docker

@pytest.fixture(scope="session")
def docker_client():
    """Provide Docker client for tests."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")

class TestDockerIntegration:
    pytestmark = pytest.mark.requires_docker

    def test_docker_connectivity(self, docker_client):
        assert docker_client.ping() is True
```

### Docker Compose Integration
```python
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return Path("docker-compose.yml")

@pytest.fixture(scope="session")
def docker_compose_project_name():
    return "panther_test"
```

## Test Categories

### 1. CLI Docker Commands (`test_cli_docker_commands.py`)
Tests PANTHER CLI commands that interact with Docker:
- `panther admin docker status`
- `panther admin docker build`
- `panther admin docker clean`
- `panther admin docker logs`

### 2. Container Lifecycle (`test_docker_integration.py`)
Tests Docker container operations:
- Container creation and cleanup
- Resource monitoring
- Network operations
- Volume management

### 3. Security Validation
Tests Docker security aspects:
- Command injection prevention
- Privilege escalation prevention
- Resource limit validation

### 4. Performance Testing
Tests Docker performance characteristics:
- Container startup time
- Resource usage monitoring
- Concurrent operations

## Usage Examples

### Run All Docker Tests
```bash
pytest tests/integration/ -m requires_docker
```

### Run Specific Docker Test Categories
```bash
# CLI Docker commands only
pytest tests/integration/test_cli_docker_commands.py

# Container lifecycle tests
pytest tests/integration/test_docker_integration.py

# Performance tests (slow)
pytest tests/integration/ -m "requires_docker and slow"
```

### Skip Docker Tests
```bash
# Run all tests except Docker
pytest -m "not requires_docker"

# Run integration tests without Docker
pytest tests/integration/ -m "not requires_docker"
```

### Conditional Docker Testing
```bash
# Only run if Docker is available
pytest tests/integration/ -m docker_integration

# Skip slow Docker tests
pytest tests/integration/ -m "requires_docker and not slow"
```

## Docker Test Fixtures

### Available Fixtures

1. **docker_client**: Basic Docker client for container operations
2. **docker_compose_file**: Path to docker-compose.yml for service testing
3. **docker_compose_project_name**: Project name for compose testing

### Example Usage
```python
def test_container_operations(docker_client):
    # Create test container
    container = docker_client.containers.create(
        "alpine:latest",
        command="echo 'test'",
        name="test_container"
    )

    try:
        container.start()
        result = container.wait(timeout=10)
        assert result['StatusCode'] == 0
    finally:
        container.remove(force=True)
```

## Best Practices

### 1. Test Isolation
- Always clean up containers, networks, and volumes
- Use unique names for test resources
- Use try/finally blocks for cleanup

### 2. Performance
- Mark slow tests with `@pytest.mark.slow`
- Use session-scoped fixtures for expensive operations
- Prefer lightweight containers (alpine) for testing

### 3. Error Handling
- Skip tests gracefully when Docker is unavailable
- Handle Docker permission errors
- Test timeout scenarios

### 4. Resource Management
```python
def test_with_cleanup(docker_client):
    container = None
    try:
        container = docker_client.containers.create(...)
        # Test operations
    finally:
        if container:
            container.remove(force=True)
```

## Integration with PANTHER CLI

### Testing Admin Commands
```python
def test_admin_docker_status(docker_client):
    from panther.cli.subcommands.admin import AdminCommand

    args = create_namespace(
        admin_action="docker",
        docker_action="status"
    )

    result = AdminCommand._handle_docker(args)
    assert result in [0, 1]
```

### Testing Service Management
```python
def test_service_docker_integration(docker_client):
    # Test PANTHER service Docker operations
    # Verify service containers can be created
    # Test service networking and volumes
```

## Troubleshooting

### Common Issues

1. **Docker Not Available**
   ```
   SKIPPED [1] Docker not available: [Errno 2] No such file or directory: 'docker'
   ```
   - Install Docker Desktop or Docker Engine
   - Ensure Docker daemon is running
   - Check Docker permissions

2. **Permission Denied**
   ```
   docker.errors.APIError: 403 Client Error: Forbidden
   ```
   - Add user to docker group: `sudo usermod -aG docker $USER`
   - Restart terminal session
   - Check Docker socket permissions

3. **Resource Limits**
   ```
   docker.errors.APIError: 500 Server Error: Internal Server Error
   ```
   - Increase Docker memory/CPU limits
   - Clean up unused containers: `docker system prune`
   - Check available disk space

### Debug Commands
```bash
# Check Docker status
docker version
docker info

# List running containers
docker ps

# Check pytest-docker plugin
pytest --markers | grep docker

# Run with verbose Docker output
pytest tests/integration/ -v -s --tb=long
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Docker Integration Tests
on: [push, pull_request]

jobs:
  docker-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -e ".[tests]"

    - name: Run Docker integration tests
      run: |
        pytest tests/integration/ -m requires_docker
```

### Local Development
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run full test suite including Docker
pytest

# Run only Docker integration tests
pytest tests/integration/ -m docker_integration
```

## Advanced Features

### Custom Docker Fixtures
```python
@pytest.fixture
def panther_test_container(docker_client):
    """Create a PANTHER-specific test container."""
    container = docker_client.containers.create(
        "panther:latest",  # Assuming PANTHER Docker image
        environment={"PANTHER_ENV": "test"},
        name="panther_test_instance"
    )

    try:
        yield container
    finally:
        container.remove(force=True)
```

### Network Testing
```python
def test_panther_network_connectivity(docker_client):
    """Test PANTHER service network connectivity."""
    # Create test network
    network = docker_client.networks.create("panther_test_net")

    try:
        # Create containers on network
        # Test connectivity between services
        pass
    finally:
        network.remove()
```

### Volume Testing
```python
def test_panther_data_persistence(docker_client):
    """Test PANTHER data persistence with volumes."""
    volume = docker_client.volumes.create("panther_test_data")

    try:
        # Test data persistence across container restarts
        pass
    finally:
        volume.remove()
```

## References

- [pytest-docker documentation](https://pytest-docker.readthedocs.io/)
- [Docker Python SDK](https://docker-py.readthedocs.io/)
- [PANTHER Docker architecture](../../docker-compose.yml)
- [PANTHER CLI admin commands](../../panther/cli/subcommands/admin.py)
