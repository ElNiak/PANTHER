# PANTHER CLI Click Test Suite

Comprehensive test suite for the PANTHER Click CLI implementation. This test suite provides 100% coverage of CLI functionality including all commands, options, error handling, and workflows.

## 🏗️ Test Structure

```text
tests/cli_click/
├── conftest.py                 # Shared fixtures and test configuration
├── pytest.ini                 # Pytest configuration
├── run_tests.py               # Test runner script
├── README.md                  # This file
├── __init__.py               # Test suite initialization
├── unit/                     # Unit tests
│   ├── core/                 # Core CLI functionality
│   │   ├── test_main.py      # Main CLI entry point tests
│   │   └── test_base.py      # Base utilities and decorators tests
│   ├── commands/             # Individual command tests
│   │   ├── test_config.py    # Config command tests
│   │   ├── test_run.py       # Run command tests
│   │   ├── test_plugins.py   # Plugins command tests
│   │   └── test_all_commands.py # Remaining commands tests
│   └── utils/                # Utility function tests
├── integration/              # Integration tests
│   └── test_cli_workflows.py # End-to-end workflow tests
└── fixtures/                 # Test data and fixtures
```

## ✨ Key Features

### 🔧 Comprehensive Coverage
- **All Commands**: Tests for every CLI command and subcommand
- **All Options**: Tests for every command-line option and argument
- **Error Handling**: Comprehensive error scenario testing
- **Edge Cases**: Boundary conditions and unusual inputs
- **Workflows**: End-to-end integration testing

### 🚀 Click Testing Framework
- **CliRunner**: Uses Click's official testing framework
- **Isolated Filesystem**: Tests run in isolated environments
- **Mock Integration**: Seamless mocking of external dependencies
- **Output Validation**: Comprehensive output format testing

### 📊 Advanced Testing Features
- **Parametrized Tests**: Efficient testing of multiple scenarios
- **Fixtures**: Reusable test data and configurations
- **Performance Testing**: Timeout and speed validation
- **Coverage Reporting**: Detailed code coverage analysis

## 🎯 Test Categories

### Unit Tests
- **Core Functionality**: Main CLI, base utilities, decorators
- **Command Logic**: Individual command implementation
- **Error Handling**: Exception handling and error messages
- **Option Parsing**: Argument validation and processing

### Integration Tests
- **Workflows**: Multi-command sequences
- **File Operations**: Configuration generation and validation
- **System Integration**: Docker, plugins, tools interaction
- **Performance**: End-to-end timing and resource usage

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
python tests/cli_click/run_tests.py

# Run with coverage
python tests/cli_click/run_tests.py --coverage --html-coverage

# Run specific test category
python tests/cli_click/run_tests.py --unit
python tests/cli_click/run_tests.py --integration
```

### Advanced Usage
```bash
# Run specific command tests
python tests/cli_click/run_tests.py --config
python tests/cli_click/run_tests.py --plugins

# Run with parallel execution
python tests/cli_click/run_tests.py --parallel 4

# Run specific test file
python tests/cli_click/run_tests.py --test-file tests/cli_click/unit/commands/test_config.py

# Run tests matching pattern
python tests/cli_click/run_tests.py --test-pattern "test_config_validate"

# Skip slow tests
python tests/cli_click/run_tests.py --fast

# Debug mode
python tests/cli_click/run_tests.py --debug --verbose
```

### Direct Pytest Usage
```bash
# From project root
pytest tests/cli_click/

# With coverage
pytest tests/cli_click/ --cov=panther.cli_click --cov-report=html

# Specific tests
pytest tests/cli_click/unit/commands/test_config.py::TestConfigValidateCommand::test_validate_valid_config

