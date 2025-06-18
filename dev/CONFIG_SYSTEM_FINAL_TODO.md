# Configuration System Migration TODO - Final Version

## Overview
Complete migration from legacy dataclass-based configurations to THE unified Pydantic-OmegaConf configuration system.
This is not a "hybrid" approach - this will be the primary configuration system going forward.

## Legacy Features to Preserve (Complete Analysis)

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

### Additional Components Found:
1. **Metrics System**: MetricsCollector, MetricsExporter, MetricsReporter, ResourceMonitor
2. **Results System**: ResultsManager, StorageHandler (local and remote)
3. **Output System**: OutputCollector, OutputAggregator, output environment mixins
4. **Reporting**: ExperimentReporter with JSON/Markdown generation
5. **Docker Registry**: Docker image management and caching
6. **Command Utils**: Shell command validation and escaping
7. **Validation Utils**: Path validation, port validation, name validation
8. **Plugin Components**: PluginManifest, PluginCatalog, PluginConfigResolver
9. **Interactive CLI**: ExperimentDesigner, ValidationHelper, Builders
10. **Web Components**: WebApp experiment setup and configuration

## Phase 0: Preparation and Analysis (Priority: CRITICAL)

### 0.1 Create Comprehensive Backup
**EXECUTE:**
```
- [ ] Create .backup/config_system_final_20250616/
- [ ] Backup ALL config-related files:
      - /panther/config/ (entire directory)
      - /panther/plugins/**/config_schema.py (all plugin configs)
      - /panther/core/observer/factory/factory_config.py
      - /panther/core/metrics/ (metrics configurations)
      - /panther/core/reporting/ (report configurations)
      - All test files using configs
- [ ] Create restoration script with checksums
- [ ] Document current inheritance hierarchy
```

### 0.2 Dependency Analysis
**CREATE:**
```
- [ ] /panther/tools/config_migration/dependency_graph.py
      - Build complete import graph
      - Identify circular dependencies
      - Generate migration order
      - Create visual dependency diagram
```

## Phase 1: Create Core Configuration Infrastructure (Priority: CRITICAL)

### 1.1 Base System (Note: No "Hybrid" naming)
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
      
- [ ] /panther/config/core/mixins.py (400 lines)
      - ValidationMixin: Enhanced Pydantic validation
      - InterpolationMixin: ${paths.output_dir}, ${oc.env:VAR}
      - CacheMixin: LRU cache with TTL
      - SerializationMixin: YAML/JSON/TOML support
      - CompatibilityMixin: Legacy field mapping
      - EnvironmentMixin: Environment variable binding
```

### 1.2 Configuration Manager (THE primary manager)
**ADD:**
```
- [ ] /panther/config/core/manager.py (1500+ lines)
      CLASS ConfigurationManager:
        # Constructor with ALL legacy parameters preserved
        __init__(
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
        )
        
        # Core configuration loading
        - load_and_validate_experiment_config() -> ExperimentConfig
        - load_and_validate_global_config() -> GlobalConfig
        - load_experiment_config(source, defaults, validate, auto_fix) -> ExperimentConfig
        - load_global_config(path, overrides, validate) -> GlobalConfig
        - reload_configuration() -> Reload with hot-reload support
        
        # Environment variable processing
        - _apply_environment_variables(config) with mappings:
          * PANTHER_LOG_LEVEL -> logging.level
          * PANTHER_BUILD_IMAGES -> docker.build_docker_image
          * PANTHER_OUTPUT_DIR -> paths.output_dir
          * PANTHER_LOG_COLORS -> logging.enable_colors
          * PANTHER_PLUGIN_DIR -> paths.plugin_dir
          * PANTHER_METRICS_ENABLED -> metrics.enabled
          * PANTHER_FAST_FAIL -> fast_fail.enabled
        
        # Feature log levels management
        - _process_feature_log_levels(config: LoggingConfig)
        - _validate_feature_names(features: Dict[str, str])
        - get_feature_log_level(feature: str) -> LoggingLevel
        
        # Plugin system integration
        - discover_plugins(force_refresh: bool = False) -> Dict[str, PluginMetadata]
        - get_plugin_metadata(plugin_name: str) -> Optional[PluginMetadata]
        - validate_plugin_config(plugin_name: str, config: Dict) -> ValidationResult
        - add_plugin(plugin_type: str, source_dir: Path, name: Optional[str])
        - remove_plugin(plugin_type: str, name: str, protocol: Optional[str])
        - load_plugin_schemas(force_refresh: bool = False) -> Dict[str, SchemaInfo]
        - get_plugin_parameters(plugin_name: str) -> Dict[str, Any]
        
        # Version discovery system
        - discover_available_versions(protocol: Optional[str]) -> Dict[str, List[str]]
        - get_version_configuration(impl_name, impl_type, protocol, version) -> Optional[Dict]
        - register_version(protocol: str, version: str, config: Dict)
        - _preload_versions() -> Preload all version configs
        
        # Configuration operations
        - validate_experiment_config(config: Union[Dict, ExperimentConfig]) -> ValidationResult
        - validate_global_config(config: Union[Dict, GlobalConfig]) -> ValidationResult
        - validate_service_configuration(service: Dict) -> ServiceConfig
        - validate_environment_config(env: Dict) -> EnvironmentConfig
        
        # Merging and templates
        - merge_configurations(*configs, strategy: MergeStrategy, 
                            conflict: ConflictResolution) -> DictConfig
        - create_experiment_from_template(name: str, params: Dict, 
                                       output: Optional[Path]) -> ExperimentConfig
        - apply_configuration_patch(base: Config, patch: Dict) -> Config
        
        # Override management
        - add_configuration_override(key: str, value: Any)
        - remove_configuration_override(key: str)
        - clear_configuration_overrides()
        - get_override_summary() -> Dict[str, Any]
        - apply_overrides(config: Config) -> Config
        
        # State and statistics
        - get_configuration_summary() -> Dict[str, Any]
        - get_statistics() -> Dict[str, Any]
        - get_validation_report() -> ValidationReport
        - export_configuration(format: str = "yaml") -> str
        
        # Validation control
        - set_validation_mode(strict: bool)
        - add_custom_validator(validator: Callable)
        - get_validation_errors() -> List[ValidationError]
        
        # Caching system
        - clear_cache()
        - get_cache_statistics() -> Dict[str, Any]
        - _generate_cache_key(source, defaults) -> str
        - preload_configurations(configs: List[Path])
        
        # Legacy compatibility API
        - load_config(path: Path, **kwargs) -> ExperimentConfig
        - validate_config(config) -> bool
        - get_plugins() -> Dict[str, Any]
        - _check_needs_legacy_handling(config: Dict) -> bool
        
        # Context manager support
        - __enter__() -> Self
        - __exit__(exc_type, exc_val, exc_tb)
        
        # Debugging and diagnostics
        - dump_configuration_state(output_dir: Path)
        - validate_all_plugins() -> ValidationReport
        - check_configuration_health() -> HealthReport
        
      # Global instance management (singleton pattern)
      _global_config_manager: Optional[ConfigurationManager] = None
      
      def get_config_manager() -> ConfigurationManager:
          global _global_config_manager
          if _global_config_manager is None:
              _global_config_manager = ConfigurationManager()
          return _global_config_manager
      
      # ConfigLoader for backward compatibility
      CLASS ConfigLoader(ConfigurationManager):
        - list_plugin_parameters(name: str, type: Optional[str], 
                               protocol: Optional[str]) -> Dict[str, Any]
        - _auto_detect_plugin_type(name: str, protocol: Optional[str]) -> Optional[str]
        - get_plugin_info(name: str) -> Dict[str, Any]
