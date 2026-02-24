# Basic Setup Examples

This document provides copy-paste examples for common PANTHER core utilities setup scenarios.

## Example 1: Simple Application Setup

```python
#!/usr/bin/env python3
"""
Basic application setup with PANTHER logging.
This is the minimal setup for most applications.
"""
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# Initialize logging for entire application
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True
})

class MyApplication(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.info("Application initialized")

    def run(self):
        self.info("Starting application")
        try:
            self._setup()
            self._process()
            self.info("Application completed successfully")
        except Exception as e:
            self.error(f"Application failed: {e}", exc_info=True)

    def _setup(self):
        self.debug("Setting up resources")
        # Setup code here

    def _process(self):
        self.info("Processing data")
        # Main application logic here

if __name__ == "__main__":
    app = MyApplication()
    app.run()
```

**Expected Output:**
```
2024-07-05 10:30:00 [INFO] - __main__.MyApplication - Application initialized
2024-07-05 10:30:00 [INFO] - __main__.MyApplication - Starting application
2024-07-05 10:30:00 [INFO] - __main__.MyApplication - Processing data
2024-07-05 10:30:00 [INFO] - __main__.MyApplication - Application completed successfully
```

## Example 2: Multi-Component Application

```python
#!/usr/bin/env python3
"""
Multi-component application with feature-specific logging levels.
Demonstrates how different components can have different log verbosity.
"""
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# Initialize with feature-specific levels
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
    "enable_colors": True,
    "output_file": "/tmp/application.log"
})

# Set feature-specific levels
LoggerFactory.update_all_feature_levels({
    "config_processing": "WARNING",  # Only show config warnings/errors
    "docker_operations": "DEBUG",    # Detailed Docker logging
    "event_system": "INFO"          # Standard event logging
})

class ConfigManager(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def load_config(self):
        self.info("Loading configuration")  # Won't appear (WARNING level)
        self.debug("Parsing config file")   # Won't appear
        self.warning("Using default value for missing setting")  # Will appear
        return {"setting1": "value1"}

class DockerService(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def start_container(self):
        self.info("Starting container")     # Will appear (DEBUG level)
        self.debug("Checking Docker daemon")  # Will appear
        self.debug("Building image")       # Will appear
        self.info("Container started")     # Will appear

class EventProcessor(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()

    def process_events(self):
        self.debug("Processing event queue")  # Won't appear (INFO level)
        self.info("Event processing started")  # Will appear
        self.info("Event processing completed")  # Will appear

class Application(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.config = ConfigManager()
        self.docker = DockerService()
        self.events = EventProcessor()

    def run(self):
        self.info("Application starting")

        config = self.config.load_config()
        self.docker.start_container()
        self.events.process_events()

        self.info("Application completed")

if __name__ == "__main__":
    app = Application()
    app.run()
```

**Expected Output:**
```
2024-07-05 10:30:00 [INFO] - __main__.Application - Application starting
2024-07-05 10:30:00 [WARNING] - __main__.ConfigManager - Using default value for missing setting
2024-07-05 10:30:00 [INFO] - __main__.DockerService - Starting container
2024-07-05 10:30:00 [DEBUG] - __main__.DockerService - Checking Docker daemon
2024-07-05 10:30:00 [DEBUG] - __main__.DockerService - Building image
2024-07-05 10:30:00 [INFO] - __main__.DockerService - Container started
2024-07-05 10:30:00 [INFO] - __main__.EventProcessor - Event processing started
2024-07-05 10:30:00 [INFO] - __main__.EventProcessor - Event processing completed
2024-07-05 10:30:00 [INFO] - __main__.Application - Application completed
```

## Example 3: Service with Statistics Monitoring

```python
#!/usr/bin/env python3
"""
Service with comprehensive logging statistics and monitoring.
Demonstrates statistics collection, performance tracking, and reporting.
"""
import time
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

# Initialize with statistics enabled
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
    "enable_colors": True
})

# Enable comprehensive statistics
LoggerFactory.enable_statistics({
    "enabled": True,
    "buffer_size": 1000,
    "track_performance": True,
    "handler_type": "buffered"
})

class MonitoredService(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.info("Service initialized with monitoring")

    def process_batch(self, batch_size=10):
        self.info(f"Processing batch of {batch_size} items")

        for i in range(batch_size):
            if i % 3 == 0:
                self.debug(f"Processing item {i}")
            elif i % 3 == 1:
                self.info(f"Completed item {i}")
            else:
                self.warning(f"Issue with item {i}")

            # Simulate processing time
            time.sleep(0.01)

        self.info(f"Batch processing completed")

    def simulate_error_conditions(self):
        self.error("Simulated error condition")
        self.critical("Simulated critical condition")

    def generate_statistics_report(self):
        # Get real-time statistics
        stats = LoggerFactory.get_log_statistics()

        if stats:
            self.info("=== Logging Statistics ===")
            self.info(f"Total messages: {stats.get('total_messages', 0)}")
            self.info(f"Messages by level: {stats.get('level_counts', {})}")
            self.info(f"Performance data available: {stats.get('has_performance_data', False)}")

            # Generate detailed report
            report = LoggerFactory.generate_statistics_report()
            self.info(f"Collection period: {report.get('collection_period', 'Unknown')}")

            # Export statistics
            json_stats = LoggerFactory.export_statistics("json")
            self.debug(f"JSON export length: {len(json_stats)} characters")
        else:
            self.warning("Statistics not available")

def main():
    service = MonitoredService()

    # Process some data
    service.process_batch(5)

    # Simulate error conditions
    service.simulate_error_conditions()

    # Generate and display statistics
    service.generate_statistics_report()

    # Check handler performance
    handler_stats = LoggerFactory.get_statistics_handler_stats()
    if handler_stats:
        print(f"\nHandler Performance:")
        print(f"Messages processed: {handler_stats.get('messages_processed', 0)}")
        print(f"Average processing time: {handler_stats.get('avg_processing_time_ms', 0):.2f}ms")

if __name__ == "__main__":
    main()
```

