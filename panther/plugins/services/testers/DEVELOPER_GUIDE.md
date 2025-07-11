# PANTHER Tester Services Developer Guide

## Overview

This guide covers development workflows, debugging techniques, and best practices for working with PANTHER tester services. Whether you're developing new tester plugins, debugging existing ones, or contributing to the framework, this guide provides practical knowledge for effective development.

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Docker 27.x+ with Docker Compose
- Git with submodule support
- Z3 theorem prover (for Ivy formal verification)
- Basic understanding of formal verification concepts

### Environment Installation

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/ElNiak/PANTHER.git
cd PANTHER

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Verify installation
python -c "import panther; print(panther.__version__)"
```

### Docker Environment Setup

```bash
# Build base containers
docker-compose -f docker/docker-compose.dev.yml build

# Verify Docker setup
docker run --rm panther/ivy:latest ivy_check --help
```

### IDE Configuration

#### VS Code Setup

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.watcherExclude": {
        "**/build/**": true,
        "**/temp/**": true,
        "**/.ivy/**": true
    }
}
```

#### PyCharm Setup

1. Open project in PyCharm
2. Configure Python interpreter: Settings → Project → Python Interpreter
3. Add source roots: Settings → Project → Project Structure
4. Configure test runner: Settings → Tools → Python Integrated Tools

## Development Workflow

### Branch Strategy

```bash
# Create feature branch
git checkout -b feature/new-tester-plugin

# Work on changes
git add .
git commit -m "feat: add custom tester plugin"

# Push for review
git push origin feature/new-tester-plugin
```

### Code Quality Standards

#### Linting and Formatting

```bash
# Format code
black panther/plugins/services/testers/

# Run linting
pylint panther/plugins/services/testers/

# Type checking
mypy panther/plugins/services/testers/

# Import sorting
isort panther/plugins/services/testers/
```

#### Testing Requirements

```bash
# Run unit tests
pytest tests/plugins/services/testers/ -v

# Run integration tests
pytest tests/integration/testers/ -v

# Run with coverage
pytest --cov=panther.plugins.services.testers tests/

# Generate coverage report
coverage html
```

### Creating a New Tester Plugin

#### 1. Plugin Structure

```
my_custom_tester/
├── __init__.py
├── my_custom_tester.py           # Main implementation
├── config_schema.py              # Configuration validation
├── command_mixin.py              # Command generation
├── analysis_mixin.py             # Output analysis
├── templates/                    # Docker and config templates
│   ├── Dockerfile
│   └── docker-compose.yml.jinja
├── version_configs/              # Version-specific configs
│   └── default.yaml
├── tests/                        # Unit tests
│   ├── test_custom_tester.py
│   └── test_config.py
└── README.md                     # Plugin documentation
```

#### 2. Base Implementation

```python
# my_custom_tester.py
from typing import Dict, Any, List, Union
from panther.plugins.services.testers.tester_interface import ITesterManager
from panther.plugins.services.testers.tester_event_mixin import TesterManagerEventMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.core.command_processor.models.shell_command import ShellCommand

@register_plugin(
    plugin_type=PluginType.TESTER,
    name="my_custom_tester",
    version="1.0.0",
    description="Custom protocol tester implementation",
    supported_protocols=["custom_protocol"],
    external_dependencies=["custom_tool=1.0"]
)
class MyCustomTesterServiceManager(ITesterManager, TesterManagerEventMixin):
    """Custom tester service manager implementation."""

    def __init__(self, service_config_to_test, service_type, protocol,
                 implementation_name, event_manager=None, test_case=None, **kwargs):
        super().__init__(service_config_to_test, service_type, protocol,
                        implementation_name, event_manager, test_case)

        # Initialize custom attributes
        self.test_scenarios = getattr(service_config_to_test, 'test_scenarios', [])
        self.custom_parameters = getattr(service_config_to_test, 'custom_parameters', {})

    def _do_run_tests(self) -> Dict[str, Any]:
        """Execute custom tests and return results."""
        try:
            self.logger.info(f"Running custom tests for {self.service_name}")

            # Initialize results
            results = {
                "success": False,
                "test_name": getattr(self, 'test_name', 'unknown'),
                "outputs": {},
                "analysis": {},
                "errors": []
            }

            # Use collected outputs if available
            if hasattr(self, '_collected_outputs') and self._collected_outputs:
                outputs = self._collected_outputs
            else:
                outputs = self.collect_outputs()

            results["outputs"] = outputs

            # Analyze outputs
            analysis = self.analyze_outputs()
            results["analysis"] = analysis
            results["success"] = analysis.get("success", False)

            if not results["success"]:
                results["errors"].append(analysis.get("error", "Test failed"))

            return results

        except Exception as e:
            error_msg = f"Error running custom tests: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "test_name": getattr(self, 'test_name', 'unknown'),
                "outputs": {},
                "analysis": {},
                "errors": [error_msg]
            }

    def set_collected_outputs(self, outputs: Dict[str, Any]) -> None:
        """Set collected outputs for analysis."""
        self._collected_outputs = outputs
        self.logger.debug(f"Set collected outputs: {len(outputs)} items")

    def analyze_outputs(self) -> Dict[str, Any]:
        """Analyze collected outputs."""
        try:
            # Implement custom analysis logic
            outputs = getattr(self, '_collected_outputs', {})

            # Example analysis
            success = self._check_test_success(outputs)
            warnings = self._check_warnings(outputs)

            return {
                "success": success,
                "warnings": warnings,
                "summary": "Custom test analysis completed"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": "Analysis failed"
            }

    def get_test_results(self) -> Dict[str, Any]:
        """Get final test results."""
        if hasattr(self, '_final_results'):
            return self._final_results
        return {"success": False, "error": "No results available"}

    def _check_test_success(self, outputs: Dict[str, Any]) -> bool:
        """Check if tests passed based on outputs."""
        # Implement success criteria
        return True

    def _check_warnings(self, outputs: Dict[str, Any]) -> List[str]:
        """Extract warnings from outputs."""
        # Implement warning detection
        return []
```

