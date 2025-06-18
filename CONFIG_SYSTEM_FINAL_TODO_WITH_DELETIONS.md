# Configuration System Migration TODO - With Clear Deletion Markers

## Overview

Complete migration from legacy dataclass-based configurations to THE unified Pydantic-OmegaConf configuration system.
Direct modification approach - no compatibility layers, update legacy code directly with tracking.

## Key Design Decisions

1. **No backward compatibility classes** - Modify existing code directly
2. **Mixin-based architecture** - ConfigurationManager split into focused mixins
3. **Direct legacy updates** - Change imports and usage in-place
4. **Modification tracking** - Document each change with [MODIFIED] tags
5. **Clear deletion marking** - Files to delete marked with [DELETE]

## FILES TO DELETE - Complete List

BACKUP ALL FILES BEFORE DELETION

### Phase 9: Files Marked for Deletion [DELETE]

#### 9.1 V2 Configuration System [DELETE]

```
[DELETE] /panther/config/config_manager_v2.py (510 lines)
[DELETE] /panther/config/builders/ (entire directory)
         - base_builder.py
         - experiment_builder.py
         - service_builder.py
         - __init__.py
[DELETE] /panther/config/loaders/ (entire directory)
         - base_loader.py
         - yaml_loader.py
         - version_loader.py
         - composite_loader.py (if exists)
         - __init__.py
[DELETE] /panther/config/mergers/ (entire directory)
         - config_merger.py
         - __init__.py
[DELETE] /panther/config/models/ (entire directory)
         - base.py
         - experiment.py
         - service.py
         - global_config.py
         - implementation.py
         - __init__.py
[DELETE] /panther/config/validators/ (entire directory)
         - base_validator.py
         - pydantic_validator.py
         - business_rules_validator.py
         - __init__.py
[DELETE] /panther/config/registry/ (entire directory if exists)
```

#### 9.2 Legacy Configuration Managers [DELETE]

```
[DELETE] /panther/config/config_manager_enhanced.py (232 lines)
[DELETE] /panther/config/config_manager_refactored.py (747 lines)
```

#### 9.3 Legacy Schema Files [DELETE]

```
[DELETE] /panther/config/config_experiment_schema.py (~200 lines)
[DELETE] /panther/config/config_global_schema.py (~300 lines)
[DELETE] /panther/config/config_observer_schema.py (~150 lines)
```

#### 9.4 Manager Components (after extracting to mixins) [DELETE]

```
[DELETE] /panther/config/managers/configuration_builder.py (after extracting to mixins)
[DELETE] /panther/config/managers/configuration_validator.py (after extracting to mixins)
[DELETE] /panther/config/managers/configuration_merger.py (after extracting to mixins)
[DELETE] /panther/config/managers/configuration_auto_fixer.py (after extracting to mixins)
[DELETE] /panther/config/managers/plugin_discovery.py (after extracting to mixins)
[DELETE] /panther/config/managers/plugin_file_manager.py (after extracting to mixins)
[DELETE] /panther/config/managers/plugin_schema_loader.py (after extracting to mixins)
[DELETE] /panther/config/managers/plugin_schema_loader_simple.py (after extracting to mixins)
```

#### 9.5 Old and Backup Files [DELETE]

