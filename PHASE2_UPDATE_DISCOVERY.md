# PHASE 2: ELIMINATE FACTORY DUPLICATION AND CONSOLIDATE PLUGIN LOADING

## Overview
Remove the critical functional duplication identified in the plugin system where ServiceFactory and EnvironmentFactory duplicate 300+ lines of PluginFactory functionality. This phase addresses the core DRY violations in plugin creation and loading mechanisms.

## Structural Redundancy Analysis (Post-Phase 1)
Based on precise codebase analysis, here are the ACTUAL duplications to eliminate:

### Critical Factory Duplication (PRIMARY ISSUE)
- **PluginFactory.create_service_manager()** (lines 146-241): 95 lines
- **ServiceFactory.create_service_manager()** (lines 69-147): 78 lines  
- **IDENTICAL LOGIC**: Loading classes, building paths, error handling, parameter passing

- **PluginFactory.create_environment_manager()** (lines 243-335): 92 lines
- **EnvironmentFactory.create_environment_manager()** (lines 73-179): 106 lines
- **IDENTICAL LOGIC**: Same class loading, same instance creation, same fallbacks

### Usage Analysis
- **PluginFactory**: Used in production by `PluginManager.plugin_factory` (line 89-93)
- **ServiceFactory/EnvironmentFactory**: ONLY used in test mocks, never instantiated in production
- **Safe to Remove**: Old factories are legacy code with no active dependencies

## Phase 2 Goals  
1. **DELETE** ServiceFactory and EnvironmentFactory (complete files)
2. **UPDATE** test mocks to use PluginFactory interface
3. **REMOVE** 300+ lines of duplicated factory code
4. **CONSOLIDATE** all plugin creation through single PluginFactory
5. **VALIDATE** no production code depends on removed factories

---

## DETAILED IMPLEMENTATION PLAN

### 1. DELETE DUPLICATE FACTORY FILES

#### 1.1 Remove ServiceFactory (Complete File Deletion)
**File**: `panther/plugins/service_factory.py` (443 lines)

**REASON FOR DELETION**:
- Lines 69-147: `create_service_manager()` duplicates `PluginFactory.create_service_manager()` (lines 146-241)
- Identical class loading logic: `load_plugin_class()` calls
- Identical path building: `implementation_dir / f"{impl_name}.py"`
- Identical error handling and parameter passing
- **ZERO production usage** - only referenced in test mocks

**IMPACT**: 
- Remove 443 lines of duplicate code
- Eliminate primary DRY violation in plugin creation

#### 1.2 Remove EnvironmentFactory (Complete File Deletion)  
**File**: `panther/plugins/environment_factory.py` (498 lines)

**REASON FOR DELETION**:
- Lines 73-179: `create_environment_manager()` duplicates `PluginFactory.create_environment_manager()` (lines 243-335)
- Identical plugin loading patterns and instance creation
- Identical backward compatibility handling for `emitter_registry`
- **ZERO production usage** - only referenced in test mocks

**IMPACT**:
- Remove 498 lines of duplicate code  
- Complete elimination of environment factory duplication

### 2. UPDATE TEST DEPENDENCIES

#### 2.1 Update Integration Test File
**File**: `tests/integration/test_plugin_system_interactions.py`

**Target Locations**:
- Line 78: `self.service_factory = MockServiceFactory()` 
- Line 79: `self.environment_factory = MockEnvironmentFactory()`

**REPLACEMENT**:
```python
# Replace lines 78-79 with:
from panther.plugins.plugin_manager import PluginManager

# In test setup:
self.plugin_manager = PluginManager()
self.plugin_factory = self.plugin_manager.plugin_factory
```

#### 2.2 Update Unit Test File
**File**: `tests/unit/test_plugins/test_plugin_discovery.py`

**Target Locations**:
- Line 20: `from panther.plugins.environment_factory import EnvironmentFactory`
- Line 25: `from panther.plugins.service_factory import ServiceFactory`

**REPLACEMENT**:
```python
# Replace lines 20, 25 with:
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.core.plugin_factory import PluginFactory
```

#### 1.2 Add Discovery Analytics
**ADDITIONS**:
```python
@dataclass
class DiscoveryAnalytics:
    """Analytics for plugin discovery performance and sources."""
    decorator_plugins: int = 0
    yaml_plugins: int = 0
    merged_plugins: int = 0
    discovery_time: float = 0.0
    warnings_issued: List[str] = field(default_factory=list)

def get_discovery_analytics(self) -> DiscoveryAnalytics:
    """Get analytics about last discovery run."""
    
def _emit_yaml_deprecation_warning(self, plugin_name: str, yaml_path: str):
    """Emit deprecation warning for YAML usage."""
```

