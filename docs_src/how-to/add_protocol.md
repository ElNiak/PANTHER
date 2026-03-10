# Add a Protocol Plugin

How to add support for a new network protocol in PANTHER.

## Overview

Protocols in PANTHER are registered with the `@register_protocol()` decorator. Each protocol defines:

- Protocol metadata (name, versions, type)
- Role definitions (client/server or peer)
- Default configuration values

See the [Plugin System explanation](../explanation/plugin_system.md) for architecture details
and the [full API reference](../panther/panther/plugins/index.md) for all classes.

## Step 1: Create Protocol Directory

```bash
mkdir -p panther/plugins/protocols/client_server/myprotocol
```

## Step 2: Register the Protocol

```python
from panther.plugins.core.plugin_decorators import register_protocol

@register_protocol(
    name="myprotocol",
    type="client_server",
    versions=["v1.0", "v2.0"],
    default_version="v1.0",
    description="My custom protocol",
)
class MyProtocol:
    ...
```

## Step 3: Create IUT Plugins

Each protocol needs at least one IUT (Implementation Under Test) plugin. See [Writing a Plugin](../tutorials/writing_a_plugin.md).

## See Also

- [Plugin Inventory](../plugins_inventory.md) -- Existing protocols
- [Plugin System](../explanation/plugin_system.md) -- Architecture details