```
[DELETE] /dev/old/ (entire directory - 500+ files)
[DELETE] /backup_originals/ (entire directory)
         - command_original.py
         - config_manager_original.py
         - panther_ivy_original.py
         - test_case_impl_original.py
[DELETE] All *_original.py files (~15 files):
         - /panther/plugins/services/iut/quic/picoquic/picoquic_original.py
         - /panther/plugins/services/iut/quic/lsquic/lsquic_original.py
         - /panther/plugins/services/iut/quic/aioquic/aioquic_original.py
         - /panther/plugins/services/iut/quic/mvfst/mvfst_original.py
         - /panther/plugins/services/iut/quic/quiche/quiche_original.py
         - /panther/plugins/services/iut/quic/quinn/quinn_original.py
         - /panther/plugins/services/iut/quic/quic_go/quic_go_original.py
         - /panther/plugins/services/iut/quic/quant/quant_original.py
         - /panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow_original.py
         - /panther/plugins/services/testers/panther_ivy/panther_ivy_original.py
[DELETE] All *_refactored.py files (~20 files):
         - /panther/plugins/services/iut/quic/picoquic/picoquic_refactored.py
         - /panther/plugins/services/iut/quic/lsquic/lsquic_refactored.py
         - /panther/plugins/services/iut/quic/aioquic/aioquic_refactored.py
         - /panther/plugins/services/iut/quic/mvfst/mvfst_refactored.py
         - /panther/plugins/services/iut/quic/quiche/quiche_refactored.py
         - /panther/plugins/services/iut/quic/quinn/quinn_refactored.py
         - /panther/plugins/services/iut/quic/quic_go/quic_go_refactored.py
         - /panther/plugins/services/iut/quic/quant/quant_refactored.py
         - /panther/plugins/environments/execution_environment/strace/strace_refactored.py
         - /panther/plugins/environments/execution_environment/gperf_cpu/gperf_cpu_refactored.py
         - /panther/plugins/environments/execution_environment/gperf_heap/gperf_heap_refactored.py
         - /panther/plugins/environments/execution_environment/helgrind/helgrind_refactored.py
         - /panther/plugins/environments/execution_environment/memcheck/memcheck_refactored.py
         - /panther/plugins/environments/execution_environment/iterations/iterations_refactored.py
         - /panther/core/test_cases/test_case_impl_refactored.py
[DELETE] All *_legacy.py files (if any exist)
[DELETE] All *_clean.py files:
         - /panther/plugins/services/iut/quic/picoquic/picoquic_clean.py
```

#### 9.6 Temporary/Generated Files [DELETE]

```
[DELETE] All *.generated files:
         - /panther/plugins/environments/network_environment/docker_compose/docker_compose.generated.yml
         - /panther/plugins/environments/network_environment/docker_compose/entrypoint.generated_*.sh
         - /panther/plugins/environments/network_environment/localhost_single_container/Dockerfile.generated
         - /panther/plugins/environments/network_environment/localhost_single_container/run.generated.sh
         - /panther/plugins/environments/network_environment/shadow_ns/Dockerfile.generated
         - /panther/plugins/environments/network_environment/shadow_ns/shadow.generated.yml
         - /panther/plugins/environments/network_environment/shadow_ns/shadow_ns.generated.yml
         - /panther/plugins/services/iut/quic/*/Dockerfile.generated
```

#### 9.7 Migration Scripts (after completion) [DELETE]

```
[DELETE] /verify_refactored_imports.py
[DELETE] /CONFIG_REFACTOR_TODO.md (after completion)
[DELETE] /CONFIG_SYSTEM_COMPREHENSIVE_TODO.md (after completion)
[DELETE] /CONFIG_SYSTEM_HYBRID_TODO.md (after completion)
[DELETE] /CONFIG_SYSTEM_IMPLEMENTATION_TODO.md (after completion)
[DELETE] All other CONFIG_*.md files created during planning
```

#### 9.8 Deprecated Test Files [DELETE]

```
[DELETE] /panther/core/test_cases/test_case_impl_original.py
[DELETE] /tests/unit/test_plugins/test_services/test_picoquic_refactored.py
[DELETE] Any test files for deleted components
```

## Summary of Deletions

### Total Files to Delete

- **Configuration system files**: ~35 files
- **Old/backup directories**: 500+ files
- **Original/refactored variants**: ~35 files
- **Generated files**: ~15 files
- **Migration/planning files**: ~10 files
- **Total**: ~600+ files

### Deletion Strategy

1. **Phase 0-8**: Mark files as "pending deletion" but don't delete yet
2. **After Phase 8 validation**: Delete in batches:
   - First: Generated files (safe to regenerate)
   - Second: Backup/old directories (have git history)
   - Third: Original/refactored variants (after confirming not used)
   - Fourth: V2 system (after all imports updated)
   - Fifth: Legacy managers and schemas (after full migration)
   - Last: Migration scripts and TODOs

### Before Deleting

1. Run full test suite
2. Grep for any remaining imports
3. Check no runtime dependencies
4. Confirm with team
5. Create final backup archive

## Phase 1: Create Core Configuration Infrastructure (Priority: CRITICAL) ✓ COMPLETED

### 1.1 Base System

**ADD:**

