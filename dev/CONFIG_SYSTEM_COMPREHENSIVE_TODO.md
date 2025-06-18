# Comprehensive Configuration System Migration TODO

## Overview
Complete migration from legacy dataclass-based configurations to a unified Pydantic-OmegaConf system.
This comprehensive TODO captures ALL features from legacy managers and ALL configuration usages across the codebase.

## Legacy Features Analysis

### From ConfigManagerRefactored (747 lines):
1. **Constructor parameters**: experiment_file, output_dir, exec_env_dir, net_env_dir, iut_dir, testers_dir, metrics_collector, debug_override, panther_dir
2. **Modular components**: ConfigurationBuilder, ConfigurationValidator, PluginDiscovery, PluginFileManager, PluginSchemaLoader
3. **Environment variables**: PANTHER_LOG_LEVEL, PANTHER_BUILD_IMAGES, PANTHER_OUTPUT_DIR, PANTHER_LOG_COLORS, PANTHER_PLUGIN_DIR
4. **Feature log levels**: FeatureLogLevelsConfig with enum conversion and validation
5. **Plugin management**: add_plugin, remove_plugin, discover_plugins, get_plugin_metadata, validate_plugin_config
6. **Schema management**: load_plugin_schemas with caching
7. **Configuration summary**: validation results, builder summary, plugin summary, schema summary
8. **Validation modes**: set_validation_mode (strict/lenient)
9. **Override management**: add_configuration_override, clear_configuration_overrides
10. **Context manager**: __enter__, __exit__ for cleanup
11. **Legacy API**: load_config, validate_config, get_plugins
12. **ConfigLoader class**: list_plugin_parameters, _auto_detect_plugin_type

### From ConfigurationManagerV2 (510 lines):
1. **Caching**: enable_cache flag, _loaded_experiments, _validation_cache, clear_cache()
2. **Auto-fix**: auto_fix_configs flag with detailed logging
3. **Composite loading**: YAMLConfigLoader, VersionConfigLoader, CompositeLoader
4. **Version discovery**: discover_available_versions, get_version_configuration, version registry
5. **Advanced merging**: MergeStrategy (DEEP_MERGE), MergeConflictResolution
6. **Templates**: create_experiment_from_template with parameter substitution
7. **Statistics**: loaded experiments, cache sizes, discovered protocols
8. **Validation chain**: PydanticValidator + BusinessRulesValidator
9. **Service validation**: validate_service_configuration
10. **Global instance**: get_config_manager_v2() with lazy initialization
11. **Convenience functions**: load_experiment, validate_service, discover_versions

### From ConfigManager Enhanced (232 lines):
1. **Hybrid routing**: V2 first, legacy fallback
2. **Compatibility detection**: _check_needs_legacy_handling
3. **Debug override**: Proper logging level management
4. **Export compatibility**: All legacy classes exported

### Additional Configuration Components Found:
1. **Observer configurations**: ObserverConfig, LoggerConfig, MetricsConfig, StorageConfig, ExperimentObserverConfig
2. **Progress configuration**: ProgressConfig with redirect_logging, enable_progress_bar
3. **Fast-fail configuration**: FastFailConfig with enabled, test_level, error categories
4. **Docker user mapping**: DockerUserMappingConfig with run_as_host_user, custom_uid/gid
5. **Command processor integration**: CommandBuilder accepts configs
6. **Template renderer**: Uses service configs for command generation
7. **Event manager**: Uses observer configs
8. **Workflow tracker**: Reads experiment config
9. **Results manager**: Uses storage config

## Phase 0: Preparation and Analysis (Priority: CRITICAL)

### 0.1 Create Comprehensive Backup
**EXECUTE:**
```
- [ ] Create .backup/config_system_20250616_comprehensive/
- [ ] Backup ALL config-related files:
      - /panther/config/ (entire directory)
      - /panther/plugins/**/config_schema.py (all plugin configs)
      - /panther/core/observer/factory/factory_config.py
      - All test files using configs
- [ ] Create detailed restoration script with file mappings
- [ ] Document current config class hierarchy
```

### 0.2 Dependency Analysis
**CREATE:**
```
- [ ] /panther/tools/config_migration/dependency_analyzer.py
      - Scan all Python files for config imports
      - Build dependency graph
      - Identify circular dependencies
      - Generate migration order
```

