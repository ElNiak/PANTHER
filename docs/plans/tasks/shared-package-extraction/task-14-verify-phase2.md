# Task 14: Verify Phase 2 - panther-types

## Goal
Install panther-types and verify all imports, re-exports, backward compatibility, and existing tests pass.

## Prerequisites
- Tasks 06-13 completed

## Steps

### Step 1: Install panther-types
```bash
source .venv/bin/activate
pip install -e packages/panther-types/
```

### Step 2: Run panther-types tests
```bash
cd packages/panther-types
pytest tests/ -v
```

All tests from tasks 07-12 should pass.

### Step 3: Verify backward-compatible imports

```bash
python -c "
# Config base classes
from panther.config.core.base import BaseConfig
from panther.config.core.models.base_model import BaseUnifiedModel
print('Config base: OK')

# Plugin configs
from panther.config.core.models.plugin import (
    BasePluginConfig, ServicePluginConfig,
    ExecutionEnvironmentPluginConfig, NetworkEnvironmentPluginConfig,
    ProtocolPluginConfig
)
print('Plugin configs: OK')

# Service enums and models
from panther.config.core.models.service import (
    ImplementationType, ProtocolRole, VersionBase, Parameter
)
print('Service enums: OK')

# Events
from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.events.base.state_base import BaseState, StateManager, StateTransition
print('Events: OK')

# Exceptions
from panther.core.exceptions import (
    PantherException, ErrorSeverity, ErrorCategory,
    DockerBuildException, ConfigurationException,
    EnvironmentPluginNotFound, ServicePluginNotFound
)
from panther.core.exceptions.fast_fail import FastFailHandler
from panther.core.exceptions.experiment_exceptions import PantherExperimentError
print('Exceptions: OK')

# Plugin structures
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.core.structures.plugin_metadata import PluginMetadata
print('Plugin structures: OK')

print('All backward-compatible imports: PASS')
"
```

### Step 4: Verify type identity across import paths

```bash
python -c "
from panther.config.core.base import BaseConfig as B1
from panther_types.config.base import BaseConfig as B2
assert B1 is B2, f'BaseConfig identity mismatch'

from panther.config.core.models.plugin import ServicePluginConfig as S1
from panther_types.config.plugin import ServicePluginConfig as S2
assert S1 is S2, f'ServicePluginConfig identity mismatch'

from panther.config.core.models.service import ImplementationType as I1
from panther_types.config.service import ImplementationType as I2
assert I1 is I2, f'ImplementationType identity mismatch'

from panther.core.events.base.event_base import BaseEvent as E1
from panther_types.events.base import BaseEvent as E2
assert E1 is E2, f'BaseEvent identity mismatch'

from panther.core.exceptions import PantherException as P1
from panther_types.exceptions import PantherException as P2
assert P1 is P2, f'PantherException identity mismatch'

print('Type identity: ALL PASS')
"
```

### Step 5: Verify panther_ivy config imports

```bash
python -c "
from panther_ivy.config_schema import PantherIvyConfig
# PantherIvyConfig should inherit from ServicePluginConfig (now from panther_types)
from panther_types.config.plugin import ServicePluginConfig
assert issubclass(PantherIvyConfig, ServicePluginConfig), 'Inheritance broken!'
print('PantherIvyConfig: OK')
"
```

### Step 6: Run full panther unit test suite

```bash
pytest tests/ -n auto -m unit --timeout=120
```

Note any test failures. Pre-existing failures (documented in MEMORY.md) should be differentiated from new regressions.

### Step 7: Verify ServiceConfig still works

ServiceConfig is NOT extracted but uses extracted types (ImplementationType, ProtocolRole). Verify it still works:

```bash
python -c "
from panther.config.core.models.service import ServiceConfig, ProtocolConfig, ImplementationConfig
# These should still be local to panther (not in panther_types)
s = ServiceConfig()
print('ServiceConfig: OK')
"
```

### Step 8: Verify FastFailHandler still works

```bash
python -c "
from panther.core.exceptions.fast_fail import FastFailHandler, PantherException, ErrorSeverity, ErrorCategory
handler = FastFailHandler()
# Should be able to create and use the handler
print('FastFailHandler: OK')
"
```

## Success Criteria
1. All panther-types tests pass
2. All backward-compatible imports work
3. Type identity is preserved across both import paths
4. PantherIvyConfig correctly inherits from ServicePluginConfig
5. Panther unit tests have no new regressions
6. ServiceConfig and FastFailHandler (not extracted) still work

## Troubleshooting

### Circular import errors
- Check that re-export shims don't accidentally import from modules that import back from them
- The validators module lazy-imports should now point to panther_types

### Pydantic model validation failures
- BaseConfig and BaseUnifiedModel have specific Config class settings. Verify they're preserved.
- Field validators in plugin.py may need specific Pydantic imports. Verify.

### Missing `omega_config` field
- BaseConfig has `omega_config: Optional[DictConfig] = Field(default=None, exclude=True)`
- This must be preserved exactly in the panther_types version

## Commit Message
```
test: verify Phase 2 panther-types extraction
```

## Files Modified
- None (verification only)
