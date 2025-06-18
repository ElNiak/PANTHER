# PANTHER Configuration System Implementation TODO

## Overview
This document outlines the implementation plan for migrating PANTHER's configuration system from OmegaConf-based dataclasses to a modular OmegaConf + Pydantic architecture following SOLID principles.

## Key Principles
- **DRY**: Avoid duplication through inheritance and composition
- **SOLID**: Single responsibility, open/closed, interface segregation
- **Type Safety**: Pydantic models with proper enum handling
- **Backward Compatibility**: Support existing dataclass interfaces
- **Modular Design**: Separate concerns for loading, validation, merging, building

## Phase 1: Core Pydantic Schema Migration

### 1.1 Base Configuration Models
**File**: `panther/config/models/base.py` ✅ (Already created)
- [x] ConfigModel base class with OmegaConf integration
- [x] Methods for conversion between OmegaConf, Pydantic, and dataclasses
- [x] Merge functionality

### 1.2 Implementation Models
**File**: `panther/config/models/implementation.py`
**Dependencies**: None
**Tasks**:
- [ ] Create ProtocolModel with proper enum types
  - Protocol name (quic, http, minip)
  - Protocol version (loaded from plugins, not hardcoded)
  - Protocol role (client, server)
  - Target service reference
- [ ] Create ImplementationModel
  - Implementation name
  - Implementation type (IUT, TESTER) as enum
  - Test name (for testers)
  - Version configuration path resolution
- [ ] Add validation for protocol-implementation compatibility

### 1.3 Service Configuration Models
**File**: `panther/config/models/service.py`
**Dependencies**: `implementation.py`
**Tasks**:
- [ ] Create ServiceConfigModel extending ConfigModel
  - Implementation (ImplementationModel)
  - Protocol (ProtocolModel)
  - Timeout with validation (1-3600)
  - Ports list with format validation
  - Certificate generation flags
  - Environment variables
- [ ] Add custom validators for port format (host:container)
- [ ] Add relationship validation (client must have server target)

### 1.4 Experiment Configuration Models
**File**: `panther/config/models/experiment.py`
**Dependencies**: `service.py`, existing environment schemas
**Tasks**:
- [ ] Create StepConfigModel
  - Wait time with range validation
  - PCAP recording flag
- [ ] Create AssertionConfigModel
  - Assertion type enum
  - Service references validation
- [ ] Create TestConfigModel
  - Services dictionary (Dict[str, ServiceConfigModel])
  - Network environment reference
  - Execution environments list
  - Fast-fail override flag
- [ ] Create ExperimentConfigModel
  - Tests list with validation

### 1.5 Global Configuration Models
**File**: `panther/config/models/global_config.py`
**Dependencies**: All above models
**Tasks**:
- [ ] Create LoggingConfigModel
  - Level enum with validation
  - Format string
  - Color output flag
- [ ] Create PathsConfigModel
  - Output directories with path validation
  - Plugin directories
- [ ] Create DockerConfigModel
  - Build flags
  - User mapping configuration
  - Registry settings
- [ ] Create ObserverConfigModel for each observer type
- [ ] Create FastFailConfigModel
  - Global enable/disable
  - Test-level control
  - Error category flags
- [ ] Create GlobalConfigModel combining all above

## Phase 2: Configuration Loading System

### 2.1 Base Loader Interface
**File**: `panther/config/loaders/base_loader.py`
**Dependencies**: Models from Phase 1
**Tasks**:
- [ ] Create AbstractConfigLoader with interface methods
  - load() -> Dict[str, Any]
  - validate() -> bool
  - get_schema() -> Type[ConfigModel]
- [ ] Add error handling mixins
- [ ] Add caching support

### 2.2 Version Configuration Loader
**File**: `panther/config/loaders/version_loader.py`
**Dependencies**: `base_loader.py`
**Tasks**:
- [ ] Create VersionConfigLoader
  - Load from `version_configs/{protocol_version}.yaml` for IUT
  - Load from `version_configs/{protocol}/{protocol_version}.yaml` for testers
  - Cache loaded versions
- [ ] Add version discovery methods
- [ ] Handle missing version configs gracefully

