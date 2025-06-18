# File Analysis: panther/config/config_experiment_schema.py

## Current Content Analysis:
- **Type**: Re-export/redirect file for unified models
- **Size**: 31 lines of code  
- **Contains dataclasses**: No - only imports and re-exports
- **Contains unique methods**: No - pure import redirects
- **Contains custom validation**: No
- **Contains enums or constants**: No

## Unified Model Comparison:
- **All fields present in unified model**: Yes - this file just re-exports them
- **All methods available in unified model**: Yes - no methods in this file
- **All validation logic preserved**: Yes - no validation in this file
- **All enums/constants available**: Yes - no constants in this file

## Dependencies Analysis:
- **Files importing from this**: 30 files found
- **Unique functionality not in unified models**: None - pure redirects
- **Business logic that would be lost**: None

## Content Analysis:
```python
# All imports are redirects to unified models:
from panther.config.core.models.experiment import (
    ExperimentConfig, ExperimentMetadata, StepsConfig, TestConfig
)
from panther.config.core.models.service import ServiceConfig
from panther.config.core.models.environment import (
    ExecutionEnvironmentConfig, NetworkEnvironmentConfig
)
```

## Decision:
✅ **SAFE TO DELETE** - Pure redirect file with no unique functionality

## Required Actions:
1. **BACKUP**: Move to legacy backup directory
2. **UPDATE IMPORTS**: Update 30 importing files to use unified models directly:
   - FROM: `from panther.config.config_experiment_schema import ExperimentConfig`
   - TO: `from panther.config.core.models import ExperimentConfig`

## Import Update Pattern:
Replace all occurrences of:
```python
from panther.config.config_experiment_schema import (...)
```
With:
```python
from panther.config.core.models import (...)
```

## Files Requiring Import Updates:
- panther/core/test_cases/base/test_case_base.py
- panther/plugins/environments/network_environment/docker_compose/docker_compose.py
- panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py
- panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py
- Plus 26 more files (mostly in tests/ directory)

## Timeline Impact:
Low - This can be deleted immediately after updating imports.