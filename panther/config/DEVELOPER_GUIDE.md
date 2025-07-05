# PANTHER Configuration System Developer Guide

## Environment Setup

### Prerequisites
- Python 3.8+
- Git
- Docker (for integration testing)
- IDE with Python language server support (recommended: VS Code, PyCharm)

### Development Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd panther/config
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"  # Install in development mode with dev dependencies
   ```

4. **Verify installation**:
   ```bash
   python -c "from panther.config.core.manager import ConfigurationManager; print('Setup successful')"
   ```

### IDE Configuration

#### VS Code Setup
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "python.autoComplete.extraPaths": ["./panther"]
}
```

#### PyCharm Setup
1. File → Settings → Project → Python Interpreter
2. Add interpreter → Existing environment → Select `venv/bin/python`
3. Enable pytest as default test runner
4. Configure code style to follow PEP 8

## Running and Debugging

### Running Tests

#### Full Test Suite
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=panther.config --cov-report=html

# Run specific test categories
pytest tests/unit/        # Unit tests only
pytest tests/integration/ # Integration tests only
```

#### Specific Module Tests
```bash
# Test specific modules
pytest tests/unit/core/test_base.py
pytest tests/unit/core/test_manager.py
pytest tests/unit/components/test_validators.py
```

#### Test with Different Python Versions
```bash
# Using tox (if configured)
tox

# Manual testing with different Python versions
python3.8 -m pytest
python3.9 -m pytest
python3.10 -m pytest
```

### Debugging Techniques

#### Debug Configuration Loading
```python
import logging
from panther.config.core.manager import ConfigurationManager

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

config_manager = ConfigurationManager()
config_manager.enable_debug_logging()

# Load configuration with detailed debugging
config = config_manager.load_and_validate_config(
    "experiment.yaml",
    debug=True
)
```

#### Debug Validation Issues
```python
from panther.config.core.components.validators import UnifiedValidator

validator = UnifiedValidator()
validator.enable_verbose_errors()

# Get detailed validation information
result = validator.validate_experiment_config(config)
print(result.get_detailed_report())

# Debug specific validation stages
result = validator.validate_schema_only(config)
result = validator.validate_business_rules_only(config)
result = validator.validate_compatibility_only(config)
```

#### Debug Plugin Loading
```python
from panther.config.core.mixins.plugin_management import PluginManagementMixin

plugin_manager = PluginManagementMixin()
plugin_manager.enable_plugin_debug()

# List discovered plugins
plugins = plugin_manager.discover_plugins()
for plugin in plugins:
    print(f"Plugin: {plugin.name}, Status: {plugin.status}")

# Debug specific plugin loading
try:
    schema = plugin_manager.load_plugin_schema("quiche")
except Exception as e:
    print(f"Plugin loading error: {e}")
```

### Performance Debugging

#### Cache Performance
```python
config_manager = ConfigurationManager()
config_manager.enable_cache(ttl=300)

# Load configuration multiple times
for i in range(10):
    config = config_manager.load_from_file("experiment.yaml")

# Check cache statistics
stats = config_manager.get_cache_stats()
print(f"Cache hits: {stats.hits}, misses: {stats.misses}")
print(f"Hit rate: {stats.hit_rate}%")
```

#### Memory Usage Profiling
```python
import tracemalloc
from panther.config.core.manager import ConfigurationManager

tracemalloc.start()

config_manager = ConfigurationManager()
config = config_manager.load_and_validate_config("large_experiment.yaml")

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
```

## Development Workflow

### Code Changes

#### 1. Branch Creation
```bash
git checkout -b feature/new-validation-rule
```

#### 2. Implementation
Follow the established patterns:
- **Mixins**: Add new capabilities as separate mixins
- **Components**: Create focused, single-responsibility components
- **Models**: Use Pydantic dataclasses for type safety
- **Validators**: Extend existing validation framework

#### 3. Testing
Write tests for new functionality:
```bash
# Create test file
touch tests/unit/components/test_new_component.py