### 2. ELIMINATE REDUNDANT DISCOVERY CLASSES

#### 2.1 Remove Core Observer Plugin Discovery
**File**: `panther/core/observer/plugins/plugin_discovery.py`

**DELETIONS** (ENTIRE FILE):
- This file contains duplicate functionality now handled by unified discovery
- All classes: `PluginDiscovery`, `PluginMetadata`, `PluginLoader`
- All methods duplicated in main plugin_discovery.py

**IMPACT ANALYSIS**:
- Check all imports of `panther.core.observer.plugins.plugin_discovery`
- Update imports to use `panther.plugins.plugin_discovery`

#### 2.2 Remove Observer Plugin Factory
**File**: `panther/core/observer/plugins/plugin_observer_factory.py`

**DELETIONS** (ENTIRE FILE):
- Factory functionality now handled by unified PluginManager
- Classes: `PluginObserverFactory`, `ObserverPluginConfig`

#### 2.3 Remove Duplicate Plugin Registry
**File**: `panther/core/observer/plugins/plugin_registry.py`

**DELETIONS** (ENTIRE FILE):
- Registry functionality now handled by decorator registry
- Classes: `PluginRegistry`, `PluginEntry`

### 3. CONSOLIDATE PLUGIN MANAGER FUNCTIONALITY

#### 3.1 Enhance Main PluginManager
**File**: `panther/plugins/plugin_manager.py`

**MAJOR REFACTORING**:
```python
class PluginManager:
    """Unified plugin management system using decorator-first discovery."""
    
    def __init__(self, 
                 discovery_mode: str = "decorator_first",  # "decorator_first", "yaml_only", "hybrid"
                 enable_caching: bool = True):
        """Initialize with configurable discovery mode."""
        
    def discover_plugins(self, directories: Optional[List[str]] = None) -> Dict[str, PluginManifest]:
        """Primary plugin discovery method."""
        
    def load_plugin(self, plugin_name: str, plugin_type: str) -> Any:
        """Load and instantiate a plugin."""
        
    def get_plugin_metadata_source(self, plugin_name: str) -> str:
        """Return metadata source: 'decorator', 'yaml', 'merged'."""
        
    def validate_plugin_consistency(self) -> Dict[str, List[str]]:
        """Validate consistency between decorator and YAML metadata."""
```

**PERFORMANCE OPTIMIZATIONS**:
```python
def _cache_discovery_results(self, results: Dict[str, PluginManifest]):
    """Cache discovery results for performance."""
    
def _invalidate_cache(self):
    """Invalidate cached discovery results."""
    
def _should_refresh_cache(self) -> bool:
    """Determine if cache should be refreshed."""
```

#### 3.2 Remove Delegated Plugin Manager
**File**: `panther/plugins/plugin_manager.py` 

**DELETIONS**:
- Remove any remaining delegation patterns to other managers
- Consolidate all functionality into single PluginManager class
- Remove backward compatibility properties that delegate to removed classes

### 4. UPDATE CONFIGURATION INTEGRATION

#### 4.1 Update Config Manager Integration
**File**: `panther/config/config_manager.py`

**UPDATES**:
```python
def _load_plugin_configs(self) -> Dict[str, Any]:
    """Load plugin configurations using decorator-first approach."""
    
def _validate_plugin_dependencies(self) -> List[str]:
    """Validate plugin dependencies using decorator metadata."""
    
def _get_plugin_schema(self, plugin_name: str) -> Dict[str, Any]:
    """Get plugin configuration schema from decorator or YAML."""
```

**DEPRECATED METHODS** (Add deprecation warnings):
```python
@deprecated("Use get_plugin_schema() instead")
def load_yaml_plugin_config(self, plugin_path: str):
    """Deprecated: Load plugin config from YAML file."""
```

#### 4.2 Update Plugin Config Resolver
**File**: `panther/plugins/plugin_config_resolver.py`

**MAJOR UPDATES**:
```python
class PluginConfigResolver:
    """Resolve plugin configurations using decorator-first approach."""
    
    def resolve_plugin_config(self, 
                             plugin_name: str, 
                             user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve plugin configuration using decorator defaults."""
        
    def _get_default_config_from_decorator(self, plugin_name: str) -> Dict[str, Any]:
        """Get default configuration from decorator metadata."""
        
    def _merge_version_configs(self, 
                              base_config: Dict[str, Any],
                              version_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base config with version-specific configuration."""
```

