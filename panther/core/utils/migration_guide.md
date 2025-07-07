# Migration Guide - PANTHER Core Utilities

## Overview

This guide helps you migrate existing Python logging setups to PANTHER's feature-aware logging system. The migration process is designed to be incremental, allowing you to adopt features gradually without breaking existing functionality.

## Migration Strategies

### Strategy 1: Drop-in Replacement (Minimal Changes)

**Use case**: Existing codebase with standard Python logging
**Effort**: Low (1-2 hours)
**Benefits**: Immediate colored output and consistent formatting

#### Before (Standard Python Logging)

```python
import logging

# Old setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MyService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self):
        self.logger.info("Processing started")
        self.logger.debug("Processing details")
        self.logger.info("Processing completed")
```

#### After (PANTHER Drop-in)

```python
from panther.core.utils import LoggerFactory

# New setup - minimal changes
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
    "enable_colors": True  # New benefit!
})

# LoggerFactory patches logging.getLogger automatically
logger = logging.getLogger(__name__)  # Works as before!

class MyService:
    def __init__(self):
        # This now gets colored output and consistent formatting
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self):
        self.logger.info("Processing started")
        self.logger.debug("Processing details")
        self.logger.info("Processing completed")
```

**Migration Steps:**
1. Add `LoggerFactory.initialize()` call at application startup
2. Replace `logging.basicConfig()` with `LoggerFactory.initialize()`
3. Existing `logging.getLogger()` calls work unchanged
4. Test - you should see colored output immediately

### Strategy 2: Gradual Feature Adoption (Recommended)

**Use case**: Want to leverage feature-aware logging over time
**Effort**: Medium (4-8 hours)
**Benefits**: Feature-specific log levels, auto-detection, runtime configuration

#### Phase 1: Initialize with Feature Levels

```python
from panther.core.utils import LoggerFactory

# Enhanced setup with feature-specific levels
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
    "enable_colors": True,
    "output_file": "/var/log/myapp.log"
})

# Define feature-specific levels
LoggerFactory.update_all_feature_levels({
    "database": "DEBUG",      # Database operations need detail
    "api": "INFO",            # API calls standard level
    "background": "WARNING",  # Background jobs only warnings
    "security": "DEBUG"       # Security events need detail
})

# Existing code works unchanged
logger = logging.getLogger(__name__)
logger.info("Application starting")  # Uses auto-detected feature level
```

#### Phase 2: Convert High-Value Components

```python
from panther.core.utils import FeatureLoggerMixin

# Convert key components to use FeatureLoggerMixin
class DatabaseManager(FeatureLoggerMixin):  # Added mixin
    def __init__(self):
        self.__init_logger__()  # Added initialization
        # self.logger = logging.getLogger(...) <- Remove old logger setup

    def connect(self):
        # Old: self.logger.debug("Connecting to database")
        self.debug("Connecting to database")  # New: direct method

    def query(self, sql):
        # Old: self.logger.info(f"Executing: {sql}")
        self.info(f"Executing: {sql}")  # New: direct method

# Keep existing components unchanged during gradual migration
class LegacyService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)  # Unchanged

    def process(self):
        self.logger.info("Legacy processing")  # Still works
```

#### Phase 3: Full Migration

```python
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# All components use FeatureLoggerMixin
class APIHandler(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.info(f"API handler using feature: {self.get_effective_feature()}")

class SecurityValidator(FeatureLoggerMixin):
    def __init__(self):
        # Explicit feature assignment for components that don't auto-detect well
        self.__init_logger__(feature="security")

class BackgroundWorker(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()  # Auto-detects as "background" from class name
```

### Strategy 3: Green Field Migration (New Components)

**Use case**: Building new features with PANTHER from the start
**Effort**: Low (30 minutes per component)
**Benefits**: Full feature set, optimal architecture

```python
from panther.core.utils import LoggerFactory, FeatureLoggerMixin, feature_registry

# Application setup
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
    "enable_colors": True,
    "output_file": "/var/log/myapp.log"
})

# Register application-specific features
feature_registry.register_feature("order_processing", [
    "order", "checkout", "payment", "fulfillment"
])

feature_registry.register_feature("inventory_management", [
    "inventory", "stock", "warehouse", "supply"
])

# Set feature levels
LoggerFactory.update_all_feature_levels({
    "order_processing": "INFO",
    "inventory_management": "DEBUG",
    "unknown": "WARNING"
})

# Enable monitoring for new application
LoggerFactory.enable_statistics({
    "enabled": True,
    "track_performance": True
})

# New components built with PANTHER patterns
class OrderProcessor(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()  # Auto-detects order_processing
        self.info("Order processor initialized")

    def process_order(self, order_id):
        self.info(f"Processing order {order_id}")
        self.debug("Validating order details")  # Won't appear (INFO level)
        self.info("Order processed successfully")

class InventoryManager(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()  # Auto-detects inventory_management
        self.info("Inventory manager initialized")

    def update_stock(self, item_id, quantity):
        self.debug(f"Updating stock for {item_id}")  # Will appear (DEBUG level)
        self.info(f"Stock updated: {item_id} = {quantity}")
```

