# Hybrid Configuration System Migration TODO

## Overview
Complete migration from legacy dataclass-based configurations to a hybrid Pydantic-OmegaConf system.
This TODO ensures ALL features from legacy managers are preserved while creating a clean, unified architecture.

## Legacy ConfigManager Features to Preserve

### From ConfigManagerRefactored (config_manager_refactored.py):
1. **Multiple constructor parameters**: experiment_file, output_dir, exec_env_dir, net_env_dir, iut_dir, testers_dir, metrics_collector, debug_override, panther_dir
2. **Modular components**: ConfigurationBuilder, ConfigurationValidator, PluginDiscovery, PluginFileManager, PluginSchemaLoader
3. **Environment variable mappings**: PANTHER_LOG_LEVEL, PANTHER_BUILD_IMAGES, PANTHER_OUTPUT_DIR, PANTHER_LOG_COLORS, PANTHER_PLUGIN_DIR
4. **Feature log levels support**: feature_levels configuration with proper enum conversion
5. **Plugin management**: add_plugin, remove_plugin, discover_plugins, get_plugin_metadata
6. **Schema management**: load_plugin_schemas, validate_plugin_config
7. **Configuration summary**: get_configuration_summary with validation results, builder summary, plugin summary
8. **Validation modes**: set_validation_mode (strict/lenient)
9. **Override management**: add_configuration_override, clear_configuration_overrides
10. **Context manager support**: __enter__, __exit__ methods
11. **Legacy API compatibility**: load_config, validate_config, get_plugins methods
12. **Backward compatible ConfigLoader class**: list_plugin_parameters, _auto_detect_plugin_type

### From ConfigurationManagerV2 (config_manager_v2.py):
1. **Caching system**: enable_cache flag, cache management, clear_cache
2. **Auto-fix configurations**: auto_fix_configs flag with detailed logging
3. **Composite loading**: YAMLConfigLoader, VersionConfigLoader, CompositeLoader
4. **Version discovery**: discover_available_versions, get_version_configuration
5. **Advanced merging**: merge_configurations with strategies (DEEP_MERGE, etc.) and conflict resolution
6. **Template support**: create_experiment_from_template with parameter substitution
7. **Statistics tracking**: get_statistics with cache sizes, protocol counts
8. **Validation chain**: PydanticValidator + BusinessRulesValidator
9. **Service validation**: validate_service_configuration
10. **Global instance management**: get_config_manager_v2() with lazy initialization
11. **Convenience functions**: load_experiment, validate_service, discover_versions

### From ConfigManager Enhanced (config_manager_enhanced.py):
1. **Hybrid routing**: Tries V2 first, falls back to legacy for compatibility
2. **Legacy compatibility detection**: _check_needs_legacy_handling for fields like 'test'
3. **Debug override handling**: Proper logging level override
4. **ConfigLoader backward compatibility**: Maintains old ConfigLoader interface

## Phase 1: Create Hybrid Core Infrastructure (Priority: CRITICAL)

### 1.1 Create Hybrid Base Classes
**ADD:**
```
- [ ] /panther/config/hybrid/base.py
      - HybridConfig base class combining Pydantic validation + OmegaConf features
      - Methods: validate(), to_omega(), from_omega(), to_dict(), merge()
      - Support for both model validation and dynamic interpolation
      
- [ ] /panther/config/hybrid/mixins.py
      - ValidationMixin: Pydantic validation features
      - InterpolationMixin: OmegaConf interpolation features
      - CacheMixin: Caching functionality
      - CompatibilityMixin: Legacy format support
```

### 1.2 Create Hybrid Manager
**ADD:**
```
- [ ] /panther/config/hybrid/manager.py (900+ lines)
      - HybridConfigManager class with ALL features from legacy managers:
        * Constructor with all legacy parameters
        * Modular component initialization (builders, validators, loaders)
        * load_and_validate_experiment_config() - main entry point
        * load_and_validate_global_config()
        * Environment variable mapping support
        * Feature log levels handling
        * Plugin management (add/remove/discover)
        * Schema management
        * Configuration summary
        * Validation modes
        * Override management
        * Context manager support
        * Legacy API methods
        * Caching system from V2
        * Auto-fix functionality
        * Version discovery
        * Advanced merging
        * Template support
        * Statistics tracking
        * Service validation
        * Global instance with lazy init
        * Convenience functions
```

