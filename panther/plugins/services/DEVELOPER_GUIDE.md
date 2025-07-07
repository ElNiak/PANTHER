# Service Plugins Developer Guide

## Prerequisites

### Environment Setup

Set up your development environment:

```bash
# Clone the PANTHER repository
git clone <repository-url>
cd PANTHER

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .
pip install -r requirements-dev.txt
```

### Required Tools

Ensure these tools are installed:

- **Docker 27.x+**: For containerized service execution
- **Docker Compose**: For multi-service orchestration
- **Python 3.10+**: Core development language
- **pytest**: For running tests
- **pre-commit**: For code quality checks

## Development Workflow

### 1. Creating a New Service Plugin

#### Step 1: Choose Service Type

Determine whether you're creating:
- **IUT Service**: Implementation being tested
- **Tester Service**: Tool for testing/validation

#### Step 2: Select Base Class

Choose the appropriate base class:

```python
# For QUIC implementations
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

# For HTTP implementations
from panther.plugins.services.base.http_service_base import BaseHTTPServiceManager

# For custom protocols
from panther.plugins.services.services_interface import IServiceManager
```

#### Step 3: Create Directory Structure

```bash
# For IUT services
mkdir -p panther/plugins/services/iut/{protocol}/{implementation_name}
cd panther/plugins/services/iut/{protocol}/{implementation_name}

# Create required files
touch __init__.py
touch README.md
touch config_schema.py
touch {implementation_name}.py
mkdir -p templates
mkdir -p version_configs
```

#### Step 4: Implement Service Manager

```python
"""Example QUIC implementation service manager."""

from typing import Any, Dict, List, Union
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.core.command_processor.models import ShellCommand


class MyQUICServiceManager(BaseQUICServiceManager):
    """Service manager for MyQUIC implementation."""

    def __init__(self, service_config_to_test, service_type, protocol,
                 implementation_name, event_manager=None, test_case=None):
        """Initialize MyQUIC service manager.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service (IUT/TESTER)
            protocol: Protocol configuration
            implementation_name: Name of implementation
            event_manager: Event manager instance
            test_case: Parent test case reference
        """
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            test_case=test_case
        )

    def generate_deployment_commands(self) -> str:
        """Generate Docker Compose deployment configuration.

        Returns:
            Docker Compose YAML configuration as string
        """
        params = {
            "service_name": self.service_name,
            "implementation": self.implementation_name,
            "port": self.get_port(),
            "role": self.role,
            "volumes": self.volumes,
            "environment": self.environments
        }

        return self.render_commands(
            params=params,
            template_name="docker-compose.yml.j2"
        )

    def generate_run_command(self) -> Dict[str, Any]:
        """Generate main execution command.

        Returns:
            Command configuration dictionary
        """
        command_args = [
            f"--{self.role}",
            "--port", str(self.get_port()),
            "--cert", "/app/certs/cert.pem",
            "--key", "/app/certs/key.pem"
        ]

        if self.is_client():
            command_args.extend(["--host", self.get_server_host()])

        return {
            "working_dir": "/opt/myquic",
            "command_binary": "myquic_app",
            "command_args": command_args,
            "timeout": self.service_config_to_test.timeout,
            "environment": self.environments
        }

    def get_output_patterns(self) -> List[tuple]:
        """Define output patterns for this implementation.

        Returns:
            List of (output_type, filename_pattern) tuples
        """
        patterns = super().get_output_patterns()  # Get base QUIC patterns
        patterns.extend([
            ("myquic_log", "myquic_{service_name}.log"),
            ("debug_log", "debug_*.log"),
            ("performance", "perf_{service_name}.json")
        ])
        return patterns
```

### 2. Template Creation

Create Jinja2 templates for command generation:

#### Docker Compose Template (`templates/docker-compose.yml.j2`)

```yaml
version: '3.8'

services:
  {{ service_name }}:
    image: myquic:latest
    container_name: {{ service_name }}
    {% if role == "server" %}
    ports:
      - "{{ port }}:{{ port }}/udp"
    {% endif %}
    volumes:
      {% for volume in volumes %}
      - {{ volume }}
      {% endfor %}
    environment:
      {% for key, value in environment.items() %}
      {{ key }}: {{ value | quote_yaml }}
      {% endfor %}
    command: >
      myquic_app
      --{{ role }}
      --port {{ port }}
      {% if role == "client" %}
      --host {{ server_host | quote_shell }}
      {% endif %}
      --cert /app/certs/cert.pem
      --key /app/certs/key.pem
      --log-level {{ log_level | default("info") }}
      {% for arg in extra_args | default([]) %}
      {{ arg | quote_shell }}
      {% endfor %}
```

#### Run Command Template (`templates/run_command.sh.j2`)