## Phase 1: Create Unified Configuration Infrastructure (Priority: CRITICAL)

### 1.1 Base System (No "Hybrid" in naming)
**ADD:**
```
- [ ] /panther/config/unified/__init__.py
      - Export main classes with backward compatible names
      
- [ ] /panther/config/unified/base.py (200 lines)
      - UnifiedConfig base class combining Pydantic + OmegaConf
      - Methods: validate(), to_omega(), from_omega(), to_dict(), merge()
      - Support interpolation: ${paths.output_dir}/logs
      - Support environment variables: ${oc.env:PANTHER_LOG_LEVEL,INFO}
      
- [ ] /panther/config/unified/mixins.py (300 lines)
      - ValidationMixin: Pydantic validation with custom error messages
      - InterpolationMixin: OmegaConf variable resolution
      - CacheMixin: LRU cache for loaded configs
      - CompatibilityMixin: Handle legacy fields
      - SerializationMixin: YAML/JSON export
```

### 1.2 Configuration Manager
**ADD:**
```
- [ ] /panther/config/unified/manager.py (1200+ lines)
      CLASS ConfigurationManager:
        # Constructor matching ALL legacy parameters
        __init__(experiment_file, output_dir, exec_env_dir, net_env_dir, 
                iut_dir, testers_dir, metrics_collector, debug_override, 
                panther_dir, enable_cache=True, auto_fix_configs=True)
        
        # Core loading methods
        - load_and_validate_experiment_config()
        - load_and_validate_global_config()
        - load_experiment_config(config_source, defaults, validate, auto_fix)
        - load_global_config(config_path, overrides, validate)
        
        # Environment variable support
        - _apply_environment_variables() with all mappings
        - _resolve_interpolations()
        
        # Feature log levels
        - _process_feature_log_levels(config)
        - _validate_feature_names()
        
        # Plugin management
        - discover_plugins(force_refresh)
        - get_plugin_metadata(plugin_name)
        - validate_plugin_config(plugin_name, config_data)
        - add_plugin(plugin_type, source_dir, plugin_name)
        - remove_plugin(plugin_type, plugin_name, protocol)
        - load_plugin_schemas(force_refresh)
        
        # Version discovery (from V2)
        - discover_available_versions(protocol)
        - get_version_configuration(impl_name, impl_type, protocol, version)
        
        # Configuration operations
        - validate_experiment_config(config)
        - validate_global_config(config)
        - validate_service_configuration(service_dict)
        - merge_configurations(*configs, strategy, conflict_resolution)
        - create_experiment_from_template(template_name, parameters, output_path)
        
        # Override management
        - add_configuration_override(key, value)
        - clear_configuration_overrides()
        - get_override_summary()
        
        # State and summary
        - get_configuration_summary()
        - get_statistics()
        - set_validation_mode(strict)
        
        # Caching
        - clear_cache()
        - _generate_cache_key()
        
        # Legacy compatibility
        - load_config() -> delegates to load_experiment_config
        - validate_config() -> returns boolean
        - get_plugins() -> delegates to discover_plugins
        - _check_needs_legacy_handling()
        
        # Context manager
        - __enter__(), __exit__()
        
      # Global instance management
      _config_manager = None
      get_config_manager() -> ConfigurationManager (lazy init)
      
      # ConfigLoader backward compatibility class
      CLASS ConfigLoader(ConfigurationManager):
        - list_plugin_parameters(plugin_name, plugin_type, protocol)
        - _auto_detect_plugin_type(plugin_name, protocol)
```

