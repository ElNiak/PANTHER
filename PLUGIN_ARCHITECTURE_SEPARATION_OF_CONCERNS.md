# Plugin Architecture - Separation of Concerns

This document describes the refactored plugin architecture that enables true separation of concerns, allowing plugin developers to add new plugins without modifying core PANTHER code.

## Problem Statement

Previously, PANTHER had:
1. **Duplicate config classes** - Plugin configs existed in both core models and plugin directories
2. **Core knowledge of plugins** - Core models explicitly imported and defined plugin-specific configs
3. **Hardcoded validation** - Validation system had hardcoded mappings for each plugin type
4. **Mixed patterns** - Some configs used dataclass, others used Pydantic

## Solution: Dynamic Plugin Config Resolution

### 1. Plugin Config Resolver

Created `panther/plugins/plugin_config_resolver.py` that provides:
- Dynamic discovery of plugin configuration classes
- Resolution based on plugin type and location
- Caching for performance
- Fallback to base classes for unknown plugins

```python
# Example usage
resolver = PluginConfigResolver()

# Resolve a config class
config_class = resolver.resolve_environment_config_class('strace', 'execution_environment')

# Create a config instance dynamically
config = resolver.create_environment_config_dynamic(
    {'type': 'strace', 'output_format': 'verbose'}, 
    'execution_environment'
)
```

### 2. Two-Layer Architecture

**Plugin Layer** (for plugin definitions):
- `BasePluginConfig` → `NetworkEnvironmentPluginConfig` / `ExecutionEnvironmentPluginConfig`
- Used by plugins to define their configuration schema
- Located in plugin directories

**Runtime Layer** (for runtime configuration):
- `BaseUnifiedModel` → `EnvironmentConfig` → `NetworkEnvironmentConfig` / `ExecutionEnvironmentConfig`
- Used by core for configuration management
- Located in core models

### 3. Core Model Cleanup

From `/panther/config/core/models/environment.py`, removed all plugin-specific configs:
- ~~DockerComposeConfig~~
- ~~LocalhostSingleContainerConfig~~
- ~~ShadowNsConfig~~
- ~~StraceConfig~~
- ~~GperfCpuConfig~~, ~~GperfHeapConfig~~
- ~~MemcheckConfig~~, ~~HelgrindConfig~~
- ~~IterationsConfig~~

Only base classes remain:
- `EnvironmentConfig`
- `NetworkEnvironmentConfig`
- `ExecutionEnvironmentConfig`

### 4. Updated Validation System

Modified `validation_ops.py` to use dynamic resolution:
```python
def validate_environment_config(self, env: Dict[str, Any]) -> 'EnvironmentConfig':
    # No hardcoded plugin lists!
    # Try to discover the category by attempting to resolve in both categories
    for category in ['network_environment', 'execution_environment']:
        config_class = config_resolver.resolve_environment_config_class(env_type, category)
        if config_class:
            return config_resolver.create_environment_config_dynamic(env, category)
```

### 5. Plugin Config Standards

All plugin configs now:
- Use Pydantic (not dataclass)
- Inherit from `*PluginConfig` base classes
- Are located in their plugin directory
- Follow naming convention: `{PluginName}Config`

## Benefits

1. **True Plugin Architecture**: Core has no knowledge of specific plugins
2. **Dynamic Extensibility**: New plugins can be added without modifying core
3. **Single Source of Truth**: Each plugin owns its configuration
4. **Better Maintainability**: Clear separation between plugin and runtime layers
5. **Consistent Patterns**: All plugins follow the same configuration pattern

## Adding a New Plugin

To add a new execution environment plugin:

1. Create plugin directory: `panther/plugins/environments/execution_environment/my_plugin/`

2. Create `config_schema.py`:
```python
from pydantic import Field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig

class MyPluginConfig(ExecutionEnvironmentPluginConfig):
    type: str = Field(default="my_plugin", description="Plugin type")
    my_option: str = Field(default="value", description="Plugin-specific option")
```

3. Create plugin implementation inheriting from base environment class

4. That's it! The plugin will be automatically discovered and validated.

## Migration Notes

- Removed duplicate `NetworkEnvironmentConfig` from plugin directory
- All plugin configs standardized to use Pydantic
- Core imports cleaned to only export base classes
- Validation system now uses dynamic discovery
- All execution environment configs migrated:
  - `gperf_cpu` - ✅ Migrated to Pydantic
  - `gperf_heap` - ✅ Migrated to Pydantic
  - `memcheck` - ✅ Migrated to Pydantic
  - `iterations` - ✅ Migrated to Pydantic
  - `strace` - ✅ Already using Pydantic
  - `helgrind` - ✅ Already using Pydantic

The architecture now properly separates concerns:
- **Core**: Provides base classes and interfaces
- **Plugins**: Implement specific functionality without modifying core
- **Resolution**: Dynamic discovery connects them at runtime