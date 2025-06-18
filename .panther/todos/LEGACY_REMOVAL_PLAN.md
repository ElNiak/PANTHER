# Legacy Code Removal Plan

**TODO ID**: legacy_code_removal_20250618  
**Priority**: HIGH 🔴  
**Status**: PENDING  
**Created**: 2025-06-18  
**Estimated Time**: 8 weeks  

## Objective
Remove all legacy code from PANTHER configuration system without breaking functionality, based on comprehensive legacy detection analysis.

## Scope of Work

### 1. Configuration System (Week 1-3)
- [ ] **Remove ConfigLoader wrapper** (1154 lines)
  - Migrate all usages to ConfigurationManager
  - Maintain temporary compatibility layer
  - Update all imports and references
  
- [ ] **Refactor plugin management methods** (350+ lines)
  - Create generic PluginManager class
  - Consolidate 15+ duplicate methods to 2-3 generic ones
  - Update all plugin operations

- [ ] **Address TODO/FIXME comments** (9 items)
  - Line 280, 320: Improve plugin copying logic
  - Line 463: Implement dependency resolution
  - Line 625: Fix protocol type defaulting
  - Line 685: Clean up version loading
  - Shadow NS line 83: Add multiple network nodes support
  - Panther Ivy lines 22, 28, 96: Complete TODOs

### 2. Schema Standardization (Week 4-5)
- [ ] **Standardize config schemas** (29 files)
  - Migrate from mixed Pydantic/Marshmallow to pure Pydantic
  - Fix inconsistent base classes
  - Implement consistent validation patterns
  
- [ ] **Add error handling** (25 files need it)
  - Wrap all config operations in try/except
  - Add graceful fallbacks
  - Fix bare except clause in base_model.py

### 3. Remove Hardcoded Values (Week 3)
- [ ] **Extract magic numbers** (14 files)
  - Ports: 4443, 8080, 3000, 5000
  - Paths: /usr/bin/valgrind, /opt/certs
  - Numbers: 1000000, 32, 100, 60
  - Move to constants or environment variables

### 4. Fix Dependencies (Week 6)
- [ ] **Resolve circular dependencies** (109 files)
  - ConfigManager ↔ Plugin System
  - Base Models ↔ Specific Configs
  - Restructure imports

### 5. Testing & Validation (Week 7-8)
- [ ] **Comprehensive testing**
  - Unit tests for all refactored components
  - Integration tests for plugin system
  - Performance benchmarking
  
- [ ] **Functionality preservation**
  - Verify all existing features work
  - Check backward compatibility
  - Run full test suite

## Success Criteria
1. All legacy code removed
2. Zero functionality regression
3. 60% code reduction achieved
4. 100% test coverage maintained
5. All hardcoded values extracted
6. Clean dependency graph

## Risk Mitigation
1. **Breaking Changes**: Maintain compatibility layer during transition
2. **Plugin Compatibility**: Provide migration guide and tools
3. **Performance**: Benchmark before/after each major change
4. **User Impact**: Gradual rollout with feature flags

## Progress Tracking
- Auto-sync enabled for file change monitoring
- Weekly progress reports
- Daily status updates in TODO system
- Git commit tracking with TODO references

## Next Steps
1. Start with generic PluginManager implementation
2. Create comprehensive test suite
3. Set up performance benchmarks
4. Begin incremental refactoring

---
*This plan is based on the comprehensive legacy detection analysis completed on 2025-06-18*