### 1.3 Unified Models
**ADD:**
```
- [ ] /panther/config/unified/models/__init__.py
      Export all models with exact legacy names for compatibility
      
- [ ] /panther/config/unified/models/base_model.py (150 lines)
      - BaseUnifiedModel(pydantic.BaseModel, UnifiedConfig)
      - Auto OmegaConf conversion in __init__
      - Validation hooks
      - Serialization methods
      
- [ ] /panther/config/unified/models/global_config.py (500 lines)
      # Main global config
      - GlobalConfig with version field
      - LoggingConfig:
        * level: LoggingLevel enum
        * format: str with default
        * enable_colors: bool = True
        * feature_levels: FeatureLogLevelsConfig
      - FeatureLogLevelsConfig (ALL fields from current):
        * docker_build, service_start, environment_setup
        * test_execution, metrics_collection, etc.
      - PathsConfig:
        * output_dir, log_dir, plugin_dir
        * Support interpolation: ${oc.env:PANTHER_OUTPUT,outputs}
      - DockerConfig:
        * build_docker_image: bool
        * user_mapping: DockerUserMappingConfig
      - DockerUserMappingConfig:
        * run_as_host_user: bool = False
        * custom_uid: Optional[int]
        * custom_gid: Optional[int]
        * user_name: str = "panther"
        * fallback_to_root: bool = True
      - ProgressConfig:
        * enable_progress_bar: bool = True
        * redirect_logging: bool = True
        * show_spinner: bool = True
      - FastFailConfig:
        * enabled: bool = True
        * test_level: bool = False
        * docker_build_failures: bool = True
        * service_start_failures: bool = True
        * ivy_compilation_failures: bool = False
        * timeout_cascade_threshold: int = 3
        * critical_only: bool = False
      
- [ ] /panther/config/unified/models/observer.py (400 lines)
      - ObserversConfig: Container for all observers
      - BaseObserverConfig:
        * enabled: bool
        * priority: int
      - LoggerObserverConfig(BaseObserverConfig):
        * log_level: str
        * enable_colors: bool
        * correlation_tracking: bool
      - MetricsObserverConfig(BaseObserverConfig):
        * collect_system_metrics: bool
        * publish_interval: int = 30
        * export_format: str = "json"
      - StorageObserverConfig(BaseObserverConfig):
        * storage_path: str
        * enable_compression: bool
        * retention_days: int
      - ExperimentObserverConfig(BaseObserverConfig):
        * track_timing: bool
        * track_steps: bool
        * generate_report: bool
      
- [ ] /panther/config/unified/models/experiment.py (300 lines)
      - ExperimentConfig:
        * tests: List[TestConfig]
        * metadata: Optional[ExperimentMetadata]
      - TestConfig:
        * name: str
        * description: Optional[str]
        * network_environment: NetworkEnvironmentConfig
        * execution_environment: List[ExecutionEnvironmentConfig]
        * services: Dict[str, ServiceConfig]
        * steps: StepsConfig
        * iterations: int = 1
        * timeout: Optional[int]
        * fast_fail_enabled: Optional[bool]
      - StepsConfig:
        * pre_commands: List[str]
        * wait: int
        * post_commands: List[str]
      
- [ ] /panther/config/unified/models/service.py (600 lines)
      - ServiceConfig:
        * implementation: ImplementationConfig
        * protocol: ProtocolConfig
        * network: Optional[NetworkConfig]
        * environment: Optional[Dict[str, str]]
        * timeout: int = 60
        * ports: List[str]
        * volumes: List[str]
        * generate_new_certificates: bool = False
        * Additional dynamic fields via __init__
      - ImplementationConfig:
        * name: str
        * type: ImplementationType (enum: IUT, TESTERS)
        * version: Optional[str]
        * Dynamic fields support (e.g., 'test' for panther_ivy)
      - ProtocolConfig:
        * name: str (quic, http, minip)
        * version: Optional[str] (dynamic, not enum)
        * role: ProtocolRole (server, client)
        * target: Optional[str] (for clients)
      - NetworkConfig:
        * interface: str
        * port: int
        * host: str
      
- [ ] /panther/config/unified/models/protocol.py (400 lines)
      - BaseProtocolConfig: Abstract base
      - ClientServerProtocolConfig:
        * All QUIC-specific fields
        * HTTP-specific fields
        * MiniP-specific fields
      - PeerToPeerProtocolConfig:
        * Peer discovery settings
        * Connection management
      - Version discovery integration
      
- [ ] /panther/config/unified/models/environment.py (500 lines)
      # Network Environments
      - NetworkEnvironmentConfig: Base class
      - DockerComposeConfig(NetworkEnvironmentConfig):
        * version: str = "3.8"
        * network_name: str
        * volumes: List[str]
        * environment: Dict[str, str]
      - LocalhostSingleContainerConfig(NetworkEnvironmentConfig):
        * container_name: str
        * working_dir: str
      - ShadowNsConfig(NetworkEnvironmentConfig):
        * topology: str
        * duration: str
        * seed: int
      
      # Execution Environments  
      - ExecutionEnvironmentConfig: Base class
      - StraceConfig(ExecutionEnvironmentConfig):
        * trace_calls: List[str]
        * output_format: str
      - GperfCpuConfig(ExecutionEnvironmentConfig):
        * sampling_frequency: int
        * output_file: str
      - GperfHeapConfig(ExecutionEnvironmentConfig):
        * profile_type: str
        * output_file: str
      - MemcheckConfig(ExecutionEnvironmentConfig):
        * leak_check: str = "full"
        * show_reachable: bool
      - HelgrindConfig(ExecutionEnvironmentConfig):
        * history_level: str = "full"
      - IterationsConfig(ExecutionEnvironmentConfig):
        * count: int = 10
```

