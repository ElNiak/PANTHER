# CLI Interface — Command-Line Operations 🖥️

!!! info "PANTHER Command-Line Interface"
    The CLI provides unified access to all PANTHER framework functionality including experiment execution, plugin management, and development tools. This is the primary interface for framework operations.

**Purpose:** Primary user interface for PANTHER framework operations
**Components:** Argument parsing, command routing, plugin management CLI
**Dependencies:** Configuration system, plugin system, experiment engine

PANTHER's CLI provides comprehensive access to framework functionality through a unified command-line interface with support for experiments, plugin management, and development tools.

---

## Architecture Overview

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
def main():
    """Main entry point for the PANTHER CLI."""
    parser = argparse.ArgumentParser(description="Panther CLI")
```

### Command Categories

1. **Experiment Operations** → Run, validate, and manage experiments
2. **Plugin Management** → Create, inspect, and manage plugins
3. **Development Tools** → Tutorials, parameter discovery, debugging
4. **Configuration** → Validate, inspect, and manage configurations

---

## Core Commands

!!! tip "Getting Started with PANTHER CLI"
    Start with `panther --help` to see all available commands, then use `--validate-config` to check your experiment configuration before running full experiments.

### Experiment Execution

**Basic Experiment Run:**

```bash
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Run experiment with default configuration
panther --experiment-config experiment-config/experiment_config.yaml

# Run with custom output directory and experiment name
panther --experiment-config config.yaml --output-dir ./results --experiment-name my_test
```

**Configuration Validation:**

```bash
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Validate configuration before running
panther --validate-config --experiment-config config.yaml

# Validate and show merged schema
panther --show-schema --experiment-config config.yaml
```

### Plugin Operations

**Plugin Creation:**

```bash
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Create new plugin with interactive prompts
panther --create-plugin service my_service

# Create plugin with default subplugins
panther --create-plugin service my_service --with-subplugins

# Create subplugin within existing plugin
panther --create-subplugin service my_service iut
```

**Plugin Parameter Discovery:**

```bash
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# List parameters for specific plugin (auto-detects type)
panther --list-plugin-params quiche

# Explicit plugin type and protocol specification
panther --list-plugin-params quiche --plugin-type iut --protocol quic
```

### Development and Learning

**Interactive Tutorials:**

```bash
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Launch interactive tutorial menu
panther --interactive-tutorials

# Run specific tutorial
panther --tutorial service
panther --tutorial environment
panther --tutorial protocol
```

**Development Mode:**

```bash
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Force development mode (plugins in source tree)
panther --create-plugin service test_plugin --dev-mode

# Force production mode (plugins in user directory)
panther --create-plugin service test_plugin --production-mode
```

---

## Command Line Arguments

### Experiment Configuration

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
parser.add_argument(
    "--experiment-config",
    type=str,
    default="experiment-config/experiment_config.yaml",
    help="Path to the configuration directory.",
)

parser.add_argument(
    "--output-dir",
    type=str,
    default="outputs",
    help="Path to the output directory.",
)

parser.add_argument(
    "--experiment-name",
    type=str,
    default=None,
    help="Name of the experiment.",
)
```

### Plugin Directories

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
parser.add_argument(
    "--exec-env-dir",
    type=str,
    help="Path to the execution plugin additional directory.",
)

parser.add_argument(
    "--net-env-dir",
    type=str,
    help="Path to the network plugin additional directory.",
)

parser.add_argument(
    "--iut-dir",
    type=str,
    help="Path to a new IUT plugin additional directory.",
)

parser.add_argument(
    "--tester-dir",
    type=str,
    help="Path to a new tester plugin additional directory.",
)
```

### Plugin Creation Arguments

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
create_group.add_argument(
    "--create-plugin",
    nargs=2,
    metavar=("TYPE", "NAME"),
    help="Create a new plugin. TYPE can be service, environment, or protocol.",
)

create_group.add_argument(
    "--create-subplugin",
    nargs=3,
    metavar=("PLUGIN_TYPE", "PLUGIN_NAME", "SUBPLUGIN_TYPE"),
    help="Create a new subplugin within an existing plugin.",
)

create_group.add_argument(
    "--with-subplugins",
    action="store_true",
    help="Create default subplugins when creating a new plugin.",
)
```

---

## Command Processing Flow

### Main Command Router

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
def main():
    """Main entry point for the PANTHER CLI."""
    parser = argparse.ArgumentParser(description="Panther CLI")
    args = parser.parse_args()

    # Handle plugin creation
    if args.create_plugin:
        return handle_plugin_creation(args)

    # Handle parameter listing
    if args.list_plugin_params:
        return handle_parameter_listing(args)

    # Handle configuration validation
    if args.validate_config:
        return handle_config_validation(args)

    # Handle experiment execution
    else:
        return handle_experiment_execution(args)