```

### 1.3 Configuration Models (Primary models, not "hybrid")
**ADD:**
```
- [ ] /panther/config/core/models/__init__.py
      # Export all models with exact legacy names
      from .global_config import (
          GlobalConfig, LoggingConfig, PathsConfig, DockerConfig,
          LoggingLevel, FeatureLogLevelsConfig, DockerUserMappingConfig,
          ProgressConfig, FastFailConfig
      )
      from .experiment import (
          ExperimentConfig, TestConfig, StepsConfig, 
          ExperimentMetadata, TestMetadata
      )
      from .service import (
          ServiceConfig, ImplementationConfig, ProtocolConfig,
          NetworkConfig, ImplementationType, ProtocolRole
      )
      from .observer import (
          ObserversConfig, LoggerObserverConfig, MetricsObserverConfig,
          StorageObserverConfig, ExperimentObserverConfig, 
          BaseObserverConfig
      )
      from .environment import (
          NetworkEnvironmentConfig, ExecutionEnvironmentConfig,
          DockerComposeConfig, LocalhostSingleContainerConfig,
          ShadowNsConfig, StraceConfig, GperfCpuConfig, 
          GperfHeapConfig, MemcheckConfig, HelgrindConfig,
          IterationsConfig
      )
      from .protocol import (
          BaseProtocolConfig, ClientServerProtocolConfig,
          PeerToPeerProtocolConfig, QuicProtocolConfig,
          HttpProtocolConfig, MinipProtocolConfig
      )
      
- [ ] /panther/config/core/models/base_model.py (200 lines)
      CLASS BaseConfigModel(pydantic.BaseModel, BaseConfig):
        - Unified base for all config models
        - class Config: use_enum_values, validate_assignment, extra='forbid'
        - Custom validators for common patterns
        - Automatic schema generation
        - Field aliases for backward compatibility
      
