# Developer Guide - Command Processor Module

## Development Environment Setup

### Prerequisites
- Python 3.8+
- PANTHER framework dependencies
- pytest for testing
- pylint for code quality

### Local Development Setup

```bash
# Navigate to PANTHER root
cd /path/to/PANTHER

# Install development dependencies
pip install -e .[dev]

# Verify installation
python -c "from panther.core.command_processor import CommandProcessor; print('OK')"
```

### Project Structure
```
command_processor/
├── __init__.py              # Public API exports
├── builders/                # Command builder implementations
├── core/                    # Core interfaces and processor
├── mixins/                  # Reusable functionality mixins
├── models/                  # Data models and constants
├── utils/                   # Utility functions
├── README.md               # Architecture documentation
├── DEVELOPER_GUIDE.md      # This file
└── api_reference.md        # API documentation
```

## Running Tests

### Unit Tests
```bash
# Run all command processor tests
pytest panther/core/command_processor/tests/ -v

# Run specific test categories
pytest -k "test_command_processing" -v
pytest -k "test_shell_utils" -v
pytest -k "test_builders" -v
```

### Integration Tests
```bash
# Test with actual shell commands
pytest panther/core/command_processor/tests/integration/ -v

# Test environment adapters
pytest -k "test_environment_adapter" -v
```

### Test Coverage
```bash
# Generate coverage report
pytest --cov=panther.core.command_processor --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Code Quality

### Linting
```bash
# Run pylint on the module
pylint panther/core/command_processor/

# Run with specific rcfile if available
pylint --rcfile=.pylintrc panther/core/command_processor/
```

### Code Formatting
```bash
# Format with black (if configured)
black panther/core/command_processor/

# Check formatting
black --check panther/core/command_processor/
```

### Type Checking
```bash
# Run mypy if configured
mypy panther/core/command_processor/
```

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from panther.core.command_processor import CommandProcessor
processor = CommandProcessor()
# Debug logs will now show detailed processing info
```

### Common Debug Scenarios

#### Command Processing Issues
```python
# Enable detailed command logging
processor.logger.setLevel(logging.DEBUG)

# Process with debugging
result = processor.process_commands({
    "run_cmd": {"command_args": "echo test"}
})
```

#### Shell Command Detection
```python
from panther.core.command_processor.models import ShellCommand

# Test command detection
cmd = ShellCommand.from_string("if [ -f file ]; then echo found; fi")
print(f"Multiline: {cmd.metadata.is_multiline}")
print(f"Control structure: {cmd.metadata.is_control_structure}")
```

#### Builder Pattern Debugging
```python
from panther.core.command_processor.builders import CommandBuilder

# Step through builder process
builder = CommandBuilder()
builder.set_command("echo test")
builder.set_working_directory("/tmp")
command = builder.build()
print(command.to_dict())
```

## Development Workflows

### Adding New Features

1. **Design Phase**
   - Update interfaces if needed (core/interfaces.py)
   - Consider impact on existing processors
   - Design for extensibility

2. **Implementation**
   - Add core logic to appropriate module
   - Implement tests alongside code
   - Update builders if command structure changes

3. **Integration**
   - Update __init__.py exports
   - Add integration tests
   - Update documentation

4. **Validation**
   - Run full test suite
   - Check lint compliance
   - Verify no regressions

### Bug Fixes

1. **Reproduce Issue**
   ```python
   # Create minimal reproduction
   from panther.core.command_processor import CommandProcessor
   processor = CommandProcessor()
   # Add failing case
   ```

2. **Add Test Case**
   ```python
   def test_bug_reproduction():
       # Test case that fails before fix
       # Should pass after fix
       pass
   ```

3. **Implement Fix**
   - Make minimal changes
   - Ensure test passes
   - Check for side effects

4. **Regression Testing**
   - Run full test suite
   - Test edge cases
   - Verify performance impact

### Performance Optimization

#### Profiling Command Processing
```python
import cProfile
from panther.core.command_processor import CommandProcessor

def profile_processing():
    processor = CommandProcessor()
    # Your test commands here
    commands = {"run_cmd": {"command_args": "complex command"}}
    processor.process_commands(commands)

cProfile.run('profile_processing()')
```

#### Memory Usage Analysis
```python
import tracemalloc
tracemalloc.start()

# Your command processing code
processor = CommandProcessor()
result = processor.process_commands(large_command_set)

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
```

## Pull Request Workflow

### Before Creating PR

1. **Code Quality Check**
   ```bash
   # Run all quality checks
   pylint panther/core/command_processor/
   pytest panther/core/command_processor/tests/ -v
   black --check panther/core/command_processor/
   ```

2. **Documentation Update**
   - Update README.md if architecture changes
   - Update this DEVELOPER_GUIDE.md if workflow changes
   - Update api_reference.md if public API changes

3. **Integration Testing**
   ```bash
   # Test with other PANTHER components
   pytest tests/integration/ -k command_processor
   ```

### PR Description Template
```markdown
## Summary
Brief description of changes

## Changes Made
- List specific changes
- Include any new features
- Note any breaking changes

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Documentation
- [ ] README.md updated if needed
- [ ] API reference updated if needed
- [ ] Code comments added for complex logic
```

## Troubleshooting

### Common Issues

#### Circular Import Errors
```python
# Use lazy imports in models
def get_shell_utils():
    from panther.core.command_processor.utils.shell_utils import ...
    return ...
```

#### Memory Leaks in Command Processing
- Check for proper cleanup in command lists
- Ensure ShellCommand objects are garbage collected
- Monitor command metadata growth

#### Performance Degradation
- Profile command detection logic
- Check for inefficient string operations
- Monitor regex compilation overhead

### Debug Environment Variables
```bash
# Enable detailed logging
export PANTHER_LOG_LEVEL=DEBUG

# Enable command processor specific logging
export PANTHER_COMMAND_PROCESSOR_DEBUG=1

# Disable command optimization for debugging
export PANTHER_DISABLE_COMMAND_OPTIMIZATION=1
```

## Contributing Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints for all public methods
- Add docstrings following Google style
- Keep functions focused and small

### Testing Requirements
- Minimum 80% code coverage
- Test edge cases and error conditions
- Include integration tests for new features
- Mock external dependencies

### Documentation Standards
- Update API documentation for public changes
- Include examples in docstrings
- Keep README.md current with architecture
- Document performance implications