### 2.3 Plugin Schema Loader Enhancement
**File**: `panther/config/loaders/plugin_schema_loader.py` (enhance existing)
**Dependencies**: `base_loader.py`, existing plugin system
**Tasks**:
- [ ] Enhance to load version configurations
- [ ] Add protocol version registry
- [ ] Implement dynamic version discovery from plugins
- [ ] Add version compatibility checking

### 2.4 YAML File Loader
**File**: `panther/config/loaders/yaml_loader.py`
**Dependencies**: `base_loader.py`
**Tasks**:
- [ ] Create YAMLConfigLoader using OmegaConf
- [ ] Support variable interpolation
- [ ] Handle missing files and syntax errors
- [ ] Support include directives

## Phase 3: Configuration Validation System

### 3.1 Base Validator
**File**: `panther/config/validators/base_validator.py`
**Dependencies**: Models from Phase 1
**Tasks**:
- [ ] Create AbstractValidator interface
  - validate(config: Any) -> ValidationResult
  - get_errors() -> List[ValidationError]
- [ ] Create ValidationResult dataclass
- [ ] Add validation context support

### 3.2 Pydantic Validator
**File**: `panther/config/validators/pydantic_validator.py`
**Dependencies**: `base_validator.py`
**Tasks**:
- [ ] Create PydanticValidator implementation
- [ ] Handle Pydantic ValidationError conversion
- [ ] Add custom error formatting
- [ ] Support nested validation

### 3.3 Business Rules Validator
**File**: `panther/config/validators/business_rules_validator.py`
**Dependencies**: `base_validator.py`
**Tasks**:
- [ ] Create BusinessRulesValidator
  - Validate service relationships (client-server)
  - Validate port uniqueness
  - Validate protocol compatibility
  - Validate environment requirements
- [ ] Add plugin-specific validation rules

## Phase 4: Configuration Merging System

### 4.1 Configuration Merger
**File**: `panther/config/mergers/config_merger.py`
**Dependencies**: OmegaConf, models
**Tasks**:
- [ ] Create ConfigMerger using OmegaConf
  - Hierarchical merging support
  - Override handling
  - Default value resolution
- [ ] Add merge strategies (replace, append, deep)
- [ ] Handle type conversions during merge

## Phase 5: Configuration Building System

### 5.1 Base Builder
**File**: `panther/config/builders/base_builder.py`
**Dependencies**: All models and validators
**Tasks**:
- [ ] Create AbstractConfigBuilder interface
  - build() -> ConfigModel
  - with_defaults() -> Self
  - validate() -> Self
- [ ] Add fluent API support

### 5.2 Experiment Configuration Builder
**File**: `panther/config/builders/experiment_builder.py`
**Dependencies**: `base_builder.py`
**Tasks**:
- [ ] Create ExperimentConfigBuilder
  - Build from YAML files
  - Apply defaults
  - Validate complete configuration
  - Resolve service references
- [ ] Add test generation helpers

### 5.3 Service Configuration Builder
**File**: `panther/config/builders/service_builder.py`
**Dependencies**: `base_builder.py`
**Tasks**:
- [ ] Create ServiceConfigBuilder
  - Build from plugin configs
  - Load version configurations
  - Apply protocol defaults
  - Generate deployment configs

## Phase 6: Main Configuration Manager

### 6.1 Configuration Manager Facade
**File**: `panther/config/config_manager_v2.py`
**Dependencies**: All above components
**Tasks**:
- [ ] Create ConfigurationManager facade
  - Coordinate loaders, validators, mergers, builders
  - Provide simple API for experiment manager
  - Handle backward compatibility
- [ ] Add configuration export/import
- [ ] Add configuration diff/comparison

### 6.2 Backward Compatibility Layer
**File**: `panther/config/compat/dataclass_adapter.py`
**Dependencies**: Old dataclasses, new models
**Tasks**:
- [ ] Create DataclassAdapter
  - Convert Pydantic models to dataclasses
  - Handle enum conversions
  - Preserve behavior compatibility
- [ ] Add migration warnings

## Phase 7: Integration Points

### 7.1 Update Service Manager Docker Mixin
**File**: `panther/core/docker_builder/service_manager_docker_mixin.py`
**Modified sections**:
- [ ] Update version extraction to use new config models
- [ ] Remove hardcoded version config loading
- [ ] Use ConfigurationManager for version resolution

