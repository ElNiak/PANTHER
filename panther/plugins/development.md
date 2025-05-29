# PANTHER Plugin Development Guide

This guide provides detailed instructions for creating new plugins for the PANTHER framework across all plugin types.

## Development Guides

Comprehensive development documentation for each plugin category:

- **[Service Plugin Development](panther/plugins/services/development.md)**: Creating IUT and tester plugins
- **[Protocol Plugin Development](panther/plugins/protocols/development.md)**: Adding protocol support
- **[Environment Plugin Development](panther/plugins/environments/development.md)**: Environment management plugins
- **[General Plugin Development](panther/plugins/development.md)**: Common plugin development patterns

## Interactive Plugin Creation

> **New Feature**: Plugins now support Jinja2 templates for dynamic code generation and better subplugin integration.

PANTHER provides tools to easily create new plugins from templates:

### Tutorial Launcher (Recommended)

```bash
# From the PANTHER root directory
python -m panther --interactive-tutorials
```

The tutorial launcher provides a menu-driven interface to access all available tutorials.

```bash
# Run tutorials
panther --tutorial service
panther --tutorial environment
panther --tutorial protocol
```

### Creating Plugins and Subplugins

1. **Top-level plugin creation**: Using `--create-plugin TYPE NAME`
2. **Subplugin creation**: Using `--create-subplugin PLUGIN_TYPE PLUGIN_NAME SUBPLUGIN_TYPE`
3. **Complete plugin setup**: Using `--create-plugin TYPE NAME --with-subplugins`

```bash
# First create the main plugin structure
python -m panther --create-plugin service my_protocol

# Then create the IUT subplugin
python -m panther --create-subplugin service my_protocol iut

# Then create the Tester subplugin
python -m panther --create-subplugin service my_protocol tester

# Create a complete service plugin with all subplugins
python -m panther --create-plugin service my_protocol --with-subplugins

# Create a network environment subplugin
python -m panther --create-subplugin environment my_env network_environment

# Create an execution environment subplugin
python -m panther --create-subplugin environment my_env execution_environment
```

### Development vs Production Mode

When creating plugins, PANTHER automatically detects whether you're in development mode (GitHub cloned repository) or production mode (installed package):

- **Development Mode**: Plugins are created in the repository structure
- **Production Mode**: Plugins are created in `~/.panther/plugins/`

You can explicitly specify the mode:

```bash
# Force development mode (put plugins in source tree)
panther --create-plugin protocol my_protocol --dev-mode

# Force production mode (put plugins in user directory)
panther --create-plugin service my_service --production-mode
```

### Interactive Tutorials

For guided plugin development:

```bash
# Launch a specific tutorial
panther --tutorial service
panther --tutorial environment
panther --tutorial protocol

# Launch the interactive tutorial menu
panther --interactive-tutorials
panther --tutorial environment
panther --tutorial protocol
```

## Manual Creating a New Plugin

### 1. Choose the Plugin Type

Determine which category your plugin belongs to:

- **Environment**: Execution or network environment
- **Protocol**: Client-server or peer-to-peer protocol
- **Service**: Implementation under test (IUT) or tester

### 2. Set Up the Plugin Directory

Create a directory for your plugin in the appropriate location:

```
plugins/<plugin_type>/<plugin_name>/
├── __init__.py
├── plugin.py           # Main plugin implementation
├── config_schema.py    # Configuration schema
├── README.md           # Plugin documentation
└── tests/              # Plugin tests
    └── test_plugin.py
```

### 3. Implement the Plugin Interface

Create a class that implements the appropriate plugin interface:

```python
# plugins/<plugin_type>/<plugin_name>/plugin.py
from panther.plugins.<plugin_type>.<type>_interface import <Type>Interface

class MyPlugin(<Type>Plugin):
    """My custom PANTHER plugin."""

    def initialize(self, config):
        """Initialize the plugin with configuration."""
        self.config = config
        # Perform setup tasks

    def execute(self):
        """Execute the plugin's main functionality."""
        # Implement main functionality
        pass

    def cleanup(self):
        """Clean up resources."""
        # Release resources, close connections, etc.
        pass
```

### 4. Define Configuration Schema

Create a schema for your plugin's configuration:

```python
# plugins/<plugin_type>/<plugin_name>/config_schema.py
from panther.core.config.schema import Schema, Optional, And, Or

# Define the configuration schema
schema = Schema({
    "required_param": str,
    Optional("optional_param"): And(int, lambda n: n > 0),
    # Additional parameters
})
```

### 5. Register Your Plugin

Make your plugin discoverable by updating your `__init__.py`:

```python
# plugins/<plugin_type>/<plugin_name>/__init__.py
from .plugin import MyPlugin

__all__ = ["MyPlugin"]
```

### 6. Create Tests

Write tests to verify your plugin functions correctly:

```python
# plugins/<plugin_type>/<plugin_name>/tests/test_plugin.py
import pytest
from panther.plugins.<plugin_type>.<plugin_name>.plugin import MyPlugin

def test_plugin_initialization():
    plugin = MyPlugin()
    config = {"required_param": "test"}
    plugin.initialize(config)
    # Assert expected behavior

def test_plugin_execution():
    plugin = MyPlugin()
    plugin.initialize({"required_param": "test"})
    result = plugin.execute()
    # Assert expected behavior
```

### 7. Document Your Plugin

Create a `README.md` file using the [plugin template](panther/plugins/plugin_template.md) that includes:

- Purpose and overview
- Requirements and dependencies
- Configuration options
- Usage examples
- Extension points
- Testing and verification

## Advanced Usage: Custom Plugin Directories

> **Work in Progress**

PANTHER supports specifying custom directories for different plugin types through CLI arguments:

```bash
# Specify custom directories for plugin discovery
python -m panther --exec-env-dir /path/to/custom/execution/env \
                 --net-env-dir /path/to/custom/network/env \
                 --iut-dir /path/to/custom/iut \
                 --tester-dir /path/to/custom/tester
```

These arguments are useful when:

1. Developing plugins outside the main PANTHER directory structure
2. Using plugins from multiple sources
3. Testing plugins without installing them in the standard locations
4. Using organization-specific plugin collections