#### 3. Configuration Schema

```python
# config_schema.py
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import ImplementationType

class MyCustomTesterConfig(ServicePluginConfig):
    """Configuration schema for custom tester."""

    name: str = Field(default="my_custom_tester", description="Tester name")
    type: ImplementationType = Field(default=ImplementationType.TESTERS)

    # Custom configuration fields
    test_scenarios: List[str] = Field(
        default_factory=list,
        description="List of test scenarios to execute"
    )
    verification_depth: int = Field(
        default=10,
        description="Depth of verification analysis"
    )
    custom_parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom parameters for test execution"
    )
    timeout: int = Field(
        default=120,
        description="Test execution timeout in seconds"
    )
    output_format: str = Field(
        default="json",
        description="Output format for test results",
        pattern=r"^(json|xml|yaml)$"
    )
```

#### 4. Command Generation Mixin

```python
# command_mixin.py
from typing import List, Union
from panther.core.command_processor.models.shell_command import ShellCommand

class MyCustomTesterCommandMixin:
    """Mixin for generating custom tester commands."""

    def generate_pre_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate setup commands."""
        return [
            "apt-get update",
            "apt-get install -y custom-tool",
            "custom-tool --version"
        ]

    def generate_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate compilation commands."""
        build_dir = getattr(self, 'build_dir', 'build')
        return [
            f"mkdir -p {build_dir}",
            f"cd {build_dir}",
            "custom-tool compile --input ../src --output ./executable"
        ]

    def generate_run_command(self) -> Dict[str, Any]:
        """Generate execution command."""
        test_name = getattr(self, 'test_name', 'default_test')
        return {
            "working_dir": "/app",
            "command_binary": f"./build/executable",
            "command_args": [f"--test={test_name}", "--verbose"],
            "timeout": getattr(self, 'timeout', 120),
            "command_env": {"CUSTOM_LOG_LEVEL": "DEBUG"}
        }

    def generate_post_run_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate cleanup commands."""
        return [
            "cp /app/logs/*.log /app/outputs/",
            "cp /app/results/*.json /app/outputs/"
        ]
```

### Testing Development

#### Unit Testing