# Write comprehensive tests
pytest tests/unit/components/test_new_component.py -v
```

#### 4. Documentation
Update relevant documentation:
- Module README files
- API reference (auto-generated)
- Developer guide (this file)

### Code Review Process

#### Pre-Review Checklist
- [ ] All tests pass locally
- [ ] Code coverage maintained (>90%)
- [ ] Lint checks pass (flake8, black, mypy)
- [ ] Documentation updated
- [ ] Performance impact evaluated

#### Review Commands
```bash
# Run full quality checks
make lint        # Linting and formatting
make typecheck   # Type checking with mypy
make test        # Full test suite
make docs        # Documentation generation
```

### Common Development Tasks

#### Adding a New Mixin
1. Create mixin file in `core/mixins/`
2. Implement mixin class with focused functionality
3. Add to `__init__.py` exports
4. Update `ConfigurationManager` inheritance
5. Write unit tests
6. Update mixin README

Example structure:
```python
# core/mixins/new_feature.py
class NewFeatureMixin:
    """Mixin providing new feature functionality."""

    def enable_new_feature(self, **kwargs):
        """Enable new feature with configuration."""
        pass

    def configure_new_feature(self, config):
        """Configure new feature behavior."""
        pass
```

#### Adding a New Component
1. Create component file in `core/components/`
2. Implement component with single responsibility
3. Add comprehensive error handling
4. Write unit and integration tests
5. Update component README

#### Adding a New Model
1. Create model file in `core/models/`
2. Use Pydantic dataclass with proper types
3. Add validation methods if needed
4. Include example usage in docstrings
5. Write validation tests

#### Adding Custom Validators
1. Extend appropriate validator base class
2. Implement validation logic with clear error messages
3. Add to validator composition in `UnifiedValidator`
4. Write test cases for all validation scenarios

### Testing Strategies

#### Unit Testing
Focus on individual components in isolation:
```python
def test_base_config_initialization():
    config = BaseConfig(name="test", port=8080)
    assert config.name == "test"
    assert config.port == 8080
    assert config.omega_config is not None
```

#### Integration Testing
Test component interactions:
```python
def test_manager_full_pipeline():
    manager = ConfigurationManager()
    config = manager.load_and_validate_config("test_experiment.yaml")
    assert config is not None
    assert len(config.tests) > 0
```

#### Performance Testing
Monitor performance characteristics:
```python
def test_large_config_performance():
    start_time = time.time()
    manager = ConfigurationManager()
    config = manager.load_from_file("large_config.yaml")
    load_time = time.time() - start_time
    assert load_time < 1.0  # Should load within 1 second
```

### Debugging Common Issues

#### Configuration Not Loading
1. Check file path and permissions
2. Verify YAML syntax with online validator
3. Enable debug logging for detailed error messages
4. Check for circular dependencies in configuration

#### Validation Failures
1. Use `validate_schema_only()` to isolate schema issues
2. Check plugin availability and versions
3. Verify required fields are present
4. Enable auto-fix to see suggested corrections

#### Plugin Loading Issues
1. Check plugin directory permissions
2. Verify plugin Python path is correct
3. Enable plugin debug logging
4. Check for missing plugin dependencies

#### Performance Issues
1. Enable cache profiling
2. Check for excessive file I/O operations
3. Profile memory usage during loading
4. Consider configuration size and complexity

### Code Quality Standards

#### Formatting and Linting
```bash
# Format code
black panther/config/

# Sort imports
isort panther/config/

# Lint code
flake8 panther/config/
pylint panther/config/
```

#### Type Checking
```bash
# Run mypy type checking
mypy panther/config/

# Check specific files
mypy panther/config/core/base.py
```

#### Documentation Standards
- All public methods have docstrings
- Docstrings follow Google style
- Examples are runnable and tested
- Type hints are complete and accurate

### Continuous Integration

The project uses automated CI checks:
- **Tests**: Full test suite on multiple Python versions
- **Linting**: Code style and formatting checks
- **Type Checking**: Static type analysis
- **Coverage**: Minimum 90% code coverage requirement
- **Documentation**: Ensure documentation builds successfully

### Release Process

1. **Version Bump**: Update version in `__init__.py`
2. **Changelog**: Update CHANGELOG.md with new features/fixes
3. **Tag Release**: Create git tag with version number
4. **Build Package**: Generate distribution packages
5. **Deploy**: Upload to package repository

```bash
# Example release commands
git tag v1.2.0
python setup.py sdist bdist_wheel
twine upload dist/*
```
