# Plugin Structure Synchronization Design

## Problem Statement

PANTHER's plugin system uses two similar but distinct data structures:
- `PluginManifest` - Complete metadata structure used by the decorator registry
- `PluginMetadata` - Lightweight structure used during plugin discovery

Manual conversions between these structures are error-prone and have caused field loss (e.g., `runtime_mode` being dropped), breaking plugin functionality.

## Root Cause Analysis

The original bug occurred in `PluginManager.discover_plugins()`:

```python
# Create a manifest from metadata for catalog compatibility
manifest = PluginManifest(
    name=metadata.name,
    version=metadata.version,
    type=metadata.type,
    # ... other fields
    # MISSING: runtime_mode=metadata.runtime_mode  ❌
)
```

This caused the strace plugin's `runtime_mode="debug"` to be lost, defaulting to `"minimal"` mode instead.

## Architectural Solution

### 1. Automatic Field Discovery

Use Python's `dataclasses.fields()` to automatically discover common fields between both structures:

```python
manifest_fields = {f.name: f for f in fields(PluginManifest)}
metadata_fields = {f.name: f for f in fields(PluginMetadata)}
common_fields = set(manifest_fields.keys()) & set(metadata_fields.keys())
```

### 2. Type-Aware Conversion

Handle type differences automatically:

```python
class FieldConverter:
    def convert_value(self, value, source_type, target_type, field_name):
        # PluginType enum ↔ string conversion
        # Path ↔ string conversion
        # List/dict normalization
        # Dependency object ↔ string conversion
```

### 3. Bidirectional Conversion

```python
class PluginStructureConverter:
    def manifest_to_metadata(self, manifest: PluginManifest) -> PluginMetadata
    def metadata_to_manifest(self, metadata: PluginMetadata) -> PluginManifest
```

### 4. Validation Layer

Ensure no critical fields are lost:

```python
def _validate_conversion(self, data: Dict[str, Any], plugin_name: str):
    required_fields = {'name', 'type', 'version', 'runtime_mode'}
    missing = required_fields - set(data.keys())
    if missing:
        raise ValueError(f"Missing fields for {plugin_name}: {missing}")
```

## Implementation

### Core Module Structure

```
panther/plugins/core/conversion/
├── __init__.py
└── structure_converter.py
```

### Integration Points

1. **PluginDiscovery** - Replace manual conversion:
   ```python
   def _convert_manifest_to_metadata(self, manifest):
       return auto_convert_manifest_to_metadata(manifest)
   ```

2. **PluginManager** - Replace manual manifest creation:
   ```python
   def discover_plugins(self):
       for plugin_name, metadata in discovered_plugins.items():
           manifest = auto_convert_metadata_to_manifest(metadata)
           self.plugin_catalog.catalog[plugin_id] = manifest
   ```

### Convenience Functions

```python
from panther.plugins.core.conversion import (
    auto_convert_manifest_to_metadata,
    auto_convert_metadata_to_manifest,
    get_field_mapping_report,
)
```

## Benefits

### 1. Automatic Evolution
New fields added to `@register_plugin` decorator automatically work without code changes:

```python
@register_plugin(
    # ... existing fields ...
    new_field="value",  # ✅ Automatically handled
)
```

### 2. Type Safety
Automatic type conversion with error handling:
- `PluginType.EXECUTION_ENVIRONMENT` ↔ `"execution_environment"`
- `Path("/path")` ↔ `"/path"`
- `[PluginDependency(...)]` ↔ `["dep1", "dep2"]`

### 3. Validation
Built-in validation prevents field loss:
```python
# Catches missing runtime_mode immediately
ValueError: Missing required fields for strace: {'runtime_mode'}
```

### 4. Maintainability
- Single source of truth for conversion logic
- Comprehensive test coverage
- Field mapping reports for debugging

### 5. Performance
- Reflection only used once per field type
- Results cached for repeated conversions
- Minimal overhead over manual conversion

## Testing Strategy

### 1. Bidirectional Conversion Tests
```python
def test_bidirectional_conversion_preserves_all_fields():
    original_manifest = create_test_manifest_with_all_fields()
    metadata = auto_convert_manifest_to_metadata(original_manifest)
    reconstructed = auto_convert_metadata_to_manifest(metadata)
    assert original_manifest.runtime_mode == reconstructed.runtime_mode
```

### 2. Regression Tests
```python
def test_strace_plugin_runtime_mode_preservation():
    # Simulate exact strace plugin scenario
    strace_manifest = PluginManifest(runtime_mode="debug", ...)
    # Verify runtime_mode preserved through conversions
```

### 3. Field Evolution Tests
```python
def test_new_field_addition_doesnt_break_conversion():
    # Verify adding new fields doesn't break existing conversions
```

## Migration Plan

### Phase 1: Implementation
1. ✅ Create conversion module
2. ✅ Implement PluginStructureConverter
3. ✅ Add comprehensive tests

### Phase 2: Integration
1. Update PluginDiscovery to use auto-conversion
2. Update PluginManager to use auto-conversion
3. Run regression tests

### Phase 3: Validation
1. Test with all existing plugins
2. Verify no fields are lost
3. Performance benchmarking

### Phase 4: Documentation
1. Update plugin development docs
2. Add examples of new field addition
3. Document field mapping behavior

## Field Mapping Report

The converter provides runtime introspection:

```python
report = get_field_mapping_report()
# {
#   'common_fields': ['name', 'version', 'type', 'runtime_mode', ...],
#   'manifest_only_fields': ['config_schema', 'default_config', ...],
#   'metadata_only_fields': ['path', 'status', ...],
#   'coverage': {'manifest_coverage': 0.85, 'metadata_coverage': 0.92}
# }
```

## Error Prevention

This architecture prevents the entire class of bugs caused by:
1. Manual field mapping errors
2. Forgotten fields during structure evolution
3. Type conversion mistakes
4. Missing validation

Future plugin developers can add new decorator parameters without worrying about conversion code - it just works automatically.

## Conclusion

This solution transforms plugin structure synchronization from a manual, error-prone process into an automatic, validated, and maintainable system that evolves gracefully as the plugin architecture grows.