- [ ] /panther/config/core/models/global_config.py (600 lines)
      # Complete global configuration hierarchy
      
      CLASS GlobalConfig(BaseConfigModel):
        version: str = "1.0.0"
        logging: LoggingConfig
        paths: PathsConfig
        docker: DockerConfig
        observers: ObserversConfig
        progress: ProgressConfig
        fast_fail: FastFailConfig
        metrics: MetricsConfig
        
      CLASS LoggingConfig(BaseConfigModel):
        level: LoggingLevel = LoggingLevel.INFO
        format: str = "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        enable_colors: bool = True
        feature_levels: FeatureLogLevelsConfig
        file_logging: bool = False
        log_rotation: LogRotationConfig
        
      CLASS FeatureLogLevelsConfig(BaseConfigModel):
        # ALL feature names from codebase analysis
        docker_build: LoggingLevel = LoggingLevel.INFO
        service_start: LoggingLevel = LoggingLevel.INFO
        environment_setup: LoggingLevel = LoggingLevel.INFO
        test_execution: LoggingLevel = LoggingLevel.INFO
        metrics_collection: LoggingLevel = LoggingLevel.INFO
        plugin_loading: LoggingLevel = LoggingLevel.INFO
        command_generation: LoggingLevel = LoggingLevel.DEBUG
        network_setup: LoggingLevel = LoggingLevel.INFO
        certificate_generation: LoggingLevel = LoggingLevel.INFO
        output_collection: LoggingLevel = LoggingLevel.INFO
        event_processing: LoggingLevel = LoggingLevel.DEBUG
        validation: LoggingLevel = LoggingLevel.INFO
        
      CLASS PathsConfig(BaseConfigModel):
        output_dir: str = "outputs"
        log_dir: str = "${paths.output_dir}/logs"  # Interpolation support
        plugin_dir: str = "panther/plugins"
        temp_dir: str = "/tmp/panther"
        cache_dir: str = "${oc.env:HOME}/.panther/cache"
        
      CLASS DockerConfig(BaseConfigModel):
        build_docker_image: bool = False
        user_mapping: DockerUserMappingConfig
        registry: DockerRegistryConfig
        build_args: Dict[str, str] = {}
        
      CLASS DockerUserMappingConfig(BaseConfigModel):
        run_as_host_user: bool = False
        custom_uid: Optional[int] = None
        custom_gid: Optional[int] = None
        user_name: str = "panther"
        fallback_to_root: bool = True
        
      CLASS ProgressConfig(BaseConfigModel):
        enable_progress_bar: bool = True
        redirect_logging: bool = True
        show_spinner: bool = True
        update_interval: float = 0.1
        
      CLASS FastFailConfig(BaseConfigModel):
        enabled: bool = True
        test_level: bool = False
        docker_build_failures: bool = True
        service_start_failures: bool = True
        ivy_compilation_failures: bool = False
        timeout_cascade_threshold: int = 3
        critical_only: bool = False
        error_categories: Dict[str, bool] = {}
        
      CLASS MetricsConfig(BaseConfigModel):
        enabled: bool = True
        collect_system_metrics: bool = True
        export_format: str = "json"
        output_dir: str = "${paths.output_dir}/metrics"
        sampling_interval: float = 3.0
        
- [ ] /panther/config/core/models/observer.py (500 lines)
      CLASS ObserversConfig(BaseConfigModel):
        logger: LoggerObserverConfig
        metrics: MetricsObserverConfig
        storage: StorageObserverConfig
        experiment: ExperimentObserverConfig
        gui: Optional[GuiObserverConfig] = None
        plugin: Optional[PluginObserverConfig] = None
        
      CLASS BaseObserverConfig(BaseConfigModel):
        enabled: bool = True
        priority: int = 100
        buffer_size: int = 1000
        
      CLASS LoggerObserverConfig(BaseObserverConfig):
        log_level: str = "INFO"
        enable_colors: bool = True
        correlation_tracking: bool = True
        format: Optional[str] = None
        
      CLASS MetricsObserverConfig(BaseObserverConfig):
        collect_system_metrics: bool = True
        publish_interval: int = 30
        export_format: str = "json"
        aggregation_window: int = 60
        
      CLASS StorageObserverConfig(BaseObserverConfig):
        storage_path: str = "${paths.output_dir}/storage"
        enable_compression: bool = False
        retention_days: int = 30
        storage_backend: str = "local"  # local, s3, gcs
        
      CLASS ExperimentObserverConfig(BaseObserverConfig):
        track_timing: bool = True
        track_steps: bool = True
        generate_report: bool = True
        report_formats: List[str] = ["json", "markdown"]
        
- [ ] /panther/config/core/models/experiment.py (400 lines)
      CLASS ExperimentConfig(BaseConfigModel):
        tests: List[TestConfig]
        metadata: Optional[ExperimentMetadata] = None
        global_timeout: Optional[int] = None
        
      CLASS TestConfig(BaseConfigModel):
        name: str
        description: Optional[str] = None
        network_environment: NetworkEnvironmentConfig
        execution_environment: List[ExecutionEnvironmentConfig] = []
        services: Dict[str, ServiceConfig]
        steps: StepsConfig
        iterations: int = 1
        timeout: Optional[int] = None
        fast_fail_enabled: Optional[bool] = None
        expected_outcome: Optional[ExpectedOutcome] = None
        tags: List[str] = []
        
      CLASS StepsConfig(BaseConfigModel):
        pre_commands: List[str] = []
        wait: int = 60
        post_commands: List[str] = []
        validation_commands: List[str] = []
        
      CLASS ExperimentMetadata(BaseConfigModel):
        author: Optional[str] = None
        created: Optional[datetime] = None
        version: str = "1.0.0"
        description: Optional[str] = None
        tags: List[str] = []
        
- [ ] /panther/config/core/models/service.py (800 lines)
      CLASS ServiceConfig(BaseConfigModel):
        implementation: ImplementationConfig
        protocol: ProtocolConfig
        network: Optional[NetworkConfig] = None
        environment: Dict[str, str] = {}
        timeout: int = 60
        ports: List[str] = []
        volumes: List[str] = []
        generate_new_certificates: bool = False
        command_override: Optional[str] = None
        health_check: Optional[HealthCheckConfig] = None
        
        # Dynamic field support via __init__
        def __init__(self, **data):
            # Extract known fields
            known_fields = {...}
            extra_fields = {k: v for k, v in data.items() 
                          if k not in known_fields}
            super().__init__(**known_fields)
            # Store extra fields
            for k, v in extra_fields.items():
                setattr(self, k, v)
                
      CLASS ImplementationConfig(BaseConfigModel):
        name: str
        type: ImplementationType
        version: Optional[str] = None
        # Support dynamic fields (e.g., 'test' for panther_ivy)
        class Config:
            extra = "allow"
            
      CLASS ProtocolConfig(BaseConfigModel):
        name: str  # quic, http, minip
        version: Optional[str] = None  # Dynamic, not enum!
        role: ProtocolRole
        target: Optional[str] = None
        parameters: Dict[str, Any] = {}
        
      CLASS NetworkConfig(BaseConfigModel):
        interface: str = "eth0"
        port: int = 4443
        host: str = "localhost"
        bind_address: str = "0.0.0.0"
        
      CLASS HealthCheckConfig(BaseConfigModel):
        command: str
        interval: int = 30
        timeout: int = 10
        retries: int = 3
        
