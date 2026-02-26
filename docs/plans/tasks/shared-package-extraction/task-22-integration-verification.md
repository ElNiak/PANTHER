# Task 22: Full Integration Verification

## Goal
Verify the entire shared package extraction works end-to-end across all phases.

## Prerequisites
- All tasks 01-21 completed

## Steps

### Step 1: Verify package installations

```bash
source .venv/bin/activate

# Both shared packages installed
pip install -e packages/panther-ivy-types/
pip install -e packages/panther-types/

# Panther itself installed (with its own panther.api)
pip install -e .

# Verify installations
pip list | grep panther
# Should show:
# panther-ivy-types  0.1.0  /path/to/packages/panther-ivy-types
# panther-types      0.1.0  /path/to/packages/panther-types
# panther            1.1.5  /path/to/PANTHER
```

### Step 2: Verify import isolation

```bash
# panther-ivy-types should have NO external deps
python -c "
import panther_ivy_types
print('panther-ivy-types imports:', dir(panther_ivy_types))
# Should work without pydantic, omegaconf, docker, etc.
"

# panther-types should only need pydantic + omegaconf
python -c "
import panther_types
print('panther-types imports:', dir(panther_types))
# Should work without docker, scapy, etc.
"
```

### Step 3: Verify type identity across all import paths

```bash
python -c "
# panther-ivy-types
from panther_ivy.api.types import DiagnosticItem as D1
from panther_ivy_types.api import DiagnosticItem as D2
assert D1 is D2, 'DiagnosticItem identity mismatch'

from panther_ivy_types.analysis import RequirementNode as R1
# If ivy-lsp re-exports it:
# from ivy_lsp.analysis.requirement_graph import RequirementNode as R2
# assert R1 is R2

# panther-types config
from panther.config.core.base import BaseConfig as B1
from panther_types.config.base import BaseConfig as B2
assert B1 is B2, 'BaseConfig identity mismatch'

from panther.config.core.models.plugin import ServicePluginConfig as S1
from panther_types.config.plugin import ServicePluginConfig as S2
assert S1 is S2, 'ServicePluginConfig identity mismatch'

from panther.config.core.models.service import ImplementationType as I1
from panther_types.config.service import ImplementationType as I2
assert I1 is I2, 'ImplementationType identity mismatch'

# panther-types events
from panther.core.events.base.event_base import BaseEvent as E1
from panther_types.events.base import BaseEvent as E2
assert E1 is E2, 'BaseEvent identity mismatch'

# panther-types exceptions
from panther.core.exceptions import PantherException as P1
from panther_types.exceptions import PantherException as P2
assert P1 is P2, 'PantherException identity mismatch'

# panther-types plugin structures
from panther.plugins.core.structures.plugin_type import PluginType as T1
from panther_types.plugin.types import PluginType as T2
assert T1 is T2, 'PluginType identity mismatch'

print('ALL TYPE IDENTITIES: PASS')
"
```

### Step 4: Verify inheritance chains work

```bash
python -c "
from panther_ivy.config_schema import PantherIvyConfig
from panther_types.config.plugin import ServicePluginConfig
from panther_types.config.base import BaseConfig, BaseUnifiedModel

# Verify inheritance chain
assert issubclass(PantherIvyConfig, ServicePluginConfig)
assert issubclass(ServicePluginConfig, BaseUnifiedModel)
assert issubclass(BaseUnifiedModel, BaseConfig)
print('Inheritance chain: PASS')

# Verify PantherIvyConfig can be instantiated with defaults
config = PantherIvyConfig()
print(f'PantherIvyConfig instantiated: name={config.name}')
print('PantherIvyConfig: PASS')
"
```

### Step 5: Run all test suites

```bash
# panther-ivy-types tests
cd packages/panther-ivy-types && pytest tests/ -v && cd -

# panther-types tests
cd packages/panther-types && pytest tests/ -v && cd -

# panther unit tests (the big one - should have NO regressions)
pytest tests/ -n auto -m unit --timeout=120

# panther API tests
pytest tests/unit/test_api/ -v
```

### Step 6: Verify panther.api works end-to-end

```bash
python -c "
# Config API
from panther.api.config import get_config_schema
schema = get_config_schema()
assert isinstance(schema, dict), 'Config schema should be a dict'
print('Config API: OK')

# Plugins API
from panther.api.plugins import list_plugins
plugins = list_plugins()
assert isinstance(plugins, list), 'Plugins should be a list'
print(f'Plugins API: OK ({len(plugins)} plugins)')

# Schemas API
from panther.api.schemas import get_config_schema as get_schema
schema = get_schema()
assert isinstance(schema, dict), 'Schema should be a dict'
print('Schemas API: OK')

# Events API
from panther.api.events import get_event_types
types = get_event_types()
assert isinstance(types, list), 'Event types should be a list'
print(f'Events API: OK ({len(types)} event types)')

print('ALL API MODULES: PASS')
"
```

### Step 7: Verify CLI still works

```bash
# Basic CLI commands should still work
panther --help
panther plugins list
panther config validate --config experiment-config/base/experiment_config_example_minimal.yaml
panther ivy list-tests 2>/dev/null || echo "ivy list-tests: requires Docker (expected)"
```

### Step 8: Check for import performance

```bash
# panther-ivy-types should import very fast (no external deps)
python -c "
import time
start = time.time()
import panther_ivy_types
elapsed = time.time() - start
print(f'panther-ivy-types import: {elapsed:.3f}s')
assert elapsed < 0.5, f'Too slow: {elapsed:.3f}s'
"

# panther-types import time (pydantic is slower)
python -c "
import time
start = time.time()
import panther_types
elapsed = time.time() - start
print(f'panther-types import: {elapsed:.3f}s')
assert elapsed < 2.0, f'Too slow: {elapsed:.3f}s'
"
```

## Success Criteria

1. Both packages install cleanly via `pip install -e`
2. All type identities are preserved across import paths
3. PantherIvyConfig inheritance chain works
4. All panther-ivy-types tests pass
5. All panther-types tests pass
6. Panther unit tests have no new regressions
7. panther.api modules are functional
8. CLI commands still work
9. Import performance is acceptable

## Summary Report Template

After verification, produce a summary:

```
=== Shared Package Extraction - Integration Report ===

Phase 1 (panther-ivy-types):
  - Package: panther-ivy-types 0.1.0
  - Types extracted: 10 (6 API + 2 analysis + 2 scope)
  - Dependencies: 0 (stdlib only)
  - Tests: X/X pass
  - Import time: X.XXXs

Phase 2 (panther-types):
  - Package: panther-types 0.1.0
  - Types extracted: X config + X events + X exceptions + X plugin
  - Dependencies: pydantic, omegaconf, PyYAML
  - Tests: X/X pass
  - Import time: X.XXXs

Phase 2b (interfaces):
  - Interfaces defined: 9 Protocol + ABC pairs
  - Conformance tests: X/X pass

Phase 3 (panther.api):
  - Modules: config, plugins, experiments, docker, events, schemas
  - Tests: X/X pass

Backward Compatibility:
  - All old import paths work: YES/NO
  - Type identity preserved: YES/NO
  - CLI commands work: YES/NO

Regressions:
  - Panther unit tests: X/X pass (Y pre-existing failures)
  - New failures: NONE / <list>
```

## Commit Message
```
test: full integration verification of shared package extraction

Verify end-to-end: package installations, type identity across import
paths, inheritance chains, all test suites, panther.api functionality,
CLI commands, and import performance.
```

## Files Modified
- None (verification only, produces report)
