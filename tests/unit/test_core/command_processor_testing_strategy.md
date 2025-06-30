# Command Processor Comprehensive Testing Strategy

## 1. Pre/Post Condition Testing Framework

### Pre-Conditions for Each Test Class

#### CommandProcessor Tests
```python
@pytest.fixture
def command_processor():
    """Pre-condition: Clean CommandProcessor instance with known state."""
    processor = CommandProcessor()
    # Pre-condition assertions
    assert processor.logger is not None
    assert hasattr(processor, 'process_commands')
    return processor

def verify_command_processor_postcondition(processor, result):
    """Post-condition: Verify processor state after operations."""
    assert processor.logger is not None  # State preserved
    assert isinstance(result, dict)  # Valid return type
    # Add more post-conditions as needed
```

#### ShellCommand Tests
```python
@pytest.fixture
def valid_shell_command():
    """Pre-condition: Valid ShellCommand with normalized state."""
    cmd = ShellCommand("echo 'test'")
    # Pre-condition assertions
    assert cmd.command is not None
    assert cmd.validate().is_valid
    return cmd

def verify_shell_command_postcondition(cmd, operation_result):
    """Post-condition: Command integrity after operations."""
    assert cmd.command is not None  # Command preserved
    assert cmd.validate().is_valid  # Still valid after operation
```

## 2. Hypothesis-Based Property Testing

### CommandProcessor Properties
```python
from hypothesis import given, strategies as st
from hypothesis import assume

@given(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10))
def test_command_processor_idempotency(command_list):
    """Property: Processing same commands twice yields same result."""
    assume(all(len(cmd.strip()) > 0 for cmd in command_list))

    processor = CommandProcessor()
    commands = {"run_cmd": command_list}

    result1 = processor.process_commands(commands)
    result2 = processor.process_commands(commands)

    assert result1 == result2  # Idempotency property

@given(st.text(min_size=1, max_size=200))
def test_shell_command_validation_consistency(command_text):
    """Property: Validation is consistent across multiple calls."""
    assume(len(command_text.strip()) > 0)

    cmd = ShellCommand(command_text)
    validation1 = cmd.validate()
    validation2 = cmd.validate()

    assert validation1.is_valid == validation2.is_valid  # Consistency
```

### Shell Utility Properties
```python
@given(st.text(min_size=1, max_size=100))
def test_escape_shell_command_safety(command):
    """Property: Escaped commands are safe from injection."""
    assume(len(command.strip()) > 0)

    escaped = escape_shell_command(command)

    # Property: Escaped command should not contain dangerous patterns
    dangerous_patterns = [';', '|', '&&', '||', '$(', '`']
    for pattern in dangerous_patterns:
        if pattern in command:
            assert escaped != command  # Should be modified if dangerous
```

## 3. Integration Testing with Pydantic Models

### Command Configuration Model
```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional

class CommandConfig(BaseModel):
    """Pydantic model for command configuration validation."""

    commands: List[str] = Field(..., min_items=1, description="List of commands")
    timeout: int = Field(60, ge=1, le=3600, description="Timeout in seconds")
    environment: Dict[str, str] = Field(default_factory=dict)
    working_directory: Optional[str] = Field(None)

    @validator('commands')
    def validate_commands(cls, v):
        """Ensure all commands are non-empty."""
        for cmd in v:
            if not cmd.strip():
                raise ValueError("Commands cannot be empty")
        return v

    @validator('working_directory')
    def validate_working_directory(cls, v):
        """Validate working directory exists."""
        if v and not os.path.exists(v):
            raise ValueError(f"Working directory does not exist: {v}")
        return v

class TestPydanticIntegration:
    """Test command processor with pydantic validation."""

    def test_command_processor_with_pydantic_config(self):
        """Test command processor accepts pydantic-validated config."""
        config = CommandConfig(
            commands=["echo 'test'", "pwd"],
            timeout=30,
            environment={"TEST_VAR": "value"}
        )

        processor = CommandProcessor()
        commands = {"run_cmd": config.commands}

        # Pre-condition: Config is valid
        assert config.commands
        assert config.timeout > 0

        result = processor.process_commands(commands)

        # Post-condition: Processing succeeded
        assert "run_cmd" in result
        assert len(result["run_cmd"]) == len(config.commands)