## Common Migration Patterns

### Pattern 1: Module-Level Logger Replacement

#### Before
```python
# module.py
import logging

logger = logging.getLogger(__name__)

def process_data():
    logger.info("Processing data")

def validate_input():
    logger.debug("Validating input")
```

#### After (Option A: Minimal Change)
```python
# module.py
from panther.core.utils import LoggerFactory

# Initialize somewhere in your application startup
logger = LoggerFactory.get_logger(__name__)

def process_data():
    logger.info("Processing data")

def validate_input():
    logger.debug("Validating input")
```

#### After (Option B: Feature-Aware)
```python
# module.py
from panther.core.utils import LoggerFactory

# Get feature-specific logger
logger = LoggerFactory.get_feature_logger(__name__, "data_processing")

def process_data():
    logger.info("Processing data")

def validate_input():
    logger.debug("Validating input")
```

### Pattern 2: Class-Based Logger Replacement

#### Before
```python
class DataProcessor:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self):
        self.logger.info("Processing started")
        try:
            self._do_work()
            self.logger.info("Processing completed")
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")

    def _do_work(self):
        self.logger.debug("Internal processing")
```

#### After
```python
class DataProcessor(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()  # Replaces logger setup

    def process(self):
        self.info("Processing started")  # Direct method call
        try:
            self._do_work()
            self.info("Processing completed")
        except Exception as e:
            self.error(f"Processing failed: {e}", exc_info=True)  # Enhanced error logging

    def _do_work(self):
        self.debug("Internal processing")
```

### Pattern 3: Configuration Migration

#### Before (logging.ini or dictConfig)
```ini
[loggers]
keys=root,myapp

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=DEBUG
handlers=consoleHandler

[logger_myapp]
level=INFO
handlers=consoleHandler,fileHandler
qualname=myapp
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=DEBUG
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=simpleFormatter
args=('/var/log/myapp.log',)

[formatter_simpleFormatter]
format=%(asctime)s [%(levelname)s] - %(name)s - %(message)s
```

#### After (Python Configuration)
```python
from panther.core.utils import LoggerFactory

# Equivalent PANTHER configuration
LoggerFactory.initialize({
    "level": "INFO",  # Console level
    "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
    "enable_colors": True,  # Added benefit
    "output_file": "/var/log/myapp.log",
    "debug_file_logging": True  # File gets DEBUG, console gets INFO
})

# Feature-specific levels (new capability)
LoggerFactory.update_all_feature_levels({
    "database": "DEBUG",
    "api": "INFO",
    "background": "WARNING"
})
```

## Troubleshooting Migration Issues

### Issue 1: Existing Loggers Not Using New Configuration

**Problem**: Loggers created before `LoggerFactory.initialize()` don't get new formatting.

**Solution**: Initialize LoggerFactory early in application startup, before creating any loggers.

```python
# main.py or __init__.py
from panther.core.utils import LoggerFactory

# Initialize FIRST, before any other imports that create loggers
LoggerFactory.initialize({...})

# Now import modules that create loggers
from .services import MyService
from .handlers import APIHandler
```

### Issue 2: Third-Party Libraries Not Using PANTHER Formatting

**Problem**: Third-party libraries still use default logging format.

**Solution**: PANTHER automatically patches `logging.getLogger()`, so this should work. If not:

```python
# Force patch application
LoggerFactory.initialize({...})

# Get specific third-party logger and it will use PANTHER formatting
import requests
requests_logger = logging.getLogger("urllib3")  # Now uses PANTHER format
```

### Issue 3: Performance Degradation After Migration

**Problem**: Application runs slower after enabling statistics.

**Solution**: Disable or optimize statistics collection:

```python
# Disable statistics for production
LoggerFactory.disable_statistics()

# Or use buffered collection for better performance
LoggerFactory.enable_statistics({
    "enabled": True,
    "handler_type": "buffered",  # Better performance
    "buffer_size": 100,          # Smaller buffer
    "track_performance": False   # Disable expensive tracking
})
```

