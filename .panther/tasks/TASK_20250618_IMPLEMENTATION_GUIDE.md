# Implementation Guide for Legacy Code Removal

## Quick Start Commands

### 1. Find All Duplication Patterns
```bash
# Find duplicate plugin methods
grep -n "def add_plugin_" panther/config/config_manager.py
grep -n "def remove_plugin_" panther/config/config_manager.py
grep -n "def get_all_.*_classes" panther/config/config_manager.py

# Count duplication
grep -c "def add_plugin_" panther/config/config_manager.py
# Expected: 5+ methods

grep -c "def remove_plugin_" panther/config/config_manager.py  
# Expected: 5+ methods
```

### 2. Analyze Config Schemas
```bash
# Find all config schemas
find panther/ -name "config_schema.py" -type f | wc -l
# Expected: 29 files

# Check for Pydantic vs Marshmallow
grep -l "from marshmallow" panther/**/config_schema.py
grep -l "from pydantic" panther/**/config_schema.py

# Find schemas without error handling
for f in $(find panther/ -name "config_schema.py"); do
  if ! grep -q "try\|except" "$f"; then
    echo "No error handling: $f"
  fi
done
```

### 3. Find Hardcoded Values
```bash
# Find hardcoded ports
grep -r "4443\|8080\|3000\|5000" panther/ --include="*.py" | grep -v test

# Find hardcoded paths
grep -r '"/usr/bin\|/opt/\|/logs"' panther/ --include="*.py"

# Find magic numbers
grep -r "\b(32|60|100|1000000)\b" panther/ --include="*.py" | grep -v test
```

## Phase 1: Generic Plugin Manager Implementation

### Step 1: Create Base Plugin Manager
```python
# panther/core/plugin_management/base_plugin_manager.py
from typing import Type, Dict, List, Optional, Any
from pathlib import Path
import importlib
import shutil
from panther.core.utils.logging_mixin import LoggingMixin

class BasePluginManager(LoggingMixin):
    """Generic plugin manager to replace 15+ duplicate methods."""
    
    PLUGIN_DIRS = {
        "tester": "panther/plugins/services/testers",
        "iut": "panther/plugins/services/iut",
        "network": "panther/plugins/environments/network_environment",
        "execution": "panther/plugins/environments/execution_environment",
    }
    
    def __init__(self):
        super().__init__()
        self._plugin_cache: Dict[str, List[Type]] = {}
    
    def add_plugin(self, plugin_type: str, plugin_dir: Path) -> None:
        """Generic method to add any plugin type."""
        if plugin_type not in self.PLUGIN_DIRS:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
        
        target_dir = Path(self.PLUGIN_DIRS[plugin_type]) / plugin_dir.name
        
        self.logger.info(f"Adding {plugin_type} plugin from {plugin_dir}")
        
        if target_dir.exists():
            self.logger.warning(f"Plugin already exists at {target_dir}")
            return
            
        # Copy plugin directory
        shutil.copytree(plugin_dir, target_dir)
        
        # Clear cache to force rediscovery
        self._plugin_cache.pop(plugin_type, None)
        
        self.logger.info(f"Successfully added {plugin_type} plugin: {plugin_dir.name}")
    
    def remove_plugin(self, plugin_type: str, plugin_name: str) -> None:
        """Generic method to remove any plugin type."""
        if plugin_type not in self.PLUGIN_DIRS:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
            
        plugin_dir = Path(self.PLUGIN_DIRS[plugin_type]) / plugin_name
        
        if not plugin_dir.exists():
            self.logger.warning(f"Plugin not found: {plugin_dir}")
            return
            
        shutil.rmtree(plugin_dir)
        self._plugin_cache.pop(plugin_type, None)
        
        self.logger.info(f"Removed {plugin_type} plugin: {plugin_name}")
    
    def get_plugin_classes(self, plugin_type: str) -> List[Type]:
        """Generic method to discover plugin classes."""
        if plugin_type in self._plugin_cache:
            return self._plugin_cache[plugin_type]
            
        if plugin_type not in self.PLUGIN_DIRS:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
            
        plugin_classes = []
        plugin_dir = Path(self.PLUGIN_DIRS[plugin_type])
        
        if not plugin_dir.exists():
            return plugin_classes
            
        for item in plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                module_path = f"{plugin_dir.as_posix().replace('/', '.')}.{item.name}.{item.name}"
                try:
                    module = importlib.import_module(module_path)
                    # Find the manager class
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            attr.__name__.endswith("ServiceManager") and
                            attr.__module__ == module.__name__):
                            plugin_classes.append(attr)
                            break
                except Exception as e:
                    self.logger.error(f"Failed to load plugin {module_path}: {e}")
                    
        self._plugin_cache[plugin_type] = plugin_classes
        return plugin_classes
```