### 1.4 Component Systems
**ADD:**
```
- [ ] /panther/config/unified/components/loaders.py (400 lines)
      - UnifiedYAMLLoader: Load with interpolation support
      - UnifiedVersionLoader: Dynamic version discovery
      - UnifiedCompositeLoader: Multiple sources
      - PluginConfigLoader: Load plugin-specific configs
      
- [ ] /panther/config/unified/components/validators.py (500 lines)
      - UnifiedValidator: Combines Pydantic + business rules
      - SchemaValidator: Validate against JSON schemas
      - BusinessRulesValidator: Port validation, timeout ranges
      - CompatibilityValidator: Check legacy format issues
      
- [ ] /panther/config/unified/components/builders.py (600 lines)
      - ExperimentBuilder: Build with auto-fix
      - ServiceBuilder: Preserve ALL fields
      - GlobalConfigBuilder: Environment variable resolution
      - BuilderContext: Track warnings and fixes
      
- [ ] /panther/config/unified/components/merger.py (300 lines)
      - UnifiedMerger: OmegaConf-based merging
      - MergeContext: Track conflicts
      - MergeStrategy enum: DEEP_MERGE, SHALLOW_MERGE, REPLACE
      - ConflictResolver: Handle merge conflicts
      
- [ ] /panther/config/unified/components/discovery.py (400 lines)
      - PluginDiscovery: Find all plugins
      - VersionDiscovery: Find version configs
      - SchemaDiscovery: Find plugin schemas
      - PluginMetadata handling
```

## Phase 2: Migration Infrastructure (Priority: HIGH)

### 2.1 Compatibility Layer
**ADD:**
```
- [ ] /panther/config/unified/compat/__init__.py
- [ ] /panther/config/unified/compat/dataclass_adapter.py (300 lines)
      - to_unified_model(dataclass_instance)
      - from_unified_model(unified_instance, target_class)
      - Handle all special cases (enums, nested, optional)
      
- [ ] /panther/config/unified/compat/import_interceptor.py (200 lines)
      - Register with sys.meta_path
      - Intercept old imports, return unified models
      - Log deprecation warnings
      
- [ ] /panther/config/unified/compat/field_mapper.py (250 lines)
      - Map legacy field names to new names
      - Handle type conversions
      - Track unmapped fields
```

### 2.2 Migration Tools
**ADD:**
```
- [ ] /panther/tools/config_migration/analyzer.py (400 lines)
      - Analyze codebase for config usage
      - Generate dependency graph
      - Identify migration order
      
- [ ] /panther/tools/config_migration/migrator.py (600 lines)
      - Convert YAML configs to new format
      - Update Python imports
      - Generate migration report
      
- [ ] /panther/tools/config_migration/validator.py (300 lines)
      - Validate migrated configs
      - Compare old vs new behavior
      - Performance benchmarks
```

## Phase 3: Core Integration Points (Priority: HIGH)

### 3.1 Main Config Module Updates
**MODIFY:**
```
- [ ] /panther/config/__init__.py (lines 1-100)
      OLD: Multiple config manager imports
      NEW: from panther.config.unified.manager import (
             ConfigurationManager as ConfigManager,
             ConfigLoader,
             get_config_manager
           )
           from panther.config.unified.models import *
           
           # Deprecation warnings for direct access
           import warnings
           if accessing old managers directly:
               warnings.warn("Use ConfigManager instead", DeprecationWarning)
```