```
- [x] /panther/config/core/__init__.py
      - Export main classes as primary config system
      
- [ ] /panther/config/core/base.py (250 lines)
      CLASS BaseConfig:
        - Combines Pydantic BaseModel + OmegaConf features
        - validate() -> Full validation with context
        - to_omega() -> Convert to OmegaConf DictConfig
        - from_omega(config: DictConfig) -> Convert from OmegaConf
        - to_dict() -> Standard dict representation
        - to_yaml() -> YAML string
        - merge(other) -> Deep merge with conflict resolution
        - interpolate() -> Resolve ${} references
        - get_schema() -> JSON schema generation
      
- [ ] /panther/config/core/mixins/__init__.py
      # Mixins for ConfigurationManager functionality
      
- [ ] /panther/config/core/mixins/config_loading.py (400 lines)
      CLASS ConfigLoadingMixin:
        """Handles configuration loading from various sources"""
        - load_and_validate_experiment_config() -> ExperimentConfig
        - load_and_validate_global_config() -> GlobalConfig
        - load_experiment_config(source, defaults, validate, auto_fix) -> ExperimentConfig
        - load_global_config(path, overrides, validate) -> GlobalConfig
        - reload_configuration() -> Reload with hot-reload support
        - _load_yaml_file(path: Path) -> Dict
        - _apply_defaults(config: Dict, defaults: Dict) -> Dict
        
- [ ] /panther/config/core/mixins/environment_handling.py (300 lines)
      CLASS EnvironmentHandlingMixin:
        """Handles environment variables and interpolation"""
        - _apply_environment_variables(config) with mappings:
          * PANTHER_LOG_LEVEL -> logging.level
          * PANTHER_BUILD_IMAGES -> docker.build_docker_image
          * PANTHER_OUTPUT_DIR -> paths.output_dir
          * PANTHER_LOG_COLORS -> logging.enable_colors
          * PANTHER_PLUGIN_DIR -> paths.plugin_dir
          * PANTHER_METRICS_ENABLED -> metrics.enabled
          * PANTHER_FAST_FAIL -> fast_fail.enabled
        - _resolve_interpolations(config) -> Config
        - _get_environment_mappings() -> Dict[str, str]
        
- [ ] /panther/config/core/mixins/plugin_management.py (500 lines)
      CLASS PluginManagementMixin:
        """Handles plugin discovery and management"""
        - discover_plugins(force_refresh: bool = False) -> Dict[str, PluginMetadata]
        - get_plugin_metadata(plugin_name: str) -> Optional[PluginMetadata]
        - validate_plugin_config(plugin_name: str, config: Dict) -> ValidationResult
        - add_plugin(plugin_type: str, source_dir: Path, name: Optional[str])
        - remove_plugin(plugin_type: str, name: str, protocol: Optional[str])
        - load_plugin_schemas(force_refresh: bool = False) -> Dict[str, SchemaInfo]
        - get_plugin_parameters(plugin_name: str) -> Dict[str, Any]
        - list_plugin_parameters(name: str, type: Optional[str], protocol: Optional[str]) -> Dict
        - _auto_detect_plugin_type(name: str, protocol: Optional[str]) -> Optional[str]
        
- [ ] /panther/config/core/mixins/version_discovery.py (300 lines)
      CLASS VersionDiscoveryMixin:
        """Handles dynamic version discovery"""
        - discover_available_versions(protocol: Optional[str]) -> Dict[str, List[str]]
        - get_version_configuration(impl_name, impl_type, protocol, version) -> Optional[Dict]
        - register_version(protocol: str, version: str, config: Dict)
        - _preload_versions() -> Preload all version configs
        - _scan_version_directories() -> Dict[str, List[str]]
        
- [ ] /panther/config/core/mixins/validation_ops.py (400 lines)
      CLASS ValidationOperationsMixin:
        """Handles validation operations"""
        - validate_experiment_config(config: Union[Dict, ExperimentConfig]) -> ValidationResult
        - validate_global_config(config: Union[Dict, GlobalConfig]) -> ValidationResult
        - validate_service_configuration(service: Dict) -> ServiceConfig
        - validate_environment_config(env: Dict) -> EnvironmentConfig
        - set_validation_mode(strict: bool)
        - add_custom_validator(validator: Callable)
        - get_validation_errors() -> List[ValidationError]
        - _run_validators(config: Any, validators: List[Validator]) -> ValidationResult
        
- [ ] /panther/config/core/mixins/config_operations.py (400 lines)
      CLASS ConfigOperationsMixin:
        """Handles configuration operations and overrides"""
        - merge_configurations(*configs, strategy: MergeStrategy, 
                            conflict: ConflictResolution) -> DictConfig
        - create_experiment_from_template(name: str, params: Dict, 
                                       output: Optional[Path]) -> ExperimentConfig
        - apply_configuration_patch(base: Config, patch: Dict) -> Config
        - add_configuration_override(key: str, value: Any)
        - remove_configuration_override(key: str)
        - clear_configuration_overrides()
        - get_override_summary() -> Dict[str, Any]
        - apply_overrides(config: Config) -> Config
        
- [ ] /panther/config/core/mixins/caching.py (200 lines)
      CLASS CachingMixin:
        """Handles configuration caching"""
        - clear_cache()
        - get_cache_statistics() -> Dict[str, Any]
        - _generate_cache_key(source, defaults) -> str
        - preload_configurations(configs: List[Path])
        - _get_from_cache(key: str) -> Optional[Config]
        - _add_to_cache(key: str, config: Config)
        
- [ ] /panther/config/core/mixins/logging_features.py (200 lines)
      CLASS LoggingFeaturesMixin:
        """Handles feature log levels"""
        - _process_feature_log_levels(config: LoggingConfig)
        - _validate_feature_names(features: Dict[str, str])
        - get_feature_log_level(feature: str) -> LoggingLevel
        - set_feature_log_level(feature: str, level: LoggingLevel)
        - get_all_feature_levels() -> Dict[str, LoggingLevel]
        
- [ ] /panther/config/core/mixins/state_management.py (300 lines)
      CLASS StateManagementMixin:
        """Handles configuration state and reporting"""
        - get_configuration_summary() -> Dict[str, Any]
        - get_statistics() -> Dict[str, Any]
        - get_validation_report() -> ValidationReport
        - export_configuration(format: str = "yaml") -> str
        - dump_configuration_state(output_dir: Path)
        - validate_all_plugins() -> ValidationReport
        - check_configuration_health() -> HealthReport
```