```bash
#!/bin/bash
set -euo pipefail

# Setup logging
mkdir -p /app/logs
exec > >(tee -a /app/logs/stdout.log)
exec 2> >(tee -a /app/logs/stderr.log >&2)

# Environment setup
export QUIC_LOG_LEVEL={{ log_level | default("info") | quote_shell }}
export SSLKEYLOGFILE=/app/logs/sslkeylogfile.txt

# Start MyQUIC implementation
cd /opt/myquic
./myquic_app \
  --{{ role }} \
  --port {{ port }} \
  {% if role == "client" %}
  --host {{ server_host | quote_shell }} \
  {% endif %}
  --cert /app/certs/cert.pem \
  --key /app/certs/key.pem \
  --qlog-dir /app/logs \
  {% for arg in command_args %}
  {{ arg | quote_shell }} \
  {% endfor %}
```

### 3. Configuration Schema

Define configuration validation:

```python
"""Configuration schema for MyQUIC implementation."""

from cerberus import Validator


MYQUIC_CONFIG_SCHEMA = {
    "implementation": {
        "type": "dict",
        "schema": {
            "name": {"type": "string", "allowed": ["myquic"]},
            "version": {"type": "string", "regex": r"^\d+\.\d+\.\d+$"},
            "build_target": {"type": "string", "allowed": ["debug", "release"]},
            "enable_qlog": {"type": "boolean", "default": True},
            "enable_keylog": {"type": "boolean", "default": True},
            "congestion_control": {
                "type": "string",
                "allowed": ["cubic", "bbr", "newreno"],
                "default": "cubic"
            }
        }
    },
    "protocol": {
        "type": "dict",
        "schema": {
            "version": {"type": "string", "allowed": ["draft-29", "v1", "v2"]},
            "role": {"type": "string", "allowed": ["client", "server"]},
            "port": {"type": "integer", "min": 1024, "max": 65535},
            "alpn": {"type": "list", "schema": {"type": "string"}}
        }
    }
}


def validate_myquic_config(config: dict) -> tuple:
    """Validate MyQUIC service configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid: bool, errors: dict)
    """
    validator = Validator(MYQUIC_CONFIG_SCHEMA)
    is_valid = validator.validate(config)
    return is_valid, validator.errors
```

### 4. Testing Your Service

#### Unit Tests

```python
"""Unit tests for MyQUIC service manager."""

import pytest
from unittest.mock import Mock, patch
from panther.plugins.services.iut.quic.myquic.myquic import MyQUICServiceManager


class TestMyQUICServiceManager:
    """Test suite for MyQUIC service manager."""

    @pytest.fixture
    def service_config(self):
        """Create test service configuration."""
        config = Mock()
        config.name = "myquic_test"
        config.timeout = 60
        config.protocol.role = "server"
        config.protocol.port = 4433
        return config

    @pytest.fixture
    def service_manager(self, service_config):
        """Create MyQUIC service manager instance."""
        from panther.config.core.models import ProtocolConfig
        protocol = ProtocolConfig(name="quic", version="v1")

        return MyQUICServiceManager(
            service_config_to_test=service_config,
            service_type="iut",
            protocol=protocol,
            implementation_name="myquic"
        )

    def test_initialization(self, service_manager):
        """Test service manager initialization."""
        assert service_manager.implementation_name == "myquic"
        assert service_manager.service_type == "iut"

    def test_generate_run_command(self, service_manager):
        """Test run command generation."""
        cmd = service_manager.generate_run_command()

        assert cmd["command_binary"] == "myquic_app"
        assert "--server" in cmd["command_args"]
        assert "--port" in cmd["command_args"]
        assert str(4433) in cmd["command_args"]

    def test_deployment_command_generation(self, service_manager):
        """Test Docker Compose generation."""
        deployment = service_manager.generate_deployment_commands()

        assert "myquic_test:" in deployment
        assert "image: myquic:latest" in deployment
        assert "4433:4433/udp" in deployment

    def test_output_patterns(self, service_manager):
        """Test output pattern configuration."""
        patterns = service_manager.get_output_patterns()

        # Check for base QUIC patterns
        pattern_types = [p[0] for p in patterns]
        assert "qlog" in pattern_types
        assert "sslkeylog" in pattern_types

        # Check for MyQUIC-specific patterns
        assert "myquic_log" in pattern_types
        assert "performance" in pattern_types
```

#### Integration Tests

```python
"""Integration tests for MyQUIC service."""

import pytest
import tempfile
import docker
from pathlib import Path


@pytest.mark.integration
class TestMyQUICIntegration:
    """Integration tests requiring Docker."""

    @pytest.fixture
    def docker_client(self):
        """Get Docker client."""
        return docker.from_env()

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_container_execution(self, service_manager, docker_client, temp_output_dir):
        """Test service execution in container."""
        # Build test container
        container_name = f"test-myquic-{os.getpid()}"

        try:
            # Generate deployment
            deployment = service_manager.generate_deployment_commands()

            # Write compose file
            compose_file = temp_output_dir / "docker-compose.yml"
            compose_file.write_text(deployment)

            # Run service
            result = subprocess.run([
                "docker-compose", "-f", str(compose_file),
                "up", "--build", "--timeout", "30"
            ], capture_output=True, text=True)

            assert result.returncode == 0

            # Check outputs
            log_patterns = service_manager.get_output_patterns()
            for output_type, pattern in log_patterns:
                if "*" not in pattern:  # Skip glob patterns
                    expected_file = temp_output_dir / pattern.format(
                        service_name=service_manager.service_name
                    )
                    assert expected_file.exists(), f"Missing output: {output_type}"

        finally:
            # Cleanup
            subprocess.run([
                "docker-compose", "-f", str(compose_file), "down", "-v"
            ], capture_output=True)
```

