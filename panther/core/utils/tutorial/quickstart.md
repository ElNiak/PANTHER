# Quick Start Tutorial - PANTHER Core Utilities

## Introduction

This tutorial walks you through the essential features of PANTHER's core utilities, focusing on the logging infrastructure and feature-aware capabilities. You'll learn how to set up logging, use feature detection, and monitor your application's logging behavior.

## Step 1: Basic Logger Setup

Let's start with the simplest possible setup:

```python
from panther.core.utils import LoggerFactory

# Initialize the logger factory with basic configuration
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True
})

# Get a logger for your component
logger = LoggerFactory.get_logger("my_component")

# Use the logger
logger.info("Application started successfully")
logger.debug("This debug message won't appear (level is INFO)")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

**Expected Output:**
```
2024-07-05 10:30:15 [INFO] - my_component - Application started successfully
2024-07-05 10:30:15 [WARNING] - my_component - This is a warning message
2024-07-05 10:30:15 [ERROR] - my_component - This is an error message
```

**What happened?**
- LoggerFactory configured all loggers with consistent formatting
- Colors are enabled (if your terminal supports them)
- DEBUG message didn't appear because level is set to INFO
- All messages follow the same format pattern

## Step 2: Using Feature-Aware Logging

PANTHER's most powerful feature is automatic feature detection and level management:

```python
from panther.core.utils import FeatureLoggerMixin

class DockerManager(FeatureLoggerMixin):
    def __init__(self):
        # Logger automatically detects this is docker-related
        self.__init_logger__()

    def build_container(self):
        self.info("Starting container build")
        self.debug("Checking Docker daemon")
        self.info("Build completed successfully")

    def check_feature(self):
        feature = self.get_effective_feature()
        self.info(f"Auto-detected feature: {feature}")

# Test the feature detection
manager = DockerManager()
manager.check_feature()
manager.build_container()
```

**Expected Output:**
```
2024-07-05 10:30:16 [INFO] - __main__.DockerManager - Auto-detected feature: docker_operations
2024-07-05 10:30:16 [INFO] - __main__.DockerManager - Starting container build
2024-07-05 10:30:16 [INFO] - __main__.DockerManager - Build completed successfully
```

**What happened?**
- PANTHER detected "docker" in the class name
- Component was automatically assigned to "docker_operations" feature
- DEBUG message didn't appear (still using INFO level)

## Step 3: Feature-Specific Log Levels

Now let's set different log levels for different features:

```python
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# Set feature-specific levels
feature_levels = {
    "docker_operations": "DEBUG",    # Very detailed for Docker
    "config_processing": "WARNING",  # Only warnings/errors for config
    "event_system": "INFO"          # Standard info for events
}

LoggerFactory.update_all_feature_levels(feature_levels)

class DockerManager(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def build_container(self):
        self.info("Starting container build")
        self.debug("Checking Docker daemon")  # Now this will appear!
        self.debug("Reading Dockerfile")     # This too!
        self.info("Build completed successfully")

class ConfigLoader(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def load_config(self):
        self.info("Loading configuration")     # Won't appear (WARNING level)
        self.debug("Parsing config file")     # Won't appear
        self.warning("Missing optional setting")  # Will appear
        self.info("Configuration loaded")     # Won't appear

# Test both components
docker_mgr = DockerManager()
config_loader = ConfigLoader()

print("=== Docker Operations (DEBUG level) ===")
docker_mgr.build_container()

print("\n=== Config Processing (WARNING level) ===")
config_loader.load_config()
```

**Expected Output:**
```
=== Docker Operations (DEBUG level) ===
2024-07-05 10:30:17 [INFO] - __main__.DockerManager - Starting container build
2024-07-05 10:30:17 [DEBUG] - __main__.DockerManager - Checking Docker daemon
2024-07-05 10:30:17 [DEBUG] - __main__.DockerManager - Reading Dockerfile
2024-07-05 10:30:17 [INFO] - __main__.DockerManager - Build completed successfully

=== Config Processing (WARNING level) ===
2024-07-05 10:30:17 [WARNING] - __main__.ConfigLoader - Missing optional setting
```

**What happened?**
- Docker component got DEBUG level (shows all messages)
- Config component got WARNING level (only warnings and errors)
- Each feature can have completely different logging verbosity

## Step 4: Explicit Feature Assignment

Sometimes auto-detection isn't perfect. You can explicitly assign features:

```python
from panther.core.utils import FeatureLoggerMixin, LoggerFactory

class MyCustomComponent(FeatureLoggerMixin):
    def __init__(self):
        # Explicitly assign to event_system feature
        self.__init_logger__(feature="event_system")

    def process_events(self):
        feature = self.get_effective_feature()
        self.info(f"Using feature: {feature}")
        self.debug("Processing events")  # INFO level, so won't appear

# Alternative: Get feature-specific logger directly
logger = LoggerFactory.get_feature_logger("my_component", "docker_operations")
logger.debug("This debug message will appear!")  # DEBUG level from docker_operations

# Test explicit assignment
component = MyCustomComponent()
component.process_events()
```

**Expected Output:**
```
2024-07-05 10:30:18 [DEBUG] - my_component - This debug message will appear!
2024-07-05 10:30:18 [INFO] - __main__.MyCustomComponent - Using feature: event_system
```

## Step 5: Statistics and Monitoring

Track your application's logging behavior:

```python
from panther.core.utils import LoggerFactory

# Enable statistics collection
LoggerFactory.enable_statistics({
    "enabled": True,
    "buffer_size": 1000,
    "track_performance": True
})

# Generate some log activity
logger = LoggerFactory.get_logger("stats_demo")
for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
    for i in range(5):
        getattr(logger, level.lower())(f"{level} message {i+1}")

# Check the statistics
stats = LoggerFactory.get_log_statistics()
print(f"\nLogging Statistics:")
print(f"Total messages: {stats.get('total_messages', 0)}")
print(f"Messages by level: {stats.get('level_counts', {})}")
print(f"Messages by feature: {stats.get('feature_counts', {})}")

# Generate a detailed report
report = LoggerFactory.generate_statistics_report()
print(f"\nDetailed Report:")
print(f"Collection period: {report.get('collection_period', 'Unknown')}")
print(f"Performance metrics available: {report.get('has_performance_data', False)}")
```

**Expected Output:**
```
2024-07-05 10:30:19 [INFO] - stats_demo - INFO message 1
2024-07-05 10:30:19 [INFO] - stats_demo - INFO message 2
... (more INFO, WARNING, ERROR messages)

Logging Statistics:
Total messages: 15
Messages by level: {'INFO': 5, 'WARNING': 5, 'ERROR': 5}
Messages by feature: {'unknown': 15}

Detailed Report:
Collection period: 2.345 seconds
Performance metrics available: True
```

## Step 6: File Logging

Add file output for persistent logging:

```python
from panther.core.utils import LoggerFactory

# Initialize with file output
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True,
    "output_file": "/tmp/panther_tutorial.log",
    "debug_file_logging": True  # File gets DEBUG, console gets INFO
})

