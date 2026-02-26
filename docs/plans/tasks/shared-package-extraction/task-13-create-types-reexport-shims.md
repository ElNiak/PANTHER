# Task 13: Create Re-export Shims for panther-types

## Goal
Replace original type definitions in panther with re-export shims that import from `panther_types`. Update `panther_ivy/config_schema.py` to import from `panther_types`.

## Prerequisites
- Tasks 07-12 completed (all types extracted to panther-types)

## Context
This task creates backward-compatible shims so all existing `from panther.config.core.xxx import Yyy` import paths continue to work while the canonical definitions now live in `panther_types`.

## Files to Update

### 1. Config base shims

**`panther/config/core/base.py`** - Replace class definition with re-export:
```python
# panther/config/core/base.py
"""Configuration base class.

Re-exported from panther_types for backward compatibility.
Canonical source: panther_types.config.base
"""
from panther_types.config.base import BaseConfig  # noqa: F401

__all__ = ["BaseConfig"]
```

**`panther/config/core/models/base_model.py`** - Replace with re-export:
```python
# panther/config/core/models/base_model.py
"""Unified model base class.

Re-exported from panther_types for backward compatibility.
Canonical source: panther_types.config.base
"""
from panther_types.config.base import BaseUnifiedModel  # noqa: F401

__all__ = ["BaseUnifiedModel"]
```

### 2. Plugin config shims

**`panther/config/core/models/plugin.py`** - Replace class definitions with re-exports:
```python
# panther/config/core/models/plugin.py
"""Plugin configuration models.

Re-exported from panther_types for backward compatibility.
Canonical source: panther_types.config.plugin
"""
from panther_types.config.plugin import (  # noqa: F401
    BasePluginConfig,
    ExecutionEnvironmentPluginConfig,
    NetworkEnvironmentPluginConfig,
    ProtocolPluginConfig,
    ServicePluginConfig,
)

__all__ = [
    "BasePluginConfig",
    "ExecutionEnvironmentPluginConfig",
    "NetworkEnvironmentPluginConfig",
    "ProtocolPluginConfig",
    "ServicePluginConfig",
]
```

### 3. Service enums/models shim

**`panther/config/core/models/service.py`** - This file is complex (550 lines). Only the extracted types become re-exports. The rest stays as-is.

At the top of `service.py`, replace the local enum/class definitions with imports from panther_types:

```python
# Replace lines 16-43 (Parameter, VersionBase, ImplementationType, ProtocolRole definitions)
# with:
from panther_types.config.service import (  # noqa: F401
    ImplementationType,
    Parameter,
    ProtocolRole,
    VersionBase,
)
```

Keep everything else (NetworkConfig, ProtocolConfig, ImplementationConfig, ServiceConfig) unchanged.

### 4. Event type shims

**`panther/core/events/base/event_base.py`** - Replace with re-exports:
```python
# panther/core/events/base/event_base.py
"""Event system base types.

Re-exported from panther_types for backward compatibility.
Canonical source: panther_types.events.base
"""
from panther_types.events.base import (  # noqa: F401
    BaseEvent,
    EventType,
    create_content_based_uuid,
    create_event_signature,
)

__all__ = ["BaseEvent", "EventType", "create_content_based_uuid", "create_event_signature"]
```

**`panther/core/events/base/state_base.py`** - Replace with re-exports:
```python
from panther_types.events.state import (  # noqa: F401
    BaseState,
    StateManager,
    StateTransition,
)

__all__ = ["BaseState", "StateManager", "StateTransition"]
```

### 5. Exception shims

**`panther/core/exceptions/fast_fail.py`** - Replace exception class definitions (lines 14-271) with re-exports from panther_types. Keep `FastFailHandler` (lines 274-535) as-is, updating its imports to use panther_types:

```python
# At top of fast_fail.py, replace exception definitions with:
from panther_types.exceptions.base import (  # noqa: F401
    AuthenticationException,
    CertificateException,
    ConfigurationException,
    CriticalAssertionException,
    DependencyException,
    DockerBuildException,
    DockerComposeException,
    ErrorCascadeException,
    ErrorCategory,
    ErrorSeverity,
    IvyCompilationException,
    NetworkSetupException,
    PantherException,
    PluginLoadException,
    PortConflictException,
    ResourceExhaustionException,
    ServiceStartException,
    TimeoutCascadeException,
)

# FastFailHandler class stays here (lines 274-535)
class FastFailHandler:
    # ... (unchanged) ...
```

**`panther/core/exceptions/experiment_exceptions.py`** - Replace with re-exports:
```python
from panther_types.exceptions.experiment import (  # noqa: F401
    ConfigurationError,
    ExperimentInitializationError,
    PantherExperimentError,
    PluginValidationError,
    TestCaseInitializationError,
    TestExecutionError,
)
```

