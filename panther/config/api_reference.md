# PANTHER Configuration API Reference

## Core Classes

### BaseConfig

```python
class BaseConfig(BaseModel, ABC)
```

Base configuration class combining Pydantic BaseModel and OmegaConf features.

This class provides a hybrid configuration model that combines:
- Pydantic validation and type checking
- OmegaConf interpolation and merging capabilities
- YAML/JSON serialization support
- Deep merging with conflict resolution

#### Parameters

**Configuration Settings:**
- `extra = "allow"`: Allow extra fields for flexibility
- `validate_assignment = True`: Validate field assignments
- `use_enum_values = True`: Use enum values in serialization
- `arbitrary_types_allowed = True`: Allow complex types

#### Methods

##### `__init__(**data)`
Initialize configuration instance with OmegaConf interpolation support.

**Args:**
- `**data`: Configuration data as keyword arguments

**Example:**
```python
config = BaseConfig(name="test", port="${PORT:8080}")
```

##### `validate_config() -> BaseConfig`
Perform full validation with context awareness.

**Returns:**
- `BaseConfig`: Self for method chaining

**Raises:**
- `ValidationError`: If validation fails

**Example:**
```python
config = MyConfig(name="test").validate_config()
```

##### `to_omega() -> DictConfig`
Convert configuration to OmegaConf DictConfig format.

**Returns:**
- `DictConfig`: OmegaConf representation enabling interpolation

**Example:**
```python
omega_config = config.to_omega()
resolved_value = omega_config.database.host  # Resolves ${DB_HOST}
```

##### `from_omega(config: DictConfig) -> T`
Create configuration instance from OmegaConf DictConfig.

**Args:**
- `config (DictConfig)`: OmegaConf configuration

**Returns:**
- `T`: New instance of the configuration class

**Example:**
```python
omega_config = OmegaConf.load("config.yaml")
config = MyConfig.from_omega(omega_config)
```

##### `to_dict(exclude_none: bool = True) -> Dict[str, Any]`
Convert configuration to standard Python dictionary.

**Args:**
- `exclude_none (bool)`: Whether to exclude None values (default: True)

**Returns:**
- `Dict[str, Any]`: Dictionary representation

**Example:**
```python
config_dict = config.to_dict()
json.dump(config_dict, file)
```

##### `merge_with(other: BaseConfig, strategy: str = "deep") -> BaseConfig`
Merge with another configuration instance.

**Args:**
- `other (BaseConfig)`: Configuration to merge with
- `strategy (str)`: Merge strategy ("deep", "replace", "append")

**Returns:**
- `BaseConfig`: New merged configuration instance

**Example:**
```python
merged = base_config.merge_with(override_config, strategy="deep")
```

##### `get_field(path: str, default: Any = None) -> Any`
Get field value using dot notation path.

**Args:**
- `path (str)`: Dot-notation field path (e.g., "database.host")
- `default (Any)`: Default value if field not found

**Returns:**
- `Any`: Field value or default

**Example:**
```python
host = config.get_field("database.host", "localhost")
port = config.get_field("database.port", 5432)
```

##### `set_field(path: str, value: Any) -> None`
Set field value using dot notation path.

**Args:**
- `path (str)`: Dot-notation field path
- `value (Any)`: Value to set

**Example:**
```python
config.set_field("database.host", "production-db")
config.set_field("logging.level", "DEBUG")
```

##### `to_yaml(file_path: Optional[str] = None) -> str`
Serialize configuration to YAML format.

**Args:**
- `file_path (Optional[str])`: File path to save YAML (optional)

**Returns:**
- `str`: YAML string representation

**Example:**
```python
yaml_str = config.to_yaml()
config.to_yaml("output.yaml")  # Save to file
```

##### `from_yaml(yaml_str: str) -> T`
Create configuration from YAML string.

**Args:**
- `yaml_str (str)`: YAML configuration string

**Returns:**
- `T`: New configuration instance

**Example:**
```python
yaml_content = """
name: test-service
port: 8080
database:
  host: ${DB_HOST:localhost}
"""
config = MyConfig.from_yaml(yaml_content)
```

---

## ConfigurationManager