- [ ] /panther/config/core/models/protocol.py (500 lines)
      # Protocol-specific configurations
      
      CLASS BaseProtocolConfig(BaseConfigModel):
        """Base for all protocol configurations"""
        name: str
        version: Optional[str] = None
        
      CLASS ClientServerProtocolConfig(BaseProtocolConfig):
        """Base for client-server protocols"""
        server_port: int = 4443
        client_port: Optional[int] = None
        
      CLASS QuicProtocolConfig(ClientServerProtocolConfig):
        # QUIC-specific parameters
        initial_version: str = "1"
        alpn: List[str] = ["hq-29"]
        zero_rtt: bool = False
        key_update: bool = False
        quantum_readiness: bool = False
        congestion_control: str = "cubic"
        
      CLASS HttpProtocolConfig(ClientServerProtocolConfig):
        # HTTP-specific parameters
        http_version: str = "2"
        tls_enabled: bool = True
        compression: bool = True
        
      CLASS MinipProtocolConfig(ClientServerProtocolConfig):
        # MiniP-specific parameters
        packet_size: int = 1024
        ping_interval: int = 1
        
      CLASS PeerToPeerProtocolConfig(BaseProtocolConfig):
        """Base for P2P protocols"""
        discovery_method: str = "broadcast"
        max_peers: int = 10
        
- [ ] /panther/config/core/models/environment.py (700 lines)
      # Environment configurations
      
      CLASS NetworkEnvironmentConfig(BaseConfigModel):
        type: str  # docker_compose, localhost_single_container, shadow_ns
        
      CLASS DockerComposeConfig(NetworkEnvironmentConfig):
        type: Literal["docker_compose"] = "docker_compose"
        version: str = "3.8"
        network_name: str = "panther_network"
        volumes: List[str] = []
        environment: Dict[str, str] = {}
        compose_file_override: Optional[str] = None
        
      CLASS LocalhostSingleContainerConfig(NetworkEnvironmentConfig):
        type: Literal["localhost_single_container"] = "localhost_single_container"
        container_name: str = "panther_single"
        working_dir: str = "/app"
        dockerfile: Optional[str] = None
        
      CLASS ShadowNsConfig(NetworkEnvironmentConfig):
        type: Literal["shadow_ns"] = "shadow_ns"
        topology: str
        duration: str = "300s"
        seed: int = 1234
        log_level: str = "info"
        
      CLASS ExecutionEnvironmentConfig(BaseConfigModel):
        type: str  # strace, gperf_cpu, etc.
        enabled: bool = True
        
      CLASS StraceConfig(ExecutionEnvironmentConfig):
        type: Literal["strace"] = "strace"
        trace_calls: List[str] = ["network", "process"]
        output_format: str = "summary"
        follow_forks: bool = True
        
      CLASS GperfCpuConfig(ExecutionEnvironmentConfig):
        type: Literal["gperf_cpu"] = "gperf_cpu"
        sampling_frequency: int = 99
        output_file: str = "cpu_profile.svg"
        
      CLASS GperfHeapConfig(ExecutionEnvironmentConfig):
        type: Literal["gperf_heap"] = "gperf_heap"
        profile_type: str = "heap"
        output_file: str = "heap_profile.svg"
        
      CLASS MemcheckConfig(ExecutionEnvironmentConfig):
        type: Literal["memcheck"] = "memcheck"
        leak_check: str = "full"
        show_reachable: bool = True
        track_origins: bool = True
        
      CLASS HelgrindConfig(ExecutionEnvironmentConfig):
        type: Literal["helgrind"] = "helgrind"
        history_level: str = "full"
        conflict_cache_size: int = 1000000
        
      CLASS IterationsConfig(ExecutionEnvironmentConfig):
        type: Literal["iterations"] = "iterations"
        count: int = 10
        delay_between: float = 0.0
```

### 1.4 Component Systems
**ADD:**
```
- [ ] /panther/config/core/components/__init__.py
      
- [ ] /panther/config/core/components/loaders.py (500 lines)
      CLASS ConfigLoader(BaseLoader):
        """Primary configuration loader"""
        - load_yaml(path: Path) -> Dict
        - load_json(path: Path) -> Dict
        - load_env_file(path: Path) -> Dict
        - supports_interpolation: bool = True
        
      CLASS VersionConfigLoader(BaseLoader):
        """Dynamic version configuration loader"""
        - load_version_config(impl, type, protocol, version) -> Optional[Config]
        - discover_versions(protocol: Optional[str]) -> Dict[str, List[str]]
        - preload_all_versions()
        
      CLASS CompositeConfigLoader(BaseLoader):
        """Combines multiple loaders"""
        - add_loader(loader: BaseLoader)
        - load(source: Union[str, Path, Dict]) -> Dict
        
      CLASS PluginConfigLoader(BaseLoader):
        """Plugin-specific configuration loading"""
        - load_plugin_config(plugin_name: str) -> Dict
        - get_plugin_schema(plugin_name: str) -> Dict
        
