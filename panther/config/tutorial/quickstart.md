# PANTHER Configuration Quickstart Tutorial

## Introduction

This tutorial walks you through the essential concepts and practical usage of the PANTHER configuration system. You'll learn how to load, validate, and work with configurations for network testing scenarios.

## Prerequisites

- Python 3.8+
- Basic familiarity with YAML
- Understanding of network testing concepts

## Setup

First, ensure you have PANTHER installed:

```bash
pip install panther-config
```

## Lesson 1: Basic Configuration Loading

Let's start with a simple configuration file and learn how to load it.

### Create Your First Configuration

Create a file named `simple_experiment.yaml`:

```yaml
# simple_experiment.yaml
logging:
  level: INFO

paths:
  output_dir: "./outputs"

tests:
  - name: "Basic QUIC Test"
    network_environment:
      type: "docker_compose"
    services:
      - name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          name: "quic"
          role: "server"
        timeout: 60
```

### Load the Configuration

```python
from panther.config.core.manager import ConfigurationManager

# Initialize the configuration manager
config_manager = ConfigurationManager()

# Load and validate the configuration
config = config_manager.load_and_validate_config("simple_experiment.yaml")

# Access configuration data
print(f"Test name: {config.tests[0].name}")
print(f"Output directory: {config.global_config.paths.output_dir}")
print(f"Logging level: {config.global_config.logging.level}")
```

**What happened?**
1. The configuration manager loaded the YAML file
2. It validated the structure against the built-in schema
3. It created type-safe configuration objects you can access with dot notation

## Lesson 2: Understanding Auto-Fix

The configuration system can automatically fix common issues. Let's see this in action.

### Create a Configuration with Issues

Create `problematic_config.yaml`:

```yaml
# problematic_config.yaml - has missing required fields
tests:
  - name: "QUIC Server Test"
    services:
      - name: "quic_server"
        protocol:
          name: "quic"
          role: "server"
        # Missing: ports, implementation, timeout
```

### Load with Auto-Fix

```python
# Load configuration with auto-fix enabled
try:
    config = config_manager.load_and_validate_config(
        "problematic_config.yaml",
        auto_fix=True
    )

    # Check what was auto-fixed
    server = config.tests[0].services[0]
    print(f"Auto-assigned ports: {server.ports}")
    print(f"Default timeout: {server.timeout}")

except Exception as e:
    print(f"Configuration error: {e}")
```

**What happened?**
- The system detected missing ports for a QUIC server
- It automatically assigned the default QUIC port (4443:4443)
- It provided sensible defaults for other missing fields

## Lesson 3: Environment Variables

Configurations often need to adapt to different environments. Let's use environment variables.

### Create Environment-Aware Configuration

Create `env_config.yaml`:

```yaml
# env_config.yaml
logging:
  level: "${LOG_LEVEL:INFO}"

database:
  host: "${DB_HOST:localhost}"
  port: "${DB_PORT:5432}"
  password: "${DB_PASSWORD}"

tests:
  - name: "Environment Test"
    services:
      - name: "test_service"
        implementation:
          name: "${SERVICE_IMPL:picoquic}"
          type: "iut"
        timeout: "${SERVICE_TIMEOUT:60}"
```

### Load with Environment Variables

```python
import os

# Set environment variables
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DB_HOST"] = "production-db"
os.environ["SERVICE_TIMEOUT"] = "120"
# Note: DB_PASSWORD is required and must be set

# Load with environment resolution
config = config_manager.load_with_environment(
    "env_config.yaml",
    env_vars={
        "DB_PASSWORD": "secret-password",
        "SERVICE_IMPL": "quiche"
    }
)

print(f"Logging level: {config.global_config.logging.level}")  # DEBUG
print(f"Database host: {config.global_config.database.host}")  # production-db
print(f"Service timeout: {config.tests[0].services[0].timeout}")  # 120
```