```

### Plugin Creation Handling

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
if args.create_plugin:
    plugin_type, plugin_name = args.create_plugin

    # Determine development mode
    dev_mode = None  # Auto-detect by default
    if args.dev_mode:
        dev_mode = True
    elif args.production_mode:
        dev_mode = False

    try:
        success = create_plugin(
            plugin_type,
            plugin_name,
            in_development_mode=dev_mode,
            create_subplugins=args.with_subplugins,
        )
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Error creating plugin: {e}")
        return 1
```

### Parameter Discovery Handling

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
if args.list_plugin_params:
    config_loader = ConfigLoader(
        args.experiment_config,
        args.output_dir,
        args.exec_env_dir,
        args.net_env_dir,
        args.iut_dir,
        args.tester_dir,
    )

    params = list_plugin_parameters(
        plugin_name=args.list_plugin_params,
        plugin_type=args.plugin_type,
        protocol=args.protocol,
    )

    if not params:
        return 1

    # Print parameters in readable format
    print(f"\n{'Parameter':<20} {'Type':<30} {'Default':<20} {'Required':<10} Description")
    print("-" * 100)
    for name, info in params.items():
        # Format parameter information for display
        print(f"{name:<20} {info['type']:<30} {info['default']:<20} {info['required']:<10} {info['description']}")
```

---

## Integration with Core Systems

### Configuration System Integration

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Load and validate configuration
config_loader = ConfigLoader(
    args.experiment_config,
    args.output_dir,
    args.exec_env_dir,
    args.net_env_dir,
    args.iut_dir,
    args.tester_dir,
)

global_config = config_loader.load_and_validate_global_config()
```

### Experiment Engine Integration

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Create and run experiment
experiment_manager = ExperimentManager(
    global_config=global_config,
    experiment_name=args.experiment_name
)

experiment_config = config_loader.load_and_validate_experiment_config()
experiment_manager.initialize_experiments(experiment_config)
experiment_manager.run_tests()
```

### Plugin System Integration

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
# Import plugin creation utilities
from panther.plugins.plugin_creator import (
    is_development_mode,
    create_plugin,
    run_tutorial,
    launch_interactive_tutorials,
)
```

---

## Error Handling and User Experience

### Error Recovery

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/__main__.py
try:
    # Command execution
    success = execute_command(args)
    return 0 if success else 1
except Exception as e:
    logging.error(e)
    return 1
finally:
    # Cleanup resources
    config_loader.cleanup()
```

### User-Friendly Output

**Parameter Listing:**

```text
Parameter           Type                           Default              Required   Description
----------------------------------------------------------------------------------------------------
binary              QuicheBinaryConfig             None                 Yes        Binary configuration
network             QuicheNetworkConfig            None                 Yes        Network settings
protocol            QuicheProtocolConfig           None                 Yes        Protocol parameters
certificates        CertificateConfig              None                 Yes        Certificate settings
```

**Plugin Creation:**

```text
✅ Successfully created service plugin: my_service
📁 Plugin location: /Users/user/.panther/plugins/services/my_service
📚 Run 'panther --tutorial service' to learn about service plugin development
```

---

## Advanced Usage Patterns

### Batch Operations

```bash
# Run multiple experiments with different configurations
for config in configs/*.yaml; do
    panther --experiment-config "$config" --output-dir "results/$(basename $config .yaml)"
done
```

### Plugin Development Workflow

```bash
# 1. Create plugin with tutorials
panther --create-plugin service my_impl --with-subplugins --dev-mode

# 2. Learn development patterns
panther --tutorial service

# 3. Inspect existing plugin parameters
panther --list-plugin-params quiche --plugin-type iut

# 4. Validate plugin configuration
panther --validate-config --experiment-config test_config.yaml
```

### Configuration Debugging

```bash
# Validate configuration structure
panther --validate-config --experiment-config config.yaml

# Check plugin parameter requirements
panther --list-plugin-params my_plugin

# Run with detailed logging
PANTHER_LOG_LEVEL=DEBUG panther --experiment-config config.yaml
```

---

## Extending the CLI

### Adding New Commands

1. Add argument parsing in `__main__.py`
2. Implement command handler function
3. Add integration with core systems
4. Update help text and documentation

### Custom Plugin Commands

Plugin-specific commands can be added through the plugin system:

```python
# Plugin can register CLI extensions
from panther.cli.extensions import register_command

@register_command("my-plugin")
def handle_my_plugin_command(args):
    """Custom command for my plugin"""
    pass
```

### Debugging CLI Issues

- Check argument parsing with `--help`
- Verify plugin discovery paths
- Enable debug logging for detailed execution traces
- Test configuration loading separately with `--validate-config`

---

**Related Documentation:**

- [Configuration System](config/README.md) — How CLI loads and validates configurations
- [Experiment Engine](core/README.md) — How CLI coordinates experiment execution
- [Plugin Development](plugins/development.md) — Creating CLI-integrated plugins