- [ ] /panther/config/core/components/validators.py (600 lines)
      CLASS ConfigValidator(BaseValidator):
        """Primary configuration validator"""
        - validate_against_schema(config: Dict, schema: Dict) -> ValidationResult
        - validate_business_rules(config: Config) -> ValidationResult
        
      CLASS SchemaValidator(BaseValidator):
        """JSON Schema validation"""
        - validate(instance: Dict, schema: Dict) -> ValidationResult
        
      CLASS BusinessRulesValidator(BaseValidator):
        """Business logic validation"""
        - validate_port_ranges(config: ServiceConfig) -> List[str]
        - validate_timeouts(config: TestConfig) -> List[str]
        - validate_service_relationships(config: ExperimentConfig) -> List[str]
        
      CLASS CompatibilityValidator(BaseValidator):
        """Legacy format detection and validation"""
        - check_legacy_fields(config: Dict) -> List[str]
        - suggest_migrations(config: Dict) -> List[str]
        
- [ ] /panther/config/core/components/builders.py (800 lines)
      CLASS ConfigBuilder:
        """Base configuration builder with fluent API"""
        - reset() -> Self
        - from_dict(data: Dict) -> Self
        - from_file(path: Path) -> Self
        - with_overrides(overrides: Dict) -> Self
        - with_environment_variables(mappings: Dict) -> Self
        - build() -> Config
        
      CLASS ExperimentConfigBuilder(ConfigBuilder):
        """Experiment-specific builder"""
        - with_test(test: TestConfig) -> Self
        - with_global_timeout(timeout: int) -> Self
        - auto_fix_services() -> Self
        - validate_before_build: bool = True
        
      CLASS ServiceConfigBuilder(ConfigBuilder):
        """Service-specific builder"""
        - with_implementation(name: str, type: str) -> Self
        - with_protocol(name: str, version: str, role: str) -> Self
        - preserve_extra_fields: bool = True
        
      CLASS BuilderContext:
        """Tracks builder state and warnings"""
        - warnings: List[str]
        - fixes_applied: List[str]
        - validation_errors: List[str]
        
- [ ] /panther/config/core/components/merger.py (400 lines)
      CLASS ConfigMerger:
        """Configuration merging with strategies"""
        - merge(*configs: Config, strategy: MergeStrategy) -> Config
        - create_merge_context(strategy, conflict_resolution) -> MergeContext
        - get_merge_report(context: MergeContext) -> Dict
        
      CLASS MergeContext:
        """Tracks merge operations"""
        - conflicts: List[MergeConflict]
        - resolutions: List[Resolution]
        - paths_merged: Set[str]
        
      ENUM MergeStrategy:
        DEEP_MERGE = "deep"
        SHALLOW_MERGE = "shallow"
        REPLACE = "replace"
        APPEND_LISTS = "append"
        
      ENUM ConflictResolution:
        OVERRIDE = "override"
        KEEP_ORIGINAL = "keep"
        MERGE_BOTH = "merge"
        RAISE_ERROR = "error"
        
- [ ] /panther/config/core/components/discovery.py (500 lines)
      CLASS PluginDiscovery:
        """Discovers and catalogs plugins"""
        - discover_all_plugins(force_refresh: bool) -> Dict[str, PluginMetadata]
        - get_plugin_metadata(name: str) -> Optional[PluginMetadata]
        - get_plugin_summary() -> Dict[str, Any]
        - register_plugin(metadata: PluginMetadata)
        
      CLASS VersionDiscovery:
        """Discovers available versions"""
        - scan_version_configs(plugin_dir: Path) -> Dict
        - register_discovered_versions(versions: Dict)
        
      CLASS SchemaDiscovery:
        """Discovers plugin schemas"""
        - load_all_schemas(force_refresh: bool) -> Dict[str, SchemaInfo]
        - get_schema_for_plugin(plugin_name: str) -> Optional[SchemaInfo]
```

## Phase 2: Migration Infrastructure (Priority: HIGH)

### 2.1 Compatibility Layer
**ADD:**
```
- [ ] /panther/config/core/compat/__init__.py
      
- [ ] /panther/config/core/compat/dataclass_adapter.py (400 lines)
      CLASS DataclassAdapter:
        - to_config_model(dataclass_obj) -> BaseConfigModel
        - from_config_model(model: BaseConfigModel, target_class) -> Any
        - handle_enum_fields(value: Any) -> Any
        - handle_nested_configs(value: Any) -> Any
        - handle_optional_fields(value: Any) -> Any
        
- [ ] /panther/config/core/compat/import_interceptor.py (300 lines)
      CLASS ConfigImportInterceptor(importlib.abc.MetaPathFinder):
        - install() -> None  # Register with sys.meta_path
        - find_spec(name, path, target) -> Optional[ModuleSpec]
        - intercept_mappings: Dict[str, str] = {
            "panther.config.config_experiment_schema": "panther.config.core.models",
            "panther.config.config_global_schema": "panther.config.core.models",
            # ... all legacy imports
        }
        
- [ ] /panther/config/core/compat/field_mapper.py (300 lines)
      CLASS FieldMapper:
        - map_legacy_field(name: str, value: Any) -> Tuple[str, Any]
        - get_field_migrations() -> Dict[str, str]
        - handle_removed_fields(config: Dict) -> Dict
        - add_required_fields(config: Dict) -> Dict
```

### 2.2 Migration Tools
**ADD:**
```
- [ ] /panther/tools/config_migration/analyzer.py (500 lines)
      CLASS ConfigUsageAnalyzer:
        - scan_codebase(root: Path) -> UsageReport
        - find_config_imports(file: Path) -> List[Import]
        - build_dependency_graph() -> nx.DiGraph
        - identify_circular_deps() -> List[List[str]]
        - generate_migration_order() -> List[str]
        