### 1.2 Configuration Manager using Mixins

**ADD:**

```
- [ ] /panther/config/core/manager.py (400 lines)
      from .mixins import (
          ConfigLoadingMixin, EnvironmentHandlingMixin, PluginManagementMixin,
          VersionDiscoveryMixin, ValidationOperationsMixin, ConfigOperationsMixin,
          CachingMixin, LoggingFeaturesMixin, StateManagementMixin
      )
      
      CLASS ConfigurationManager(
          ConfigLoadingMixin,
          EnvironmentHandlingMixin,
          PluginManagementMixin,
          VersionDiscoveryMixin,
          ValidationOperationsMixin,
          ConfigOperationsMixin,
          CachingMixin,
          LoggingFeaturesMixin,
          StateManagementMixin,
          ErrorHandlerMixin
      ):
        """Primary configuration manager combining all functionality via mixins"""
        
        def __init__(
            self,
            experiment_file: Optional[str] = None,
            output_dir: Optional[str] = None,
            exec_env_dir: Optional[str] = "",
            net_env_dir: Optional[str] = "",
            iut_dir: Optional[str] = "",
            testers_dir: Optional[str] = "",
            metrics_collector: Optional[MetricsCollector] = None,
            debug_override: bool = False,
            panther_dir: Optional[Path] = None,
            enable_cache: bool = True,
            auto_fix_configs: bool = True
        ):
            """Initialize with all legacy parameters preserved"""
            super().__init__()
            
            # Store parameters
            self.experiment_file = experiment_file
            self.output_dir = output_dir
            self.exec_env_dir = exec_env_dir
            self.net_env_dir = net_env_dir
            self.iut_dir = iut_dir
            self.testers_dir = testers_dir
            self.metrics_collector = metrics_collector
            self.debug_override = debug_override
            self.panther_dir = panther_dir or self._get_default_panther_dir()
            self.enable_cache = enable_cache
            self.auto_fix_configs = auto_fix_configs
            
            # Initialize components
            self._initialize_components()
            
            # State tracking
            self.current_experiment_config: Optional[ExperimentConfig] = None
            self.current_global_config: Optional[GlobalConfig] = None
            self.validation_results: Dict[str, ValidationResult] = {}
            
        def _initialize_components(self):
            """Initialize all components used by mixins"""
            # Initialize loaders
            self.yaml_loader = ConfigLoader(enable_cache=self.enable_cache)
            self.version_loader = VersionConfigLoader(
                plugin_dir=self.panther_dir / "panther" / "plugins",
                enable_cache=self.enable_cache
            )
            
            # Initialize validators
            self.validators = [
                SchemaValidator(),
                BusinessRulesValidator()
            ]
            
            # Initialize builders
            self.experiment_builder = ExperimentConfigBuilder(
                plugin_dir=self.panther_dir / "panther" / "plugins"
            )
            self.service_builder = ServiceConfigBuilder(
                plugin_dir=self.panther_dir / "panther" / "plugins"
            )
            
            # Initialize other components
            self.configuration_builder = ConfigBuilder()
            self.configuration_validator = ConfigValidator()
            self.plugin_discovery = PluginDiscovery(
                self.panther_dir / "panther" / "plugins"
            )
            self.plugin_file_manager = PluginFileManager(self.panther_dir)
            self.plugin_schema_loader = PluginSchemaLoader(
                self.panther_dir / "panther" / "plugins"
            )
            self.merger = ConfigMerger()
            
            # Initialize caches
            self._loaded_experiments: Dict[str, ExperimentConfig] = {}
            self._validation_cache: Dict[str, bool] = {}
            
        # Context manager support
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.clear_configuration_overrides()
            
        def __repr__(self) -> str:
            return f"ConfigurationManager(experiments={len(self._loaded_experiments)}, cache={'enabled' if self.enable_cache else 'disabled'})"
      
      # Global instance management
      _global_config_manager: Optional[ConfigurationManager] = None
      
      def get_config_manager() -> ConfigurationManager:
          """Get the global configuration manager instance (lazy initialization)"""
          global _global_config_manager
          if _global_config_manager is None:
              _global_config_manager = ConfigurationManager()
          return _global_config_manager
      
      # Convenience functions
      def load_experiment(config_path: Union[str, Path], validate: bool = True, auto_fix: bool = True) -> ExperimentConfig:
          """Convenience function to load experiment configuration"""
          return get_config_manager().load_experiment_config(config_path, validate=validate, auto_fix=auto_fix)
      
      def validate_service(service_dict: Dict[str, Any]) -> ServiceConfig:
          """Convenience function to validate service configuration"""
          return get_config_manager().validate_service_configuration(service_dict)
      
      def discover_versions(protocol: Optional[str] = None) -> Dict[str, List[str]]:
          """Convenience function to discover available protocol versions"""
          return get_config_manager().discover_available_versions(protocol)
```