**Environment Variable Syntax:**
- `${VARIABLE}`: Required variable, fails if not set
- `${VARIABLE:default}`: Optional variable with default value

## Lesson 4: Validation and Error Handling

Understanding validation helps you write better configurations.

### Detailed Validation

```python
from panther.config.core.components.validators import UnifiedValidator

# Create a validator for detailed analysis
validator = UnifiedValidator()

# Load a configuration (may have issues)
config_dict = config_manager.load_from_file("simple_experiment.yaml")

# Validate step by step
schema_result = validator.validate_schema_only(config_dict)
business_result = validator.validate_business_rules_only(config_dict)

print("Schema validation:", "✓" if schema_result.is_valid else "✗")
print("Business rules:", "✓" if business_result.is_valid else "✗")

# Get detailed validation report
full_result = validator.validate_experiment_config(config_dict)
if not full_result.is_valid:
    print("\nValidation issues:")
    for error in full_result.errors:
        print(f"  Error: {error}")
    for warning in full_result.warnings:
        print(f"  Warning: {warning}")
```

## Lesson 5: Working with Plugins

PANTHER uses plugins for different implementations. Let's explore plugin capabilities.

### Discover Available Plugins

```python
# Discover all available plugins
plugins = config_manager.discover_plugins()

print("Available plugins:")
for plugin in plugins:
    print(f"  {plugin.name} ({plugin.plugin_type}) - {plugin.protocol}")

# Discover specific plugin types
iut_plugins = config_manager.discover_plugins(plugin_type="iut")
print(f"\nIUT implementations: {[p.name for p in iut_plugins]}")
```

### Plugin-Specific Configuration

```python
# Get configuration schema for a specific plugin
try:
    quiche_schema = config_manager.load_plugin_schema("quiche")
    print("Quiche configuration options:")
    for field, details in quiche_schema.items():
        print(f"  {field}: {details.get('type', 'unknown')}")

except Exception as e:
    print(f"Plugin not available: {e}")
```

## Lesson 6: Performance Optimization

For larger configurations or repeated operations, use caching.

### Enable Caching

```python
# Enable caching with 10-minute TTL
config_manager.enable_cache(ttl=600, max_size=50)

# Load configurations (first time - cache miss)
config1 = config_manager.load_from_file("simple_experiment.yaml")
config2 = config_manager.load_from_file("simple_experiment.yaml")  # cache hit

# Check cache performance
stats = config_manager.get_cache_stats()
print(f"Cache hit rate: {stats.hit_rate}%")
print(f"Cache entries: {stats.entry_count}")
```

### Pre-warm Cache

```python
# Pre-load frequently used configurations
config_manager.warm_cache([
    "experiment1.yaml",
    "experiment2.yaml",
    "base_config.yaml"
])

print("Cache warmed with common configurations")
```

## Lesson 7: Configuration Merging

Combine multiple configurations for complex scenarios.

### Create Base and Override Configurations

Base configuration (`base.yaml`):
```yaml
# base.yaml
logging:
  level: INFO

paths:
  output_dir: "./outputs"

tests:
  - name: "Base Test"
    services:
      - name: "base_service"
        timeout: 60
```

Override configuration (`override.yaml`):
```yaml
# override.yaml
logging:
  level: DEBUG

tests:
  - name: "Base Test"
    services:
      - name: "base_service"
        timeout: 120
        debug: true
```

### Merge Configurations

```python
# Load both configurations
base_config = config_manager.load_from_file("base.yaml")
override_config = config_manager.load_from_file("override.yaml")

# Merge with different strategies
merged = config_manager.merge_configs(
    base_config,
    override_config,
    strategy="deep_merge"
)

print(f"Merged logging level: {merged['logging']['level']}")  # DEBUG
print(f"Merged timeout: {merged['tests'][0]['services'][0]['timeout']}")  # 120
```

## Lesson 8: Custom Configuration Classes

Extend the configuration system for your specific needs.

