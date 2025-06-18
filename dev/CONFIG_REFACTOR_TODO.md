# Configuration System Refactoring TODO List

## Overview
Complete migration from dataclass-based configuration to hybrid Pydantic-OmegaConf system.
This document tracks all additions, modifications, and removals needed across the entire codebase.

## Phase 1: Create Core Infrastructure (Priority: HIGH)

### 1.1 Create Hybrid Base System
**ADD:**
- [ ] `/panther/config/hybrid/__init__.py` - Package initialization
- [ ] `/panther/config/hybrid/base.py` - HybridConfig base class
- [ ] `/panther/config/hybrid/exceptions.py` - Custom exceptions
- [ ] `/panther/config/hybrid/types.py` - Type definitions and aliases

### 1.2 Create Unified Models (Replace ALL Dataclasses)
**ADD:**
- [ ] `/panther/config/hybrid/models/__init__.py` - Model exports
- [ ] `/panther/config/hybrid/models/service.py` - ServiceConfig (replaces dataclass)
- [ ] `/panther/config/hybrid/models/protocol.py` - ProtocolConfig (replaces dataclass)
- [ ] `/panther/config/hybrid/models/implementation.py` - ImplementationConfig
- [ ] `/panther/config/hybrid/models/experiment.py` - ExperimentConfig
- [ ] `/panther/config/hybrid/models/global_config.py` - GlobalConfig
- [ ] `/panther/config/hybrid/models/environment.py` - Environment configs
- [ ] `/panther/config/hybrid/models/docker.py` - Docker-related configs
- [ ] `/panther/config/hybrid/models/logging.py` - Logging configuration
- [ ] `/panther/config/hybrid/models/paths.py` - Path configuration

### 1.3 Create Hybrid Manager
**ADD:**
- [ ] `/panther/config/hybrid/manager.py` - HybridConfigManager
- [ ] `/panther/config/hybrid/loaders.py` - Specialized loaders
- [ ] `/panther/config/hybrid/validators.py` - Custom validators
- [ ] `/panther/config/hybrid/resolvers.py` - OmegaConf resolvers

### 1.4 Create Migration Tools
**ADD:**
- [ ] `/panther/tools/config_migration/__init__.py`
- [ ] `/panther/tools/config_migration/migrator.py` - Main migration logic
- [ ] `/panther/tools/config_migration/dataclass_parser.py` - Parse dataclass definitions
- [ ] `/panther/tools/config_migration/pydantic_generator.py` - Generate Pydantic models
- [ ] `/panther/tools/config_migration/import_updater.py` - Update import statements

## Phase 2: Create Adapters for Transition (Priority: HIGH)

### 2.1 Backward Compatibility Layer
**ADD:**
- [ ] `/panther/config/hybrid/adapters/__init__.py`
- [ ] `/panther/config/hybrid/adapters/dataclass_adapter.py` - Dataclass to Pydantic
- [ ] `/panther/config/hybrid/adapters/omega_adapter.py` - OmegaConf integration
- [ ] `/panther/config/hybrid/adapters/legacy_compat.py` - Legacy format support

## Phase 3: Update Core Components (Priority: HIGH)

### 3.1 Replace Main Config Files
**MODIFY:**
- [ ] `/panther/config/__init__.py` - Export new hybrid system
- [ ] `/panther/config/config_manager.py` - Use HybridConfigManager

**REMOVE:**
- [ ] `/panther/config/config_experiment_schema.py` - Replace with hybrid models
- [ ] `/panther/config/config_global_schema.py` - Replace with hybrid models
- [ ] `/panther/config/config_observer_schema.py` - Replace with hybrid models
- [ ] `/panther/config/config_manager_enhanced.py` - No longer needed
- [ ] `/panther/config/config_manager_refactored.py` - No longer needed