```python
class ConfigurationManager(
    ConfigLoadingMixin,
    EnvironmentHandlingMixin,
    ValidationOperationsMixin,
    ConfigOperationsMixin,
    CachingMixin,
    LoggingFeaturesMixin,
    PluginManagementMixin,
    StateManagementMixin,
    ErrorHandlerMixin,
)
```

Primary configuration manager orchestrating all configuration operations through mixin composition.

### Core Methods

##### `load_and_validate_config(source: Union[str, Dict, Path], auto_fix: bool = False) -> ExperimentConfig`
Load and validate configuration from various sources.

**Args:**
- `source (Union[str, Dict, Path])`: Configuration source (file path, dict, or Path object)
- `auto_fix (bool)`: Enable automatic fixing of common issues (default: False)

**Returns:**
- `ExperimentConfig`: Validated configuration instance

**Raises:**
- `ConfigurationError`: If loading or validation fails
- `FileNotFoundError`: If configuration file not found

**Example:**
```python
manager = ConfigurationManager()

# Load from file with auto-fix
config = manager.load_and_validate_config("experiment.yaml", auto_fix=True)

# Load from dictionary
config_dict = {"tests": [...]}
config = manager.load_and_validate_config(config_dict)
```

##### `load_from_file(file_path: Union[str, Path], enable_cache: bool = True) -> Dict[str, Any]`
Load configuration from file with caching support.

**Args:**
- `file_path (Union[str, Path])`: Path to configuration file
- `enable_cache (bool)`: Enable caching for performance (default: True)

**Returns:**
- `Dict[str, Any]`: Raw configuration dictionary

**Example:**
```python
# Load with caching
config_dict = manager.load_from_file("experiment.yaml")

# Load without caching
config_dict = manager.load_from_file("experiment.yaml", enable_cache=False)
```

##### `validate_experiment_config(config: ExperimentConfig, strict: bool = False) -> ValidationResult`
Validate experiment configuration with multiple validation stages.

**Args:**
- `config (ExperimentConfig)`: Configuration to validate
- `strict (bool)`: Enable strict validation mode (default: False)

**Returns:**
- `ValidationResult`: Detailed validation results