- [ ] /panther/tools/config_migration/migrator.py (800 lines)
      CLASS ConfigMigrator:
        - migrate_yaml_config(path: Path) -> MigrationResult
        - migrate_python_file(path: Path) -> MigrationResult
        - update_imports(content: str) -> str
        - convert_dataclass_to_model(content: str) -> str
        - generate_migration_report() -> MigrationReport
        
- [ ] /panther/tools/config_migration/validator.py (400 lines)
      CLASS MigrationValidator:
        - validate_migrated_config(old: Path, new: Path) -> ValidationResult
        - compare_behaviors(old_config, new_config) -> List[Difference]
        - run_compatibility_tests() -> TestReport
        - benchmark_performance() -> PerformanceReport
```

## Phase 3: Core Integration Points (Priority: HIGH)

### 3.1 Main Config Module Updates
**MODIFY:**
```
- [ ] /panther/config/__init__.py (Update entire file)
      """
      PANTHER Configuration System
      
      This module provides the unified configuration system for PANTHER.
      """
      
      # Primary exports (no "hybrid" naming)
      from panther.config.core.manager import (
          ConfigurationManager,
          ConfigLoader,
          get_config_manager,
          # Convenience functions
          load_experiment,
          validate_service,
          discover_versions
      )
      
      # Model exports (maintain exact legacy names)
      from panther.config.core.models import (
          # Global configs
          GlobalConfig, LoggingConfig, PathsConfig, DockerConfig,
          LoggingLevel, FeatureLogLevelsConfig, DockerUserMappingConfig,
          ProgressConfig, FastFailConfig, MetricsConfig,
          
          # Experiment configs
          ExperimentConfig, TestConfig, StepsConfig,
          
          # Service configs
          ServiceConfig, ImplementationConfig, ProtocolConfig,
          NetworkConfig, ImplementationType, ProtocolRole,
          
          # Observer configs
          ObserversConfig, LoggerObserverConfig, MetricsObserverConfig,
          StorageObserverConfig, ExperimentObserverConfig,
          
          # Environment configs
          NetworkEnvironmentConfig, ExecutionEnvironmentConfig,
          DockerComposeConfig, LocalhostSingleContainerConfig,
          ShadowNsConfig, StraceConfig, GperfCpuConfig,
          GperfHeapConfig, MemcheckConfig, HelgrindConfig,
          IterationsConfig
      )
      
      # Backward compatibility with deprecation warnings
      import warnings
      
      def __getattr__(name):
          deprecated_managers = {
              'ConfigManagerRefactored': ConfigurationManager,
              'ConfigManagerEnhanced': ConfigurationManager,
              'ConfigManagerV2': ConfigurationManager,
          }
          
          if name in deprecated_managers:
              warnings.warn(
                  f"{name} is deprecated. Use ConfigurationManager instead.",
                  DeprecationWarning,
                  stacklevel=2
              )
              return deprecated_managers[name]
          
          raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
      
      __all__ = [
          # Managers
          'ConfigurationManager', 'ConfigLoader', 'get_config_manager',
          
          # Functions
          'load_experiment', 'validate_service', 'discover_versions',
          
          # Models (all of them for compatibility)
          'GlobalConfig', 'LoggingConfig', 'PathsConfig', 'DockerConfig',
          'LoggingLevel', 'FeatureLogLevelsConfig', 'DockerUserMappingConfig',
          'ProgressConfig', 'FastFailConfig', 'MetricsConfig',
          'ExperimentConfig', 'TestConfig', 'StepsConfig',
          'ServiceConfig', 'ImplementationConfig', 'ProtocolConfig',
          'NetworkConfig', 'ImplementationType', 'ProtocolRole',
          'ObserversConfig', 'LoggerObserverConfig', 'MetricsObserverConfig',
          'StorageObserverConfig', 'ExperimentObserverConfig',
          'NetworkEnvironmentConfig', 'ExecutionEnvironmentConfig',
          'DockerComposeConfig', 'LocalhostSingleContainerConfig',
          'ShadowNsConfig', 'StraceConfig', 'GperfCpuConfig',
          'GperfHeapConfig', 'MemcheckConfig', 'HelgrindConfig',
          'IterationsConfig'
      ]
      
- [ ] /panther/config/config_manager.py (Delegate to new system)
      """Legacy config manager - delegates to new system."""
      warnings.warn(
          "Direct import of config_manager.py is deprecated. "
          "Import from panther.config instead.",
          DeprecationWarning
      )
      
      from panther.config.core.manager import *
      
      # Maintain exact same interface for compatibility
```

## Phase 4: CLI and Entry Points (Priority: HIGH)

### 4.1 CLI Command Updates
**MODIFY:**
```
- [ ] /panther/cli/subcommands/run.py
      Lines 10: from panther.config import ConfigLoader
      Lines 157-198: Update all config handling
      Add: Migration check and warning if using old format
      
- [ ] /panther/cli/subcommands/config.py
      Update all imports to use new config system
      Add new commands:
        - config migrate <file> - Migrate old config to new format
        - config validate <file> - Validate configuration
        - config schema <type> - Show schema for config type
        
- [ ] /panther/cli/subcommands/plugins.py
      Update plugin discovery to use new system
      
- [ ] /panther/cli/interactive/experiment_designer.py
      Update to use new config models
      Add validation during design process
      