### 3.2 Update Existing V2 System
**MODIFY:**
- [ ] `/panther/config/config_manager_v2.py` - Integrate with hybrid system
- [ ] `/panther/config/models/*.py` - Enhance with hybrid base class

### 3.3 Update Builders and Validators
**MODIFY:**
- [ ] `/panther/config/managers/configuration_builder.py` - Use hybrid models
- [ ] `/panther/config/managers/configuration_validator.py` - Validate hybrid models
- [ ] `/panther/config/managers/configuration_merger.py` - Merge hybrid configs
- [ ] `/panther/config/managers/configuration_auto_fixer.py` - Fix hybrid configs

## Phase 4: Update Plugin System (Priority: MEDIUM)

### 4.1 Service Plugin Configs
**MODIFY:**
- [ ] `/panther/plugins/services/config_schema.py` - Use hybrid ServiceConfig
- [ ] `/panther/plugins/services/iut/config_schema.py` - Use hybrid models
- [ ] `/panther/plugins/services/base/config_base.py` - Update base configs

**REMOVE:**
- [ ] All `@dataclass` decorators in service configs
- [ ] All `field()` usage from dataclasses

### 4.2 Protocol Plugin Configs
**MODIFY:**
- [ ] `/panther/plugins/protocols/config_schema.py` - Use hybrid ProtocolConfig
- [ ] `/panther/plugins/protocols/client_server/config_schema.py`
- [ ] `/panther/plugins/protocols/peer_to_peer/config_schema.py`

### 4.3 Environment Plugin Configs
**MODIFY:**
- [ ] `/panther/plugins/environments/network_environment/config_schema.py`
- [ ] `/panther/plugins/environments/execution_environment/config_schema.py`
- [ ] All environment-specific config schemas

### 4.4 Individual Service Implementation Configs
**MODIFY:** (for each service implementation)
- [ ] `/panther/plugins/services/iut/quic/picoquic/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/aioquic/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/quiche/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/quinn/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/lsquic/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/mvfst/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/quic_go/config_schema.py`
- [ ] `/panther/plugins/services/iut/quic/quant/config_schema.py`
- [ ] `/panther/plugins/services/iut/minip/ping_pong/config_schema.py`
- [ ] `/panther/plugins/services/testers/panther_ivy/config_schema.py`

## Phase 5: Update Service Managers (Priority: MEDIUM)

### 5.1 Update Constructor Signatures
**MODIFY:** (all service managers to accept hybrid configs)
- [ ] All files matching pattern `/panther/plugins/services/iut/**/*_manager.py`
- [ ] All files matching pattern `/panther/plugins/services/testers/**/*_manager.py`
- [ ] Base service manager classes

### 5.2 Remove Config Conversions
**MODIFY:**
- [ ] Remove all `hasattr(config, 'value')` enum checks
- [ ] Remove all dataclass to dict conversions
- [ ] Remove all compatibility layers

## Phase 6: Update Core Classes (Priority: MEDIUM)

### 6.1 Test Case Implementation
**MODIFY:**
- [ ] `/panther/core/test_cases/test_case_impl.py` - Use hybrid configs
- [ ] `/panther/core/test_cases/test_case_impl_refactored.py` - Merge or remove

### 6.2 Command Processor
**MODIFY:**
- [ ] `/panther/core/command_processor/command_builder.py` - Accept hybrid configs
- [ ] `/panther/core/command_processor/interfaces.py` - Update interfaces

### 6.3 Docker Builder
**MODIFY:**
- [ ] `/panther/core/docker_builder/docker_builder.py` - Use hybrid configs
- [ ] `/panther/core/docker_builder/service_manager_docker_mixin.py` - Remove hardcoded versions

### 6.4 Experiment Manager
**MODIFY:**
- [ ] `/panther/core/experiment_manager.py` - Use HybridConfigManager

## Phase 7: Update CLI and Entry Points (Priority: LOW)

