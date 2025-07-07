# ADR-0002: Error Handling and Exit Codes

## Status

Accepted

## Date

2023-12-01

## Context

The PANTHER CLI must provide consistent error handling that serves both human users and automated systems. Requirements include:

- **Human Users**: Clear, actionable error messages with suggestions
- **Shell Scripts**: Proper exit codes for conditional execution
- **CI/CD Pipelines**: Reliable failure detection and reporting
- **Development**: Detailed debugging information when needed
- **Production**: User-friendly messages without exposing internals

## Decision

Implement a layered error handling strategy with:

1. **Exception-to-Exit Code Translation** at command boundaries
2. **Consistent Error Message Formatting** with emoji indicators
3. **Debug Mode** for detailed troubleshooting information
4. **Unix Standard Exit Codes** for shell integration

### Exit Code Standards

```python
EXIT_SUCCESS = 0        # Successful completion
EXIT_FAILURE = 1        # General error condition
EXIT_USAGE = 2          # Incorrect command usage
EXIT_NOINPUT = 66       # Cannot open input file
EXIT_UNAVAILABLE = 69   # Service unavailable
EXIT_SOFTWARE = 70      # Internal software error
EXIT_INTERRUPT = 130    # Interrupted by signal (Ctrl+C)
```

### Error Message Format

```python
# Success indicators
print("✅ Configuration validated successfully")

# Error indicators
print("❌ Validation failed: Missing required field 'experiment.name'")

# Warning indicators
print("⚠️  Plugin 'old_plugin' is deprecated, use 'new_plugin' instead")

# Information indicators
print("🔍 Scanning for available plugins...")
print("💡 Suggestion: Use 'panther config design' for guided setup")
```

### Exception Handling Pattern

```python
@classmethod
def handle(cls, args) -> int:
    try:
        # Command logic
        result = execute_operation(args)
        print(f"✅ {result.success_message}")
        return EXIT_SUCCESS

    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        if hasattr(e, 'suggestions'):
            print(f"💡 Suggestion: {e.suggestions}")
        return EXIT_FAILURE

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("💡 Check the file path and try again")
        return EXIT_NOINPUT

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return EXIT_INTERRUPT

    except Exception as e:
        if args.debug:
            logging.exception("Detailed error information:")
            raise
        else:
            print(f"❌ Unexpected error: {e}")
            print("💡 Run with --debug for more details")
        return EXIT_SOFTWARE
```

## Consequences

### Positive

- **Shell Integration**: Scripts can reliably detect success/failure
- **User Experience**: Clear feedback with actionable suggestions
- **Debugging**: Debug mode provides detailed information when needed
- **Consistency**: Uniform error handling across all commands
- **Automation**: CI/CD systems get reliable failure indicators

### Negative

- **Additional Complexity**: Exception handling boilerplate in each command
- **Message Maintenance**: Error messages require ongoing maintenance
- **Debug Mode Logic**: Conditional behavior based on debug flag

### Mitigation Strategies

1. **Error Handler Decorators**: Reduce boilerplate with common patterns
2. **Error Message Registry**: Centralized message management
3. **Testing**: Comprehensive error condition testing

## Implementation Details

### Debug Mode Integration

Debug mode activated by:
- `--debug` command line flag
- `PANTHER_DEBUG=1` environment variable
- LoggerFactory debug configuration

Debug mode provides:
- Full exception stack traces
- Detailed logging from all components
- Performance timing information
- Internal state information

### Error Message Guidelines

**Structure**: `[Indicator] [Category]: [Specific Error] [Optional Context]`

**Examples**:
```
❌ Validation error: Missing required field 'experiment.name'
❌ Plugin error: Plugin 'invalid_plugin' not found
❌ Network error: Connection timeout after 30 seconds
⚠️  Configuration warning: Using deprecated option 'old_setting'
💡 Suggestion: Use 'panther plugins list' to see available options
```