### Create Custom Configuration

```python
from panther.config.core.base import BaseConfig
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DatabaseConfig(BaseConfig):
    host: str
    port: int = 5432
    database: str = "panther"
    ssl_enabled: bool = False

@dataclass
class MyAppConfig(BaseConfig):
    app_name: str
    version: str
    database: DatabaseConfig
    feature_flags: List[str] = None
    debug_mode: bool = False

# Create and use custom configuration
db_config = DatabaseConfig(host="localhost", ssl_enabled=True)
app_config = MyAppConfig(
    app_name="PANTHER Test",
    version="1.0.0",
    database=db_config,
    feature_flags=["new_ui", "advanced_metrics"]
)

# Convert to various formats
config_dict = app_config.to_dict()
omega_config = app_config.to_omega()
yaml_string = app_config.to_yaml()

print(f"App: {app_config.app_name}")
print(f"Database host: {app_config.database.host}")
```

## Common Patterns and Best Practices

### Pattern 1: Configuration Validation in Tests

```python
import pytest

def test_configuration_validity():
    """Ensure all test configurations are valid."""
    config_files = [
        "experiment1.yaml",
        "experiment2.yaml",
        "production.yaml"
    ]

    manager = ConfigurationManager()

    for config_file in config_files:
        config = manager.load_and_validate_config(config_file)
        assert config is not None
        assert len(config.tests) > 0
```

### Pattern 2: Environment-Specific Loading

```python
def load_config_for_environment(env: str):
    """Load configuration appropriate for the environment."""
    base_config = f"configs/base.yaml"
    env_config = f"configs/{env}.yaml"

    manager = ConfigurationManager()

    # Load base configuration
    base = manager.load_from_file(base_config)

    # Load environment-specific overrides
    try:
        env_overrides = manager.load_from_file(env_config)
        return manager.merge_configs(base, env_overrides)
    except FileNotFoundError:
        print(f"No environment config for {env}, using base")
        return base

# Usage
prod_config = load_config_for_environment("production")
test_config = load_config_for_environment("testing")
```

### Pattern 3: Configuration with Fallbacks

```python
def robust_config_loading(primary_path: str, fallback_path: str):
    """Load configuration with fallback support."""
    manager = ConfigurationManager()

    try:
        return manager.load_and_validate_config(primary_path, auto_fix=True)
    except Exception as e:
        print(f"Primary config failed: {e}")
        print(f"Falling back to: {fallback_path}")
        return manager.load_and_validate_config(fallback_path, auto_fix=True)

# Usage
config = robust_config_loading("experiment.yaml", "default_experiment.yaml")
```

## Next Steps

Now that you understand the basics, you can:

1. **Explore Advanced Features**: Look into plugin development and custom validators
2. **Read the Developer Guide**: Learn about contributing to the configuration system
3. **Check the API Reference**: Dive deep into all available methods and classes
4. **Study Real Examples**: Examine the `experiment-config/` directory for complex scenarios

## Troubleshooting

### Common Issues

**Configuration not loading:**
- Check file path and permissions
- Verify YAML syntax with an online validator
- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

**Validation errors:**
- Use `auto_fix=True` to see suggested corrections
- Check plugin availability with `discover_plugins()`
- Verify all required fields are present

**Environment variable issues:**
- Ensure required variables are set
- Use `${VAR:default}` syntax for optional variables
- Check variable names for typos

**Performance problems:**
- Enable caching for repeated operations
- Use `warm_cache()` for frequently accessed configurations
- Monitor cache statistics with `get_cache_stats()`

## Summary

You've learned how to:
- Load and validate configurations
- Use auto-fix for common issues
- Work with environment variables
- Handle validation errors
- Discover and use plugins
- Optimize performance with caching
- Merge multiple configurations
- Create custom configuration classes

The PANTHER configuration system provides a powerful, flexible foundation for managing complex network testing scenarios while maintaining type safety and developer productivity.
