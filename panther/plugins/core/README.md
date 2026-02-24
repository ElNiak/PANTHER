# Plugin Core System

The `panther/plugins/core/` package implements PANTHER's plugin registration, discovery, cataloging, and instantiation infrastructure. It provides the backbone that allows protocol implementations, testers, environments, and observers to be added without modifying core framework code.

## Registration Flow

The end-to-end lifecycle of a plugin from definition to runtime instance follows this pipeline:

```
@register_plugin() decorator
        |
        v
PluginManifest created (dataclass with full metadata)
        |
        v
Stored in _DECORATED_PLUGINS global registry (dict keyed by "type:name")
        |
        v
PluginDiscovery.discover_plugins() scans directories, imports modules,
reads the registry, converts PluginManifest -> PluginMetadata
        |
        v
PluginCatalog.scan_plugins() indexes manifests, builds dependency graph,
validates config schemas, supports topological dependency resolution
        |
        v
PluginFactory.create_service_manager() / create_environment()
loads plugin class, injects dependencies, instantiates with config
```

## Supported Plugin Types

Defined in `structures/plugin_type.py` as the `PluginType` enum:

| Value                     | Description                                        |
|---------------------------|----------------------------------------------------|
| `IUT`                     | Implementation Under Test (protocol implementations)|
| `TESTER`                  | Testing frameworks and formal verification tools   |
| `SERVICE`                 | Generic service plugins                            |
| `NETWORK_ENVIRONMENT`     | Network simulation and container orchestration     |
| `EXECUTION_ENVIRONMENT`   | Performance profiling and analysis environments    |
| `PROTOCOL`                | Protocol definitions and behavioral specifications |
| `OBSERVER`                | Monitoring and metrics collection plugins          |

## Core Components