### 3.2 Replace Current Managers
**MODIFY:**
```
- [ ] /panther/config/config_manager.py
      NEW: Simple delegation to unified.manager.ConfigurationManager
      
- [ ] Mark for removal: config_manager_enhanced.py (after Phase 8)
- [ ] Mark for removal: config_manager_refactored.py (after Phase 8)
- [ ] Mark for removal: config_manager_v2.py (after Phase 8)
```

## Phase 4: CLI and Entry Points (Priority: HIGH)

### 4.1 CLI Commands
**MODIFY:**
```
- [ ] /panther/cli/subcommands/run.py (lines 10, 157-198)
      OLD: from ...config.config_manager_enhanced import ConfigLoader
      NEW: from ...config import ConfigLoader
      
      Update Docker user mapping handling (lines 166-177)
      Update feature_levels handling (lines 192-195)
      
- [ ] /panther/cli/subcommands/config.py (lines 5-20)
      Update all config manager imports
      Add new commands for config migration
      
- [ ] /panther/cli/subcommands/plugins.py (lines 5-20)
      Update plugin discovery imports
      
- [ ] /panther/cli/interactive/experiment_designer.py
      Update to use unified models
      
- [ ] /panther/__main__.py
      Add migration detection
      Update config loading
```

## Phase 5: Core System Updates (Priority: HIGH)

### 5.1 Experiment Manager
**MODIFY:**
```
- [ ] /panther/core/experiment_manager.py (lines 20-21, 94-100)
      OLD: from panther.config.config_experiment_schema import ExperimentConfig
           from panther.config.config_global_schema import GlobalConfig
      NEW: from panther.config.unified.models import ExperimentConfig, GlobalConfig
      
      Update fast_fail config handling
      Update observer config creation
```

### 5.2 Test Case System
**MODIFY:**
```
- [ ] /panther/core/test_cases/test_case_impl.py
- [ ] /panther/core/test_cases/test_case_impl_refactored.py
- [ ] /panther/core/test_cases/test_case_impl_enhanced.py
- [ ] /panther/core/test_cases/base/test_case_base.py
      Update all config imports
      Update service config handling
      
- [ ] /panther/core/test_cases/mixins/service_management.py
      Update UnifiedImplementationConfig usage
```

### 5.3 Observer System
**MODIFY:**
```
- [ ] /panther/core/observer/factory/factory_config.py
      Replace ObserverConfig dataclasses
      
- [ ] /panther/core/observer/factory/factory_builders.py
      Update config usage
      
- [ ] /panther/core/observer/impl/*.py (all observers)
      Update constructor signatures
```

### 5.4 Command and Docker Systems
**MODIFY:**
```
- [ ] /panther/core/command_processor/command_builder.py
      Accept unified configs
      
- [ ] /panther/core/docker_builder/docker_builder.py
      Update user mapping config usage
      
- [ ] /panther/core/docker_builder/service_manager_docker_mixin.py
      Remove version enum usage
```

### 5.5 Template and Utils
**MODIFY:**
```
- [ ] /panther/core/template/template_renderer.py
      Use unified service configs
      
- [ ] /panther/core/utils/logger_factory.py
      Handle feature log levels
```

## Phase 6: Plugin System Updates (Priority: MEDIUM)

### 6.1 Plugin Manager
**MODIFY:**
```
- [ ] /panther/plugins/plugin_manager.py
      Update config handling
      Integrate version discovery
```

### 6.2 Service System
**MODIFY:**
```
- [ ] /panther/plugins/services/config_schema.py
      Replace with import from unified.models
      
- [ ] /panther/plugins/services/base/config_base.py
      Update base config classes
      
- [ ] /panther/plugins/services/services_interface.py
      Update interfaces
      
- [ ] /panther/plugins/services/iut/config_schema.py
      Update IUT-specific configs
```

