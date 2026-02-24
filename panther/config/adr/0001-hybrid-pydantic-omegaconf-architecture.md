# ADR 0001: Hybrid Pydantic-OmegaConf Configuration Architecture

## Status

Accepted

## Context

PANTHER's configuration system must satisfy two competing requirements:

1. **Flexible YAML loading with variable interpolation** -- Experiment configurations reference environment variables, cross-reference other config sections, and use default-value substitution syntax (`${VAR:default}`). They also need deep merging of multiple configuration sources (global config, experiment config, plugin configs, version-specific overrides).

2. **Strict type validation and schema enforcement** -- Plugin configurations define typed fields (ports, timeouts, enum-valued roles, file paths) that must be validated before experiments run. Errors need to be caught early with clear messages, not at Docker build time or during test execution.

No single library handles both concerns well:

- **OmegaConf** excels at YAML loading, hierarchical config composition, variable interpolation (`${section.key}`), and deep merging. However, it provides no type validation, no schema enforcement, and no field-level error messages.
- **Pydantic** excels at data validation, type coercion, schema generation, and structured error reporting. However, it cannot parse OmegaConf interpolation syntax, does not support deep merge natively, and has no built-in YAML loading.

A pure-OmegaConf approach would defer type errors to runtime. A pure-Pydantic approach would lose interpolation and merge capabilities that make YAML configurations maintainable.

## Decision

Use a hybrid architecture where OmegaConf handles loading, interpolation, and merging, and Pydantic handles validation and type safety. The bridge between them is the `BaseConfig` class (`panther/config/core/base.py`), which inherits from both `pydantic.BaseModel` and maintains an internal `OmegaConf.DictConfig` representation for interpolation.

The `ConfigurationManager` is composed from 9 mixins (defined in `panther/config/core/mixins/`) that each own a single configuration concern:

| Order | Mixin                        | Source file              | Responsibility                                                                |
|-------|------------------------------|--------------------------|-------------------------------------------------------------------------------|
| 1     | `ConfigLoadingMixin`         | `config_loading.py`      | Core file/dict/env loading. Parses YAML via `OmegaConf.load()`, supports JSON and `DictConfig` inputs. Hot-reload support. |
| 2     | `EnvironmentHandlingMixin`   | `environment_handling.py`| Resolves `${VAR}` / `${VAR:default}` placeholders. Maps well-known `PANTHER_*` environment variables to config paths. |
| 3     | `ValidationOperationsMixin`  | `validation_ops.py`      | Multi-stage validation pipeline: Pydantic schema validation, business-rule validation, auto-fix suggestions, and structured `ValidationResult` reporting. |
| 4     | `ConfigOperationsMixin`      | `config_operations.py`   | Deep/shallow merge via `MergeStrategy` enum, scalar conflict resolution via `ConflictResolution` enum, dot-notation field access, config transformation helpers. |
| 5     | `CachingMixin`               | `caching.py`             | TTL-based in-memory caching for loaded experiments, validation results, plugin schemas, and version data. Tracks cache hit/miss statistics. |
| 6     | `LoggingFeaturesMixin`       | `logging_features.py`    | Maps per-feature log level overrides (e.g., `docker_build: DEBUG`) from `LoggingConfig` to the Python logging subsystem. |
| 7     | `PluginManagementMixin`      | `plugin_management.py`   | Copies external tester plugin directories into the PANTHER plugin tree. Manages plugin file lifecycle. |
| 8     | `StateManagementMixin`       | `state_management.py`    | Health-check reporting, config state persistence to disk, resource lifecycle management. |
| 9     | `ErrorHandlerMixin`          | (from `panther.core`)    | Centralized error handling and recovery boundary. Imported from `panther.core.exceptions.error_handler_mixin`. |

The mixin inheritance order in `ConfigurationManager` (defined in `panther/config/core/manager.py`) is significant for Python's C3 linearization:

```python
class ConfigurationManager(
    ConfigLoadingMixin,          # 1
    EnvironmentHandlingMixin,    # 2
    ValidationOperationsMixin,   # 3
    ConfigOperationsMixin,       # 4
    CachingMixin,                # 5
    LoggingFeaturesMixin,        # 6
    PluginManagementMixin,       # 7
    StateManagementMixin,        # 8
    ErrorHandlerMixin,           # 9
):
    ...
```

All mixins inherit from `LoggerMixin` (via `panther.core.utils`), and Python's C3 linearization resolves `super().__init__()` chains correctly as long as every mixin calls `super().__init__()`.

### Data Flow

```
YAML file
    |  OmegaConf.load()
    v
DictConfig (raw, with ${interpolation} placeholders)
    |  EnvironmentHandlingMixin resolves placeholders
    v
DictConfig (resolved)
    |  ConfigOperationsMixin merges with defaults/overrides
    v
DictConfig (merged)
    |  Converted to dict, passed to Pydantic model constructor
    v
BaseConfig subclass (validated, typed)
    |  BaseConfig.__init__ also creates an omega_config for later interpolation
    v
Ready for use by experiment manager and plugins
```

### Dual Validator Modules

The project maintains two `universal_validators.py` files with distinct roles:

- **`panther/config/core/components/universal_validators.py`** -- Standalone validation functions (`validate_integer_field`, `validate_time_field`, `validate_enum_field`, `validate_boolean_field`) for imperative use outside Pydantic models. They accept a raw value and field name, return a validated/coerced result, or raise `ValueError`.

- **`panther/config/core/validators/universal_validators.py`** -- Factory functions (`create_enum_validator`, `create_time_string_validator`, etc.) that return Pydantic-compatible validator callables. These are designed for use with `@field_validator` decorators on Pydantic model classes. Pre-configured validators for PANTHER-specific enums (protocol roles, implementation types, log levels) are also provided.

### Dual MergeStrategy / ConflictResolution Enums

Both `ConfigOperationsMixin` (mixin level) and `panther.config.core.components.merger` (component level) define `MergeStrategy` and `ConflictResolution` enums. The component-level versions include additional members (`APPEND_LISTS`, `UNION_LISTS`, `COMBINE`) that the mixin-level versions do not expose. This is intentional: the mixin provides a simplified interface for common operations, while the component provides the full set for advanced use cases.

## Consequences

### Benefits

- **Early error detection**: Pydantic validation catches type mismatches, missing required fields, and constraint violations before experiment execution begins.
- **Readable YAML configs**: OmegaConf interpolation (`${section.key}`, `${ENV_VAR:default}`) keeps configurations DRY and environment-aware.
- **Composable configuration**: Deep merge support allows layering global defaults, experiment overrides, plugin-specific settings, and version-specific configs without manual dict manipulation.
- **Testable mixins**: Each of the 8 configuration mixins (plus `ErrorHandlerMixin`) can be unit-tested in isolation since they each own a single concern.
- **Plugin extensibility**: Plugins contribute their own Pydantic config schemas via `config_schema.py` files, and the `PluginConfigResolver` discovers them dynamically at runtime.

### Costs

- **Two validation systems**: Developers must understand when to use standalone validators (components) vs. Pydantic factory validators. The distinction is documented in each module's docstring.
- **MergeStrategy/ConflictResolution divergence**: The existence of both mixin-level and component-level enums with overlapping but non-identical members requires awareness of which level is being used.
- **OmegaConf-Pydantic bridge overhead**: The `BaseConfig` class maintains both a Pydantic model and an internal `DictConfig`, which duplicates some data in memory. The `omega_config` field is excluded from Pydantic serialization to minimize confusion.
- **MRO sensitivity**: The mixin composition order matters. Reordering mixins can change method resolution behavior, particularly for `__init__` chains. The ordering constraints are documented in the `mixins/__init__.py` docstring.