### 5. Docker Image Creation

Create a Dockerfile for your implementation:

```dockerfile
# Multi-stage build for MyQUIC
FROM ubuntu:22.04 AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Clone and build MyQUIC
WORKDIR /src
RUN git clone https://github.com/example/myquic.git .
RUN mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc)

# Runtime stage
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy built application
COPY --from=builder /src/build/myquic_app /usr/local/bin/
COPY --from=builder /src/build/lib*.so* /usr/local/lib/

# Setup application environment
RUN useradd -m -u 1000 myquic
USER myquic
WORKDIR /opt/myquic

# Create required directories
RUN mkdir -p /app/logs /app/certs

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/myquic_app"]
```

## Debugging and Troubleshooting

### Common Issues

#### 1. Template Rendering Errors

**Problem**: Jinja2 template errors during command generation

**Solution**:
```python
# Add debug logging
self.logger.debug("Template parameters: %s", params)
try:
    result = self.render_commands(params, template_name)
    self.logger.debug("Rendered command: %s", result)
except Exception as e:
    self.logger.error("Template rendering failed: %s", e)
    raise
```

#### 2. Container Startup Failures

**Problem**: Service containers fail to start

**Debugging steps**:
```bash
# Check container logs
docker logs <container_name>

# Inspect container configuration
docker inspect <container_name>

# Test image manually
docker run -it --entrypoint /bin/bash <image_name>
```

#### 3. Output Collection Issues

**Problem**: Expected outputs not collected

**Solution**:
```python
def debug_output_patterns(self):
    """Debug output pattern resolution."""
    patterns = self.get_output_patterns()
    for output_type, pattern in patterns:
        resolved = pattern.format(service_name=self.service_name)
        self.logger.debug(f"Pattern {output_type}: {pattern} -> {resolved}")
```

### Performance Optimization

#### 1. Container Build Times

- Use multi-stage builds to reduce image size
- Cache dependencies in separate layers
- Use .dockerignore to exclude unnecessary files

#### 2. Template Rendering

- Cache compiled templates
- Minimize template complexity
- Use structured parameters instead of string concatenation

#### 3. Output Collection

- Use specific patterns instead of broad globs
- Implement streaming for large outputs
- Configure log rotation for long-running services

## Code Quality Standards

### 1. Code Style

Follow PEP 8 and use automated tools:

```bash
# Format code
black panther/plugins/services/iut/quic/myquic/

# Check style
flake8 panther/plugins/services/iut/quic/myquic/

# Type checking
mypy panther/plugins/services/iut/quic/myquic/
```

### 2. Documentation

All public methods must have docstrings following Google style:

```python
def generate_run_command(self) -> Dict[str, Any]:
    """Generate the main execution command for the service.

    Creates a structured command configuration that will be used
    to execute the service implementation within its container.

    Returns:
        A dictionary containing:
            - working_dir: Directory to execute command in
            - command_binary: Executable name or path
            - command_args: List of command arguments
            - timeout: Maximum execution time in seconds
            - environment: Environment variables dict

    Raises:
        ConfigurationError: If required configuration is missing
        TemplateError: If command template rendering fails

    Example:
        >>> cmd = service.generate_run_command()
        >>> cmd['command_binary']
        'myquic_app'
        >>> '--server' in cmd['command_args']
        True
    """
```

### 3. Testing Requirements

- **Unit test coverage**: Minimum 80%
- **Integration tests**: For all service lifecycle methods
- **Property-based tests**: For complex configuration validation
- **Docker tests**: For containerized execution

### 4. Error Handling

Implement comprehensive error handling:

```python
class MyQUICServiceManager(BaseQUICServiceManager):

    def generate_run_command(self) -> Dict[str, Any]:
        """Generate run command with proper error handling."""
        try:
            # Validate configuration
            if not self.service_config_to_test:
                raise ConfigurationError("Service configuration not provided")

            # Generate command
            return self._build_run_command()

        except ConfigurationError:
            self.logger.error("Configuration error in %s", self.service_name)
            raise
        except Exception as e:
            self.logger.error("Unexpected error generating run command: %s", e)
            self.notify_service_error(
                error_type="command_generation_failed",
                error_message=str(e),
                details={"service_name": self.service_name}
            )
            raise
```

## Release Process

### 1. Version Management

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases with service-specific versions
- Maintain compatibility matrices

### 2. Testing Pipeline

Before release, ensure:
- All unit tests pass
- Integration tests pass in all environments
- Docker images build successfully
- Documentation is updated

### 3. Deployment

Services are deployed through:
- Docker image registry updates
- Plugin configuration updates
- Compatibility testing with existing services

---

*This guide provides comprehensive instructions for developing, testing, and maintaining service plugins within the PANTHER framework, following established patterns and best practices.*