### 6.3 Individual Implementations
**MODIFY:** (Each needs config import updates)
```
- [ ] /panther/plugins/services/iut/quic/picoquic/picoquic.py
- [ ] /panther/plugins/services/iut/quic/aioquic/aioquic.py
- [ ] /panther/plugins/services/iut/quic/quiche/quiche.py
- [ ] /panther/plugins/services/iut/quic/quinn/quinn.py
- [ ] /panther/plugins/services/iut/quic/lsquic/lsquic.py
- [ ] /panther/plugins/services/iut/quic/mvfst/mvfst.py
- [ ] /panther/plugins/services/iut/quic/quic_go/quic_go.py
- [ ] /panther/plugins/services/iut/quic/quant/quant.py
- [ ] /panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py
- [ ] /panther/plugins/services/iut/minip/ping_pong/ping_pong.py
- [ ] /panther/plugins/services/testers/panther_ivy/panther_ivy.py

And their config_schema.py files
```

### 6.4 Environment Plugins
**MODIFY:**
```
- [ ] /panther/plugins/environments/network_environment/config_schema.py
- [ ] /panther/plugins/environments/network_environment/docker_compose/docker_compose.py
- [ ] /panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py
- [ ] /panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py

- [ ] /panther/plugins/environments/execution_environment/config_schema.py
- [ ] /panther/plugins/environments/execution_environment/strace/strace.py
- [ ] /panther/plugins/environments/execution_environment/gperf_cpu/gperf_cpu.py
- [ ] /panther/plugins/environments/execution_environment/gperf_heap/gperf_heap.py
- [ ] /panther/plugins/environments/execution_environment/memcheck/memcheck.py
- [ ] /panther/plugins/environments/execution_environment/helgrind/helgrind.py
- [ ] /panther/plugins/environments/execution_environment/iterations/iterations.py

And their config_schema.py files
```

### 6.5 Protocol Plugins
**MODIFY:**
```
- [ ] /panther/plugins/protocols/config_schema.py
- [ ] /panther/plugins/protocols/client_server/config_schema.py
- [ ] /panther/plugins/protocols/client_server/quic/config_schema.py
- [ ] /panther/plugins/protocols/client_server/http/config_schema.py
- [ ] /panther/plugins/protocols/client_server/minip/config_schema.py
- [ ] /panther/plugins/protocols/peer_to_peer/config_schema.py
```

## Phase 7: Testing Updates (Priority: HIGH)

### 7.1 Create New Tests
**ADD:**
```
- [ ] /tests/unit/config/test_unified_manager.py
- [ ] /tests/unit/config/test_unified_models.py
- [ ] /tests/unit/config/test_unified_compatibility.py
- [ ] /tests/unit/config/test_unified_loaders.py
- [ ] /tests/unit/config/test_unified_validators.py
- [ ] /tests/integration/test_unified_config_loading.py
- [ ] /tests/integration/test_unified_migration.py
- [ ] /tests/e2e/test_unified_experiment_flow.py
```

### 7.2 Update Existing Tests
**MODIFY:**
```
- [ ] /tests/unit/test_core/test_experiment_manager.py
- [ ] /tests/unit/test_config/*.py
- [ ] /tests/integration/*.py
- [ ] /tests/config/*.py
- [ ] /tests/validate_*.py
      
      Update all config imports and usage
```

## Phase 8: Webapp and Tools (Priority: LOW)

**MODIFY:**
```
- [ ] /panther/webapp/web_app.py
- [ ] /panther/webapp/experiment_setup.py
- [ ] /panther/tools/plugins/environments/tutorials/tutorial.py
- [ ] /panther/tools/plugins/services/tutorials/tutorial.py
```

## Phase 9: Legacy Code Removal (Priority: LOW - AFTER ALL TESTS PASS)

### 9.1 Remove V2 System
**REMOVE:**
```
- [ ] /panther/config/config_manager_v2.py
- [ ] /panther/config/builders/ (entire directory)
- [ ] /panther/config/loaders/ (entire directory)
- [ ] /panther/config/mergers/ (entire directory)
- [ ] /panther/config/models/ (entire directory)
- [ ] /panther/config/validators/ (entire directory)
- [ ] /panther/config/registry/ (entire directory)
- [ ] /panther/config/managers/ (after extracting needed code)
```