### Step 2: Refactor ConfigManager
```python
# In config_manager.py, replace all duplicate methods with:

class ConfigurationManager:
    def __init__(self):
        # ... existing init ...
        self.plugin_manager = BasePluginManager()
    
    # Replace 5 add_plugin_* methods with:
    def add_plugin(self, plugin_type: str, plugin_dir: str):
        """Generic plugin addition."""
        return self.plugin_manager.add_plugin(plugin_type, Path(plugin_dir))
    
    # Compatibility wrappers (temporary)
    def add_plugin_tester_service(self, plugin_dir: str):
        """Deprecated: Use add_plugin('tester', plugin_dir) instead."""
        warnings.warn("add_plugin_tester_service is deprecated", DeprecationWarning)
        return self.add_plugin("tester", plugin_dir)
    
    # Similar wrappers for other old methods...
```

## Phase 2: Schema Standardization Pattern

### Base Schema Template
```python
# panther/config/core/schemas/base_schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import os

class BasePluginConfig(BaseModel):
    """Base configuration for all plugins."""
    
    name: str = Field(..., description="Plugin name")
    version: str = Field(default="1.0.0", description="Plugin version")
    enabled: bool = Field(default=True, description="Enable/disable plugin")
    
    class Config:
        extra = "forbid"  # Consistent across all schemas
        validate_assignment = True
        
    @validator("version")
    def validate_version(cls, v):
        """Ensure version follows semantic versioning."""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError("Version must follow semantic versioning (x.y.z)")
        return v

class NetworkPluginConfig(BasePluginConfig):
    """Base for network environment plugins."""
    
    network_delay: int = Field(default=0, ge=0, description="Network delay in ms")
    packet_loss: float = Field(default=0.0, ge=0.0, le=1.0, description="Packet loss rate")
    
class ServicePluginConfig(BasePluginConfig):
    """Base for service plugins."""
    
    # Extract hardcoded values to environment variables
    port: int = Field(
        default_factory=lambda: int(os.getenv("DEFAULT_SERVICE_PORT", "4443")),
        gt=0,
        le=65535
    )
    timeout: int = Field(
        default_factory=lambda: int(os.getenv("DEFAULT_TIMEOUT", "60")),
        gt=0
    )
```

### Migration Example
```python
# BEFORE (with hardcoded values and no error handling):
class PicoquicConfig(BaseUnifiedModel):
    port: int = 4443  # Hardcoded!
    max_clients: int = 100  # Magic number!
    
    @staticmethod
    def load_available_versions():  # Anti-pattern!
        # File I/O in config schema
        with open("versions.yaml") as f:
            return yaml.load(f)

# AFTER (following standards):
from panther.config.core.schemas.base_schemas import ServicePluginConfig
from panther.config.core.constants import DEFAULT_QUIC_PORT, DEFAULT_MAX_CLIENTS

class PicoquicConfig(ServicePluginConfig):
    """Picoquic QUIC implementation configuration."""
    
    port: int = Field(default=DEFAULT_QUIC_PORT, description="QUIC port")
    max_clients: int = Field(
        default=DEFAULT_MAX_CLIENTS,
        gt=0,
        description="Maximum concurrent clients"
    )
    
    # Version loading moved to plugin manager
    available_versions: List[str] = Field(
        default_factory=list,
        description="Available Picoquic versions"
    )
    
    @validator("port")
    def validate_port(cls, v):
        """Ensure QUIC port is appropriate."""
        if v < 1024 and os.geteuid() != 0:
            raise ValueError("Ports below 1024 require root privileges")
        return v
```

