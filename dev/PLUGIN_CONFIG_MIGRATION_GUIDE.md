# Plugin Configuration Migration Guide

This guide helps with the transition from hardcoded plugin configurations to dynamic plugin discovery in PANTHER.

## Overview

We're transitioning from a system where plugin configurations were hardcoded in `panther/config/core/models/environment.py` to a dynamic discovery system where each plugin defines its own configuration in its plugin directory.

## Changes Made

### 1. Core Models Cleaned Up

The following configs have been removed from `panther/config/core/models/environment.py`:

**Execution Environment Configs:**
- `StraceConfig`
- `GperfCpuConfig`
- `GperfHeapConfig`
- `MemcheckConfig`
- `HelgrindConfig`
- `IterationsConfig`

**Network Environment Configs:**
- `DockerComposeConfig`
- `LocalhostSingleContainerConfig`
- `ShadowNsConfig`

Only base classes remain:
- `EnvironmentConfig`
- `ExecutionEnvironmentConfig`
- `NetworkEnvironmentConfig`

### 2. Dynamic Config Resolution

A new `PluginConfigResolver` class provides dynamic config resolution:

```python
# In panther/plugins/plugin_config_resolver.py
config_resolver = PluginConfigResolver()

# Resolve config class dynamically
config_class = config_resolver.resolve_environment_config_class(
    env_type="strace",
    plugin_discovery=plugin_discovery
)

# Create config instance
config = config_resolver.create_environment_config_dynamic(
    {"type": "strace"},
    plugin_discovery=plugin_discovery
)
```

### 3. Updated Validation

The `ValidationOperationsMixin.validate_environment_config()` method now uses dynamic resolution instead of hardcoded mappings.

## Migration Steps for Plugin Developers

### 1. Update Plugin Config Classes

Plugin configs should:

1. Be located in `{plugin_dir}/config_schema.py`
2. Inherit from the appropriate base class:
   - `ExecutionEnvironmentPluginConfig` for execution environments
   - `NetworkEnvironmentPluginConfig` for network environments
3. Use Pydantic models (not dataclasses)

**Example Migration:**

```python
# OLD (in core models)
from dataclasses import dataclass
from panther.config.core.models import ExecutionEnvironmentConfig

@dataclass
class StraceConfig(ExecutionEnvironmentConfig):
    type: str = "strace"
    trace_calls: List[str] = field(default_factory=lambda: ["all"])
```

```python
# NEW (in plugin directory)
from pydantic import Field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig

class StraceConfig(ExecutionEnvironmentPluginConfig):
    type: str = Field("strace", description="Environment type")
    trace_calls: List[str] = Field(
        default_factory=lambda: ["all"],
        description="System calls to trace"
    )
```

### 2. Update Imports

Replace imports from core models:

```python
# OLD
from panther.config.core.models import StraceConfig

# NEW
from panther.plugins.environments.execution_environment.strace.config_schema import StraceConfig
```

### 3. Config Class Naming Convention

Follow the naming convention:
- Class name: `{PluginName}Config`
- File location: `{plugin_dir}/config_schema.py`

Special cases:
- `shadow_ns` → `ShadowNSConfig` (maintains NS capitalization)

## Backward Compatibility

During the transition:

1. The system will attempt dynamic resolution first
2. If that fails, it falls back to base config classes
3. A compatibility module is available for special cases

## Benefits

1. **True Plugin Architecture**: Core has no knowledge of specific plugins
2. **Easier Plugin Development**: Add new plugins without modifying core
3. **Better Separation of Concerns**: Each plugin manages its own config
4. **Type Safety**: Proper inheritance ensures type compatibility

## Testing

Use the provided test script to verify your plugin's config resolution:

```bash
python dev/scripts/test_dynamic_config_resolution.py
```

## Common Issues

1. **Import Errors**: Ensure plugin directory structure follows conventions
2. **Class Not Found**: Check class naming matches convention
3. **Inheritance Issues**: Use proper base classes from `panther.config.core.models.plugin`
4. **Dataclass Compatibility**: Migrate to Pydantic models

## Future Work

1. Complete migration of all plugin configs to Pydantic
2. Add plugin manifest support for config schema declaration
3. Implement config version migration support
4. Add JSON Schema export for config validation