### 1.3 Create Unified Models
**ADD:**
```
- [ ] /panther/config/hybrid/models/__init__.py
      - Export all models with backward compatible names

- [ ] /panther/config/hybrid/models/base_model.py
      - BaseHybridModel: Base for all configuration models
      - Inherits from both Pydantic BaseModel and HybridConfig
      - Automatic OmegaConf conversion methods

- [ ] /panther/config/hybrid/models/global_config.py (300+ lines)
      - GlobalConfig: Replaces config_global_schema.py
      - LoggingConfig with LoggingLevel enum
      - FeatureLogLevelsConfig with all feature fields
      - PathsConfig, DockerConfig, ObserversConfig
      - All current dataclass fields as Pydantic fields
      
- [ ] /panther/config/hybrid/models/experiment.py (200+ lines)
      - ExperimentConfig: Replaces config_experiment_schema.py
      - TestConfig with all fields
      - StepsConfig with proper validation
      
- [ ] /panther/config/hybrid/models/service.py (400+ lines)
      - ServiceConfig: Replaces all service config dataclasses
      - ImplementationConfig with dynamic type handling
      - ProtocolConfig with version discovery
      - NetworkConfig, EnvironmentConfig
      - All plugin-specific configs (QuicConfig, HttpConfig, etc.)
      
- [ ] /panther/config/hybrid/models/environment.py (300+ lines)
      - NetworkEnvironmentConfig: Base + specific implementations
      - ExecutionEnvironmentConfig: Base + specific implementations
      - DockerComposeConfig, LocalhostConfig, ShadowNsConfig
      - All execution env configs (StraceConfig, GperfConfig, etc.)
      
- [ ] /panther/config/hybrid/models/protocol.py (200+ lines)
      - ProtocolConfig: Base protocol configuration
      - ClientServerProtocolConfig
      - PeerToPeerProtocolConfig
      - Dynamic version support (no hardcoded enums)
```

### 1.4 Create Component Adapters
**ADD:**
```
- [ ] /panther/config/hybrid/components/loaders.py
      - HybridYAMLLoader: Enhanced YAML loading with interpolation
      - HybridVersionLoader: Version discovery with caching
      - HybridCompositeLoader: Multiple source support
      
- [ ] /panther/config/hybrid/components/validators.py
      - HybridValidator: Combined Pydantic + business rules
      - LegacyCompatibilityValidator: Validates old formats
      - MigrationValidator: Helps identify migration issues
      
- [ ] /panther/config/hybrid/components/builders.py
      - HybridExperimentBuilder: Builds with auto-fix support
      - HybridServiceBuilder: Service-specific building
      - Preserves all fields (including 'test' for panther_ivy)
      
- [ ] /panther/config/hybrid/components/merger.py
      - HybridMerger: OmegaConf merger with enhancements
      - Supports all merge strategies from V2
      - Conflict resolution with detailed reporting
```

## Phase 2: Create Migration Layer (Priority: HIGH)

### 2.1 Dataclass to Hybrid Adapters
**ADD:**
```
- [ ] /panther/config/hybrid/adapters/dataclass_adapter.py
      - DataclassToHybrid: Convert dataclass configs to hybrid
      - HybridToDataclass: Convert hybrid configs to dataclass
      - Handles all special cases (enums, nested configs, etc.)
      
- [ ] /panther/config/hybrid/adapters/import_adapter.py
      - ImportAdapter: Intercepts old imports, returns hybrid models
      - Registers with sys.meta_path for transparent migration
```

### 2.2 Compatibility Checkers
**ADD:**
```
- [ ] /panther/config/hybrid/compatibility/checker.py
      - CompatibilityChecker: Detects legacy format usage
      - MigrationAdvisor: Suggests migration steps
      - LegacyFieldDetector: Finds deprecated fields
```

## Phase 3: Update Core Integration Points (Priority: HIGH)

### 3.1 Update Main Config Module
**MODIFY:**
```
- [ ] /panther/config/__init__.py (lines 1-50)
      OLD: Export legacy managers and schemas
      NEW: Export HybridConfigManager as ConfigManager
           Export hybrid models with legacy names
           Add deprecation warnings for direct schema imports
           
- [ ] /panther/config/config_manager.py (lines 1-100)
      OLD: Original ConfigManager implementation
      NEW: Simple wrapper that delegates to HybridConfigManager
           Maintains exact same interface for compatibility
```

