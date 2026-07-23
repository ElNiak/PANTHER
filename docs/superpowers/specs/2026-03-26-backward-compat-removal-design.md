# Backward Compatibility Debt Removal

**Date**: 2026-03-26
**Branch**: `production` (worktree: `lsp-to-claude`)
**Scope**: Full sweep of all backward compat patterns in `panther/` (excluding `panther_ivy` submodule)

## Context

The PANTHER codebase has accumulated backward compatibility shims across ~50+ instances in 25+ files. These include cascading try/except constructor probing, triple-fallback event emission, legacy event name mapping, multi-attribute identifier chains, getattr/hasattr defensive defaults on typed fields, duplicate type definitions, empty facade classes, and lazy import patterns. These patterns introduce technical debt that masks bugs, prevents schema enforcement, and complicates maintenance.

## Design

### Batch 1: Standardize Service Manager Constructors (CRITICAL)

**Problem**: `plugin_factory.py:403-487` has a triple-nested try/except that catches `TypeError` and inspects exception message strings to determine which constructor parameters a service manager supports.

**Fix**:
- Add `emitter_registry=None` and `global_config=None` as keyword params to `IServiceManager.__init__` in `services_interface.py:112`
- Update `BaseQUICServiceManager.__init__` to pass through to super
- Remove redundant `global_config=None` from all QUIC implementations (aioquic, quiche, quinn, mvfst, quic_go, lsquic, quant, picoquic_shadow)
- Replace the try/except cascade in `plugin_factory.py` with a single direct call

**Files**: `services_interface.py`, `plugin_factory.py`, `quic_service_base.py`, `service_manager_mixin.py`, `iut_service_manager_mixin.py`, `tester_service_manager_mixin.py`, 8 QUIC implementations

### Batch 2: Canonicalize Service Identifier (HIGH)

**Problem**: `service_event_mixin.py:21-48` probes 4 attributes via `hasattr` chain: `name` -> `service_name` -> `implementation_name` -> `__class__.__name__`.

**Fix**: Replace `_get_service_identifier()` with direct `self.service_name` access (guaranteed by `IServiceManager.__init__:190`). Remove all `getattr(service_manager, "service_name", "unknown")` calls.

**Files**: `service_event_mixin.py`, `output_environment_mixins.py`, `service_management.py`

### Batch 3: Collapse Event System to Single API (CRITICAL)

**Problem**: Each `notify_service_*` method (8 total) has 3 fallback layers: `hasattr(emitter, "emit_X_with_validation")` -> direct `service_emitter.emit_X()` -> fallback `event_emitter.emit_X()`. ~200 lines of repeated pattern.

**Fix**:
- After Batch 1, `emitter_registry` is a first-class constructor param. Make `event_emitter` always be an `EmitterRegistry`.
- Flatten all 8 `notify_service_*` methods to direct `self.event_emitter.emit_service_*_with_validation()` calls.
- Fix dual teardown API in `emitter.py:709` (accepts both `ServiceEvent` object and keyword args).

**Files**: `services_interface.py`, `service_event_mixin.py`, `emitter.py`, `service_management.py`

### Batch 4: Remove Legacy Event Name Mapping (HIGH)

**Problem**: `service_event_mixin.py:409-599` is a 190-line dispatcher mapping 10+ old event names to new emitter methods, with a generic error fallback for unknown events.

**Fix**: Replace each caller of `notify_service_event("old_name")` with the appropriate direct emitter call. Delete the dispatcher entirely.

**Callers**: `services_interface.py`, `service_manager_docker_mixin.py`, `ping_pong.py`, `ivy_command_mixin.py`

**Files**: `service_event_mixin.py`, `services_interface.py`, `service_manager_docker_mixin.py`, `ping_pong.py`, `ivy_command_mixin.py`

### Batch 5: Remove Facades + Duplicate Types (LOW)

**5a**: Delete `IUTManagerEventMixin` (`iut_event_mixin.py`) and `TesterManagerEventMixin` (`tester_event_mixin.py`) — empty `pass` classes. Update 11 importers to use `ServiceManagerEventMixin` directly.

**5b**: Consolidate duplicate `ValidationError`/`ValidationResult` from `components/validators.py` and `mixins/validation_ops.py` into single location.

### Batch 6: Clean getattr/hasattr on Typed Fields (MEDIUM)

Replace `getattr`/`hasattr` with direct access where the schema guarantees the field exists:

| File | Pattern | Fix |
|------|---------|-----|
| `experiment_manager.py` | `hasattr(level, "name")`, `getattr(config, "enable_colors", True)` | Direct enum/field access |
| `docker_builder.py` | `getattr(self.global_config.docker, ...)` | Direct Pydantic field access |
| `output_environment_mixins.py` | `getattr(self, "env_sub_type", ...)` | Ensure set in `__init__` |
| `cli/config.py` | `hasattr(config, "tests")` | Direct access (required field) |
| `docker_compose_lifecycle_manager.py` | `hasattr(service, "environment_variables")` | Use canonical field name |
| `services_interface.py:128` | `hasattr(service_type, "name")` | Standardize to string |

**Exceptions kept** (legitimate boundary defense):
- `dict.get()` on untyped external data (events, YAML, Docker API)
- Conditional imports for optional features (Jinja2, NiceGUI)
- Plugin-specific `getattr` in aioquic for duck-typed config

### Batch 7: Infrastructure Cleanup (MEDIUM)

- **ConfigurationManager**: Remove "legacy parameters preserved" docstring, audit param usage
- **Docker Compose command adapter**: Standardize to single `Dict[str, List[ShellCommand]]` input format
- **Plugin loader**: Remove dual module name registration (`sys.modules[simple_name]`)
- **Background service monitor**: Remove Docker Compose v1 naming fallback
- **Phase collection**: Remove `compilation_status_legacy` filename mapping

### Batch 8: Replace Lazy Imports (LOW)

Replace `__getattr__` lazy import patterns in `config/__init__.py` and `validators/__init__.py` with explicit imports. Keep lazy pattern only if circular dependency genuinely requires it (document why).

## Execution Order

```
Batch 1 --> Batch 2 + Batch 3 (parallel) --> Batch 4 --> Batch 5 + 6 + 7 + 8 (parallel)
```

## Verification

- Run `pytest tests/unit/` after each batch
- Run `pytest tests/integration/` after Batches 1, 3, 4
- Grep for removed patterns to confirm zero residual after each batch
- Final: full `pytest tests/` pass