### 5. CREATE YAML DEPRECATION SYSTEM

#### 5.1 New File: panther/plugins/yaml_deprecation.py
**CREATE NEW FILE**:
```python
"""
YAML Deprecation Management System

Handles deprecation warnings and migration tracking for plugin.yaml files.
"""

import warnings
from typing import Set, Dict, List
from pathlib import Path
import logging

class YamlDeprecationManager:
    """Manages deprecation of plugin.yaml files."""
    
    def __init__(self, 
                 emit_warnings: bool = True,
                 track_usage: bool = True):
        self.emit_warnings = emit_warnings
        self.track_usage = track_usage
        self._yaml_usage_tracked: Set[str] = set()
        
    def warn_yaml_usage(self, plugin_name: str, yaml_path: str, context: str = ""):
        """Emit deprecation warning for YAML usage."""
        
    def get_yaml_usage_report(self) -> Dict[str, List[str]]:
        """Get report of YAML usage across the system."""
        
    def mark_plugin_migrated(self, plugin_name: str):
        """Mark a plugin as fully migrated to decorators."""
        
    def check_migration_status(self) -> Dict[str, str]:
        """Check migration status of all plugins."""
```

#### 5.2 Integration with Discovery
**File**: `panther/plugins/plugin_discovery.py`

**ADDITIONS**:
```python
from panther.plugins.yaml_deprecation import YamlDeprecationManager

class PluginDiscovery:
    def __init__(self, ...):
        self.deprecation_manager = YamlDeprecationManager()
        
    def _discover_via_yaml(self, directories: List[str]) -> Dict[str, PluginMetadata]:
        """Fallback discovery with deprecation warnings."""
        for yaml_file in yaml_files:
            self.deprecation_manager.warn_yaml_usage(
                plugin_name, yaml_file, "plugin discovery"
            )
```

### 6. UPDATE CLI INTEGRATION

#### 6.1 Update CLI Commands
**Files**: All CLI command files that use plugin discovery

**UPDATES**:
```python
# Update imports
from panther.plugins.plugin_manager import PluginManager
# Remove: from panther.core.observer.plugins.plugin_discovery import PluginDiscovery

# Update command implementations
def list_plugins_command():
    """List available plugins using unified discovery."""
    manager = PluginManager(discovery_mode="decorator_first")
    plugins = manager.discover_plugins()
    
    # Show metadata source in output
    for name, manifest in plugins.items():
        source = manager.get_plugin_metadata_source(name)
        print(f"{name} (source: {source})")
```

#### 6.2 Add Discovery Mode CLI Option
**ADDITIONS**:
```python
# Add to CLI argument parser
parser.add_argument(
    '--discovery-mode',
    choices=['decorator_first', 'yaml_only', 'hybrid'],
    default='decorator_first',
    help='Plugin discovery mode'
)

parser.add_argument(
    '--show-yaml-warnings',
    action='store_true',
    help='Show deprecation warnings for YAML usage'
)
```

### 7. UPDATE TESTING INFRASTRUCTURE

#### 7.1 Update Plugin Discovery Tests
**File**: `tests/unit/test_plugins/test_plugin_discovery.py`

**MAJOR UPDATES**:
```python
class TestUnifiedPluginDiscovery:
    """Test unified plugin discovery system."""
    
    def test_decorator_first_discovery(self):
        """Test decorator-first discovery mode."""
        
    def test_yaml_fallback_discovery(self):
        """Test YAML fallback when decorators unavailable."""
        
    def test_hybrid_discovery_mode(self):
        """Test hybrid discovery merging decorator and YAML."""
        
    def test_deprecation_warnings(self):
        """Test YAML deprecation warnings."""
        
    def test_discovery_analytics(self):
        """Test discovery performance analytics."""
```

#### 7.2 Update Plugin Manager Tests
**File**: `tests/unit/test_plugins/test_plugin_manager.py`

**DELETIONS**:
- Remove tests for removed classes (observer plugin discovery, etc.)
- Remove tests for delegation patterns

**ADDITIONS**:
```python
def test_unified_plugin_loading(self):
    """Test unified plugin loading system."""
    
def test_metadata_source_tracking(self):
    """Test tracking of plugin metadata sources."""
    
def test_consistency_validation(self):
    """Test validation between decorator and YAML metadata."""
```

