# PANTHER Core Utilities

## Overview

The PANTHER core utilities module provides a sophisticated logging and utility infrastructure that serves as the foundation for the entire PANTHER framework. This module implements feature-aware logging, dynamic configuration management, and comprehensive statistics collection capabilities.

## Architecture

The core utilities are organized around several key architectural patterns:

```
panther.core.utils/
├── Logging Infrastructure
│   ├── LoggerFactory          # Centralized logger management
│   ├── FeatureLoggerMixin     # Feature-aware logging capabilities
│   └── LoggerMixin           # Basic logging mixin
├── Feature Management
│   ├── FeatureRegistry       # Dynamic feature registration system
│   └── Auto-Detection        # Intelligent feature mapping
├── Statistics & Analytics
│   ├── LogStatisticsCollector # Real-time log analytics
│   ├── LogPerformanceAnalyzer # Performance monitoring
│   └── LogFeatureAnalyzer    # Feature-specific analysis
├── Configuration Management
│   ├── ConfigSummarizer      # Configuration analysis and reporting
│   └── FileUtils            # File operations and configuration loading
└── Utility Components
    ├── DebugTools            # Development and debugging utilities
    └── StringRepresentationMixin # Enhanced object representation
```

## Core Design Principles

### Feature-Aware Logging

The logging system automatically detects and categorizes components based on their functionality, enabling intelligent log level management:

- **Automatic Feature Detection**: Components are automatically categorized into features like `docker_operations`, `event_system`, `config_processing`
- **Dynamic Level Management**: Different features can have different logging levels set at runtime
- **Hierarchical Configuration**: Feature-specific levels override global defaults

### Centralized Factory Pattern

All logging resources are managed through the `LoggerFactory` singleton, ensuring:

- **Consistent Configuration**: All loggers use the same formatting and handlers
- **Resource Efficiency**: Handlers and formatters are shared and cached
- **Dynamic Updates**: Configuration changes apply to all existing loggers

### Performance-First Design

The infrastructure is designed for high-performance operation:

- **Lazy Initialization**: Components are initialized only when needed
- **Buffered Handlers**: Optional buffering for high-volume logging scenarios
- **Minimal Overhead**: Statistics collection adds <5% performance impact

## Key Components

### LoggerFactory

Central factory for creating and managing loggers with feature-aware capabilities.

**Features:**
- Feature-based automatic log level assignment
- Dynamic configuration updates without restart
- Color support with graceful fallback
- Multi-handler coordination (console + file)
- Comprehensive statistics integration

### FeatureLoggerMixin

Mixin class that provides automatic feature detection and logging setup for any component.

**Capabilities:**
- Automatic feature detection from class/module names
- Lazy logger initialization
- Feature-specific logging methods
- Runtime level updates

### FeatureRegistry

Dynamic registry system for mapping components to features and managing feature-specific behavior.

**Functions:**
- Runtime feature registration
- Pattern-based feature detection
- Module-level feature management
- Cross-component feature coordination

## Integration Points

### Framework Dependencies

The utilities module integrates with:

- **Command Processing**: Provides logging for command generation and execution
- **Docker Operations**: Feature-aware logging for container management
- **Event System**: Specialized logging for event emission and processing
- **Configuration Management**: Integrated config analysis and reporting

### External Dependencies

Minimal external dependencies for reliability:

- `colorlog`: Optional color support (graceful fallback if unavailable)
- `psutil`: Optional performance monitoring (detected at runtime)
- Standard library logging module (enhanced, not replaced)

## Performance Characteristics

### Initialization
- **Factory Setup**: <10ms for complete initialization
- **Logger Creation**: <1ms per logger with feature detection
- **Feature Detection**: O(1) lookup with cached results

### Runtime Performance
- **Level Updates**: O(n) where n is number of existing loggers
- **Statistics Collection**: <5% overhead when enabled
- **Memory Usage**: Bounded caches with automatic cleanup

### Scalability
- **Handler Sharing**: Efficient resource usage across loggers
- **Buffered Output**: Configurable buffering for high-volume scenarios
- **Thread Safety**: All operations are thread-safe

## Configuration

### Basic Configuration

```python
from panther.core.utils import LoggerFactory

# Initialize with basic configuration
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True,
    "output_file": "/path/to/logfile.log"
})
```

### Feature-Specific Levels

```python
# Set different levels for different features
feature_levels = {
    "docker_operations": "DEBUG",
    "event_system": "INFO",
    "config_processing": "WARNING"
}

LoggerFactory.update_all_feature_levels(feature_levels)
```

### Statistics Configuration

```python
# Enable comprehensive statistics
LoggerFactory.enable_statistics({
    "enabled": True,
    "buffer_size": 1000,
    "track_performance": True,
    "handler_type": "buffered"
})
```

## Usage Patterns

### Component Integration

```python
from panther.core.utils import FeatureLoggerMixin

class MyComponent(FeatureLoggerMixin):
    def __init__(self):
        # Logger automatically configured with feature detection
        self.__init_logger__()

    def process_data(self):
        self.info("Processing data")  # Feature-aware logging
        # ... implementation
```

### Factory Usage

```python
from panther.core.utils import LoggerFactory

# Get feature-specific logger
logger = LoggerFactory.get_feature_logger("component_name", "docker_operations")

# Get standard logger with auto-detection
logger = LoggerFactory.get_logger(__name__)
```

### Statistics and Monitoring

```python
# Real-time statistics
stats = LoggerFactory.get_log_statistics()

# Comprehensive reporting
report = LoggerFactory.generate_statistics_report()

# Export in different formats
json_stats = LoggerFactory.export_statistics("json")
csv_stats = LoggerFactory.export_statistics("csv")
```

## Debugging and Troubleshooting

### Common Issues

1. **Missing Colors**: Ensure `colorlog` is installed for colored output
2. **Performance Issues**: Check if statistics collection is enabled unnecessarily
3. **Level Not Applied**: Verify feature detection is working correctly

### Diagnostic Tools

```python
# Check feature detection
logger = LoggerFactory.get_logger("my_component")
detected_feature = LoggerFactory._detect_feature_from_name("my_component")

# Verify configuration
factory_config = LoggerFactory._config
feature_levels = LoggerFactory._feature_levels

# Statistics diagnostics
handler_stats = LoggerFactory.get_statistics_handler_stats()
```

## Extension Points

### Custom Feature Detection

```python
from panther.core.utils import feature_registry

# Register custom feature patterns
feature_registry.register_feature("custom_feature", ["pattern1", "pattern2"])

# Register module-specific features
feature_registry.register_module_feature("my_module", "custom_feature")
```

### Custom Statistics

```python
from panther.core.utils.log_statistics_collector import LogStatisticsCollector

# Create custom collector with specific configuration
collector = LogStatisticsCollector(buffer_size=5000, track_performance=True)

# Integrate with factory
LoggerFactory._statistics_collector = collector
```

## Thread Safety

All public methods in the utilities module are thread-safe:

- **Logger Creation**: Protected by internal locks
- **Configuration Updates**: Atomic operations with proper synchronization
- **Statistics Collection**: Lock-free data structures where possible
- **Handler Management**: Synchronized access to shared resources

## Future Enhancements

The utilities module is designed for extensibility:

- **Plugin System**: Framework for custom logging plugins
- **Remote Logging**: Support for remote log aggregation
- **Advanced Analytics**: Machine learning-based log analysis
- **Configuration Hot-Reload**: Dynamic configuration updates from external sources
