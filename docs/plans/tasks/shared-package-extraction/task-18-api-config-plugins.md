# Task 18: Implement panther.api config and plugins Modules

## Goal
Implement `panther/api/config.py` and `panther/api/plugins.py` as thin facades wrapping existing managers.

## Prerequisites
- Task 17 completed (module scaffolded)

## Source Files to Read

Before implementing, read these to understand the existing APIs:

### For config.py:
- `panther/config/core/mixins/__init__.py` - ConfigurationManager class
- `panther/config/core/manager.py` (if it exists) - may be the actual manager
- `panther/webapp/web_app.py` - existing Flask endpoints for config operations
- `panther/config/core/base.py` - BaseConfig.load(), .save(), .to_yaml(), .get_schema()

### For plugins.py:
- `panther/plugins/core/plugin_manager.py` - PluginManager singleton
- `panther/plugins/core/registry.py` - Plugin registry with get_all_*_classes()
- `panther/webapp/web_app.py` - existing Flask endpoints: GET /api/plugins

## Steps

### Step 1: Implement config.py

```python
# panther/api/config.py
"""Configuration operations.

Thin facade wrapping ConfigurationManager and BaseConfig utilities.
All functions return plain dicts/dataclasses, not framework-specific objects.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Lazy imports to avoid circular deps at module level


def load_config(path: Union[str, Path]) -> Any:
    """Load an experiment configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        ExperimentConfig object (Pydantic model).

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ConfigurationException: If config is invalid.
    """
    # Read the actual ConfigurationManager API and implement
    # This should delegate to the existing config loading mechanism
    pass


def validate_config(config: Any) -> Dict[str, Any]:
    """Validate an experiment configuration.

    Args:
        config: ExperimentConfig object to validate.

    Returns:
        Dict with keys: "valid" (bool), "errors" (list), "warnings" (list).
    """
    pass


def save_config(config: Any, path: Union[str, Path]) -> None:
    """Save an experiment configuration to a YAML file.

    Args:
        config: ExperimentConfig object to save.
        path: Output file path.
    """
    pass


def get_config_schema() -> Dict[str, Any]:
    """Get JSON Schema for the experiment configuration.

    Returns:
        JSON Schema dict that can be used to build frontend forms.
    """
    pass


def merge_configs(base: Dict[str, Any], overlay: Dict[str, Any]) -> Any:
    """Merge two configuration dicts with overlay taking precedence.

    Args:
        base: Base configuration dict.
        overlay: Override configuration dict.

    Returns:
        Merged ExperimentConfig object.
    """
    pass
```

### Step 2: Implement plugins.py

```python
# panther/api/plugins.py
"""Plugin discovery operations.

Thin facade wrapping PluginManager for plugin listing and info retrieval.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def list_plugins() -> List[Dict[str, Any]]:
    """List all registered plugins.

    Returns:
        List of dicts with keys: name, type, version, description, enabled.
    """
    # Delegate to PluginManager.get_all_plugins() or similar
    # Read the actual PluginManager API
    pass


def get_plugin_info(name: str) -> Dict[str, Any]:
    """Get detailed info about a specific plugin.

    Args:
        name: Plugin name.

    Returns:
        Dict with full plugin metadata.

    Raises:
        KeyError: If plugin not found.
    """
    pass


def get_plugin_config_schema(name: str) -> Dict[str, Any]:
    """Get JSON Schema for a specific plugin's configuration.

    Args:
        name: Plugin name.

    Returns:
        JSON Schema dict for the plugin's config model.
    """
    pass


def list_protocols() -> List[Dict[str, Any]]:
    """List all registered protocol plugins.

    Returns:
        List of dicts with: name, versions, default_port, supports_tls.
    """
    pass


def list_environments() -> List[Dict[str, Any]]:
    """List all registered environment plugins.

    Returns:
        List of dicts with: name, type (network/execution), description.
    """
    pass


def list_implementations(protocol: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available IUT implementations, optionally filtered by protocol.

    Args:
        protocol: Optional protocol name to filter by.

    Returns:
        List of dicts with: name, type, supported_protocols.
    """
    pass
```

### Step 3: Implementation Notes

Each function should:
1. Import the required manager lazily (to avoid circular imports)
2. Call the existing manager method
3. Convert the result to plain dicts/primitives (no framework objects in the return type)
4. Handle exceptions gracefully, converting internal exceptions to documented ones

Example pattern:
```python
def list_plugins() -> List[Dict[str, Any]]:
    from panther.plugins.core.plugin_manager import PluginManager

    manager = PluginManager.get_instance()  # or however the singleton is accessed
    plugins = manager.get_all_plugins()  # or whatever the actual method is

    return [
        {
            "name": p.name,
            "type": p.type.value if hasattr(p.type, 'value') else str(p.type),
            "version": getattr(p, "version", ""),
            "description": getattr(p, "description", ""),
            "enabled": getattr(p, "enabled", True),
        }
        for p in plugins
    ]
```

### Step 4: Write tests

```python
# tests/unit/test_api/test_api_config.py
"""Tests for panther.api.config module."""
import pytest
from unittest.mock import patch, MagicMock


class TestLoadConfig:
    def test_load_valid_file(self, tmp_path):
        """Test loading a valid YAML config."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("logging:\n  level: INFO\n")
        # Implementation-specific test
        pass

    def test_load_missing_file(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        from panther.api.config import load_config
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.yaml")


class TestGetConfigSchema:
    def test_returns_dict(self):
        """Schema should be a valid JSON Schema dict."""
        from panther.api.config import get_config_schema
        schema = get_config_schema()
        assert isinstance(schema, dict)
        # JSON Schema should have "type" or "properties"


# tests/unit/test_api/test_api_plugins.py
"""Tests for panther.api.plugins module."""


class TestListPlugins:
    def test_returns_list(self):
        """list_plugins should return a list of dicts."""
        from panther.api.plugins import list_plugins
        result = list_plugins()
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], dict)
            assert "name" in result[0]
```

## Verification
```bash
# Run the API tests
pytest tests/unit/test_api/ -v

# Smoke test
python -c "
from panther.api.config import get_config_schema
from panther.api.plugins import list_plugins
print('API modules imported: OK')
"
```

## Important Notes
- **Read the actual manager classes** before implementing. The method names and patterns shown above are approximations.
- Use **lazy imports** inside each function to avoid circular import issues.
- All return types should be **plain dicts/lists/primitives**, not Pydantic models or OmegaConf objects. This ensures the API is framework-agnostic.
- Some functions may need a "context" or "initialization" step (e.g., PluginManager needs to discover plugins first). Document these requirements.

## Commit Message
```
feat(api): implement config and plugins API modules

Add panther.api.config (load_config, validate_config, save_config,
get_config_schema, merge_configs) and panther.api.plugins (list_plugins,
get_plugin_info, get_plugin_config_schema, list_protocols,
list_environments, list_implementations).
```

## Files Modified
- `panther/api/config.py` (implemented)
- `panther/api/plugins.py` (implemented)
- `tests/unit/test_api/__init__.py` (new)
- `tests/unit/test_api/test_api_config.py` (new)
- `tests/unit/test_api/test_api_plugins.py` (new)