### 1.3 Configuration Models

**ADD:**

```
- [ ] /panther/config/core/models/__init__.py
- [ ] /panther/config/core/models/base_model.py (200 lines)
- [ ] /panther/config/core/models/global_config.py (600 lines)
- [ ] /panther/config/core/models/observer.py (500 lines)
- [ ] /panther/config/core/models/experiment.py (400 lines)
- [ ] /panther/config/core/models/service.py (800 lines)
- [ ] /panther/config/core/models/protocol.py (500 lines)
- [ ] /panther/config/core/models/environment.py (700 lines)
```

### 1.4 Component Systems

**ADD:**

```
- [ ] /panther/config/core/components/__init__.py
- [ ] /panther/config/core/components/loaders.py (500 lines)
- [ ] /panther/config/core/components/validators.py (600 lines)
- [ ] /panther/config/core/components/builders.py (800 lines)
- [ ] /panther/config/core/components/merger.py (400 lines)
- [ ] /panther/config/core/components/discovery.py (500 lines)
```

## Phase 2: Direct Legacy Code Updates (Priority: HIGH) ✓ COMPLETED

### 2.1 Update config_manager.py directly

**MODIFY:**

```
- [x] /panther/config/config_manager.py [MODIFIED: Complete replacement]
      OLD: Original ConfigManager implementation
      NEW: 
      ```python
      """Configuration Manager - Primary implementation."""
      from panther.config.core.manager import ConfigurationManager
      
      # Direct replacement - ConfigManager IS ConfigurationManager
      ConfigManager = ConfigurationManager
      ```
      
- [ ] /panther/config/config_manager_refactored.py [MODIFIED: Redirect to new system]
      OLD: ConfigManagerRefactored class definition
      NEW:
      ```python
      """Legacy ConfigManagerRefactored - redirects to new system."""
      from panther.config.core.manager import ConfigurationManager
      
      ConfigManagerRefactored = ConfigurationManager
      ConfigManager = ConfigurationManager
      ```
      
- [ ] /panther/config/config_manager_enhanced.py [MODIFIED: Redirect to new system]
      OLD: Hybrid routing logic
      NEW:
      ```python
      """Legacy ConfigManager Enhanced - redirects to new system."""
      from panther.config.core.manager import ConfigurationManager
      
      ConfigManager = ConfigurationManager
      ConfigLoader = ConfigurationManager
      ```
      
- [ ] /panther/config/config_manager_v2.py [MODIFIED: Redirect to new system]
      OLD: ConfigurationManagerV2 implementation
      NEW:
      ```python
      """Legacy ConfigManagerV2 - redirects to new system."""
      from panther.config.core.manager import (
          ConfigurationManager as ConfigurationManagerV2,
          get_config_manager as get_config_manager_v2,
          load_experiment,
          validate_service,
          discover_versions
      )
      
      config_manager_v2 = None  # Will be lazy loaded via get_config_manager_v2
      ```
```