**Tone**:
- Direct and specific about the problem
- Actionable suggestions when possible
- No blame language ("you did wrong" → "missing required field")
- Technical accuracy without jargon

### Special Cases

#### Network Errors
```python
except requests.ConnectionError as e:
    print("❌ Network error: Cannot connect to plugin registry")
    print("💡 Check your internet connection and try again")
    return EXIT_UNAVAILABLE
```

#### Permission Errors
```python
except PermissionError as e:
    print(f"❌ Permission denied: Cannot write to {e.filename}")
    print("💡 Run with appropriate permissions or choose different location")
    return EXIT_NOPERMS
```

#### Resource Exhaustion
```python
except MemoryError:
    print("❌ Out of memory: Experiment too large for available resources")
    print("💡 Try reducing experiment scope or running on larger system")
    return EXIT_SOFTWARE
```

## Testing Strategy

### Error Condition Testing

```python
def test_validation_error_handling():
    """Test that validation errors return proper exit codes"""
    result = subprocess.run([
        'panther', 'config', 'validate', '--config', 'invalid.yaml'
    ], capture_output=True, text=True)

    assert result.returncode == EXIT_FAILURE
    assert "❌ Validation error:" in result.stdout
    assert "💡 Suggestion:" in result.stdout

def test_keyboard_interrupt_handling():
    """Test graceful handling of user cancellation"""
    # Simulate KeyboardInterrupt during command execution
    with patch('signal.alarm'), patch('signal.signal'):
        result = run_command_with_interrupt(['panther', 'run', '--config', 'test.yaml'])

    assert result.returncode == EXIT_INTERRUPT
    assert "⚠️  Operation cancelled by user" in result.stdout
```

### Debug Mode Testing

```python
def test_debug_mode_stack_traces():
    """Test that debug mode provides detailed error information"""
    result = subprocess.run([
        'panther', '--debug', 'config', 'validate', '--config', 'broken.yaml'
    ], capture_output=True, text=True)

    assert result.returncode == EXIT_FAILURE
    assert "Traceback" in result.stderr  # Stack trace in debug mode

def test_normal_mode_user_friendly():
    """Test that normal mode provides user-friendly errors"""
    result = subprocess.run([
        'panther', 'config', 'validate', '--config', 'broken.yaml'
    ], capture_output=True, text=True)

    assert result.returncode == EXIT_FAILURE
    assert "Traceback" not in result.stdout  # No stack trace in normal mode
    assert "❌" in result.stdout  # User-friendly error indicator
```

## Alternatives Considered

### Rich Library for Enhanced Output
- **Pros**: Beautiful formatting, progress bars, enhanced error display
- **Cons**: External dependency, potential terminal compatibility issues
- **Decision**: Deferred to future enhancement to maintain minimal dependencies

### Structured Error Objects
- **Pros**: Consistent error structure, easier testing, internationalization support
- **Cons**: Additional complexity, harder to maintain simple error messages
- **Decision**: Rejected in favor of simple string-based messages

### Logging-Only Error Handling
- **Pros**: Centralized error management, structured logging
- **Cons**: Poor user experience, harder shell integration
- **Decision**: Rejected - logging supplements but doesn't replace user-facing errors

## Monitoring

Error handling effectiveness measured by:

- **User Support Requests**: Frequency of "unclear error" reports
- **Debug Mode Usage**: How often users need debug mode for resolution
- **Shell Integration**: Success rate of automated CLI usage
- **Error Recovery**: Percentage of errors that include actionable suggestions

## Related Decisions

- [ADR-0001: Command Pattern Architecture](0001-command-pattern-architecture.md) - Establishes command interface
- [ADR-0003: Interactive Component Architecture](0003-interactive-component-architecture.md) - Interactive error handling

---

*This ADR ensures consistent, user-friendly error handling while maintaining reliable automation support through proper exit codes.*