```python
# tests/test_custom_tester.py
import pytest
from unittest.mock import Mock, patch
from panther.plugins.services.testers.my_custom_tester import MyCustomTesterServiceManager

class TestMyCustomTester:

    @pytest.fixture
    def tester_config(self):
        """Create test configuration."""
        config = Mock()
        config.name = "test_custom_tester"
        config.test_scenarios = ["scenario1", "scenario2"]
        config.timeout = 60
        return config

    @pytest.fixture
    def tester(self, tester_config):
        """Create tester instance."""
        protocol = Mock()
        protocol.name = "custom_protocol"

        return MyCustomTesterServiceManager(
            service_config_to_test=tester_config,
            service_type="TESTERS",
            protocol=protocol,
            implementation_name="my_custom_tester"
        )

    def test_initialization(self, tester):
        """Test tester initialization."""
        assert tester.service_name == "test_custom_tester"
        assert tester.test_scenarios == ["scenario1", "scenario2"]

    def test_set_collected_outputs(self, tester):
        """Test output collection."""
        outputs = {"log": "test log content", "result": "test result"}
        tester.set_collected_outputs(outputs)

        assert hasattr(tester, '_collected_outputs')
        assert tester._collected_outputs == outputs

    def test_analyze_outputs_success(self, tester):
        """Test successful output analysis."""
        outputs = {"log": "SUCCESS: All tests passed"}
        tester.set_collected_outputs(outputs)

        with patch.object(tester, '_check_test_success', return_value=True):
            analysis = tester.analyze_outputs()

        assert analysis["success"] is True
        assert "summary" in analysis

    def test_run_tests_integration(self, tester):
        """Test complete test execution."""
        outputs = {"log": "test execution log"}
        tester.set_collected_outputs(outputs)

        with patch.object(tester, 'analyze_outputs') as mock_analyze:
            mock_analyze.return_value = {"success": True, "summary": "Tests passed"}

            results = tester._do_run_tests()

        assert results["success"] is True
        assert "outputs" in results
        assert "analysis" in results
```

#### Integration Testing

```python
# tests/test_integration.py
import pytest
import tempfile
import shutil
from pathlib import Path

class TestCustomTesterIntegration:

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_full_workflow(self, temp_workspace):
        """Test complete tester workflow."""
        # Set up test files
        (temp_workspace / "test_input.txt").write_text("test data")

        # Create and configure tester
        config = self._create_test_config()
        tester = MyCustomTesterServiceManager(
            service_config_to_test=config,
            service_type="TESTERS",
            protocol=Mock(),
            implementation_name="my_custom_tester"
        )

        # Execute test workflow
        results = tester.run_tests()

        # Verify results
        assert "success" in results
        assert "outputs" in results

    def _create_test_config(self):
        """Create realistic test configuration."""
        config = Mock()
        config.name = "integration_test"
        config.test_scenarios = ["integration_scenario"]
        config.timeout = 30
        return config
```

## Debugging Techniques

### Logging Configuration

#### Enable Debug Logging

```python
import logging

# Configure logging for development
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# Enable specific logger
logger = logging.getLogger('panther.plugins.services.testers')
logger.setLevel(logging.DEBUG)
```

#### Docker Container Debugging

```bash
# Run container interactively
docker run -it --rm \
  -v $(pwd):/workspace \
  panther/tester:latest /bin/bash

# Execute commands manually
cd /workspace
python -c "import panther.plugins.services.testers; print('Import successful')"

# Check environment
env | grep PANTHER
env | grep IVY
```

### Common Issues and Solutions

#### 1. Plugin Registration Issues

**Problem**: Plugin not found during discovery

```python
# Check plugin registration
from panther.plugins.plugin_manager import PluginManager

manager = PluginManager()
available_plugins = manager.discover_plugins()
print("Available tester plugins:", [p.name for p in available_plugins if p.plugin_type == "TESTER"])
```

**Solution**: Verify `@register_plugin` decorator and ensure module is imported

#### 2. Configuration Validation Errors

**Problem**: Pydantic validation failures

```python
# Debug configuration loading
from panther.plugins.services.testers.my_custom_tester.config_schema import MyCustomTesterConfig

try:
    config = MyCustomTesterConfig(**config_dict)
except ValidationError as e:
    print("Validation errors:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
```

**Solution**: Check field types and constraints in schema

#### 3. Docker Build Failures

**Problem**: Container build errors

```bash
# Build with debug output
docker build --no-cache --progress=plain -t my-tester .

# Check intermediate layers
docker run --rm -it <intermediate_layer_id> /bin/bash
```

**Solution**: Verify Dockerfile syntax and dependency availability

#### 4. Test Execution Timeouts

**Problem**: Tests timeout during execution

```python
# Increase timeout in configuration
config.timeout = 300  # 5 minutes

# Add progress logging
def _do_run_tests(self):
    self.logger.info("Starting test execution")
    # ... test code ...
    self.logger.info("Test execution completed")
```

**Solution**: Adjust timeout values and add progress indicators

### Performance Profiling

#### Memory Usage Analysis

```python
import tracemalloc
import psutil
import os

def profile_memory_usage():
    """Profile memory usage during test execution."""
    tracemalloc.start()

    # Execute tests
    tester = MyCustomTesterServiceManager(...)
    results = tester.run_tests()

    # Get memory statistics
    current, peak = tracemalloc.get_traced_memory()
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    print(f"Current memory: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
    print(f"RSS memory: {memory_info.rss / 1024 / 1024:.2f} MB")

    tracemalloc.stop()
```