```

## 4. Coverage and Quality Testing

### Comprehensive Test Suite Structure
```python
class TestCommandProcessorComprehensive:
    """Comprehensive test suite with full coverage."""

    @pytest.mark.parametrize("command_type,commands,expected_count", [
        ("run_cmd", ["echo test"], 1),
        ("setup_cmd", ["mkdir /tmp/test"], 1),
        ("cleanup_cmd", ["rm -rf /tmp/test"], 1),
        ("mixed", [], 0),
    ])
    def test_command_processing_coverage(self, command_type, commands, expected_count):
        """Test all command types for coverage."""
        processor = CommandProcessor()
        input_commands = {command_type: commands}

        result = processor.process_commands(input_commands)

        if expected_count > 0:
            assert command_type in result
            assert len(result[command_type]) == expected_count
        else:
            assert result == {}

class TestSecurityValidation:
    """Security-focused testing."""

    @pytest.mark.parametrize("malicious_cmd", [
        "rm -rf /",
        "cat /etc/passwd",
        "nc -l 4444 < /etc/passwd",
        "; rm important_file",
        "command && rm file",
        "$(dangerous_command)",
        "`malicious_code`"
    ])
    def test_malicious_command_detection(self, malicious_cmd):
        """Test detection of potentially malicious commands."""
        cmd = ShellCommand(malicious_cmd)
        validation = cmd.validate()

        # Should either reject or properly escape dangerous commands
        if validation.is_valid:
            escaped = escape_shell_command(malicious_cmd)
            assert escaped != malicious_cmd  # Should be modified
```

## 5. Performance and Load Testing

### Performance Benchmarks
```python
import time
import pytest

class TestPerformance:
    """Performance testing for command processor."""

    def test_large_command_list_performance(self):
        """Test processing large number of commands."""
        processor = CommandProcessor()

        # Generate large command list
        large_command_list = [f"echo 'command_{i}'" for i in range(1000)]
        commands = {"run_cmd": large_command_list}

        start_time = time.time()
        result = processor.process_commands(commands)
        end_time = time.time()

        # Performance assertion: Should process 1000 commands in < 1 second
        assert (end_time - start_time) < 1.0
        assert len(result["run_cmd"]) == 1000

    def test_memory_usage_stability(self):
        """Test memory doesn't leak during processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        processor = CommandProcessor()

        # Process many command batches
        for i in range(100):
            commands = {"run_cmd": [f"echo 'batch_{i}'"]}
            processor.process_commands(commands)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 10MB)
        assert memory_increase < 10 * 1024 * 1024
```

## 6. Test Execution Strategy

### Test Markers and Organization
```python
# pytest.ini additions
[tool:pytest]
markers =
    unit_command_processor: Unit tests for command processor
    integration_pydantic: Integration tests with pydantic models
    hypothesis_property: Property-based tests with hypothesis
    performance: Performance and load tests
    security: Security validation tests
    legacy_cleanup: Tests for legacy code removal
```

### Coverage Requirements
- **Minimum coverage: 95%** for command_processor module
- **Branch coverage: 90%** for critical paths
- **Integration coverage: 80%** for cross-module interactions

### Test Data Generation
```python
# conftest.py additions
@pytest.fixture
def sample_commands():
    """Generate variety of test commands."""
    return {
        "simple": ["echo 'hello'", "pwd", "date"],
        "complex": ["find /tmp -name '*.txt' | head -10"],
        "dangerous": ["rm -rf /tmp/test", "; echo dangerous"],
        "empty": [],
        "malformed": ["", "   ", None]
    }

@pytest.fixture
def pydantic_configs():
    """Generate pydantic configuration objects."""
    return [
        CommandConfig(commands=["echo test"]),
        CommandConfig(commands=["pwd", "ls"], timeout=120),
        CommandConfig(commands=["env"], environment={"TEST": "value"})
    ]
```

This comprehensive testing strategy ensures:
- ✅ **Quality**: Pre/post conditions validate state integrity
- ✅ **Robustness**: Hypothesis testing finds edge cases
- ✅ **Integration**: Pydantic models provide type safety
- ✅ **Performance**: Load testing ensures scalability
- ✅ **Security**: Malicious input validation
- ✅ **Coverage**: 95%+ test coverage requirement