## Phase 3: Error Handling Wrapper

### Config Error Handler
```python
# panther/config/core/error_handler.py
from contextlib import contextmanager
from typing import TypeVar, Type, Optional
import logging

T = TypeVar('T')

@contextmanager
def config_error_handler(operation: str, default: Optional[T] = None):
    """Unified error handling for config operations."""
    logger = logging.getLogger(__name__)
    try:
        yield
    except ValidationError as e:
        logger.error(f"Validation failed for {operation}: {e}")
        if default is not None:
            logger.info(f"Using default value: {default}")
            return default
        raise ConfigValidationError(f"Invalid configuration for {operation}: {str(e)}")
    except FileNotFoundError as e:
        logger.error(f"Config file not found for {operation}: {e}")
        raise ConfigFileNotFoundError(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in {operation}: {e}", exc_info=True)
        raise ConfigOperationError(f"Failed to {operation}: {str(e)}")

# Usage in config loading:
def load_config(self, config_path: Path) -> BasePluginConfig:
    with config_error_handler(f"load config from {config_path}"):
        data = yaml.safe_load(config_path.read_text())
        return self.config_class(**data)
```

## Phase 4: Circular Dependency Resolution

### Before (Circular Import)
```python
# config_manager.py
from panther.plugins.plugin_config_resolver import PluginConfigResolver

# plugin_config_resolver.py  
from panther.config.config_manager import ConfigurationManager  # Circular!
```

### After (Dependency Injection)
```python
# config_manager.py
class ConfigurationManager:
    def __init__(self, plugin_resolver=None):
        self.plugin_resolver = plugin_resolver or self._create_plugin_resolver()
        
    def _create_plugin_resolver(self):
        # Late import to avoid circular dependency
        from panther.plugins.plugin_config_resolver import PluginConfigResolver
        return PluginConfigResolver(config_manager=self)

# plugin_config_resolver.py
class PluginConfigResolver:
    def __init__(self, config_manager=None):
        # Accept config_manager as parameter instead of importing
        self.config_manager = config_manager
```

## Daily Implementation Checklist

### Day 1: Setup and Analysis
- [ ] Create feature branch: `git checkout -b refactor/remove-legacy-code`
- [ ] Run initial metrics: `flake8 panther/ --count`
- [ ] Create backup: `cp -r panther/ panther_backup_$(date +%Y%m%d)/`
- [ ] Set up test coverage: `pytest --cov=panther --cov-report=html`

### Day 2: Start Plugin Manager
- [ ] Create `panther/core/plugin_management/` directory
- [ ] Implement `BasePluginManager` class
- [ ] Write unit tests for new plugin manager
- [ ] Run tests: `pytest tests/unit/test_plugin_manager.py -v`

### Day 3-4: Refactor ConfigManager
- [ ] Replace duplicate methods one by one
- [ ] Add compatibility wrappers
- [ ] Update imports across codebase
- [ ] Continuous testing after each change

### Day 5: Begin Schema Migration
- [ ] Create base schema classes
- [ ] Start with one schema as proof of concept
- [ ] Validate functionality preserved
- [ ] Document migration pattern

## Verification Commands

```bash
# After each major change:
# 1. Check for broken imports
python -c "import panther; print('Import successful')"

# 2. Run quick test
pytest tests/unit/test_config_manager.py -k "test_plugin" -v

# 3. Check for regressions
flake8 panther/config/ --max-line-length=88

# 4. Verify no functionality lost
python -m panther config validate --config experiment-config/experiment_config_example_minimal.yaml
```

## Commit Strategy

```bash
# Atomic commits for easy rollback
git add panther/core/plugin_management/
git commit -m "feat: Add generic BasePluginManager class

- Replaces 15+ duplicate plugin management methods
- Implements caching for better performance
- Follows DRY principle"

# After each successful phase
git tag -a "legacy-removal-phase-1" -m "Completed generic plugin manager"
```