logger = LoggerFactory.get_logger("file_demo")

logger.debug("This appears in file only")
logger.info("This appears in both console and file")
logger.error("This also appears in both")

print("\nCheck /tmp/panther_tutorial.log for all messages including DEBUG")
```

**What happened?**
- Console still shows INFO and above
- File captures ALL messages including DEBUG
- Same logger, different output destinations with different levels

## Step 7: Dynamic Configuration Updates

Change logging behavior at runtime:

```python
from panther.core.utils import LoggerFactory

# Start with INFO level
logger = LoggerFactory.get_logger("dynamic_demo")
logger.debug("Initial debug - won't appear")
logger.info("Initial info - will appear")

# Change to DEBUG level
LoggerFactory.update_feature_level("unknown", "DEBUG")  # "unknown" is default feature
logger.debug("Updated debug - now appears!")
logger.info("Updated info - still appears")

# Change specific feature level
LoggerFactory.update_feature_level("docker_operations", "ERROR")
docker_logger = LoggerFactory.get_feature_logger("docker_test", "docker_operations")
docker_logger.info("Docker info - won't appear")
docker_logger.error("Docker error - will appear")
```

**Expected Output:**
```
2024-07-05 10:30:20 [INFO] - dynamic_demo - Initial info - will appear
2024-07-05 10:30:20 [DEBUG] - dynamic_demo - Updated debug - now appears!
2024-07-05 10:30:20 [INFO] - dynamic_demo - Updated info - still appears
2024-07-05 10:30:20 [ERROR] - docker_test - Docker error - will appear
```

## Complete Example: Building a Service

Here's a complete example showing how to use the utilities in a real service:

```python
from panther.core.utils import FeatureLoggerMixin, LoggerFactory

# Configure logging for the entire application
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True,
    "output_file": "/tmp/service.log"
})

# Set feature-specific levels
LoggerFactory.update_all_feature_levels({
    "docker_operations": "DEBUG",
    "config_processing": "WARNING",
    "event_system": "INFO"
})

# Enable monitoring
LoggerFactory.enable_statistics({"enabled": True, "track_performance": True})

class ServiceManager(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.info(f"ServiceManager initialized with feature: {self.get_effective_feature()}")

    def start_service(self):
        self.info("Starting service")
        try:
            self._load_config()
            self._setup_docker()
            self._start_event_processing()
            self.info("Service started successfully")
        except Exception as e:
            self.error(f"Service startup failed: {e}", exc_info=True)

    def _load_config(self):
        # This would be detected as config_processing (WARNING level)
        config_logger = LoggerFactory.get_feature_logger("config", "config_processing")
        config_logger.info("Loading config")  # Won't appear
        config_logger.warning("Using default for missing setting")  # Will appear

    def _setup_docker(self):
        # This would be detected as docker_operations (DEBUG level)
        docker_logger = LoggerFactory.get_feature_logger("docker", "docker_operations")
        docker_logger.debug("Checking Docker daemon")  # Will appear
        docker_logger.info("Docker setup complete")  # Will appear

    def _start_event_processing(self):
        # This would be detected as event_system (INFO level)
        event_logger = LoggerFactory.get_feature_logger("events", "event_system")
        event_logger.debug("Event loop details")  # Won't appear
        event_logger.info("Event processing started")  # Will appear

# Run the service
service = ServiceManager()
service.start_service()

# Check final statistics
stats = LoggerFactory.get_log_statistics()
print(f"\nFinal Statistics: {stats.get('total_messages', 0)} total messages")
```

## Next Steps

You now understand the core concepts:

1. **LoggerFactory**: Centralized logger management with consistent configuration
2. **Feature Detection**: Automatic categorization of components for targeted logging
3. **Dynamic Configuration**: Runtime updates to logging levels
4. **Statistics**: Monitoring and analysis of logging behavior
5. **File Output**: Persistent logging with different console/file levels

For advanced usage, see:
- Developer Guide for extending the utilities
- API Reference for complete method documentation
- README for architecture details and integration patterns

Try experimenting with your own components and see how the feature detection works!