## Example 4: Custom Feature Registration

```python
#!/usr/bin/env python3
"""
Demonstrates custom feature registration and explicit feature assignment.
Shows how to extend the feature detection system for custom components.
"""
from panther.core.utils import LoggerFactory, FeatureLoggerMixin, feature_registry

# Initialize logging
LoggerFactory.initialize({
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
    "enable_colors": True
})

# Register custom features
feature_registry.register_feature("payment_processing", [
    "payment", "billing", "invoice", "transaction"
])

feature_registry.register_feature("user_management", [
    "user", "account", "profile", "authentication"
])

# Set levels for custom features
LoggerFactory.update_all_feature_levels({
    "payment_processing": "DEBUG",  # Very detailed for payments
    "user_management": "INFO",      # Standard for user operations
    "unknown": "WARNING"            # Conservative default
})

class PaymentProcessor(FeatureLoggerMixin):
    def __init__(self):
        # Auto-detected as payment_processing due to class name
        self.__init_logger__()
        feature = self.get_effective_feature()
        self.info(f"PaymentProcessor initialized with feature: {feature}")

    def process_payment(self, amount):
        self.debug(f"Starting payment processing for ${amount}")
        self.debug("Validating payment details")
        self.info(f"Payment of ${amount} processed successfully")

class UserManager(FeatureLoggerMixin):
    def __init__(self):
        # Auto-detected as user_management due to class name
        self.__init_logger__()
        feature = self.get_effective_feature()
        self.info(f"UserManager initialized with feature: {feature}")

    def create_user(self, username):
        self.debug(f"Creating user: {username}")  # Won't appear (INFO level)
        self.info(f"User {username} created successfully")

class CustomComponent(FeatureLoggerMixin):
    def __init__(self):
        # Explicitly assign to payment_processing feature
        self.__init_logger__(feature="payment_processing")
        feature = self.get_effective_feature()
        self.info(f"CustomComponent using explicit feature: {feature}")

    def do_work(self):
        self.debug("This will appear due to payment_processing DEBUG level")
        self.info("Work completed")

class UnknownComponent(FeatureLoggerMixin):
    def __init__(self):
        # Will be assigned to "unknown" feature (WARNING level)
        self.__init_logger__()
        feature = self.get_effective_feature()
        self.info(f"UnknownComponent feature: {feature}")  # Won't appear

    def do_work(self):
        self.info("This won't appear")      # Won't appear (WARNING level)
        self.warning("This will appear")    # Will appear
        self.error("This will also appear") # Will appear

def main():
    # Demonstrate feature detection and levels
    payment = PaymentProcessor()
    payment.process_payment(99.99)

    user = UserManager()
    user.create_user("testuser")

    custom = CustomComponent()
    custom.do_work()

    unknown = UnknownComponent()
    unknown.do_work()

if __name__ == "__main__":
    main()
```

**Expected Output:**
```
2024-07-05 10:30:00 [INFO] - __main__.PaymentProcessor - PaymentProcessor initialized with feature: payment_processing
2024-07-05 10:30:00 [DEBUG] - __main__.PaymentProcessor - Starting payment processing for $99.99
2024-07-05 10:30:00 [DEBUG] - __main__.PaymentProcessor - Validating payment details
2024-07-05 10:30:00 [INFO] - __main__.PaymentProcessor - Payment of $99.99 processed successfully
2024-07-05 10:30:00 [INFO] - __main__.UserManager - UserManager initialized with feature: user_management
2024-07-05 10:30:00 [INFO] - __main__.UserManager - User testuser created successfully
2024-07-05 10:30:00 [INFO] - __main__.CustomComponent - CustomComponent using explicit feature: payment_processing
2024-07-05 10:30:00 [DEBUG] - __main__.CustomComponent - This will appear due to payment_processing DEBUG level
2024-07-05 10:30:00 [INFO] - __main__.CustomComponent - Work completed
2024-07-05 10:30:00 [WARNING] - __main__.UnknownComponent - This will appear
2024-07-05 10:30:00 [ERROR] - __main__.UnknownComponent - This will also appear
```