### 8. PERFORMANCE OPTIMIZATIONS

#### 8.1 Implement Smart Caching
**File**: `panther/plugins/plugin_discovery.py`

**ADDITIONS**:
```python
class DiscoveryCache:
    """Intelligent caching for plugin discovery results."""
    
    def __init__(self, cache_ttl: int = 300):  # 5 minutes default
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
    def get_cached_discovery(self, cache_key: str) -> Optional[Dict[str, PluginMetadata]]:
        """Get cached discovery results if valid."""
        
    def cache_discovery_results(self, cache_key: str, results: Dict[str, PluginMetadata]):
        """Cache discovery results with timestamp."""
        
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern."""
```

#### 8.2 Optimize Module Import Performance
**ADDITIONS**:
```python
def _lazy_import_plugin_modules(self, directories: List[str]):
    """Lazily import plugin modules only when needed."""
    
def _batch_import_modules(self, module_paths: List[str]):
    """Import multiple modules in batch for better performance."""
```

---

## FILES TO MODIFY/DELETE/CREATE

### Files to DELETE (COMPLETE REMOVAL):
1. `panther/core/observer/plugins/plugin_discovery.py` - Duplicate discovery functionality
2. `panther/core/observer/plugins/plugin_observer_factory.py` - Duplicate factory
3. `panther/core/observer/plugins/plugin_registry.py` - Duplicate registry
4. `panther/core/observer/plugins/__init__.py` - If now empty

### Files to MODIFY (MAJOR UPDATES):
1. `panther/plugins/plugin_discovery.py` - Refactor to decorator-first approach
2. `panther/plugins/plugin_manager.py` - Consolidate all plugin management
3. `panther/plugins/plugin_config_resolver.py` - Update for decorator-first config
4. `panther/config/config_manager.py` - Update plugin config integration
5. All CLI command files - Update imports and usage

### Files to CREATE:
1. `panther/plugins/yaml_deprecation.py` - Deprecation management
2. `tests/unit/test_yaml_deprecation.py` - Deprecation tests
3. `tests/integration/test_unified_discovery.py` - Integration tests

### Import Updates Required:
**Replace these imports throughout codebase**:
```python
# OLD (to be removed)
from panther.core.observer.plugins.plugin_discovery import PluginDiscovery
from panther.core.observer.plugins.plugin_registry import PluginRegistry

# NEW (unified system)
from panther.plugins.plugin_discovery import PluginDiscovery
from panther.plugins.plugin_manager import PluginManager
```

---

## VALIDATION AND TESTING

### Automated Validation:
1. **Discovery Consistency**: Verify decorator and YAML discovery return same plugins
2. **Performance Benchmarks**: Ensure decorator discovery is faster than YAML
3. **Deprecation Tracking**: Verify all YAML usage is properly tracked and warned
4. **Import Validation**: Check all import updates are correct

### Manual Testing:
1. **CLI Commands**: All plugin-related CLI commands work correctly
2. **Plugin Loading**: All existing plugins load without issues
3. **Error Handling**: Graceful handling when decorator or YAML data is missing
4. **Backward Compatibility**: Existing configurations continue to work

### Success Criteria:
- [ ] Plugin discovery time reduced by >50%
- [ ] Zero plugins fail to load during transition
- [ ] All duplicate classes successfully removed
- [ ] Deprecation warnings properly displayed
- [ ] CLI commands work with unified system
- [ ] Performance benchmarks show improvement

---

## ROLLBACK PLAN

### If Issues Arise:
1. **Temporary Fallback**: Switch discovery_mode to "yaml_only"
2. **Selective Rollback**: Restore specific removed files if needed
3. **Import Restoration**: Revert import changes in stages
4. **Performance Regression**: Disable caching if it causes issues

### Monitoring Points:
- Plugin load success rate
- Discovery performance metrics
- CLI command functionality
- User-reported issues with plugin loading

---

## ESTIMATED EFFORT
- **Development Time**: 4-6 days
- **Testing Time**: 3 days
- **Files Deleted**: 4 files
- **Files Modified**: ~15 files
- **Files Created**: 3 new files
- **Lines Removed**: ~1500 lines
- **Lines Added**: ~800 lines

This phase significantly reduces code duplication while establishing decorator-based discovery as the primary plugin source, setting the stage for complete YAML elimination in Phase 3.