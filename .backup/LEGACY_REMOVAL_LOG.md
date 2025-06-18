# Legacy Code Removal Log

## Overview
This document tracks all legacy code to be removed during the configuration system refactoring.
Each entry includes the file path, reason for removal, and any dependencies.

## Files to be Deleted

### 1. Development and Old Code Directories

#### `/dev/old/` (Entire Directory)
- **Reason**: Contains outdated implementations and experiments
- **Contents**: 
  - Old plugin implementations (*_original.py, *_refactored.py)
  - Legacy test files
  - Deprecated documentation
- **Dependencies**: None - these are backup/reference files only
- **Size**: ~500+ files

#### `/backup_originals/` (Entire Directory)
- **Reason**: Contains original versions before previous refactoring
- **Contents**:
  - command_original.py
  - config_manager_original.py
  - panther_ivy_original.py
  - test_case_impl_original.py
- **Dependencies**: None - backup files only

### 2. Configuration System Files

#### `/panther/config/config_experiment_schema.py`
- **Reason**: Dataclass-based schema replaced by Pydantic models
- **Dependencies**: 
  - Used by: experiment_manager.py, test cases, CLI
  - Imports: OmegaConf, dataclasses
- **Replacement**: `/panther/config/hybrid/models/experiment.py`

#### `/panther/config/config_global_schema.py`
- **Reason**: Dataclass-based schema replaced by Pydantic models
- **Dependencies**:
  - Used by: config managers, CLI
  - Contains: GlobalConfig, LoggingConfig, PathConfig, etc.
- **Replacement**: `/panther/config/hybrid/models/global_config.py`

#### `/panther/config/config_observer_schema.py`
- **Reason**: Dataclass-based schema replaced by Pydantic models
- **Dependencies**:
  - Used by: observer system
- **Replacement**: Integrated into hybrid models

#### `/panther/config/config_manager_enhanced.py`
- **Reason**: Complex legacy routing no longer needed
- **Dependencies**:
  - Contains hybrid legacy/V2 routing logic
  - Used by: CLI entry points
- **Replacement**: Direct use of HybridConfigManager

#### `/panther/config/config_manager_refactored.py`
- **Reason**: Intermediate refactoring step, superseded by hybrid approach
- **Dependencies**:
  - Alternative config manager implementation
- **Replacement**: HybridConfigManager

### 3. Service Implementation Files

#### All `*_original.py` files
- **Pattern**: `/panther/plugins/services/**/original.py`
- **Examples**:
  - lsquic_original.py
  - picoquic_original.py
  - panther_ivy_original.py
- **Reason**: Backup files from previous refactoring
- **Count**: ~15 files

#### All `*_refactored.py` files
- **Pattern**: `/panther/plugins/services/**/refactored.py`
- **Examples**:
  - lsquic_refactored.py
  - gperf_cpu_refactored.py
  - helgrind_refactored.py
- **Reason**: Intermediate refactoring versions
- **Count**: ~20 files

### 4. Legacy Plugin Files

#### `/panther/plugins/services/config_schema.py` (After Migration)
- **Current**: Dataclass-based ServiceConfig
- **Reason**: Replaced by hybrid Pydantic model
- **Dependencies**: All service managers
- **Replacement**: `/panther/config/hybrid/models/service.py`

#### `/panther/plugins/protocols/config_schema.py` (After Migration)
- **Current**: Dataclass-based ProtocolConfig
- **Reason**: Replaced by hybrid Pydantic model
- **Dependencies**: All protocol implementations
- **Replacement**: `/panther/config/hybrid/models/protocol.py`

### 5. Test Files

#### `/panther/core/test_cases/test_case_impl_original.py`
- **Reason**: Original implementation before refactoring
- **Dependencies**: None (backup only)

#### `/tests/unit/test_plugins/test_services/test_picoquic_refactored.py`
- **Reason**: Test for refactored version, will be updated
- **Dependencies**: Unit test suite

### 6. Migration and Temporary Files

#### `/verify_refactored_imports.py`
- **Reason**: One-time verification script
- **Dependencies**: None

#### All `.backup` files created during migration
- **Pattern**: `**/*.backup`
- **Reason**: Temporary backup files
- **Action**: Delete after successful migration

## Code Patterns to Remove

### 1. Dataclass Imports and Decorators
```python
# REMOVE:
from dataclasses import dataclass, field
@dataclass
class ConfigClass:
    field_name: type = field(default=value)
```

### 2. Legacy Enum Compatibility
```python
# REMOVE:
if hasattr(config.type, 'value'):
    # Enum compatibility
    type_value = config.type.value
else:
    type_value = config.type
```

### 3. OmegaConf Dataclass Usage
```python
# REMOVE:
from omegaconf import MISSING
field_name: str = MISSING  # OmegaConf pattern
```

### 4. Legacy Config Checks
```python
# REMOVE:
def _check_needs_legacy_handling(self, config):
    # Legacy compatibility checks
```

### 5. Hardcoded Version Enums
```python
# REMOVE:
class ProtocolVersion(Enum):
    RFC9000 = "rfc9000"
    DRAFT29 = "draft29"
```

## Dependencies to Update

### Files Importing Deleted Schemas
1. `/panther/core/experiment_manager.py`
2. `/panther/core/test_cases/*.py`
3. `/panther/cli/subcommands/*.py`
4. All service manager files
5. All test files

### Import Changes Required
```python
# OLD:
from panther.config.config_experiment_schema import ExperimentConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.services.config_schema import ServiceConfig

# NEW:
from panther.config.hybrid.models import (
    ExperimentConfig,
    GlobalConfig,
    ServiceConfig
)
```

## Validation Steps Before Removal

1. **Run full test suite** after each phase
2. **Check import dependencies** with automated script
3. **Verify no runtime imports** of removed files
4. **Test all CLI commands** work correctly
5. **Validate all plugins** load successfully

## Metrics

- **Total files to remove**: ~100+
- **Lines of code to remove**: ~15,000+
- **Duplicate definitions eliminated**: ~50 classes
- **Import statements to update**: ~500+

## Risk Assessment

- **High Risk**: Removing config schemas (many dependencies)
- **Medium Risk**: Removing service implementations (isolated impact)
- **Low Risk**: Removing backup/old directories (no dependencies)

## Rollback Strategy

1. All files backed up in `.backup/config_refactor_*`
2. Restoration script available
3. Git history preserves all changes
4. Can restore individual files if needed