## Example 5: Production Deployment Setup

```python
#!/usr/bin/env python3
"""
Production-ready logging setup with file rotation, performance optimization,
and comprehensive error handling.
"""
import os
import logging.handlers
from pathlib import Path
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

def setup_production_logging():
    """Setup logging configuration for production deployment."""

    # Create log directory
    log_dir = Path("/var/log/myapp")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Production configuration
    config = {
        "level": "INFO",  # Conservative level for production
        "format": "%(asctime)s [%(levelname)s] %(name)s [%(process)d] - %(message)s",
        "enable_colors": False,  # Disable colors for file logging
        "output_file": str(log_dir / "application.log"),
        "debug_file_logging": False  # File uses same level as console
    }

    LoggerFactory.initialize(config)

    # Production feature levels (conservative)
    LoggerFactory.update_all_feature_levels({
        "docker_operations": "INFO",    # Standard level
        "config_processing": "WARNING", # Only issues
        "event_system": "INFO",         # Standard level
        "error_handling": "DEBUG",      # Detailed error info
        "unknown": "WARNING"            # Conservative default
    })

    # Disable statistics in production for performance
    LoggerFactory.disable_statistics()

class ProductionService(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.info("Production service starting")

    def run(self):
        try:
            self.info("Service operational")
            self._health_check()
            self._process_requests()
        except Exception as e:
            self.critical(f"Service failure: {e}", exc_info=True)
            raise

    def _health_check(self):
        self.debug("Running health check")  # Won't appear in production
        self.info("Health check passed")

    def _process_requests(self):
        self.info("Processing requests")
        # Simulate some work
        for i in range(3):
            self.debug(f"Processing request {i}")  # Won't appear
            if i == 2:
                self.warning("High latency detected")  # Will appear

def main():
    # Setup production logging
    setup_production_logging()

    # Start service
    service = ProductionService()
    service.run()

    print("Check /var/log/myapp/application.log for output")

if __name__ == "__main__":
    main()
```

## Example 6: Testing and Development Setup

```python
#!/usr/bin/env python3
"""
Development and testing setup with verbose logging and comprehensive monitoring.
Ideal for debugging and development environments.
"""
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

def setup_development_logging():
    """Setup logging for development with maximum verbosity."""

    config = {
        "level": "DEBUG",  # Maximum verbosity for development
        "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        "enable_colors": True,  # Colors for better readability
        "output_file": "/tmp/development.log",
        "debug_file_logging": True  # File gets everything
    }

    LoggerFactory.initialize(config)

    # Development feature levels (very verbose)
    LoggerFactory.update_all_feature_levels({
        "docker_operations": "DEBUG",
        "config_processing": "DEBUG",
        "event_system": "DEBUG",
        "template_rendering": "DEBUG",
        "unknown": "DEBUG"  # Show everything in development
    })

    # Enable comprehensive statistics for analysis
    LoggerFactory.enable_statistics({
        "enabled": True,
        "buffer_size": 5000,  # Larger buffer for development
        "track_performance": True,
        "handler_type": "standard"  # Real-time for immediate feedback
    })

class DevelopmentComponent(FeatureLoggerMixin):
    def __init__(self):
        self.__init_logger__()
        self.trace("Component initialization started")  # TRACE level
        self.debug("Setting up development environment")
        self.info("Development component ready")

    def test_logging_levels(self):
        """Test all logging levels to verify configuration."""
        self.trace("This is TRACE level")
        self.debug("This is DEBUG level")
        self.info("This is INFO level")
        self.warning("This is WARNING level")
        self.error("This is ERROR level")
        self.critical("This is CRITICAL level")

    def performance_test(self):
        """Generate load for performance testing."""
        self.info("Starting performance test")

        for i in range(100):
            if i % 10 == 0:
                self.info(f"Processed {i} items")
            else:
                self.debug(f"Processing item {i}")

        # Check statistics
        stats = LoggerFactory.get_log_statistics()
        self.info(f"Generated {stats.get('total_messages', 0)} log messages")

def main():
    setup_development_logging()

    component = DevelopmentComponent()
    component.test_logging_levels()
    component.performance_test()

    # Final statistics report
    report = LoggerFactory.generate_statistics_report()
    print(f"\nDevelopment Session Report:")
    print(f"Total messages: {report.get('total_messages', 0)}")
    print(f"Collection period: {report.get('collection_period', 'Unknown')}")

if __name__ == "__main__":
    main()
```

These examples cover the most common usage patterns for PANTHER core utilities. Copy and modify them for your specific use cases. For more advanced scenarios, see the Advanced Configuration Examples.