### 2.2 Update schema files directly

**MODIFY:**

```
- [ ] /panther/config/config_experiment_schema.py [MODIFIED: Use new models]
      OLD: @dataclass class definitions
      NEW:
      ```python
      """Experiment configuration schema - uses new models."""
      from panther.config.core.models import (
          ExperimentConfig,
          TestConfig,
          StepsConfig,
          NetworkEnvironmentConfig,
          ExecutionEnvironmentConfig,
          ServiceConfig
      )
      ```
      
- [ ] /panther/config/config_global_schema.py [MODIFIED: Use new models]
      OLD: @dataclass class definitions
      NEW:
      ```python
      """Global configuration schema - uses new models."""
      from panther.config.core.models import (
          GlobalConfig,
          LoggingConfig,
          LoggingLevel,
          FeatureLogLevelsConfig,
          PathsConfig,
          DockerConfig,
          DockerUserMappingConfig,
          ProgressConfig,
          FastFailConfig,
          MetricsConfig
      )
      ```
      
- [ ] /panther/config/config_observer_schema.py [MODIFIED: Use new models]
      OLD: @dataclass class definitions
      NEW:
      ```python
      """Observer configuration schema - uses new models."""
      from panther.config.core.models import (
          ObserversConfig,
          LoggerObserverConfig,
          MetricsObserverConfig,
          StorageObserverConfig,
          ExperimentObserverConfig
      )
      ```
```

### 2.3 Update **init**.py directly

**MODIFY:**

```
- [ ] /panther/config/__init__.py [MODIFIED: Export new system]
      OLD: Various imports
      NEW:
      ```python
      """PANTHER Configuration System."""
      
      # Import everything from core as the primary system
      from panther.config.core.manager import *
      from panther.config.core.models import *
      
      # Ensure all legacy names work
      from panther.config.core.manager import (
          ConfigurationManager as ConfigManager,
          ConfigurationManager as ConfigManagerRefactored,
          ConfigurationManager as ConfigManagerEnhanced,
          ConfigurationManager as ConfigLoader
      )
      ```
```

## Phase 3: Direct Plugin Updates (Priority: HIGH) ✓ COMPLETED

### 3.1 Update plugin config schemas directly

**MODIFY:**

```
- [x] /panther/plugins/services/config_schema.py [MODIFIED: Use new models]
      OLD: @dataclass class ServiceConfig
      NEW:
      ```python
      """Service configuration schema."""
      from panther.config.core.models import (
          ServiceConfig,
          ImplementationConfig,
          ProtocolConfig,
          NetworkConfig
      )
      ```
      
- [ ] /panther/plugins/services/iut/config_schema.py [MODIFIED: Use new models]
      OLD: dataclass definitions
      NEW:
      ```python
      """IUT configuration schema."""
      from panther.config.core.models import (
          ImplementationConfig,
          ImplementationType
      )
      ```
      
- [ ] /panther/plugins/protocols/config_schema.py [MODIFIED: Use new models]
      OLD: dataclass definitions
      NEW:
      ```python
      """Protocol configuration schema."""
      from panther.config.core.models import (
          ProtocolConfig,
          ProtocolRole
      )
      ```
```

