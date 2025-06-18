# Configuration System Migration TODO - Final Revised Version

## Overview
Complete migration from legacy dataclass-based configurations to THE unified Pydantic-OmegaConf configuration system.
Direct modification approach - no compatibility layers, update legacy code directly with tracking.

## Key Design Decisions
1. **No backward compatibility classes** - Modify existing code directly
2. **Mixin-based architecture** - ConfigurationManager split into focused mixins
3. **Direct legacy updates** - Change imports and usage in-place
4. **Modification tracking** - Document each change with [MODIFIED] tags

## Phase 1: Create Core Configuration Infrastructure (Priority: CRITICAL)

### 1.1 Base System
**ADD:**
```
- [ ] /panther/config/core/__init__.py
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

## Phase 2: Direct Legacy Code Updates (Priority: HIGH)

### 2.1 Update config_manager.py directly
**MODIFY:**
```
- [ ] /panther/config/config_manager.py [MODIFIED: Complete replacement]
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

### 2.3 Update __init__.py directly
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

## Phase 3: Direct Plugin Updates (Priority: HIGH)

### 3.1 Update plugin config schemas directly
**MODIFY:**
```
- [ ] /panther/plugins/services/config_schema.py [MODIFIED: Use new models]
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

## Phase 4: Update Core Components Directly (Priority: HIGH)

### 4.1 Update imports in core files
**MODIFY:**
```
- [ ] /panther/core/experiment_manager.py [MODIFIED: Lines 20-21]
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

## Phase 5: Component Building Order

### 5.1 Core Models First
**BUILD ORDER:**
```
1. BaseConfig and mixins
2. Global config models
3. Experiment config models
4. Service config models
5. Observer config models
6. Environment config models
7. Protocol config models
```

### 5.2 Manager Components
**BUILD ORDER:**
```
1. Config loading mixin
2. Environment handling mixin
3. Plugin management mixin
4. Version discovery mixin
5. Validation operations mixin
6. Config operations mixin
7. Caching mixin
8. Logging features mixin
9. State management mixin
10. ConfigurationManager combining all mixins
```

### 5.3 Supporting Components
**BUILD ORDER:**
```
1. Loaders (YAML, Version, Composite)
2. Validators (Schema, Business Rules)
3. Builders (Experiment, Service)
4. Merger
5. Discovery components
```

## Modification Tracking Legend

**[MODIFIED]** tags indicate:
- **[MODIFIED: Complete replacement]** - Entire file content replaced
- **[MODIFIED: Lines X-Y]** - Specific lines changed
- **[MODIFIED: Use new models]** - Changed to import/use new model classes
- **[MODIFIED: Redirect to new system]** - Legacy file redirects to new implementation
- **[MODIFIED: Each file]** - Pattern applied to multiple files

## Key Benefits of This Approach

1. **No compatibility layers** - Cleaner, simpler code
2. **Mixin architecture** - Better separation of concerns
3. **Direct updates** - No confusion about which system to use
4. **Clear tracking** - Every modification documented
5. **Gradual migration** - Can update files incrementally

## Testing Strategy for Direct Updates

After each modification:
1. Run unit tests for modified component
2. Run integration tests for affected systems
3. Verify no import errors
4. Check that behavior remains identical

## Rollback Strategy

Since we're modifying files directly:
1. Git commit before each phase
2. Tag each successful phase
3. Can revert individual files if needed
4. Backup created in Phase 0 as ultimate fallback