### 7.1 CLI Commands
**MODIFY:**
- [ ] `/panther/cli/subcommands/run.py` - Use hybrid config loading
- [ ] `/panther/cli/subcommands/config.py` - Update config commands
- [ ] `/panther/__main__.py` - Update main entry point

## Phase 8: Remove Legacy Code (Priority: LOW - AFTER ALL UPDATES)

### 8.1 Delete Deprecated Files
**REMOVE:**
- [ ] `/dev/old/` - Entire directory
- [ ] `/backup_originals/` - Entire directory
- [ ] All files matching `*_original.py`
- [ ] All files matching `*_refactored.py`
- [ ] All files matching `*_legacy.py`
- [ ] `/panther/config/config_manager_refactored.py`
- [ ] `/panther/config/config_manager_enhanced.py`

### 8.2 Clean Up Imports
**MODIFY:** (remove these imports from all files)
- [ ] `from dataclasses import dataclass, field`
- [ ] `from panther.config.config_experiment_schema import *`
- [ ] `from panther.config.config_global_schema import *`
- [ ] All old schema imports

**REPLACE WITH:**
- [ ] `from panther.config.hybrid.models import *`
- [ ] `from panther.config.hybrid.manager import HybridConfigManager`

## Phase 9: Testing and Validation (Priority: HIGH)

### 9.1 Create Tests
**ADD:**
- [ ] `/tests/unit/config/test_hybrid_models.py`
- [ ] `/tests/unit/config/test_hybrid_manager.py`
- [ ] `/tests/unit/config/test_migration.py`
- [ ] `/tests/integration/test_hybrid_config_loading.py`

### 9.2 Update Existing Tests
**MODIFY:**
- [ ] All tests using dataclass configs
- [ ] All tests importing old schemas

## Phase 10: Documentation (Priority: MEDIUM)

### 10.1 Create Documentation
**ADD:**
- [ ] `/docs/configuration/hybrid_system.md`
- [ ] `/docs/configuration/migration_guide.md`
- [ ] `/docs/configuration/examples/`

### 10.2 Update Existing Docs
**MODIFY:**
- [ ] `/README.md` - Update configuration section
- [ ] `/CLAUDE.md` - Document new config system
- [ ] All example configurations

## Processing Order (Following DRY and SOLID)

1. **Create new hybrid system first** (Single Responsibility)
   - Base classes
   - Models
   - Manager

2. **Create adapters** (Open/Closed Principle)
   - Allow old code to work with new system
   - No modification of existing code yet

3. **Update one module at a time** (Interface Segregation)
   - Start with least dependent modules
   - Work up to core components

4. **Test each phase** (Dependency Inversion)
   - Ensure abstractions work before removing concrete implementations

5. **Remove legacy only after validation** (Liskov Substitution)
   - New system must fully replace old system

## Key Principles Applied

### DRY (Don't Repeat Yourself)
- Single model definition for each concept (no dataclass + Pydantic duplicates)
- Shared validation logic in base classes
- Reusable adapters for conversion

### SOLID Principles
- **S**: Each class has one responsibility (HybridConfig, HybridConfigManager)
- **O**: Extend through inheritance, not modification
- **L**: Hybrid models can replace dataclasses everywhere
- **I**: Small, focused interfaces (separate loading, validation, conversion)
- **D**: Depend on abstractions (HybridConfig base class)

## Success Criteria

1. All dataclass configs replaced with hybrid models
2. No duplicate model definitions
3. All tests passing
4. No legacy imports remaining
5. Performance equal or better than current system
6. Full type safety throughout codebase

## Rollback Plan

1. All changes backed up in `.backup/config_refactor_*`
2. Restoration script available
3. Git commits at each major phase
4. Can revert to any phase independently

---

**Total Estimated Changes:**
- Files to ADD: ~35
- Files to MODIFY: ~100+
- Files to REMOVE: ~25
- Lines of code affected: ~10,000+

**Estimated Timeline:** 4-6 weeks for complete migration