**Example:**
```python
result = manager.validate_experiment_config(config, strict=True)

if result.is_valid:
    print("Configuration is valid")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

##### `merge_configs(base: Dict, override: Dict, strategy: str = "deep_merge") -> Dict`
Merge two configuration dictionaries with specified strategy.

**Args:**
- `base (Dict)`: Base configuration
- `override (Dict)`: Override configuration
- `strategy (str)`: Merge strategy ("deep_merge", "replace", "append")

**Returns:**
- `Dict`: Merged configuration

**Example:**
```python
merged = manager.merge_configs(
    base_config,
    override_config,
    strategy="deep_merge"
)
```

### Plugin Management Methods

##### `discover_plugins(plugin_type: Optional[str] = None) -> List[PluginInfo]`
Discover available plugins with optional type filtering.

**Args:**
- `plugin_type (Optional[str])`: Filter by plugin type ("iut", "tester", etc.)

**Returns:**
- `List[PluginInfo]`: List of discovered plugins

**Example:**
```python
all_plugins = manager.discover_plugins()
iut_plugins = manager.discover_plugins(plugin_type="iut")
```

##### `load_plugin_schema(plugin_name: str) -> Dict[str, Any]`
Load configuration schema for a specific plugin.

**Args:**
- `plugin_name (str)`: Name of the plugin

**Returns:**
- `Dict[str, Any]`: Plugin configuration schema

**Raises:**
- `PluginNotFoundError`: If plugin not found

**Example:**
```python
quiche_schema = manager.load_plugin_schema("quiche")
print(quiche_schema.get("required_fields", []))
```

### Caching Methods

##### `enable_cache(ttl: int = 300, max_size: int = 128) -> None`
Enable configuration caching with TTL and size limits.

**Args:**
- `ttl (int)`: Time-to-live in seconds (default: 300)
- `max_size (int)`: Maximum cache entries (default: 128)

**Example:**
```python
manager.enable_cache(ttl=600, max_size=256)
```

##### `get_cache_stats() -> CacheStats`
Get cache performance statistics.

**Returns:**
- `CacheStats`: Cache statistics including hit rate and memory usage

**Example:**
```python
stats = manager.get_cache_stats()
print(f"Hit rate: {stats.hit_rate}%")
print(f"Memory usage: {stats.memory_usage} MB")
```

##### `warm_cache(config_files: List[str]) -> None`
Pre-load configurations into cache for better performance.

**Args:**
- `config_files (List[str])`: List of configuration files to cache

**Example:**
```python
manager.warm_cache([
    "experiment1.yaml",
    "experiment2.yaml",
    "base_config.yaml"
])
```

### Environment Handling Methods

##### `load_with_environment(config_path: str, env_vars: Optional[Dict[str, str]] = None) -> Dict`
Load configuration with environment variable resolution.

**Args:**
- `config_path (str)`: Path to configuration file
- `env_vars (Optional[Dict[str, str]])`: Additional environment variables

**Returns:**
- `Dict`: Configuration with resolved environment variables

**Example:**
```python
config = manager.load_with_environment(
    "config.yaml",
    env_vars={"ENV": "production", "DEBUG": "false"}
)
```

##### `resolve_environment_variables(config: Dict, env_context: Dict[str, str]) -> Dict`
Resolve environment variables in configuration.

**Args:**
- `config (Dict)`: Configuration dictionary
- `env_context (Dict[str, str])`: Environment variable context

**Returns:**
- `Dict`: Configuration with resolved variables

---

## Validation Classes

### ValidationResult

```python
class ValidationResult
```

Comprehensive validation result container with detailed error reporting.

#### Properties

- `is_valid (bool)`: Whether validation passed
- `errors (List[str])`: List of validation errors
- `warnings (List[str])`: List of validation warnings
- `suggestions (List[str])`: List of improvement suggestions

#### Methods

##### `get_summary() -> str`
Get concise validation summary.

**Returns:**
- `str`: Summary of validation results

##### `get_detailed_report() -> str`
Get detailed validation report with all errors and suggestions.

**Returns:**
- `str`: Detailed validation report

**Example:**
```python
result = validator.validate_experiment_config(config)
print(result.get_summary())
if not result.is_valid:
    print(result.get_detailed_report())
```

### UnifiedValidator

```python
class UnifiedValidator
```

Multi-stage validation framework combining schema, business rules, and compatibility validation.

##### `validate_experiment_config(config: ExperimentConfig) -> ValidationResult`
Validate complete experiment configuration.

**Args:**
- `config (ExperimentConfig)`: Configuration to validate

**Returns:**
- `ValidationResult`: Comprehensive validation results

##### `validate_schema_only(config: ExperimentConfig) -> ValidationResult`
Validate only Pydantic schema requirements.

##### `validate_business_rules_only(config: ExperimentConfig) -> ValidationResult`
Validate only business logic rules.

##### `validate_compatibility_only(config: ExperimentConfig) -> ValidationResult`
Validate only plugin and version compatibility.

---

## Exception Classes

### ConfigurationError

```python
class ConfigurationError(Exception)
```

Base exception for configuration-related errors.

### PluginNotFoundError

```python
class PluginNotFoundError(ConfigurationError)
```

Raised when a requested plugin cannot be found.

### ValidationError

```python
class ValidationError(ConfigurationError)
```

Raised when configuration validation fails.

---

## Usage Examples

### Basic Configuration Loading
```python
from panther.config.core.manager import ConfigurationManager

manager = ConfigurationManager()
config = manager.load_and_validate_config("experiment.yaml")

# Access configuration data
print(f"Experiment: {config.tests[0].name}")
print(f"Service count: {len(config.tests[0].services)}")
```

### Advanced Configuration with Auto-Fix
```python
manager = ConfigurationManager()
manager.enable_cache(ttl=600)

try:
    config = manager.load_and_validate_config(
        "experiment.yaml",
        auto_fix=True
    )
    print("Configuration loaded successfully")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

### Custom Validation
```python
from panther.config.core.components.validators import UnifiedValidator

validator = UnifiedValidator()
result = validator.validate_experiment_config(config)

if result.is_valid:
    print(result.get_summary())
else:
    print("Validation failed:")
    for error in result.errors:
        print(f"  - {error}")
```
