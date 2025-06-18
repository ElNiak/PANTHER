# Modifications for Task 20250618: Legacy Code Removal

## Phase 1: Plugin Manager Refactoring

### Core Files to Modify

**panther/config/config_manager.py**
- [ ] Lines 132-343: Replace 15+ duplicate plugin methods with generic calls
  - `add_plugin_tester_service()` → `add_plugin("tester", ...)`
  - `add_plugin_iut_service()` → `add_plugin("iut", ...)`
  - `add_plugin_network_environment()` → `add_plugin("network", ...)`
  - `add_plugin_execution_environment()` → `add_plugin("execution", ...)`
- [ ] Lines 732-926: Replace 5 discovery methods with generic `get_plugin_classes()`
- [ ] Lines 51-1205: Remove ConfigLoader backward compatibility wrapper
- [ ] Line 625: Fix TODO - Default to client-server protocol
- [ ] Line 685: Fix TODO - Clean up version loading

**panther/core/experiment_manager.py**
- [ ] Update plugin manager imports
- [ ] Replace old plugin method calls with new generic API
- [ ] Add error handling for config operations

## Phase 2: Schema Standardization

### Schema Files to Modify (29 files)

**panther/plugins/services/base/config_base.py**
- [ ] Convert from Marshmallow to Pydantic
- [ ] Inherit from new BasePluginConfig
- [ ] Add consistent validation

**panther/plugins/services/iut/quic/picoquic/config_schema.py**
- [ ] Lines 66-84: Remove static version loading method
- [ ] Convert to standard schema pattern
- [ ] Extract hardcoded values

**panther/plugins/services/iut/quic/aioquic/config_schema.py**
- [ ] Standardize base class inheritance
- [ ] Add error handling
- [ ] Remove Any types

**panther/plugins/services/iut/quic/lsquic/config_schema.py**
- [ ] Update to consistent validation pattern
- [ ] Add missing error handling
- [ ] Standardize Config class

[Continue for all 29 config_schema.py files...]

## Phase 3: Hardcoded Value Extraction

### Files with Hardcoded Values (14 files)

**panther/plugins/services/iut/quic/*/config_schema.py**
- [ ] Replace port 4443 with DEFAULT_QUIC_PORT
- [ ] Replace paths with environment variables
- [ ] Extract magic numbers to constants

**panther/plugins/environments/network_environment/*/config_schema.py**
- [ ] Replace hardcoded timeouts with constants
- [ ] Extract cache sizes to configuration
- [ ] Remove hardcoded paths

## Phase 4: Import Updates

### Files Importing from panther.config (109 files)

**panther/plugins/plugin_manager.py**
- [ ] Update ConfigLoader imports to ConfigurationManager
- [ ] Fix circular dependency with config module

**panther/plugins/plugin_config_resolver.py**
- [ ] Break circular import with ConfigManager
- [ ] Use dependency injection pattern

**panther/core/observer/*.py**
- [ ] Update all config imports
- [ ] Remove legacy ConfigLoader references

## Phase 5: Event System Integration

**panther/core/events/emitter_registry.py**
- [ ] Add config change events
- [ ] Register plugin manager events

**panther/core/events/plugin/events.py**
- [ ] Add events for plugin operations
- [ ] Include migration events

## Phase 6: Test Updates

**tests/unit/test_config_manager.py**
- [ ] Update tests for new plugin manager
- [ ] Add tests for generic methods
- [ ] Remove tests for duplicate methods

**tests/integration/test_plugin_system.py**
- [ ] Update integration tests
- [ ] Test backward compatibility
- [ ] Add migration tests

## Phase 7: Documentation Updates

**CLAUDE.md**
- [ ] Update plugin development section
- [ ] Add migration guide
- [ ] Update configuration examples

**panther/plugins/README.md**
- [ ] Update with new plugin manager API
- [ ] Add examples of generic usage

**CHANGELOG.md**
- [ ] Document all breaking changes
- [ ] Add migration instructions

## Summary of Modifications

| Category | Files | Lines Changed | Reduction |
|----------|-------|---------------|-----------|
| Plugin Manager | 1 | ~500 → ~50 | 90% |
| Config Schemas | 29 | ~50 each | 30% |
| Imports | 109 | ~5 each | - |
| Tests | 15 | ~100 each | - |
| Documentation | 5 | ~200 each | - |

**Total Estimated Changes**: 
- Files modified: 159
- Lines changed: ~3000
- Net reduction: ~1500 lines