### 3.2 Create Backup of Current System
**EXECUTE:**
```
- [ ] Create .backup/config_system_20250616_phase3/
- [ ] Copy all current config files before modification
- [ ] Create restore_phase3.sh script
```

## Phase 4: Update Entry Points (Priority: HIGH)

### 4.1 Update CLI Commands
**MODIFY:**
```
- [ ] /panther/cli/subcommands/run.py (lines 10, 157-163)
      OLD: from ...config.config_manager_enhanced import ConfigLoader
      NEW: from ...config.hybrid import ConfigLoader
      
- [ ] /panther/cli/subcommands/config.py (lines 5-15)
      OLD: Import old config managers
      NEW: Import HybridConfigManager
      
- [ ] /panther/cli/subcommands/plugins.py (lines 5-15)
      OLD: Import old plugin discovery
      NEW: Import from hybrid system
```

### 4.2 Update Main Entry Point
**MODIFY:**
```
- [ ] /panther/__main__.py (lines 1-50)
      OLD: Import old config system
      NEW: Import hybrid system
      Add migration detection and warnings
```

## Phase 5: Update Core Classes (Priority: HIGH)

### 5.1 Update Experiment Manager
**MODIFY:**
```
- [ ] /panther/core/experiment_manager.py (lines 20-21, 94-96)
      OLD: from panther.config.config_experiment_schema import ExperimentConfig
           from panther.config.config_global_schema import GlobalConfig
      NEW: from panther.config.hybrid.models import ExperimentConfig, GlobalConfig
      
      Ensure constructor parameters remain compatible
```

### 5.2 Update Test Case Implementation
**MODIFY:**
```
- [ ] /panther/core/test_cases/test_case_impl.py (lines 15-30)
      OLD: Import old schemas
      NEW: Import hybrid models
      
- [ ] /panther/core/test_cases/test_case_impl_enhanced.py
      OLD: Import old schemas
      NEW: Import hybrid models
      
- [ ] /panther/core/test_cases/test_case_impl_refactored.py
      Remove if redundant with enhanced version
```

### 5.3 Update Observer System
**MODIFY:**
```
- [ ] /panther/core/observer/impl/*.py (all observer implementations)
      OLD: Import old observer schemas
      NEW: Import hybrid observer configs
      Update constructor signatures if needed
```

## Phase 6: Update Plugin System (Priority: MEDIUM)

### 6.1 Update Plugin Manager
**MODIFY:**
```
- [ ] /panther/plugins/plugin_manager.py (lines 50-100)
      OLD: Use old config schemas
      NEW: Use hybrid models
      Ensure version discovery integration works
```

### 6.2 Update Service Base Classes
**MODIFY:**
```
- [ ] /panther/plugins/services/base/config_base.py
      OLD: Dataclass configs
      NEW: Hybrid model configs
      
- [ ] /panther/plugins/services/base/service_base.py
      Update to accept hybrid configs
      
- [ ] /panther/plugins/services/config_schema.py
      Replace with import from hybrid.models.service
```

### 6.3 Update Individual Service Implementations
**MODIFY:** (for each implementation)
```
- [ ] /panther/plugins/services/iut/quic/picoquic/picoquic.py
- [ ] /panther/plugins/services/iut/quic/aioquic/aioquic.py
- [ ] /panther/plugins/services/iut/quic/quiche/quiche.py
- [ ] /panther/plugins/services/iut/quic/quinn/quinn.py
- [ ] /panther/plugins/services/iut/quic/lsquic/lsquic.py
- [ ] /panther/plugins/services/iut/quic/mvfst/mvfst.py
- [ ] /panther/plugins/services/iut/quic/quic_go/quic_go.py
- [ ] /panther/plugins/services/iut/quic/quant/quant.py
- [ ] /panther/plugins/services/testers/panther_ivy/panther_ivy.py
      
      For each:
      - Update config imports
      - Ensure compatibility with new config structure
      - Test that existing functionality works
```

### 6.4 Update Environment Plugins
**MODIFY:**
```
- [ ] /panther/plugins/environments/network_environment/*.py
- [ ] /panther/plugins/environments/execution_environment/*.py
      Update config imports and usage
```

## Phase 7: Update Docker Builder (Priority: MEDIUM)