# With markers
pytest tests/cli_click/ -m "config and not slow"
```

## 🧪 Test Configuration

### Pytest Configuration
The test suite includes comprehensive pytest configuration in `pytest.ini`:
- Test discovery patterns
- Output formatting
- Marker definitions
- Warning filters
- Timeout settings

### Environment Variables
- `PANTHER_TEST_MODE=1`: Enables test mode
- `PANTHER_DEBUG=0`: Controls debug output in tests

### Test Markers
- `unit`: Unit tests
- `integration`: Integration tests
- `slow`: Time-consuming tests
- `config`: Configuration-related tests
- `plugins`: Plugin-related tests
- `docker`: Docker-related tests
- `requires_docker`: Tests requiring Docker
- `requires_network`: Tests requiring network access

## 📋 Fixtures

### Core Fixtures
- `cli_runner`: Click CliRunner instance
- `temp_dir`: Temporary directory for test files
- `sample_config`: Sample configuration data
- `sample_config_file`: Temporary configuration file

### Mock Fixtures
- `mock_argparse_adapter`: Mocked argparse compatibility
- `mock_logging`: Mocked logging setup
- `mock_subprocess`: Mocked subprocess calls
- `mock_docker`: Mocked Docker operations

### Helper Fixtures
- `click_helper`: Test helper methods
- `env_vars`: Environment variable management
- `cli_isolated_filesystem`: Isolated filesystem testing

## 🎨 Test Patterns

### Command Testing Pattern
```python
def test_command_help(self, cli_runner):
    """Test command help output."""
    result = cli_runner.invoke(cli, ['command', '--help'])
    assert result.exit_code == 0
    assert 'expected content' in result.output

def test_command_with_options(self, cli_runner, sample_config_file):
    """Test command with various options."""
    result = cli_runner.invoke(cli, [
        'command',
        '--option1', 'value1',
        '--option2', 'value2'
    ])
    assert result.exit_code == 0
```

### Error Testing Pattern
```python
def test_command_error_handling(self, cli_runner):
    """Test command error handling."""
    result = cli_runner.invoke(cli, ['command', '--invalid'])
    assert result.exit_code != 0
    assert 'error message' in result.output
```

### Workflow Testing Pattern
```python
def test_complete_workflow(self, cli_runner, temp_dir):
    """Test complete workflow."""
    # Step 1: Setup
    result1 = cli_runner.invoke(cli, ['setup-command'])
    assert result1.exit_code == 0

    # Step 2: Main operation
    result2 = cli_runner.invoke(cli, ['main-command'])
    assert result2.exit_code == 0

    # Step 3: Verification
    result3 = cli_runner.invoke(cli, ['verify-command'])
    assert result3.exit_code == 0
```

## 📊 Coverage Goals

### Target Coverage
- **Overall**: 95%+ line coverage
- **Commands**: 100% command coverage
- **Error Paths**: 90%+ error handling coverage
- **Integration**: 100% workflow coverage

### Coverage Reports
- **Terminal**: Basic coverage summary
- **HTML**: Detailed interactive reports
- **XML**: CI/CD integration

## 🔧 Debugging Tests

### Common Issues
1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Missing Dependencies**: Install test requirements
3. **Timeout Issues**: Increase timeout for slow tests
4. **Fixture Conflicts**: Check fixture scoping

### Debug Commands
```bash
# Run single test with full output
pytest tests/cli_click/unit/commands/test_config.py::test_specific -s -vv

# Run with pdb debugging
pytest tests/cli_click/unit/commands/test_config.py::test_specific --pdb

# Run with full traceback
pytest tests/cli_click/ --tb=long
```

## 🚀 Continuous Integration

### GitHub Actions Integration
```yaml
- name: Run CLI Tests
  run: |
    python tests/cli_click/run_tests.py --coverage --junit-xml=test-results.xml

- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

### Pre-commit Hooks
```yaml
repos:
  - repo: local
    hooks:
      - id: cli-tests
        name: CLI Tests
        entry: python tests/cli_click/run_tests.py --fast
        language: system
        pass_filenames: false
```

## 📈 Performance Benchmarks

### Expected Performance
- **Help Commands**: < 2 seconds
- **List Commands**: < 10 seconds
- **Validation Commands**: < 5 seconds
- **Full Test Suite**: < 5 minutes

### Performance Testing
```bash
# Run performance tests
python tests/cli_click/run_tests.py -k "performance"

# Monitor test timing
python tests/cli_click/run_tests.py --durations=10
```

## 🔄 Maintenance

### Adding New Tests
1. Follow existing patterns
2. Use appropriate fixtures
3. Add proper markers
4. Include error cases
5. Update documentation

### Test Review Checklist
- [ ] Tests follow naming conventions
- [ ] Appropriate fixtures used
- [ ] Error cases covered
- [ ] Performance considerations
- [ ] Documentation updated

## 📚 Additional Resources

- [Click Testing Documentation](https://click.palletsprojects.com/en/8.1.x/testing/)
- [Pytest Documentation](https://docs.pytest.org/)
- [PANTHER CLI Documentation](../../docs/cli/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

**Note**: This test suite is designed to provide comprehensive validation of the PANTHER Click CLI implementation while maintaining fast execution times and clear error reporting.
