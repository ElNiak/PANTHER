# ADR-0001: Feature-Aware Logging Architecture

## Status

Accepted

## Context

PANTHER framework consists of multiple subsystems (Docker operations, event processing, config management, etc.) that require different levels of logging verbosity. Traditional logging approaches either apply global levels uniformly or require manual configuration for each component.

The framework needs:
- Automatic categorization of components into logical features
- Independent log level control per feature
- Runtime reconfiguration capability
- Minimal configuration overhead for developers

## Decision

We implement a feature-aware logging architecture centered around automatic component categorization and centralized level management.

### Core Components

1. **LoggerFactory (Singleton Pattern)**
   - Centralizes all logger creation and configuration
   - Maintains feature-to-level mappings
   - Provides consistent formatting and handler management

2. **Feature Detection System**
   - Automatic pattern matching on class/module names
   - Dynamic feature registry for runtime updates
   - Fallback to explicit feature assignment

3. **FeatureLoggerMixin**
   - Provides feature-aware logging to any class
   - Lazy initialization for performance
   - Automatic feature detection with override capability

### Feature Categories

Features align with PANTHER's architectural boundaries:
- `docker_operations`: Container management, build processes
- `event_system`: Event emission, processing, state management
- `config_processing`: Configuration loading, validation
- `template_rendering`: Template processing and rendering
- `network_environments`: Network setup and management

## Consequences

### Positive

- **Targeted Debugging**: Enable DEBUG for specific features without noise
- **Production Safety**: Keep most features at WARNING/ERROR while debugging specific issues
- **Zero Configuration**: Components automatically get appropriate logging behavior
- **Runtime Flexibility**: Change levels without restart

### Negative

- **Magic Behavior**: Feature detection may be non-obvious to developers
- **Complexity**: Additional abstraction layer over standard logging
- **Memory Overhead**: Feature mappings and logger caching

### Mitigation Strategies

- Provide explicit feature assignment methods
- Comprehensive documentation of detection patterns
- Debug methods to inspect effective feature assignments
- Performance monitoring to track overhead

## Implementation Details

### Feature Detection Algorithm

1. Check dynamic feature registry first
2. Apply static pattern matching against FEATURE_MAPPINGS
3. Fallback to "unknown" feature with global level

### Pattern Examples

```python
FEATURE_MAPPINGS = {
    "docker_operations": ["docker", "container", "build"],
    "event_system": ["event", "emitter", "state"],
    "config_processing": ["config", "configuration"]
}
```

### Logger Creation Flow

```python
# Automatic detection
logger = LoggerFactory.get_logger("docker_builder")  # -> docker_operations

# Explicit assignment
logger = LoggerFactory.get_feature_logger("custom", "event_system")
```

### Level Management

```python
# Individual feature
LoggerFactory.update_feature_level("docker_operations", "DEBUG")

# Bulk update
LoggerFactory.update_all_feature_levels({
    "docker_operations": "DEBUG",
    "event_system": "INFO"
})
```

## Related Decisions

- ADR-0002: Statistics collection architecture
- ADR-0003: Performance optimization strategies

## References

- Gang of Four Singleton Pattern
- Python logging module documentation
- PANTHER framework architecture documentation
