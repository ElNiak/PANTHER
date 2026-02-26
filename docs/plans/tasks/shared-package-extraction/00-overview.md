# Shared Package Extraction - Task Overview

## Phase 1: `panther-ivy-types` (stdlib only, zero external deps)

| Task | File | Description | Risk | Depends On |
|------|------|-------------|------|------------|
| 01 | task-01-scaffold-panther-ivy-types.md | Scaffold package directory and pyproject.toml | Low | None |
| 02 | task-02-extract-api-types.md | Extract 6 API dataclasses from panther_ivy | Low | 01 |
| 03 | task-03-extract-analysis-scope-types.md | Extract RequirementNode, StateVarNode, ActionNode, PropertyNode, ExportImportInfo, TestScope | Low | 01 |
| 04 | task-04-create-ivy-reexport-shims.md | Replace originals with re-export shims | Low | 02, 03 |
| 05 | task-05-verify-phase1.md | Install and verify all imports + tests | Low | 04 |

## Phase 2: `panther-types` (deps: pydantic>=2, omegaconf>=2.3)

| Task | File | Description | Risk | Depends On |
|------|------|-------------|------|------------|
| 06 | task-06-scaffold-panther-types.md | Scaffold package directory and pyproject.toml | Low | 05 |
| 07 | task-07-extract-config-base.md | Extract BaseConfig + BaseUnifiedModel | Medium | 06 |
| 08 | task-08-extract-config-enums-models.md | Extract ImplementationType, ProtocolRole, VersionBase, Parameter | Low | 07 |
| 09 | task-09-extract-plugin-config.md | Extract BasePluginConfig -> ServicePluginConfig hierarchy | Medium | 08 |
| 10 | task-10-extract-event-types.md | Extract BaseEvent, EventType, BaseState, StateTransition, StateManager | Low | 06 |
| 11 | task-11-extract-exceptions.md | Extract PantherException hierarchy (fast_fail + experiment + network) | Low | 06 |
| 12 | task-12-extract-plugin-structures.md | Extract PluginType, PluginMetadata (not PluginManifest - too many deps) | Low | 06 |
| 13 | task-13-create-types-reexport-shims.md | Create re-export shims in panther, update panther_ivy imports | Medium | 09, 10, 11, 12 |
| 14 | task-14-verify-phase2.md | Install and verify all imports + run full test suite | Medium | 13 |

## Phase 2b: Mixin Interfaces

| Task | File | Description | Risk | Depends On |
|------|------|-------------|------|------------|
| 15 | task-15-define-mixin-interfaces.md | Define Protocol + ABC interfaces for key mixin categories (design sketch, ~8-10 interfaces) | Low | 14 |
| 16 | task-16-verify-mixin-interfaces.md | Verify existing concrete mixins satisfy protocols | Low | 15 |

## Phase 3: `panther.api` Module

| Task | File | Description | Risk | Depends On |
|------|------|-------------|------|------------|
| 17 | task-17-scaffold-panther-api.md | Scaffold panther/api/ package with __init__.py | Low | 14 |
| 18 | task-18-api-config-plugins.md | Implement config.py + plugins.py (wrapping managers) | Medium | 17 |
| 19 | task-19-api-experiments-docker.md | Implement experiments.py + docker.py | Medium | 17 |
| 20 | task-20-api-events-schemas.md | Implement events.py + schemas.py | Medium | 17 |
| 21 | task-21-test-panther-api.md | Write tests for all panther.api modules | Medium | 18, 19, 20 |
| 22 | task-22-integration-verification.md | Full integration test across all packages | Medium | 21 |

## Key Design Decisions

### What goes in `panther-types` vs stays in `panther`

**Extracted** (cross-project deps only):
- BaseConfig, BaseUnifiedModel (config base classes)
- BasePluginConfig, ServicePluginConfig (panther_ivy inherits these)
- ImplementationType, ProtocolRole, VersionBase, Parameter (enums + simple models)
- BaseEvent, EventType, BaseState, StateTransition, StateManager (event foundations)
- PantherException hierarchy (error handling contracts)
- PluginType, PluginMetadata (plugin metadata)

**NOT extracted** (too many internal deps):
- ServiceConfig (550 lines, depends on get_plugin_config_resolver, ServiceDockerOverrideConfig)
- ProtocolConfig (depends on validators module with circular lazy imports)
- EnvironmentConfig (runtime import of get_plugin_config_resolver)
- IObserver (imports BaseEvent from panther.core.events)
- ITypedObserver (imports ALL concrete event types - 100+ imports)
- PluginManifest (depends on PluginDependency, packaging.version, DockerRequirements)
- FastFailHandler (536 lines of business logic, not just types)
- universal_validators.py (lazy imports back to service.py - circular)

### Circular dependency handling

`service.py` imports from `..validators` which lazy-imports from `service.py`:
- `universal_validators.py:protocol_role_validator()` -> lazy imports `ProtocolRole` from service
- `universal_validators.py:implementation_type_validator()` -> lazy imports `ImplementationType` from service

**Strategy**: Extract the enums (ProtocolRole, ImplementationType) to panther-types. Update lazy imports in validators to import from panther_types. The validators themselves stay in panther.

### Observer interfaces in panther-types

Rather than extracting the existing IObserver (which imports BaseEvent), Phase 2b creates NEW lightweight Protocol interfaces that describe the observer contract without requiring panther imports. These are structural types for type-checking, not replacements for the existing ABC.

---

## Review Notes (2026-02-26)

Comprehensive review validated all assumptions against the actual codebase. Full review at:
`/Users/elniak/.claude/plans/delegated-coalescing-lightning.md`

### Corrections Applied
- **task-03**: Fixed StateVarNode (removed 5 invented fields), RequirementNode (fixed optionality), ExportImportInfo (List not Set), added has_exports property and TestScope methods
- **task-03**: Added ActionNode and PropertyNode extraction (aligning with overview __init__.py)
- **task-01**: Updated __init__.py to include ActionNode/PropertyNode
- **task-11**: Fixed exception test enum values (CRITICAL/HIGH/MEDIUM/LOW, not ERROR/WARNING) and constructor signatures
- **Build system**: Standardized on setuptools (not hatchling) in high-level plan
- **task-05**: Added dependency declaration step

### Known Limitations
- **Phase 2b (task-15)**: Mixin interfaces are design sketches. Method signatures must be verified from actual source during implementation. "9 categories" is approximate (29+ actual mixin classes exist).
- **Phase 3 (tasks 17-22)**: Underspecified. ExperimentManager is per-experiment (no list/status/stop). ConfigurationManager method names differ from proposed API. Needs separate design phase.
- **Missing**: No rollback strategy, no CI/CD plan, no `py.typed` markers, no package dependency declarations in consuming pyproject.toml files.