**`panther/core/exceptions/network_resolution_exceptions.py`** - Replace with re-exports.

**`panther/core/exceptions/__init__.py`** - The existing __init__.py already re-exports from submodules. It should continue to work since the submodules now re-export from panther_types.

### 6. Plugin structure shims

**`panther/plugins/core/structures/plugin_type.py`** - Replace with re-export:
```python
from panther_types.plugin.types import PluginType  # noqa: F401
```

**`panther/plugins/core/structures/plugin_metadata.py`** - Replace PluginStatus and PluginMetadata class definitions with re-exports. Keep PluginMetadataLoader as-is:
```python
from panther_types.plugin.metadata import PluginMetadata, PluginStatus  # noqa: F401

# PluginMetadataLoader stays here
class PluginMetadataLoader:
    # ... (unchanged) ...
```

### 7. Update panther_ivy consumer

**`panther/plugins/services/testers/panther_ivy/config_schema.py`** (lines 7-8):

```python
# BEFORE:
from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import ImplementationType, VersionBase

# AFTER (preferred - direct from panther_types):
from panther_types.config.plugin import ServicePluginConfig
from panther_types.config.service import ImplementationType, VersionBase
```

Note: The old import paths still work via the shims, but direct panther_types imports are preferred for new/updated code.

### 8. Update validators lazy imports

**`panther/config/core/validators/universal_validators.py`** - Update the lazy imports in `protocol_role_validator()` and `implementation_type_validator()`:

```python
# BEFORE (lines 208-219):
def protocol_role_validator():
    from panther.config.core.models.service import ProtocolRole
    return create_enum_validator(ProtocolRole)

def implementation_type_validator():
    from panther.config.core.models.service import ImplementationType
    return create_enum_validator(ImplementationType)

# AFTER:
def protocol_role_validator():
    from panther_types.config.service import ProtocolRole
    return create_enum_validator(ProtocolRole)

def implementation_type_validator():
    from panther_types.config.service import ImplementationType
    return create_enum_validator(ImplementationType)
```

## Verification

```bash
# 1. Verify backward-compatible imports still work
python -c "
from panther.config.core.base import BaseConfig
from panther.config.core.models.base_model import BaseUnifiedModel
from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import ImplementationType, ProtocolRole
print('Backward-compatible imports: OK')
"

# 2. Verify type identity
python -c "
from panther.config.core.models.plugin import ServicePluginConfig as S1
from panther_types.config.plugin import ServicePluginConfig as S2
assert S1 is S2, 'Type identity mismatch!'
print('Type identity: OK')
"

# 3. Verify panther_ivy imports work
python -c "
from panther_ivy.config_schema import PantherIvyConfig
print('PantherIvyConfig loaded: OK')
"

# 4. Verify events
python -c "
from panther.core.events.base.event_base import BaseEvent, EventType
print('Event imports: OK')
"

# 5. Verify exceptions
python -c "
from panther.core.exceptions import PantherException, ErrorSeverity
from panther.core.exceptions.fast_fail import FastFailHandler
print('Exception imports: OK, FastFailHandler present')
"
```

## Important Notes
- This is the highest-risk task in Phase 2. Each file modification must preserve ALL existing import paths.
- The `service.py` file is only PARTIALLY converted - enums/simple models become imports, but NetworkConfig/ProtocolConfig/ServiceConfig stay as local definitions.
- `fast_fail.py` is partially converted - exception classes become imports, FastFailHandler stays.
- Test after each file modification, not just at the end.
- If any shim breaks, the fix is to restore the original definition alongside the import.

## Commit Message
```
refactor: replace type definitions with panther-types re-exports

Update panther config, events, exceptions, and plugin structure files
to re-export from panther-types. All existing import paths remain
backward compatible. Update panther_ivy to import directly from
panther-types.
```

## Files Modified
- `panther/config/core/base.py` (rewritten as shim)
- `panther/config/core/models/base_model.py` (rewritten as shim)
- `panther/config/core/models/plugin.py` (rewritten as shim)
- `panther/config/core/models/service.py` (partial - top enums/models replaced with imports)
- `panther/core/events/base/event_base.py` (rewritten as shim)
- `panther/core/events/base/state_base.py` (rewritten as shim)
- `panther/core/exceptions/fast_fail.py` (partial - exception classes replaced, FastFailHandler stays)
- `panther/core/exceptions/experiment_exceptions.py` (rewritten as shim)
- `panther/core/exceptions/network_resolution_exceptions.py` (rewritten as shim)
- `panther/plugins/core/structures/plugin_type.py` (rewritten as shim)
- `panther/plugins/core/structures/plugin_metadata.py` (partial - PluginMetadataLoader stays)
- `panther/plugins/services/testers/panther_ivy/config_schema.py` (updated imports)
- `panther/config/core/validators/universal_validators.py` (updated lazy imports)