### 9.2 Remove Legacy Schemas
**REMOVE:**
```
- [ ] /panther/config/config_experiment_schema.py
- [ ] /panther/config/config_global_schema.py
- [ ] /panther/config/config_observer_schema.py
```

### 9.3 Remove Old Managers
**REMOVE:**
```
- [ ] /panther/config/config_manager_enhanced.py
- [ ] /panther/config/config_manager_refactored.py
```

### 9.4 Remove Backup/Old Files
**REMOVE:**
```
- [ ] /dev/old/ (entire directory - 500+ files)
- [ ] /backup_originals/ (entire directory)
- [ ] All *_original.py files (~15 files)
- [ ] All *_refactored.py files (~20 files)
- [ ] All *_legacy.py files
```

## Phase 10: Documentation (Priority: MEDIUM)

**ADD/UPDATE:**
```
- [ ] /docs/configuration/unified_system.md
- [ ] /docs/configuration/migration_guide.md
- [ ] /docs/configuration/api_reference.md
- [ ] /CLAUDE.md - Update configuration section
- [ ] /README.md - Update examples
- [ ] Example configurations in experiment-config/
```

## Implementation Order with Dependencies

### Week 1: Foundation
1. Phase 0: Preparation (Day 1)
2. Phase 1.1-1.2: Base system and manager (Days 2-3)
3. Phase 1.3: Models (Days 4-5)

### Week 2: Core Integration
1. Phase 1.4: Components (Days 1-2)
2. Phase 2: Migration infrastructure (Days 3-4)
3. Phase 3-4: Integration points (Day 5)

### Week 3: System Updates
1. Phase 5: Core system updates (Days 1-3)
2. Phase 6.1-6.2: Plugin base updates (Days 4-5)

### Week 4: Plugin Updates
1. Phase 6.3-6.5: Individual plugins (Days 1-3)
2. Phase 7.1: New tests (Days 4-5)

### Week 5: Testing and Migration
1. Phase 7.2: Update existing tests (Days 1-2)
2. Phase 8: Webapp and tools (Day 3)
3. Run full test suite (Days 4-5)

### Week 6: Cleanup and Documentation
1. Phase 9: Legacy removal (Days 1-2)
2. Phase 10: Documentation (Days 3-4)
3. Final validation (Day 5)

## Critical Success Factors

### Must Preserve:
1. ALL constructor parameters from legacy managers
2. Environment variable mappings
3. Feature log levels with validation
4. Plugin discovery and management
5. Version discovery system
6. Caching mechanisms
7. Auto-fix functionality
8. Template support
9. Context manager behavior
10. Backward compatibility for all public APIs

### Performance Requirements:
1. Config loading < 100ms for typical experiment
2. Plugin discovery cached after first run
3. No memory leaks in long-running experiments
4. Efficient merge operations for large configs

### Validation Requirements:
1. All existing experiments must run unchanged
2. All tests must pass
3. No breaking changes to public APIs
4. Migration tool validates all conversions

## Risk Mitigation

### Rollback Strategy:
1. Full backup before each phase
2. Restoration scripts tested
3. Git tags at phase boundaries
4. Feature flags for gradual rollout

### Testing Strategy:
1. Unit tests for each new component
2. Integration tests for config loading
3. E2E tests for full experiments
4. Performance benchmarks
5. Memory profiling

### Migration Strategy:
1. Compatibility layer allows gradual migration
2. Import interceptor for transparent updates
3. Clear deprecation warnings
4. Migration tools for automated conversion

## Metrics

### Code Impact:
- Files to ADD: ~40 new files
- Files to MODIFY: ~200 files
- Files to REMOVE: ~75 files
- Total lines affected: ~25,000+

### Complexity Reduction:
- Config managers: 4 → 1
- Config schemas: 15+ → 10 (unified models)
- Duplicate definitions eliminated: ~50 classes
- Import statements simplified: ~500 locations

### Timeline:
- Total duration: 6 weeks
- Critical path: Weeks 1-3
- Buffer time: 1 week built into schedule

## Final Notes

This comprehensive TODO ensures:
1. No features are lost during migration
2. All configuration usages are updated
3. Complete backward compatibility
4. Clean, maintainable architecture
5. Single source of truth for configurations
6. Improved type safety and validation
7. Better error messages and debugging
8. Simplified plugin development