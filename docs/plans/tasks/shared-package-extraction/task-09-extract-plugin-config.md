# Task 09: Extract Plugin Config Hierarchy to panther-types

## Goal
Extract `BasePluginConfig` and `ServicePluginConfig` (and siblings) from `plugin.py` into `panther_types/config/plugin.py`.

## Prerequisites
- Task 07 completed (BaseConfig + BaseUnifiedModel in panther-types)
- Task 08 completed (enums available in panther-types)

## Source File
`panther/config/core/models/plugin.py` (177 lines)

Extract:
- `BasePluginConfig` (lines 12-72) - base for all plugins
- `ExecutionEnvironmentPluginConfig` (lines 75-104) - execution env plugins
- `NetworkEnvironmentPluginConfig` (lines 107-118) - network env plugins
- `ServicePluginConfig` (lines 120-163) - service plugins (IUT/testers)
- `ProtocolPluginConfig` (lines 166-177) - protocol plugins

## Context
`panther_ivy/config_schema.py` inherits from `ServicePluginConfig` (line 8: `from panther.config.core.models.plugin import ServicePluginConfig`). This is the primary cross-project consumer.

### Dependency Analysis
All 5 classes extend `BaseUnifiedModel` (now in panther-types via task 07). The only cross-reference is:
- `ServicePluginConfig.validate_type()` field_validator - self-contained, no external imports
- `ServicePluginConfig.create_with_protocol_context()` - classmethod, self-contained

No imports from validators module or other panther internals. Clean extraction.

## Steps

### Step 1: Create panther_types/config/plugin.py

Read the full source of `panther/config/core/models/plugin.py` and copy the class hierarchy, updating the import of BaseUnifiedModel to come from panther_types:

```python
# packages/panther-types/panther_types/config/plugin.py
"""Plugin configuration base classes.

These models define the configuration schema for different plugin types
in the PANTHER framework: services, environments, protocols.
"""
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import Field, field_validator

from panther_types.config.base import BaseUnifiedModel

T = TypeVar("T", bound="BasePluginConfig")


class BasePluginConfig(BaseUnifiedModel):
    # ... copy full class from source ...
    pass


class ExecutionEnvironmentPluginConfig(BasePluginConfig):
    # ... copy full class from source ...
    pass


class NetworkEnvironmentPluginConfig(BasePluginConfig):
    # ... copy full class from source ...
    pass


class ServicePluginConfig(BasePluginConfig):
    # ... copy full class from source ...
    pass


class ProtocolPluginConfig(BasePluginConfig):
    # ... copy full class from source ...
    pass
```

**Critical**: Read the ACTUAL source file. Copy each class exactly, only changing the import line for BaseUnifiedModel.

### Step 2: Update __init__.py

```python
# packages/panther-types/panther_types/config/__init__.py
"""Configuration base classes and models."""
from panther_types.config.base import BaseConfig, BaseUnifiedModel
from panther_types.config.plugin import (
    BasePluginConfig,
    ExecutionEnvironmentPluginConfig,
    NetworkEnvironmentPluginConfig,
    ProtocolPluginConfig,
    ServicePluginConfig,
)
from panther_types.config.service import (
    ImplementationType,
    Parameter,
    ProtocolRole,
    VersionBase,
)

__all__ = [
    "BaseConfig",
    "BaseUnifiedModel",
    "BasePluginConfig",
    "ExecutionEnvironmentPluginConfig",
    "NetworkEnvironmentPluginConfig",
    "ProtocolPluginConfig",
    "ServicePluginConfig",
    "ImplementationType",
    "Parameter",
    "ProtocolRole",
    "VersionBase",
]
```

### Step 3: Write tests

```python
# packages/panther-types/tests/test_config_plugin.py
"""Tests for plugin config classes."""
from panther_types.config.plugin import (
    BasePluginConfig,
    ExecutionEnvironmentPluginConfig,
    NetworkEnvironmentPluginConfig,
    ProtocolPluginConfig,
    ServicePluginConfig,
)


class TestBasePluginConfig:
    def test_defaults(self):
        c = BasePluginConfig()
        assert c.enabled is True
        assert c.version == ""
        assert c.priority == 0

    def test_get_plugin_type(self):
        c = BasePluginConfig()
        assert c.get_plugin_type() == "base"

    def test_validate_plugin_specific(self):
        c = BasePluginConfig()
        # Should not raise
        c.validate_plugin_specific()


class TestServicePluginConfig:
    def test_defaults(self):
        c = ServicePluginConfig()
        assert c.docker_image == ""
        assert c.build_from_source is False

    def test_get_plugin_type(self):
        c = ServicePluginConfig()
        assert c.get_plugin_type() == "service"

    def test_inheritance(self):
        c = ServicePluginConfig()
        assert isinstance(c, BasePluginConfig)

    def test_create_with_protocol_context(self):
        c = ServicePluginConfig.create_with_protocol_context(
            protocol_name="quic",
            protocol_version="rfc9000",
            role="server"
        )
        assert isinstance(c, ServicePluginConfig)


class TestExecutionEnvironmentPluginConfig:
    def test_defaults(self):
        c = ExecutionEnvironmentPluginConfig()
        assert c.get_plugin_type() == "execution_environment"


class TestNetworkEnvironmentPluginConfig:
    def test_defaults(self):
        c = NetworkEnvironmentPluginConfig()
        assert c.get_plugin_type() == "network_environment"


class TestProtocolPluginConfig:
    def test_defaults(self):
        c = ProtocolPluginConfig()
        assert c.get_plugin_type() == "protocol"
        assert c.supports_tls is False
```

## Verification
```bash
cd packages/panther-types
pytest tests/test_config_plugin.py -v
```

## Important Notes
- The `ServicePluginConfig.validate_type` field_validator handles case-insensitive enum conversion. Verify this works without importing from panther validators.
- `ServicePluginConfig.create_with_protocol_context()` may reference field names that need to match the actual source.
- Some field defaults may use `Field(default=...)` with validators. Preserve these exactly.

## Commit Message
```
feat(panther-types): extract plugin config hierarchy

Move BasePluginConfig, ServicePluginConfig, and sibling configs from
panther/config/core/models/plugin.py into panther-types. This enables
panther_ivy to depend on panther-types instead of the full panther package.
```

## Files Modified
- `packages/panther-types/panther_types/config/plugin.py` (new)
- `packages/panther-types/panther_types/config/__init__.py` (updated)
- `packages/panther-types/tests/test_config_plugin.py` (new)