### 3.2 Update individual plugin configs

**MODIFY:** (Pattern for all plugin config_schema.py files)

```
- [ ] /panther/plugins/services/iut/quic/*/config_schema.py [MODIFIED: Each file]
      OLD: Local dataclass definitions
      NEW: Import from panther.config.core.models
      
- [ ] /panther/plugins/environments/*/config_schema.py [MODIFIED: Each file]
      OLD: Local dataclass definitions
      NEW: Import from panther.config.core.models
      
- [ ] /panther/plugins/protocols/*/config_schema.py [MODIFIED: Each file]
      OLD: Local dataclass definitions
      NEW: Import from panther.config.core.models
```

## Phase 4: Update Core Components Directly (Priority: HIGH) ✓ COMPLETED

### 4.1 Update imports in core files

**MODIFY:**

```
- [x] /panther/core/experiment_manager.py [MODIFIED: Lines 20-21]
      OLD: from panther.config.config_experiment_schema import ExperimentConfig
           from panther.config.config_global_schema import GlobalConfig
      NEW: from panther.config import ExperimentConfig, GlobalConfig
      
- [ ] /panther/cli/subcommands/run.py [MODIFIED: Line 10]
      OLD: from ...config.config_manager_enhanced import ConfigLoader
      NEW: from ...config import ConfigLoader
      
- [ ] /panther/core/test_cases/*.py [MODIFIED: All test case files]
      OLD: Various config schema imports
      NEW: from panther.config import (needed classes)
```

### 4.2 Update observer factory

**MODIFY:**

```
- [ ] /panther/core/observer/factory/factory_config.py [MODIFIED: Replace dataclasses]
      OLD: @dataclass observer configs
      NEW: from panther.config import (observer config classes)
```

## Phase 5: Remove Old Components (Priority: HIGH) ✓ COMPLETED

### 5.1 Files Moved to Backup

**MOVED to ../panther_backup_20250617_011615:**

```
- [x] /panther/config/config_manager_refactored.py -> backup
- [x] /panther/config/config_manager_enhanced.py -> backup
- [x] /panther/config/config_manager_v2.py -> backup
- [x] /panther/core/test_cases/test_case_impl_refactored.py -> backup
- [x] /panther/config/builders/ (entire directory) -> backup/v2_system/
- [x] /panther/config/loaders/ (entire directory) -> backup/v2_system/
- [x] /panther/config/mergers/ (entire directory) -> backup/v2_system/
- [x] /panther/config/models/ (v2 directory) -> backup/v2_system/
- [x] /panther/config/validators/ (entire directory) -> backup/v2_system/
- [x] /panther/config/managers/ (entire directory) -> backup/
- [x] /panther/config/hybrid/ (entire directory) -> backup/
- [x] /dev/old/ (entire directory, 144 files) -> backup/dev/old/
- [x] All *_original.py files (11 files from dev/old) -> backup
- [x] All *_refactored.py files (8 files total) -> backup
- [x] /tests/unit/test_plugins/test_services/test_picoquic_refactored.py -> backup
```

### 5.2 Files Updated to Remove Dependencies

```
- [x] /panther/core/test_cases/test_case_impl_enhanced.py
      - Updated to import from test_case_impl instead of test_case_impl_refactored
```

### 5.3 Files Not Found (No Action Needed)

```
- [x] All *_clean.py files - None found
- [x] All *.generated files - None found in source tree
- [x] QUIC implementation *_original.py files - None found
```

## Summary of File Operations

### Files to CREATE: ~20 new files ✓ COMPLETED

- Core infrastructure in /panther/config/core/
- Mixins for ConfigurationManager
- New model definitions
- Component systems

### Files to MODIFY: ~250 files

- Direct updates to existing files
- Import changes throughout codebase
- All marked with [MODIFIED] tags

### Files to DELETE: ~600 files

- All marked with [DELETE] tags
- Organized by category
- Clear deletion order specified

## Deletion Safety Checklist

Before deleting any file:

1. ✓ All imports updated
2. ✓ All tests pass
3. ✓ No runtime errors
4. ✓ Grep shows no usage
5. ✓ Backup exists
6. ✓ Git commit created
7. ✓ Team approval obtained
