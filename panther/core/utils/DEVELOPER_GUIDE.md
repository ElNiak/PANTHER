# Developer Guide - PANTHER Core Utilities

## Development Environment Setup

### Prerequisites

- Python 3.8+
- Access to PANTHER repository
- Optional: `colorlog` for colored logging output
- Optional: `psutil` for performance monitoring

### Local Development Setup

1. **Clone and Navigate**:
   ```bash
   cd panther/core/utils
   ```

2. **Install Dependencies**:
   ```bash
   pip install colorlog  # Optional for colors
   pip install psutil    # Optional for performance monitoring
   ```

3. **Verify Installation**:
   ```python
   from panther.core.utils import LoggerFactory, FeatureLoggerMixin
   print("Core utilities loaded successfully")
   ```

## Running and Testing

### Manual Testing

#### Basic Logger Testing
```python
from panther.core.utils import LoggerFactory

# Initialize factory
LoggerFactory.initialize({
    "level": "DEBUG",
    "enable_colors": True,
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
})

# Test basic logging
logger = LoggerFactory.get_logger("test_component")
logger.info("Test message")
logger.debug("Debug message")
```

#### Feature Detection Testing
```python
from panther.core.utils import FeatureLoggerMixin

class TestComponent(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def test_logging(self):
        self.info(f"Feature detected: {self.get_effective_feature()}")
        self.debug("Testing debug output")

# Test the component
component = TestComponent()
component.test_logging()
```

#### Statistics Testing
```python
from panther.core.utils import LoggerFactory

# Enable statistics
LoggerFactory.enable_statistics({
    "enabled": True,
    "track_performance": True,
    "buffer_size": 100
})

# Generate some log messages
logger = LoggerFactory.get_logger("stats_test")
for i in range(10):
    logger.info(f"Test message {i}")

# Check statistics
stats = LoggerFactory.get_log_statistics()
print(f"Messages logged: {stats.get('total_messages', 0)}")
```

### Debugging

#### Enable Debug Logging
```python
LoggerFactory.initialize({
    "level": "DEBUG",
    "debug_file_logging": True,
    "output_file": "debug.log"
})
```

#### Feature Detection Debugging
```python
from panther.core.utils import LoggerFactory

# Test feature detection for your component
component_name = "your_component_name"
detected = LoggerFactory._detect_feature_from_name(component_name)
print(f"Component '{component_name}' detected as feature: {detected}")

# Check available features
print("Available feature mappings:")
for feature, patterns in LoggerFactory.FEATURE_MAPPINGS.items():
    print(f"  {feature}: {patterns}")
```

#### Configuration Verification
```python
# Check current configuration
config = LoggerFactory._config
print(f"Current config: {config}")

# Check feature levels
levels = LoggerFactory._feature_levels
print(f"Feature levels: {levels}")

# Check if statistics are enabled
enabled = LoggerFactory.is_statistics_enabled()
print(f"Statistics enabled: {enabled}")
```

## Extending the Utilities

### Adding New Features

1. **Register Feature Patterns**:
   ```python
   from panther.core.utils import feature_registry

   # Add new feature with detection patterns
   feature_registry.register_feature("my_new_feature", [
       "pattern1", "pattern2", "keyword"
   ])
   ```

2. **Update Factory Mappings** (for static mappings):
   ```python
   # Add to LoggerFactory.FEATURE_MAPPINGS in logger_factory.py
   "my_new_feature": ["component_name", "module_pattern"]
   ```

### Custom Mixins

```python
from panther.core.utils import FeatureLoggerMixin

class CustomMixin(FeatureLoggerMixin):
    def __init__(self, custom_feature=None):
        # Initialize with specific feature
        self.__init_logger__(feature=custom_feature)

    def log_operation(self, operation_name, **context):
        """Log operation with context."""
        self.info(f"Operation: {operation_name}", extra=context)

    def log_error_with_context(self, error, **context):
        """Enhanced error logging."""
        self.error(f"Error: {error}", extra=context, exc_info=True)
```

### Custom Statistics Collectors

```python
from panther.core.utils.log_statistics_collector import LogStatisticsCollector

class CustomStatsCollector(LogStatisticsCollector):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_metrics = {}

    def collect_message(self, record):
        """Override to add custom metrics."""
        super().collect_message(record)

        # Add custom metric collection
        feature = getattr(record, 'feature', 'unknown')
        self.custom_metrics[feature] = self.custom_metrics.get(feature, 0) + 1

    def get_custom_stats(self):
        """Get custom statistics."""
        return self.custom_metrics.copy()
```

## Code Quality Standards

### Docstring Requirements

All public methods must have Google-style docstrings:

```python
def example_function(param1: str, param2: Optional[int] = None) -> bool:
    """Brief one-line description under 72 characters.

    Longer description explaining the function's purpose, behavior,
    and any important implementation details.

    Args:
        param1: Description of first parameter
        param2: Description of optional parameter with default

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
        RuntimeError: When system is not initialized

    Examples:
        >>> result = example_function("test", 42)
        >>> assert result is True
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    return True
```

### Testing Requirements

- All new functionality must include doctest examples
- Critical paths must have manual testing procedures
- Performance-sensitive code should include timing tests

### Code Style

- Use type hints for all parameters and return values
- Follow PEP 8 naming conventions
- Maximum line length: 88 characters
- Use f-strings for string formatting

## Performance Guidelines

### Optimization Practices

1. **Lazy Initialization**: Initialize expensive resources only when needed
2. **Caching**: Cache frequently accessed data (feature detection results, formatters)
3. **Efficient Data Structures**: Use appropriate collections for different access patterns
4. **Resource Cleanup**: Properly close handlers and clean up resources

### Performance Testing

```python
import time
from panther.core.utils import LoggerFactory

# Test logger creation performance
start_time = time.time()
for i in range(1000):
    logger = LoggerFactory.get_logger(f"test_logger_{i}")
creation_time = time.time() - start_time
print(f"Created 1000 loggers in {creation_time:.3f}s")

# Test logging performance
logger = LoggerFactory.get_logger("perf_test")
start_time = time.time()
for i in range(10000):
    logger.info(f"Test message {i}")
logging_time = time.time() - start_time
print(f"Logged 10000 messages in {logging_time:.3f}s")
```

## Troubleshooting Common Issues

### Logger Not Getting Feature-Specific Level

**Problem**: Logger is not using the expected feature-specific level.

**Solution**:
```python
# Check feature detection
logger_name = "your_logger_name"
detected_feature = LoggerFactory._detect_feature_from_name(logger_name)
print(f"Detected feature: {detected_feature}")

# Check if feature has configured level
levels = LoggerFactory._feature_levels
print(f"Feature levels: {levels}")

# Manually set feature level
LoggerFactory.update_feature_level("your_feature", "DEBUG")
```

### Statistics Not Working

**Problem**: Statistics collection is not capturing data.

**Solution**:
```python
# Check if statistics are enabled
enabled = LoggerFactory.is_statistics_enabled()
print(f"Statistics enabled: {enabled}")

# Enable statistics if needed
if not enabled:
    LoggerFactory.enable_statistics({
        "enabled": True,
        "track_performance": True
    })

# Verify handler is attached
handler_stats = LoggerFactory.get_statistics_handler_stats()
print(f"Handler stats: {handler_stats}")
```

### Memory Usage Growing

**Problem**: Memory usage increases over time.

**Solution**:
```python
# Check statistics buffer size
collector = getattr(LoggerFactory, '_statistics_collector', None)
if collector:
    print(f"Buffer size: {collector.buffer_size}")
    print(f"Current buffer length: {len(collector.message_buffer)}")

# Reset statistics if needed
LoggerFactory.reset_statistics()

# Consider disabling statistics for production
LoggerFactory.disable_statistics()
```

## Contributing Guidelines

### Pull Request Process

1. **Feature Branch**: Create feature branch from main
2. **Implementation**: Add functionality with tests and documentation
3. **Testing**: Verify all manual testing procedures pass
4. **Documentation**: Update relevant documentation files
5. **Review**: Submit PR for code review

### Testing Checklist

- [ ] All doctest examples pass
- [ ] Manual testing procedures verified
- [ ] Performance impact assessed
- [ ] Memory usage tested for leaks
- [ ] Thread safety verified for concurrent usage
- [ ] Error handling tested with invalid inputs

### Documentation Updates

When adding new features:

- [ ] Update API reference documentation
- [ ] Add usage examples to README
- [ ] Update this developer guide with new procedures
- [ ] Add troubleshooting section if applicable
- [ ] Update architecture diagrams if structure changes

## IDE Integration

### VSCode Settings

Recommended settings for development:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.linting.mypyEnabled": true,
    "files.trimTrailingWhitespace": true
}
```

### Debugging Configuration

VSCode launch configuration for debugging:

```json
{
    "name": "Debug Core Utils",
    "type": "python",
    "request": "launch",
    "program": "${workspaceFolder}/debug_runner.py",
    "console": "integratedTerminal",
    "env": {
        "PYTHONPATH": "${workspaceFolder}"
    }
}
```

Create `debug_runner.py` for testing:

```python
#!/usr/bin/env python3
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# Your debugging code here
LoggerFactory.initialize({"level": "DEBUG", "enable_colors": True})
logger = LoggerFactory.get_logger(__name__)
logger.info("Debug session started")
```