### 7.2 Update Experiment Manager
**File**: `panther/core/experiment_manager.py`
**Modified sections**:
- [ ] Replace ConfigLoader with ConfigurationManager
- [ ] Update config access patterns
- [ ] Use new validation results

### 7.3 Update CLI
**File**: `panther/__main__.py`
**Modified sections**:
- [ ] Update config loading calls
- [ ] Use new validation error formatting
- [ ] Add config migration command

### 7.4 Update Plugin Manager
**File**: `panther/plugins/plugin_manager.py`
**Modified sections**:
- [ ] Use new service config models
- [ ] Update plugin config validation
- [ ] Use version registry

## Phase 8: Testing

### 8.1 Unit Tests
**Directory**: `tests/unit/config/`
**Tasks**:
- [ ] Test each model with valid/invalid data
- [ ] Test loaders with various file formats
- [ ] Test validators with edge cases
- [ ] Test merger with complex hierarchies
- [ ] Test builders with incomplete data

### 8.2 Integration Tests
**Directory**: `tests/integration/config/`
**Tasks**:
- [ ] Test complete configuration loading flow
- [ ] Test plugin configuration discovery
- [ ] Test version configuration loading
- [ ] Test backward compatibility

### 8.3 Migration Tests
**File**: `tests/integration/config/test_migration.py`
**Tasks**:
- [ ] Test old config format compatibility
- [ ] Test dataclass adapter
- [ ] Test deprecation warnings

## Phase 9: Documentation

### 9.1 API Documentation
**Directory**: `docs/api/config/`
**Tasks**:
- [ ] Document new configuration models
- [ ] Document validation rules
- [ ] Document builder patterns
- [ ] Add migration guide

### 9.2 Update CLAUDE.md
**File**: `CLAUDE.md`
**Tasks**:
- [ ] Add configuration system overview
- [ ] Add common configuration patterns
- [ ] Add troubleshooting guide

## Phase 10: Cleanup

### 10.1 Remove Legacy Code
**Files to remove** (after verification):
- [ ] `panther/config/config_manager.py` (old monolithic)
- [ ] `panther/config/config_manager_enhanced.py` (if unused)
- [ ] `panther/config/config_manager_refactored.py` (if replaced)

### 10.2 Update Imports
**Tasks**:
- [ ] Find and replace all ConfigLoader imports
- [ ] Update all config dataclass imports
- [ ] Remove unused imports

## Dependencies Summary

```
1. Models (Phase 1) - No external dependencies
2. Loaders (Phase 2) - Depends on Models
3. Validators (Phase 3) - Depends on Models
4. Mergers (Phase 4) - Depends on Models
5. Builders (Phase 5) - Depends on Models, Validators, Loaders, Mergers
6. Manager (Phase 6) - Depends on all above
7. Integration (Phase 7) - Depends on Manager
8. Testing (Phase 8) - Can be done in parallel with implementation
9. Documentation (Phase 9) - After implementation
10. Cleanup (Phase 10) - After full verification
```

## Implementation Order

1. **Week 1**: Complete Phase 1 (Models) and Phase 2 (Loaders)
2. **Week 2**: Complete Phase 3 (Validators) and Phase 4 (Mergers)
3. **Week 3**: Complete Phase 5 (Builders) and Phase 6 (Manager)
4. **Week 4**: Complete Phase 7 (Integration) and Phase 8 (Testing)
5. **Week 5**: Complete Phase 9 (Documentation) and Phase 10 (Cleanup)

## Success Criteria

- [ ] All tests pass with new configuration system
- [ ] No hardcoded protocol versions (loaded from plugins)
- [ ] Clear validation errors with actionable messages
- [ ] Backward compatibility maintained
- [ ] Performance equal or better than old system
- [ ] Zero code duplication in configuration handling
- [ ] Full type safety with proper enum handling

## Notes

- Protocol versions are defined in plugin config schemas as enums
- Version configurations are YAML files loaded dynamically
- The new system must maintain the same external API for minimal disruption
- Focus on clear error messages for configuration issues
- Use dependency injection for testability