| File                          | Class / Contents                  | Purpose                                                                                                  |
|-------------------------------|-----------------------------------|----------------------------------------------------------------------------------------------------------|
| `plugin_decorators.py`        | `register_plugin()`, `register_protocol()`, `version_config()`, helper decorators | Decorator-based registration that stores a `PluginManifest` in the `_DECORATED_PLUGINS` global registry. Also manages `_PROTOCOL_PLUGINS` and `_VERSION_CONFIGS` registries. Provides query functions (`get_decorated_plugins`, `get_plugin_by_name`, `get_plugins_by_type`). |
| `plugin_discovery.py`         | `PluginDiscovery`                 | Scans plugin directories using naming conventions (`plugin_name/plugin_name.py`), imports modules to trigger decorator registration, then reads the global registry. Converts `PluginManifest` to `PluginMetadata` via the structure converter. Supports caching and external plugin paths. |
| `plugin_catalog.py`           | `PluginCatalog`                   | Central catalog for registered plugins. Validates plugin configurations against JSON schemas, resolves dependency graphs via topological sort (Kahn's algorithm), and validates experiment-level plugin requirements. Supports cache persistence to `.plugin_catalog_cache.json`. |
| `plugin_factory.py`           | `PluginFactory`                   | Unified factory that creates instances of all plugin types. Handles dependency injection (EventManager, FastFailHandler, config), class caching, version-specific configuration loading, and error recovery. Replaces the previously separate ServiceFactory and EnvironmentFactory. |
| `plugin_config_resolver.py`   | `PluginConfigResolver`            | Dynamically discovers and loads plugin configuration Pydantic classes from `config_schema.py` files in plugin directories. Resolves service, environment, and protocol configs with LRU caching. Provides a global singleton via `get_plugin_config_resolver()`. |
| `plugin_loader_utils.py`      | `PluginManagerUtils`              | Low-level utilities for dynamic module loading (`importlib.util.spec_from_file_location`), class lookup by name with optional base-class type checking, and standard naming convention support (snake_case directory to PascalCase class). |
| `version_loader.py`           | `VersionLoader`                   | Discovers and loads version-specific YAML configuration files from `version_configs/` directories within plugin trees. Validates versions against protocol-defined version lists. Registers loaded configs into the decorator system's `_VERSION_CONFIGS` registry. |
| `__init__.py`                 | Package exports                   | Re-exports `PluginDiscovery`, `PluginFactory`, `PluginManifest`, `PluginMetadata`, `PluginMetadataLoader`, and `PluginStatus`. |

## Data Structures (`structures/`)

| File                      | Class                    | Purpose                                                                                            |
|---------------------------|--------------------------|----------------------------------------------------------------------------------------------------|
| `plugin_type.py`          | `PluginType` (Enum)      | Enumerates the seven supported plugin types (`IUT`, `TESTER`, `SERVICE`, `NETWORK_ENVIRONMENT`, `EXECUTION_ENVIRONMENT`, `PROTOCOL`, `OBSERVER`). |
| `plugin_manifest.py`      | `PluginManifest` (dataclass) | Full metadata attached to a plugin class by `@register_plugin`. Contains name, version, type, author, description, license, dependencies (`List[PluginDependency]`), config schema, capabilities, tags, entry point, file path, runtime mode, and PANTHER version compatibility bounds. Supports `to_dict()` / `from_dict()` serialization and `is_compatible_with_panther()` version checking. |
| `plugin_metadata.py`      | `PluginMetadata` (dataclass), `PluginMetadataLoader`, `PluginStatus` (Enum) | Lightweight discovery-phase metadata with string-typed fields (vs. enum-typed in `PluginManifest`). `PluginStatus` tracks lifecycle states: `DISCOVERED -> LOADED -> INITIALIZED -> ACTIVE` (or `FAILED` / `UNLOADED`). `PluginMetadataLoader` can extract metadata from modules, decorator data, or directory structures. |
| `plugin_dependency.py`    | `PluginDependency` (dataclass) | Represents a versioned dependency requirement. Uses `packaging.version.SpecifierSet` for semantic version matching via `is_satisfied_by()`. |
| `plugin_registration.py`  | `PluginRegistration` (dataclass) | Runtime state for a loaded plugin instance. Wraps a `PluginManifest` with instance reference, loaded/active flags, load order, and error message. Generates a unique `plugin_id` as `"type:name:version"`. |

## Conversion Utilities (`conversion/`)

| File                      | Class                           | Purpose                                                                                 |
|---------------------------|---------------------------------|-----------------------------------------------------------------------------------------|
| `structure_converter.py`  | `PluginStructureConverter`, `FieldConverter` | Reflection-based automatic conversion between `PluginManifest` and `PluginMetadata`. Discovers common fields via dataclass introspection, handles type conversions (`PluginType` enum to/from string, `Path` to/from string), and maps field-name mismatches (`file_path` in manifest vs. `path` in metadata). Provides module-level convenience functions `auto_convert_manifest_to_metadata()` and `auto_convert_metadata_to_manifest()`. |

## Decorator Subpackage (`decorators/`)

The `decorators/__init__.py` is a placeholder. All decorator logic lives in the top-level `plugin_decorators.py`.

## Usage Example

Registering an IUT plugin:

```python
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType

@register_plugin(
    plugin_type=PluginType.IUT,
    name="picoquic",
    version="1.0.0",
    description="PicoQUIC QUIC implementation",
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
    dependencies=["quic_protocol>=1.0.0"],
    external_dependencies=["docker>=20.0"],
    runtime_mode="minimal",
)
class PicoquicServiceManager(BaseQUICServiceManager):
    """PicoQUIC service manager plugin."""
    ...
```

Registering a protocol:

```python
from panther.plugins.core.plugin_decorators import register_protocol

@register_protocol(
    name="quic",
    type="client_server",
    versions=["rfc9000", "draft-29"],
    default_version="rfc9000",
    description="QUIC transport protocol",
    capabilities=["0-rtt", "connection-migration"],
)
class QuicProtocol:
    ...
```

After registration, the discovery system finds these plugins automatically during PANTHER initialization and makes them available through the `PluginFactory` for experiment execution.
