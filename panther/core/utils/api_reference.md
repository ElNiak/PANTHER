# API Reference - PANTHER Core Utilities

## Classes

### LoggerFactory

Central factory for creating and managing feature-aware loggers.

#### Class Methods

##### `initialize(config: Dict[str, Any]) -> None`

Initialize the logger factory with configuration.

**Args:**
- `config`: Configuration dictionary containing:
  - `level`: Logging level (DEBUG, INFO, etc.)
  - `format`: Log message format string
  - `enable_colors`: Whether to enable colored output
  - `output_file`: Optional log file path
  - `feature_levels`: Optional feature-specific logging levels

**Example:**
```python
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True,
    "output_file": "/path/to/logfile.log"
})
```

##### `get_logger(name: str, feature: Optional[str] = None) -> logging.Logger`

Get a logger with consistent configuration and feature-aware logging level.

**Args:**
- `name`: Logger name (usually module or class name)
- `feature`: Optional feature name for feature-specific logging levels

**Returns:**
- Configured logger instance

**Example:**
```python
logger = LoggerFactory.get_logger(__name__)
feature_logger = LoggerFactory.get_logger("component", "docker_operations")
```

##### `get_feature_logger(name: str, feature: str) -> logging.Logger`

Get a logger explicitly configured for a specific feature.

**Args:**
- `name`: Logger name
- `feature`: Feature name for feature-specific logging level

**Returns:**
- Configured logger instance with feature-specific level

**Example:**
```python
logger = LoggerFactory.get_feature_logger("docker_builder", "docker_operations")
```

##### `update_feature_level(feature: str, level: str) -> None`

Update the logging level for a specific feature.

**Args:**
- `feature`: Feature name to update
- `level`: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Example:**
```python
LoggerFactory.update_feature_level("docker_operations", "DEBUG")
```

##### `update_all_feature_levels(feature_levels_dict: Dict[str, str]) -> None`

Update all feature levels at once and apply to existing loggers.

**Args:**
- `feature_levels_dict`: Dictionary mapping feature names to logging levels

**Example:**
```python
levels = {
    "docker_operations": "DEBUG",
    "event_system": "INFO",
    "config_processing": "WARNING"
}
LoggerFactory.update_all_feature_levels(levels)
```

##### `enable_statistics(config: Dict[str, Any]) -> None`

Enable log statistics collection with configuration.

**Args:**
- `config`: Statistics configuration containing:
  - `enabled`: Whether to enable statistics collection
  - `buffer_size`: Size of message buffer
  - `track_performance`: Whether to track performance metrics
  - `handler_type`: Type of handler ('standard' or 'buffered')

**Example:**
```python
LoggerFactory.enable_statistics({
    "enabled": True,
    "buffer_size": 1000,
    "track_performance": True,
    "handler_type": "buffered"
})
```

##### `get_log_statistics() -> Optional[Dict]`

Get current log statistics if enabled.

**Returns:**
- Dictionary containing current statistics or None if disabled

**Example:**
```python
stats = LoggerFactory.get_log_statistics()
if stats:
    print(f"Total messages: {stats.get('total_messages', 0)}")
```

---

### FeatureLoggerMixin

Mixin class that provides feature-aware logging capabilities with automatic feature detection.

#### Methods

##### `__init_logger__(feature: Optional[str] = None) -> None`

Initialize the logger for this component.

**Args:**
- `feature`: Optional explicit feature name. If not provided, will be auto-detected from class name

**Example:**
```python
class MyComponent(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()  # Auto-detect feature
        # or
        self.__init_logger__("custom_feature")  # Explicit feature
```

##### `logger: logging.Logger` (Property)

Get the logger instance with lazy initialization.

**Returns:**
- Configured logger instance

##### `get_effective_feature() -> Optional[str]`

Get the effective feature for this component.

**Returns:**
- Feature name or None if no feature detected

**Example:**
```python
component = MyComponent()
feature = component.get_effective_feature()
print(f"Component feature: {feature}")
```

##### `log_with_feature(level: str, message: str, *args, **kwargs) -> None`

Log a message with explicit feature context.

**Args:**
- `level`: Logging level (DEBUG, INFO, etc.)
- `message`: Log message
- `*args`: Additional positional arguments
- `**kwargs`: Additional keyword arguments

##### Convenience Logging Methods

- `trace(message: str, *args, **kwargs) -> None`: Log TRACE level message
- `debug(message: str, *args, **kwargs) -> None`: Log DEBUG level message
- `info(message: str, *args, **kwargs) -> None`: Log INFO level message
- `warning(message: str, *args, **kwargs) -> None`: Log WARNING level message
- `error(message: str, *args, **kwargs) -> None`: Log ERROR level message
- `critical(message: str, *args, **kwargs) -> None`: Log CRITICAL level message

---

### FeatureRegistry

Dynamic registry system for mapping components to features.

#### Functions

##### `register_feature(feature_name: str, patterns: List[str]) -> None`

Register a new feature with detection patterns.

**Args:**
- `feature_name`: Name of the feature to register
- `patterns`: List of patterns for automatic detection

**Example:**
```python
from panther.core.utils import register_feature
register_feature("my_feature", ["pattern1", "pattern2"])
```

##### `register_module_feature(module_name: str, feature_name: str) -> None`