#### Execution Time Profiling

```python
import cProfile
import pstats

def profile_execution_time():
    """Profile execution time for performance optimization."""
    profiler = cProfile.Profile()

    profiler.enable()

    # Execute tests
    tester = MyCustomTesterServiceManager(...)
    results = tester.run_tests()

    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Show top 10 functions
```

## Best Practices

### Code Organization

#### Mixin Pattern Usage

```python
# Good: Focused mixins with single responsibilities
class CommandGenerationMixin:
    """Handles command generation only."""

class OutputAnalysisMixin:
    """Handles output analysis only."""

class NetworkResolutionMixin:
    """Handles network configuration only."""

# Combine in main class
class MyTester(CommandGenerationMixin, OutputAnalysisMixin, NetworkResolutionMixin):
    """Main tester combining focused mixins."""
```

#### Error Handling

```python
# Good: Comprehensive error handling with context
def _do_run_tests(self) -> Dict[str, Any]:
    try:
        results = self._execute_tests()
        return results
    except ConfigurationError as e:
        self.logger.error(f"Configuration error: {e}")
        return {"success": False, "error": "Configuration invalid", "details": str(e)}
    except ExecutionError as e:
        self.logger.error(f"Execution error: {e}")
        return {"success": False, "error": "Execution failed", "details": str(e)}
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}", exc_info=True)
        return {"success": False, "error": "Unexpected failure", "details": str(e)}
```

### Configuration Management

#### Version-Specific Configurations

```yaml
# version_configs/v1.0.yaml
version: "1.0"
commit: "abc123"
parameters:
  optimization_level: "O2"
  debug_symbols: false
environment:
  TOOL_VERSION: "1.0"
  PERFORMANCE_MODE: "true"

# version_configs/v1.1.yaml
version: "1.1"
commit: "def456"
parameters:
  optimization_level: "O3"
  debug_symbols: true
  new_feature_enabled: true
environment:
  TOOL_VERSION: "1.1"
  PERFORMANCE_MODE: "true"
  FEATURE_FLAGS: "new_feature"
```

#### Environment-Specific Settings

```python
# Development configuration
development_config = {
    "log_level": "DEBUG",
    "timeout": 30,
    "debug_mode": True,
    "detailed_output": True
}

# Production configuration
production_config = {
    "log_level": "INFO",
    "timeout": 300,
    "debug_mode": False,
    "detailed_output": False
}

# Test configuration
test_config = {
    "log_level": "DEBUG",
    "timeout": 10,
    "debug_mode": True,
    "mock_external_services": True
}
```

### Documentation Standards

#### Docstring Format

```python
def analyze_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze collected test outputs to determine success/failure.

    Examines log files, result files, and execution artifacts to determine
    whether the test execution was successful and extract relevant metrics.

    Args:
        outputs: Dictionary of collected outputs organized by type
                Example: {"log": "log content", "result": "result data"}

    Returns:
        Dict[str, Any]: Analysis results containing:
            - success: bool - Whether test passed
            - warnings: List[str] - Warning messages
            - errors: List[str] - Error messages
            - metrics: Dict[str, float] - Extracted metrics
            - summary: str - Human-readable summary

    Raises:
        AnalysisError: When output analysis fails due to invalid format
        ValueError: When required outputs are missing

    Example:
        >>> outputs = {"log": "TEST PASSED", "metrics": "latency=10ms"}
        >>> result = tester.analyze_outputs(outputs)
        >>> print(result["success"])
        True
    """
```

### Testing Strategies

#### Test Organization

```python
# Organize tests by functionality
tests/
├── unit/
│   ├── test_config.py          # Configuration testing
│   ├── test_commands.py        # Command generation testing
│   ├── test_analysis.py        # Output analysis testing
│   └── test_events.py          # Event handling testing
├── integration/
│   ├── test_workflow.py        # End-to-end workflow
│   ├── test_docker.py          # Docker integration
│   └── test_networking.py      # Network functionality
└── fixtures/
    ├── sample_configs/         # Test configurations
    ├── sample_outputs/         # Expected outputs
    └── mock_data/             # Mock test data
```

#### Test Data Management

