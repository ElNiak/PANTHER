---
status: new
---

# Writing a Plugin

This tutorial guides you through creating a new IUT (Implementation Under Test) plugin for PANTHER.

## Plugin Architecture

PANTHER uses a decorator-based plugin system. Every plugin:

1. Lives under `panther/plugins/services/` (for IUT/testers) or `panther/plugins/environments/`
2. Registers itself with `@register_plugin()`
3. Provides a `config_schema.py` with Pydantic models
4. Includes Docker build files

See the [Plugin System explanation](../explanation/plugin_system.md) for architecture details
and the [full API reference](../panther/panther/plugins/index.md) for all classes.

## Step 1: Create the Plugin Directory

```bash
mkdir -p panther/plugins/services/iut/myprotocol/myimpl
```

## Step 2: Define the Config Schema

Create `config_schema.py` with your plugin's configuration:

```python
from pydantic import BaseModel, Field

class MyImplConfig(BaseModel):
    """Configuration for MyImpl plugin."""
    build_mode: str = Field("release", description="Build mode for compilation")
    extra_flags: list[str] = Field(default_factory=list, description="Additional compiler flags")
```

## Step 3: Register the Plugin

In your plugin's `__init__.py`, use the `@register_plugin` decorator:

```python
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.plugin_manifest import PluginType

@register_plugin(
    name="myimpl",
    version="0.1.0",
    plugin_type=PluginType.IUT,
    supported_protocols=["myprotocol"],
    description="My custom implementation",
)
class MyImplManager(IUTServiceManagerMixin):
    ...
```

## Step 4: Add Docker Support

Create a `Dockerfile` in your plugin directory and a Jinja template for docker-compose.

## Next Steps

- [Plugin Inventory](../plugins_inventory.md) -- See existing plugins for reference
- [Config Schema Reference](../reference/config_schema.md) -- All config options