Register a module-specific feature mapping.

**Args:**
- `module_name`: Name of the module
- `feature_name`: Feature to associate with the module

##### `detect_module_feature(module_name: str) -> Optional[str]`

Detect feature for a specific module.

**Args:**
- `module_name`: Module name to check

**Returns:**
- Detected feature name or None

##### `feature_logger(feature_name: str) -> logging.Logger`

Get a logger for a specific feature.

**Args:**
- `feature_name`: Name of the feature

**Returns:**
- Feature-configured logger

---

### ConfigSummarizer

Configuration analysis and reporting utilities.

#### Class Methods

##### `log_omega_config_summary(config, logger: Optional[logging.Logger] = None) -> None`

Log a summary of Omega/Hydra configuration.

**Args:**
- `config`: Configuration object to summarize
- `logger`: Optional logger instance (creates one if not provided)

##### `log_omega_config_full(config, logger: Optional[logging.Logger] = None) -> None`

Log full detailed configuration.

**Args:**
- `config`: Configuration object to log
- `logger`: Optional logger instance

---

### Statistics Classes

#### LogStatisticsCollector

Real-time log statistics collection.

##### `__init__(buffer_size: int = 1000, track_performance: bool = True) -> None`

Initialize statistics collector.

**Args:**
- `buffer_size`: Maximum number of messages to buffer
- `track_performance`: Whether to track performance metrics

##### `get_real_time_stats() -> Dict`

Get current real-time statistics.

**Returns:**
- Dictionary containing current statistics

##### `generate_summary_report() -> Dict`

Generate comprehensive statistics report.

**Returns:**
- Detailed statistics report

##### `export_statistics(format: str = "json") -> str`

Export statistics in specified format.

**Args:**
- `format`: Export format ('json', 'csv', 'text')

**Returns:**
- Formatted statistics string

#### LogPerformanceAnalyzer

Performance monitoring and analysis.

##### `create_performance_analyzer() -> LogPerformanceAnalyzer`

Factory function to create performance analyzer.

**Returns:**
- Configured performance analyzer instance

#### LogFeatureAnalyzer

Feature-specific log analysis.

##### `create_feature_analyzer() -> LogFeatureAnalyzer`

Factory function to create feature analyzer.

**Returns:**
- Configured feature analyzer instance

---

### File Utilities

#### FileUtils

File operation utilities with error handling.

##### `read_file(filepath: Path) -> str`

Read file contents with proper error handling.

**Args:**
- `filepath`: Path to file to read

**Returns:**
- File contents as string

**Raises:**
- `FileOperationError`: If file cannot be read

#### ConfigurationLoader

Configuration file loading utilities.

##### `load_config(filepath: Path) -> Dict`

Load configuration from file.

**Args:**
- `filepath`: Path to configuration file

**Returns:**
- Parsed configuration dictionary

---

### Debug Tools

#### DebugTools

Development and debugging utilities.

##### `F: str`

Debug flag constant for conditional debugging.

---

### Mixins

#### LoggerMixin

Basic logging mixin for components that need simple logging capabilities.

#### StringRepresentationMixin

Enhanced object representation mixin for better debugging output.

---

## Constants

### TRACE

Custom TRACE logging level (value: 5) for very detailed debugging output.

**Usage:**
```python
logger.log(TRACE, "Detailed trace message")
# or with trace method
logger.trace("Detailed trace message")
```

---

## Error Classes

### FileOperationError

Exception raised for file operation failures.

**Inherits:** `Exception`

**Usage:**
```python
try:
    content = FileUtils.read_file(path)
except FileOperationError as e:
    logger.error(f"Failed to read file: {e}")
```

---

## Usage Examples

### Basic Setup

```python
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# Initialize logging
LoggerFactory.initialize({
    "level": "INFO",
    "enable_colors": True,
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
})

# Use in a component
class MyService(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def process(self):
        self.info("Starting processing")
        try:
            # Do work
            self.debug("Processing step completed")
        except Exception as e:
            self.error(f"Processing failed: {e}", exc_info=True)
```

### Feature-Specific Configuration

```python
# Set different levels for different features
feature_levels = {
    "docker_operations": "DEBUG",    # Detailed Docker logging
    "event_system": "INFO",          # Standard event logging
    "config_processing": "WARNING"   # Only config warnings and errors
}

LoggerFactory.update_all_feature_levels(feature_levels)

# Components automatically use appropriate levels
docker_logger = LoggerFactory.get_feature_logger("docker_builder", "docker_operations")
event_logger = LoggerFactory.get_feature_logger("event_manager", "event_system")
```

### Statistics and Monitoring

```python
# Enable comprehensive statistics
LoggerFactory.enable_statistics({
    "enabled": True,
    "buffer_size": 5000,
    "track_performance": True,
    "handler_type": "buffered"
})

# Generate logs
logger = LoggerFactory.get_logger("monitored_component")
for i in range(100):
    logger.info(f"Operation {i} completed")

# Analyze statistics
stats = LoggerFactory.get_log_statistics()
print(f"Total messages: {stats['total_messages']}")
print(f"Messages by level: {stats['level_counts']}")

# Export detailed report
report = LoggerFactory.generate_statistics_report()
json_export = LoggerFactory.export_statistics("json")
```