```python
# fixtures/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def sample_outputs():
    """Load sample test outputs."""
    fixtures_dir = Path(__file__).parent / "sample_outputs"
    return {
        "success_log": (fixtures_dir / "success.log").read_text(),
        "failure_log": (fixtures_dir / "failure.log").read_text(),
        "metrics_json": json.loads((fixtures_dir / "metrics.json").read_text())
    }

@pytest.fixture
def tester_config():
    """Create standard test configuration."""
    return {
        "name": "test_tester",
        "timeout": 30,
        "test_scenarios": ["basic_test"],
        "debug_mode": True
    }
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/tester-ci.yml
name: Tester Services CI

on:
  push:
    branches: [main, develop]
    paths: ['panther/plugins/services/testers/**']
  pull_request:
    branches: [main]
    paths: ['panther/plugins/services/testers/**']

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11]

    steps:
    - uses: actions/checkout@v3
      with:
        submodules: recursive

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .

    - name: Run linting
      run: |
        pylint panther/plugins/services/testers/
        black --check panther/plugins/services/testers/
        isort --check-only panther/plugins/services/testers/

    - name: Run type checking
      run: mypy panther/plugins/services/testers/

    - name: Run unit tests
      run: pytest tests/plugins/services/testers/ -v --cov=panther.plugins.services.testers

    - name: Run integration tests
      run: pytest tests/integration/testers/ -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  docker-test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
      with:
        submodules: recursive

    - name: Build Docker images
      run: docker-compose -f docker/docker-compose.test.yml build

    - name: Run Docker tests
      run: docker-compose -f docker/docker-compose.test.yml run --rm test-runner
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        args: [--line-length=88]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/pylint
    rev: v3.0.0a5
    hooks:
      - id: pylint
        args: [--rcfile=.pylintrc]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
```

## Troubleshooting Guide

### Plugin Loading Issues

**Symptom**: `PluginNotFoundError: Plugin 'my_tester' not found`

**Diagnosis**:
```python
import sys
from panther.plugins.plugin_manager import PluginManager

# Check if module is importable
try:
    import panther.plugins.services.testers.my_custom_tester
    print("Module import successful")
except ImportError as e:
    print(f"Import error: {e}")

# Check plugin registration
manager = PluginManager()
plugins = manager.discover_plugins()
tester_plugins = [p for p in plugins if p.plugin_type.value == "TESTER"]
print("Registered tester plugins:", [p.name for p in tester_plugins])
```

**Solution**: Verify plugin registration decorator and module import paths

### Configuration Validation Failures

**Symptom**: `ValidationError: Invalid configuration`

**Diagnosis**:
```python
from pydantic import ValidationError
from panther.plugins.services.testers.my_custom_tester.config_schema import MyCustomTesterConfig

config_data = {...}  # Your configuration
try:
    config = MyCustomTesterConfig(**config_data)
    print("Configuration valid")
except ValidationError as e:
    print("Validation errors:")
    for error in e.errors():
        print(f"  Field: {error['loc']}")
        print(f"  Error: {error['msg']}")
        print(f"  Value: {error.get('input', 'N/A')}")
```

**Solution**: Fix configuration fields according to schema requirements

### Docker Container Issues

**Symptom**: Container build or runtime failures

**Diagnosis**:
```bash
# Check Docker daemon
docker version

# Verify base image
docker pull python:3.10-slim

# Build with verbose output
docker build --no-cache --progress=plain -t my-tester .

# Test container interactively
docker run -it --rm my-tester /bin/bash
```

**Solution**: Fix Dockerfile issues and dependency problems

### Memory and Performance Issues

**Symptom**: High memory usage or slow execution

**Diagnosis**:
```python
# Monitor memory usage
import psutil
import os

def monitor_resources():
    process = psutil.Process(os.getpid())
    print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"CPU: {process.cpu_percent()}%")

# Profile specific functions
import cProfile

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # Your function call
    result = tester.run_tests()

    profiler.disable()
    profiler.print_stats(sort='cumulative')
```

**Solution**: Optimize algorithms and reduce memory allocations

## Contributing Guidelines

### Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass (unit and integration)
- [ ] Documentation is updated
- [ ] Type hints are provided
- [ ] Error handling is comprehensive
- [ ] Performance impact is considered
- [ ] Security implications are reviewed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
```

## Related Documentation

- [Tester Services API Reference](api_reference.md) — Detailed API documentation
- [Plugin Development Guide](../development.md) — General plugin development
- [Docker Integration](../../../docker/README.md) — Container development
- [Event System](../../../core/events/README.md) — Event-driven programming

## Support and Resources

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides and API references
- **Community Forum**: Ask questions and share knowledge
- **Developer Chat**: Real-time collaboration and support

---

This developer guide provides comprehensive coverage of tester service development workflows. For specific implementation details, refer to the API reference documentation and existing plugin examples.
