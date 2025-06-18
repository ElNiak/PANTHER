# File Analysis: panther/plugins/services/iut/config_schema.py

## Current Content Analysis:
- **Type**: Legacy dataclass definitions
- **Size**: 49 lines of code
- **Contains dataclasses**: YES - Parameter, VersionBase, ImplementationConfig
- **Contains unique methods**: NO
- **Contains custom validation**: NO
- **Contains enums or constants**: YES - ImplementationType enum

## Unique Functionality Analysis:

### Classes in Legacy File:
1. **Parameter** - Simple parameter class (value, description)
2. **VersionBase** - Version info class (version, commit, dependencies)  
3. **ImplementationType** - Enum (IUT, TESTERS)
4. **ImplementationConfig** - Implementation config with shadow/gperf compatibility flags

### Integration Status:
✅ **ImplementationType** - Already exists in unified models
✅ **ImplementationConfig** - Already exists in unified models (enhanced version)
❌ **Parameter** - Not in unified models (but may not be needed)
❌ **VersionBase** - Not in unified models (but may not be needed)

### Special Fields in Legacy ImplementationConfig:
- shadow_compatible: bool = False
- gperf_compatible: bool = False

### Unified ImplementationConfig Fields:
- name: str
- type: ImplementationType  
- version: Optional[str]
- Dynamic extra fields support

## Decision:
⚠️ **NEEDS INVESTIGATION** - Check if shadow_compatible and gperf_compatible are used

## Required Investigation:
1. Search for usage of shadow_compatible and gperf_compatible
2. Search for usage of Parameter and VersionBase classes
3. Determine if these need to be added to unified models