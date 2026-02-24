# Phase 0 - Dispatch 1C: Configuration System Documentation Evidence

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE
**Files Analyzed:** panther/config/README.md, api_reference.md, DEVELOPER_GUIDE.md, tutorial/quickstart.md, core/README.md, core/mixins/README.md
**Cross-referenced:** Pydantic models in panther/config/core/models/, manager.py, base.py, validators.py, config_loading.py

## Critical Findings

### CRITICAL: ADR File Does Not Exist
- `panther/config/adr/0001-hybrid-pydantic-omegaconf-architecture.md` referenced in CLAUDE.md
- Directory `panther/config/adr/` does not exist
- Severity: CRITICAL (ACC-06)

### CRITICAL: api_reference.md Method Names Wrong
| Documented | Actual | Source |
|-----------|--------|--------|
| `BaseConfig.merge_with(other, strategy)` | `merge(other)` - no strategy param | api_reference.md:96 |
| `BaseConfig.to_yaml(file_path=None)` | `to_yaml(resolve=True)` - no file_path | api_reference.md:140 |
| `BaseConfig.from_yaml(yaml_str)` classmethod | Does not exist; use `load(path)` | api_reference.md:155 |
| `BaseConfig.set_field(path, value)` | `update_field(field_path, value)` | api_reference.md:127 |
| `ConfigurationManager.load_and_validate_config(source, auto_fix)` | `load_experiment_config(source, defaults, validate, auto_fix)` | api_reference.md:197 |

### CRITICAL: ValidationResult API Fabricated
- `ValidationResult.suggestions`, `.get_summary()`, `.get_detailed_report()` documented but none exist
- `ConfigurationValidator` import path `panther.config.managers.configuration_validator` does not exist
- Actual class: `UnifiedValidator` at `components/validators.py:66`
- Severity: CRITICAL (ACC-02)

### CRITICAL: Plugin Schema Pattern Uses Wrong Base
- README documents plugin schemas using `@dataclass`
- Actual base is `BasePluginConfig(BaseUnifiedModel)` - a Pydantic model
- Following the documented pattern produces incompatible configs
- Severity: CRITICAL (ACC-04)

## Major Findings

| Finding | Source | Severity |
|---------|--------|----------|
| `services` documented as list but actual type is `Dict[str, ServiceConfig]` | README.md:317-395 | MAJOR (ACC-03) |
| 6 non-existent config fields documented: `logging.file`, `logging.console`, `paths.config_dir`, `paths.data_dir`, `docker.pull_images`, `docker.cleanup_on_exit` | README.md:193-213 | MAJOR (ACC-01) |
| `docker.network_name` documented but field is `network_mode` | README.md:213 | MAJOR (ACC-01) |
| `debug_environment` field in test config does not exist | README.md:49 | MAJOR (ACC-01) |
| Server port rule documented as "must" (hard error) but implementation is warning only | README.md:453 | MAJOR (ACC-05) |
| README lists 8 mixins but ConfigurationManager has 9 (ErrorHandlerMixin omitted) | README.md:119-127 | MAJOR (CMP-10) |
| Thread safety contradiction: manager.py says "Not thread-safe" but core/README.md and mixins/README.md claim thread-safe | manager.py:97 vs core/README.md:148 | MAJOR (CON-01) |
| OmegaConf described as doing "validation" but it does interpolation/merging; Pydantic validates | README.md:19 | MAJOR (ACC-01) |
| `panther config validate --auto-fix --output` flags documented but don't exist | README.md:463-469 | MAJOR (ACC-02) |
| Old argparse flags `--validate-config`, `--show-schema` etc. documented but don't exist | README.md:596-608 | MAJOR (ACC-02) |
| `BaseUnifiedModel` is the concrete base for all models but README only mentions `BaseConfig` | README.md:101 | MAJOR (CMP-10) |
| Quickstart references `config.global_config.paths.output_dir` but ExperimentConfig has no `global_config` | quickstart.md:65 | MAJOR (ACC-01) |
| Quickstart references `load_and_validate_config()` which doesn't exist | quickstart.md:61 | MAJOR (ACC-02) |

## Massively Undocumented Config Fields

The following subsystems exist in code but are absent from all user-facing docs:

### GlobalConfig Undocumented Sections
- **progress** -> `ProgressConfig`: 6 fields (progress_bar, spinner, test_status, emojis, etc.)
- **fast_fail** -> `FastFailConfig`: 7 fields (enabled, test_level, docker/service/ivy failures, etc.)
- **metrics** -> `MetricsConfig`: 5 fields (enabled, collect_system, publish_interval, etc.)
- **observers** -> `ObserversConfig`: 4 sub-observer configs (logger, metrics, storage, experiment)

### DockerConfig Undocumented Fields (10 fields)
- `log_docker_image_build`, `user_mapping`, `build_args`, `cache_from`, `network_mode`
- `use_buildx`, `target_platform`, `buildx_builder`, `multi_platform`, `no_docker_cache`

### LoggingConfig Undocumented Fields
- `enable_colors`, `debug_file_logging`, `feature_levels` (with 16 per-feature log level overrides)

### TestConfig Undocumented Fields
- `fast_fail_enabled`, `continue_on_failure`, `collect_artifacts`

### ServiceConfig Undocumented Fields (9 fields)
- `network`, `environment`, `volumes`, `command_override`, `working_directory`
- `depends_on`, `restart_policy`, `docker` (per-service override), `plugin_config`

### README Omits 20+ Model Classes
Including: `TestConfig`, `StepsConfig`, `ExperimentMetadata`, `ProgressConfig`, `FastFailConfig`, `MetricsConfig`, `DockerConfig`, `DockerUserMappingConfig`, `ServiceDockerOverrideConfig`, `ObserversConfig`, `LoggerObserverConfig`, `MetricsObserverConfig`, `StorageObserverConfig`, `ExperimentObserverConfig`, `NetworkConfig`, `ProtocolConfig`, `ImplementationConfig`, `BaseProtocolConfig`, `ClientServerProtocolConfig`, `PeerToPeerProtocolConfig`, `BasePluginConfig` and variants.

## Confirmed Accurate

| Claim | Source | Status |
|-------|--------|--------|
| `ExperimentConfig`, `ServiceConfig`, `GlobalConfig`, `EnvironmentConfig` names | README.md:140-143 | ACCURATE |
| `StepsConfig.wait` must be positive | README.md:88 | ACCURATE |
| Client services must specify target | README.md:64 | ACCURATE |
| QUIC default port 4443 | README.md:447 | ACCURATE |
| Port format validation `host:container` | README.md | ACCURATE |
| `ConfigurationManager(auto_fix_configs, enable_cache)` constructor | README.md:665 | ACCURATE |

## Summary Statistics
- **Total claims verified:** 33
- **ACCURATE:** 8 (24.2%)
- **INACCURATE/MISSING:** 22 (66.7%)
- **UNDOCUMENTED (code exists, no docs):** 3 categories with 40+ fields