### Issue 4: Feature Detection Not Working

**Problem**: Components not getting expected feature assignment.

**Solution**: Check and adjust feature detection:

```python
from panther.core.utils import LoggerFactory

# Debug feature detection
component_name = "MyComponent"
detected = LoggerFactory._detect_feature_from_name(component_name)
print(f"'{component_name}' detected as: {detected}")

# Register custom patterns if needed
from panther.core.utils import feature_registry
feature_registry.register_feature("my_feature", ["MyComponent", "pattern"])

# Or use explicit assignment
class MyComponent(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__(feature="explicit_feature")
```

### Issue 5: File Logging Not Working

**Problem**: Log messages not appearing in specified file.

**Solution**: Check file permissions and paths:

```python
import os
from pathlib import Path

log_file = Path("/var/log/myapp.log")

# Ensure directory exists
log_file.parent.mkdir(parents=True, exist_ok=True)

# Check permissions
if not os.access(log_file.parent, os.W_OK):
    print(f"No write permission to {log_file.parent}")
    # Use alternative location
    log_file = Path("/tmp/myapp.log")

LoggerFactory.initialize({
    "output_file": str(log_file),
    # ... other config
})
```

## Migration Testing

### Test 1: Verify Basic Functionality

```python
def test_basic_migration():
    """Test that basic logging still works after migration."""
    from panther.core.utils import LoggerFactory

    LoggerFactory.initialize({"level": "DEBUG", "enable_colors": True})

    # Test standard logging still works
    import logging
    logger = logging.getLogger("test")

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    print("✓ Basic logging functionality verified")

test_basic_migration()
```

### Test 2: Verify Feature Detection

```python
def test_feature_detection():
    """Test that feature detection works for your components."""
    from panther.core.utils import LoggerFactory, FeatureLoggerMixin

    LoggerFactory.initialize({"level": "DEBUG"})
    LoggerFactory.update_all_feature_levels({
        "database": "DEBUG",
        "api": "INFO"
    })

    class DatabaseService(FeatureLoggerMixin):
        def __init__(self):
            self.__init_logger__()
            feature = self.get_effective_feature()
            assert feature == "database", f"Expected 'database', got '{feature}'"
            self.info("Database service feature detection verified")

    class APIHandler(FeatureLoggerMixin):
        def __init__(self):
            self.__init_logger__()
            feature = self.get_effective_feature()
            print(f"API handler detected as feature: {feature}")

    db = DatabaseService()
    api = APIHandler()

    print("✓ Feature detection verified")

test_feature_detection()
```

### Test 3: Performance Baseline

```python
def test_performance_impact():
    """Measure performance impact of migration."""
    import time
    from panther.core.utils import LoggerFactory

    # Test with standard logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("perf_test")

    start = time.time()
    for i in range(1000):
        logger.info(f"Standard logging message {i}")
    standard_time = time.time() - start

    # Test with PANTHER
    LoggerFactory.initialize({"level": "INFO", "enable_colors": True})
    panther_logger = LoggerFactory.get_logger("perf_test_panther")

    start = time.time()
    for i in range(1000):
        panther_logger.info(f"PANTHER logging message {i}")
    panther_time = time.time() - start

    overhead = ((panther_time - standard_time) / standard_time) * 100
    print(f"Standard logging: {standard_time:.3f}s")
    print(f"PANTHER logging: {panther_time:.3f}s")
    print(f"Overhead: {overhead:.1f}%")

    assert overhead < 20, f"Performance overhead too high: {overhead:.1f}%"
    print("✓ Performance impact acceptable")

test_performance_impact()
```

## Best Practices for Migration

### 1. Start Small
- Begin with a single module or component
- Verify functionality before expanding
- Keep old and new logging side by side initially

### 2. Plan Feature Categories
- Map your application's components to logical features
- Start with obvious categories (database, api, background)
- Refine based on actual usage patterns

### 3. Gradual Rollout
- Week 1: Initialize LoggerFactory with basic config
- Week 2: Add feature-specific levels
- Week 3: Convert high-traffic components to FeatureLoggerMixin
- Week 4: Enable statistics and monitoring

### 4. Monitor and Tune
- Watch for performance impact
- Adjust feature levels based on debugging needs
- Use statistics to understand logging patterns

### 5. Document Changes
- Update deployment documentation
- Train team on new logging capabilities
- Document feature categories and conventions

The migration to PANTHER's feature-aware logging is designed to be incremental and low-risk. Start with the minimal changes and gradually adopt more features as you become comfortable with the system.