- [ ] /panther/cli/interactive/validation_helper.py
      Use new validation system
      
- [ ] /panther/__main__.py
      Add config format detection
      Show migration suggestions for old formats
```

## Phase 5: Core System Updates (Priority: HIGH)

### 5.1 Experiment Manager
**MODIFY:**
```
- [ ] /panther/core/experiment_manager.py
      Lines 20-21: from panther.config import ExperimentConfig, GlobalConfig
      Lines 56-57: Update plugin manager import
      Update all config usage throughout
      
- [ ] /panther/core/test_cases/test_case_impl.py
- [ ] /panther/core/test_cases/test_case_impl_refactored.py
- [ ] /panther/core/test_cases/test_case_impl_enhanced.py
- [ ] /panther/core/test_cases/base/test_case_base.py
      Update all config imports and usage
      
- [ ] /panther/core/test_cases/mixins/service_management.py
      Update service config handling
```

### 5.2 Observer System
**MODIFY:**
```
- [ ] /panther/core/observer/factory/factory_config.py
      Replace dataclass configs with new models
      
- [ ] /panther/core/observer/factory/factory_builders.py
- [ ] /panther/core/observer/factory/observer_factory.py
      Update config handling
      
- [ ] /panther/core/observer/impl/*.py (all implementations)
      Update constructor signatures to use new configs
```

### 5.3 Docker and Command Systems
**MODIFY:**
```
- [ ] /panther/core/docker_builder/docker_builder.py
- [ ] /panther/core/docker_builder/docker_registry.py
- [ ] /panther/core/docker_builder/service_manager_docker_mixin.py
- [ ] /panther/core/docker_builder/environment_manager_docker_mixing.py
      Update all config usage
      
- [ ] /panther/core/command_processor/command_builder.py
- [ ] /panther/core/command_processor/command_utils.py
- [ ] /panther/core/command_processor/command_validator.py
      Accept new config types
```

### 5.4 Metrics and Reporting
**MODIFY:**
```
- [ ] /panther/core/metrics/metrics_collector.py
- [ ] /panther/core/metrics/metrics_exporter.py
- [ ] /panther/core/metrics/metrics_reporter.py
- [ ] /panther/core/metrics/resource_monitor.py
      Update config handling
      
- [ ] /panther/core/reporting/experiment_reporter.py
- [ ] /panther/core/reporting/status_collector.py
      Use new config models
      
- [ ] /panther/core/results/result_handlers/storage_handler.py
- [ ] /panther/core/results/result_handlers/local_storage_handler.py
      Update storage configurations
```

### 5.5 Other Core Components
**MODIFY:**
```
- [ ] /panther/core/template/template_renderer.py
- [ ] /panther/core/utils/logger_factory.py
- [ ] /panther/core/utils/validation_utils.py
- [ ] /panther/core/utils/file_utils.py
- [ ] /panther/core/outputs/output_collector.py
- [ ] /panther/core/outputs/output_aggregator.py
      Update all config usage
```

## Phase 6: Plugin System Updates (Priority: MEDIUM)

### 6.1 Plugin Core
**MODIFY:**
```
- [ ] /panther/plugins/plugin_manager.py
      Update to use new config system
      Integrate version discovery
      
- [ ] /panther/plugins/plugin_discovery.py
- [ ] /panther/plugins/plugin_catalog.py
- [ ] /panther/plugins/plugin_manifest.py
- [ ] /panther/plugins/plugin_config_resolver.py
      Update all config handling
```

### 6.2 Service System Base
**MODIFY:**
```
- [ ] /panther/plugins/services/config_schema.py
      from panther.config import ServiceConfig, ImplementationConfig
      # Re-export for compatibility
      
- [ ] /panther/plugins/services/base/config_base.py
      Update base classes to use new models
      
- [ ] /panther/plugins/services/services_interface.py
- [ ] /panther/plugins/services/service_factory.py
      Update interfaces
```

### 6.3 All Service Implementations
**MODIFY:** (Each file needs updates)
```
- [ ] QUIC implementations:
      - /panther/plugins/services/iut/quic/picoquic/picoquic.py
      - /panther/plugins/services/iut/quic/aioquic/aioquic.py
      - /panther/plugins/services/iut/quic/quiche/quiche.py
      - /panther/plugins/services/iut/quic/quinn/quinn.py
      - /panther/plugins/services/iut/quic/lsquic/lsquic.py
      - /panther/plugins/services/iut/quic/mvfst/mvfst.py
      - /panther/plugins/services/iut/quic/quic_go/quic_go.py
      - /panther/plugins/services/iut/quic/quant/quant.py
      - /panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py
      
- [ ] Other protocols:
      - /panther/plugins/services/iut/minip/ping_pong/ping_pong.py
      
- [ ] Testers:
      - /panther/plugins/services/testers/panther_ivy/panther_ivy.py
      - All Ivy components
      
- [ ] All config_schema.py files in services
```

### 6.4 Environment Plugins
**MODIFY:**
```
- [ ] Network environments:
      - /panther/plugins/environments/network_environment/config_schema.py
      - docker_compose/docker_compose.py
      - localhost_single_container/localhost_single_container.py
      - shadow_ns/shadow_ns.py
      - All monitoring components
      
- [ ] Execution environments:
      - /panther/plugins/environments/execution_environment/config_schema.py
      - strace/strace.py
      - gperf_cpu/gperf_cpu.py
      - gperf_heap/gperf_heap.py
      - memcheck/memcheck.py
      - helgrind/helgrind.py
      - iterations/iterations.py
      
- [ ] All config_schema.py files in environments
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

## Phase 7: Testing Infrastructure (Priority: HIGH)

### 7.1 New Test Suite
**ADD:**
```
- [ ] /tests/unit/config/test_config_manager.py
- [ ] /tests/unit/config/test_config_models.py
- [ ] /tests/unit/config/test_config_loaders.py
- [ ] /tests/unit/config/test_config_validators.py
- [ ] /tests/unit/config/test_config_builders.py
- [ ] /tests/unit/config/test_config_merger.py
- [ ] /tests/unit/config/test_config_compatibility.py
- [ ] /tests/integration/test_config_loading.py
- [ ] /tests/integration/test_config_migration.py
- [ ] /tests/integration/test_config_validation.py
- [ ] /tests/e2e/test_config_experiment_flow.py
- [ ] /tests/performance/test_config_performance.py
```

### 7.2 Update Existing Tests
**MODIFY:**
```
- [ ] All files in /tests/ that import configs
- [ ] Update test fixtures to use new models
- [ ] Add migration tests for each component
```

## Phase 8: Additional Components (Priority: LOW)

**MODIFY:**
```
- [ ] /panther/webapp/web_app.py
- [ ] /panther/webapp/experiment_setup.py
- [ ] /panther/builder_metrics/core.py
- [ ] /panther/builder_metrics/pytest_plugin.py
- [ ] /panther/tools/plugins/environments/tutorials/tutorial.py
- [ ] /panther/tools/plugins/services/tutorials/tutorial.py
- [ ] /panther/tools/plugins/plugin_migration_tool.py
```

## Phase 9: Legacy Code Removal (Priority: LOW - AFTER VALIDATION)

### 9.1 Remove V2 System
**REMOVE:** (Only after all tests pass)
```
- [ ] /panther/config/config_manager_v2.py
- [ ] /panther/config/builders/ (entire directory)
- [ ] /panther/config/loaders/ (entire directory)
- [ ] /panther/config/mergers/ (entire directory)
- [ ] /panther/config/models/ (entire directory)
- [ ] /panther/config/validators/ (entire directory)
- [ ] /panther/config/registry/ (entire directory)
```

### 9.2 Remove Legacy Files
**REMOVE:**
```
- [ ] /panther/config/config_experiment_schema.py
- [ ] /panther/config/config_global_schema.py
- [ ] /panther/config/config_observer_schema.py
- [ ] /panther/config/config_manager_enhanced.py
- [ ] /panther/config/config_manager_refactored.py
```

### 9.3 Remove Old/Backup Files
**REMOVE:**
```
- [ ] /dev/old/ (500+ files)
- [ ] /backup_originals/
- [ ] All *_original.py files
- [ ] All *_refactored.py files
- [ ] All *_legacy.py files
```

## Phase 10: Documentation (Priority: MEDIUM)

**ADD/UPDATE:**
```
- [ ] /docs/configuration/system_overview.md
- [ ] /docs/configuration/migration_guide.md
- [ ] /docs/configuration/api_reference.md
- [ ] /docs/configuration/examples/
- [ ] /docs/configuration/troubleshooting.md
- [ ] /CLAUDE.md - Complete rewrite of config section
- [ ] /README.md - Update all examples
- [ ] All example configs in experiment-config/
```

## Implementation Schedule

### Week 1: Foundation (Critical Path)
- Day 1: Phase 0 - Preparation and backup
- Day 2-3: Phase 1.1-1.2 - Base system and manager
- Day 4-5: Phase 1.3 - All models

### Week 2: Core Infrastructure
- Day 1-2: Phase 1.4 - Components
- Day 3-4: Phase 2 - Migration infrastructure
- Day 5: Phase 3 - Config module updates

### Week 3: Integration
- Day 1-2: Phase 4 - CLI updates
- Day 3-5: Phase 5 - Core system updates

### Week 4: Plugins
- Day 1-2: Phase 6.1-6.2 - Plugin core
- Day 3-5: Phase 6.3-6.5 - All implementations

### Week 5: Testing and Validation
- Day 1-2: Phase 7.1 - New tests
- Day 3-4: Phase 7.2 - Update existing tests
- Day 5: Phase 8 - Additional components

### Week 6: Finalization
- Day 1-2: Full system validation
- Day 3: Phase 9 - Legacy removal (if safe)
- Day 4-5: Phase 10 - Documentation

## Critical Success Metrics

### Must Achieve:
1. Zero breaking changes to public APIs
2. All existing experiments run unchanged
3. 100% test coverage for new system
4. Performance equal or better than legacy
5. Complete feature parity with all managers

### Quality Metrics:
1. Config loading < 100ms
2. Memory usage < current system
3. Better error messages
4. Type safety throughout
5. No circular dependencies

## Risk Mitigation

### Technical Risks:
1. **Import cycles**: Use dependency analyzer first
2. **Performance**: Benchmark each component
3. **Compatibility**: Extensive testing suite
4. **Migration errors**: Automated validation

### Process Risks:
1. **Scope creep**: Strict phase boundaries
2. **Testing gaps**: Coverage requirements
3. **Documentation lag**: Write as we go

## Final Statistics

### Code Impact:
- New files: ~45
- Modified files: ~250
- Removed files: ~100
- Total lines: ~30,000 affected

### Complexity Reduction:
- Config managers: 4 → 1
- Config systems: 3 → 1
- Duplicate code eliminated: ~60%

This is THE configuration system for PANTHER going forward.