**MODIFY:**
```
- [ ] /panther/core/docker_builder/docker_builder.py
      Update config imports
      Ensure user mapping features work
      
- [ ] /panther/core/docker_builder/service_manager_docker_mixin.py
      Update to use hybrid configs
```

## Phase 8: Testing Infrastructure (Priority: HIGH)

### 8.1 Create Hybrid System Tests
**ADD:**
```
- [ ] /tests/unit/config/test_hybrid_manager.py
- [ ] /tests/unit/config/test_hybrid_models.py
- [ ] /tests/unit/config/test_hybrid_compatibility.py
- [ ] /tests/integration/test_hybrid_loading.py
- [ ] /tests/integration/test_hybrid_migration.py
```

### 8.2 Update Existing Tests
**MODIFY:**
```
- [ ] /tests/unit/test_core/test_experiment_manager.py
- [ ] /tests/unit/test_config/*.py
- [ ] /tests/integration/*.py
      Update imports to use hybrid system
```

## Phase 9: Migration Tools (Priority: MEDIUM)

**ADD:**
```
- [ ] /panther/tools/config_migration/migrate.py
      - Main migration script
      - Converts old configs to new format
      - Updates imports in Python files
      
- [ ] /panther/tools/config_migration/validator.py
      - Validates migrated configurations
      - Checks for compatibility issues
```

## Phase 10: Remove Legacy Code (Priority: LOW - AFTER ALL TESTS PASS)

### 10.1 Remove V2 System Files
**REMOVE:**
```
- [ ] /panther/config/config_manager_v2.py
- [ ] /panther/config/builders/
- [ ] /panther/config/loaders/
- [ ] /panther/config/mergers/
- [ ] /panther/config/models/
- [ ] /panther/config/validators/
- [ ] /panther/config/registry/
- [ ] /panther/config/managers/ (after extracting needed code)
```

### 10.2 Remove Legacy Dataclass Schemas
**REMOVE:**
```
- [ ] /panther/config/config_experiment_schema.py
- [ ] /panther/config/config_global_schema.py
- [ ] /panther/config/config_observer_schema.py
```

### 10.3 Remove Intermediate Managers
**REMOVE:**
```
- [ ] /panther/config/config_manager_enhanced.py
- [ ] /panther/config/config_manager_refactored.py
```

### 10.4 Remove Old/Backup Files
**REMOVE:**
```
- [ ] /dev/old/ (entire directory)
- [ ] /backup_originals/ (entire directory)
- [ ] All *_original.py files
- [ ] All *_refactored.py files
- [ ] All *_legacy.py files
```

## Phase 11: Documentation (Priority: MEDIUM)

**ADD/UPDATE:**
```
- [ ] /docs/configuration/hybrid_system.md
- [ ] /docs/configuration/migration_guide.md
- [ ] /CLAUDE.md - Update configuration section
- [ ] /README.md - Update examples
```

## Implementation Order

1. **Phase 1**: Create hybrid infrastructure (Week 1)
2. **Phase 2**: Create migration layer (Week 1)
3. **Phase 3-4**: Update integration points (Week 2)
4. **Phase 5-7**: Update core classes (Week 2-3)
5. **Phase 8**: Testing (Week 3-4)
6. **Phase 9**: Migration tools (Week 4)
7. **Phase 10**: Legacy removal (Week 5)
8. **Phase 11**: Documentation (Week 5-6)

## Success Criteria

1. All existing experiments run without modification
2. All tests pass with new system
3. No performance degradation
4. Full backward compatibility maintained
5. Clean migration path for users
6. Improved type safety and validation
7. Single source of truth for configurations
8. No code duplication

## Key Principles

1. **Create new before deleting old**: Always have working system
2. **Test at each phase**: Ensure nothing breaks
3. **Maintain exact interfaces**: No breaking changes
4. **Preserve ALL features**: Nothing lost in migration
5. **Document changes**: Clear migration guide
6. **Incremental migration**: Users can migrate gradually

## File Count Estimates

- Files to ADD: ~25 new files
- Files to MODIFY: ~150 files
- Files to REMOVE: ~50 files
- Total lines affected: ~20,000+

## Risk Mitigation

1. Create full backup before each phase
2. Run full test suite after each change
3. Keep restoration scripts ready
4. Use feature flags for gradual rollout
5. Monitor performance metrics
6. Have rollback plan for each phase