# ATLAS Commands MCP Server Test Suite

## Overview

This comprehensive test suite ensures the reliability and correctness of the ATLAS Commands MCP Server. The tests cover all major components and their interactions.

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and shared fixtures
├── test_checklist_manager.py      # Tests for checklist functionality
├── test_todowrite_integration.py  # Tests for TodoWrite integration
├── test_memory_graph.py          # Tests for memory graph management
├── test_workflow_enforcer.py     # Tests for workflow enforcement
├── test_validation.py            # Tests for validation modules
├── test_error_recovery.py        # Tests for error handling and recovery
├── test_resources.py             # Tests for resource management
└── test_server_integration.py    # Integration tests for complete server
```

## Running Tests

### Basic Usage

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py -v

# Run specific test file
python run_tests.py tests/test_checklist_manager.py

# Run tests matching pattern
python run_tests.py -k "checklist"

# Stop on first failure
python run_tests.py -x

# Run last failed tests
python run_tests.py --lf
```

### Interactive Mode

```bash
# Select test suite interactively
python run_tests.py -i
```

Available suites:
- `unit` - Unit tests only
- `integration` - Integration tests only
- `checklist` - Checklist-related tests
- `memory` - Memory graph tests
- `workflow` - Workflow enforcement tests
- `validation` - Validation tests
- `errors` - Error handling tests
- `resources` - Resource management tests
- `all` - Run all tests

### Advanced Options

```bash
# Run tests in parallel (4 workers)
python run_tests.py -n 4

# Run without coverage
python run_tests.py --no-cov

# Show local variables in failures
python run_tests.py -l

# Run specific markers
python run_tests.py -m "unit and not slow"
```

## Test Coverage

The test suite aims for 80%+ code coverage. Coverage reports are generated in:
- Terminal output (with missing lines)
- `htmlcov/index.html` - Interactive HTML report
- `coverage.xml` - XML report for CI/CD

## Test Categories

### 1. Checklist Manager Tests
- Creating checklists with items or templates
- Updating item status
- Tracking progress
- Dependency validation
- Import/export functionality

### 2. TodoWrite Integration Tests
- Syncing checklists to TodoWrite
- Creating and updating milestones
- Status and priority mapping
- Batch operations
- Error handling

### 3. Memory Graph Tests
- Creating workflow entities
- Adding relations between entities
- Searching patterns
- Compacting old entities
- Extracting high-value observations

### 4. Workflow Enforcer Tests
- Creating workflows
- Executing workflow steps
- Command validation
- Parallel workflow execution
- Command compatibility checks

### 5. Validation Tests
- Input validation with auto-fix
- Output schema validation
- Semantic validation
- Custom validation rules
- Range constraints

### 6. Error Recovery Tests
- Error hierarchy
- Automatic recovery strategies
- Circuit breaker pattern
- Error history tracking
- Recovery statistics

### 7. Resource Management Tests
- Resource usage monitoring
- Operation tracking
- Usage statistics
- Resource pools
- Cleanup operations

### 8. Integration Tests
- Complete server initialization
- End-to-end workflows
- Concurrent operations
- Error propagation
- Resource monitoring

## Writing New Tests

### Test Structure

```python
import pytest
from atlas_commands.module import MyClass

class TestMyClass:
    """Test suite for MyClass."""
    
    def test_basic_functionality(self):
        """Test basic functionality of MyClass."""
        instance = MyClass()
        result = instance.method()
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method."""
        instance = MyClass()
        result = await instance.async_method()
        assert result["success"] is True
```

### Using Fixtures

```python
def test_with_fixtures(self, sample_checklist_items, temp_dir):
    """Test using provided fixtures."""
    # sample_checklist_items provides test data
    # temp_dir provides temporary directory
    pass
```

### Marking Tests

```python
@pytest.mark.unit
def test_unit_functionality(self):
    """Unit test marked for filtering."""
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_integration_scenario(self):
    """Integration test that takes time."""
    pass
```

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

1. **GitHub Actions**: Tests run on every push and PR
2. **Coverage Reporting**: Coverage reports uploaded to coverage services
3. **Parallel Execution**: Tests can run in parallel for faster CI
4. **Failure Reports**: Detailed failure information for debugging

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the virtual environment
2. **Async Warnings**: Use `pytest.mark.asyncio` for async tests
3. **Resource Errors**: Some tests require system resources
4. **Timeout Errors**: Increase timeout for slow tests

### Debug Mode

```bash
# Run with full traceback
pytest -vvv --tb=long

# Run with pdb on failure
pytest --pdb

# Run with logging
pytest --log-cli-level=DEBUG
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what they test
3. **Coverage**: Aim for high coverage but focus on quality
4. **Speed**: Mark slow tests appropriately
5. **Fixtures**: Use fixtures for common setup
6. **Mocking**: Mock external dependencies appropriately

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Check coverage doesn't decrease
4. Add appropriate test markers
5. Document complex test scenarios