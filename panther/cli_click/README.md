# PANTHER Click CLI

## Overview

The PANTHER Click CLI is a modern, user-friendly command-line interface built with the Click framework. It provides enhanced user experience, better error handling, and comprehensive functionality for protocol testing and analysis.

## Key Features

### Enhanced User Experience
- **Colored Output**: Visual feedback with emojis and color coding
- **Progress Bars**: Real-time progress indication for long operations
- **Better Error Messages**: Contextual error messages with suggested solutions
- **Bash Completion**: Built-in tab completion support
- **Interactive Tutorials**: Guided learning system
- **Comprehensive Help**: Detailed help text with examples

### Modern CLI Architecture
- **Command Groups**: Logical organization of related commands
- **Consistent Options**: Standardized option patterns across commands
- **Input Validation**: Immediate feedback on invalid input
- **Dry Run Mode**: Preview operations before execution
- **Plugin Integration**: Seamless plugin discovery and management

## Architecture

### Core Components

```
panther/cli_click/
├── __init__.py          # Package initialization
├── core/                # Core CLI functionality
│   ├── __init__.py
│   ├── base.py          # Base utilities and decorators
│   └── main.py          # Main CLI entry point
├── commands/            # Command implementations
│   ├── __init__.py
│   ├── admin.py         # Administrative commands
│   ├── check.py         # Code quality checks
│   ├── config.py        # Configuration management
│   ├── create.py        # Resource creation
│   ├── metrics.py       # Metrics management
│   ├── plugins.py       # Plugin management
│   ├── run.py           # Experiment execution
│   ├── tools.py         # Development tools
│   └── tutorial.py      # Interactive tutorials
└── utils/               # Utility functions
    ├── __init__.py
    └── migration.py     # Migration helpers
```

### Design Principles

1. **User-Centric Design**: Focus on developer productivity and ease of use
2. **Consistent Interface**: Uniform command structure and option patterns
3. **Progressive Disclosure**: Simple commands for common tasks, advanced options available
4. **Error Recovery**: Helpful error messages with actionable suggestions
5. **Extensibility**: Easy to add new commands and functionality

## Command Reference

### Main Commands

#### `panther run` - Execute Experiments
Execute PANTHER experiments with comprehensive configuration support.

**Key Features:**
- Configuration validation before execution
- Dry run mode for preview
- Metrics collection integration
- Docker container management
- Progress tracking and status updates

**Example:**
```bash
panther run --config experiment.yaml --enable-metrics --verbose
```

#### `panther config` - Configuration Management
Manage and validate PANTHER configurations.

**Subcommands:**
- `validate`: Validate configuration files with detailed feedback
- `schema`: Display configuration schema documentation
- `generate`: Generate configuration templates

**Example:**
```bash
panther config validate --config experiment.yaml --explain
```

#### `panther plugins` - Plugin Management
Discover, inspect, and manage PANTHER plugins.

**Subcommands:**
- `list`: List available plugins with filtering
- `info`: Show detailed plugin information
- `params`: Display plugin parameters
- `validate`: Validate plugin structure

**Example:**
```bash
panther plugins list --type iut --format table
```

#### `panther create` - Resource Creation
Create new plugins and configuration templates.

**Subcommands:**
- `plugin`: Create new plugin scaffolding
- `subplugin`: Create plugin variants
- `template`: Generate configuration templates

**Example:**
```bash
panther create plugin service my_quic_impl --dev-mode
```

#### `panther tutorial` - Interactive Learning
Access interactive tutorials and learning resources.

**Subcommands:**
- `run`: Execute specific tutorials
- `interactive`: Menu-driven tutorial selection
- `list`: Show available tutorials
- `progress`: Track learning progress

**Example:**
```bash
panther tutorial run service --mode guided --level beginner
```

### Utility Commands

#### `panther tools` - Development Tools
Development and maintenance utilities.

**Features:**
- System diagnostics (`doctor`)
- Resource cleanup (`clean`)
- Docker optimization (`install-slim`)

#### `panther check` - Code Quality
Run code quality checks and validation.

#### `panther metrics` - Metrics Management
Manage metrics collection and analysis.

#### `panther admin` - Administrative Commands
System administration and maintenance.

## Implementation Details

### Base Command Pattern

All commands inherit from common base utilities:

```python
from panther.cli_click.core.base import (
    handle_errors,
    pass_context_and_setup_logging,
    success_message,
    info_message,
    error_message,
)

@click.command()
@click.option('--config', '-c', required=True, help='Configuration file')
@handle_errors
@pass_context_and_setup_logging
def my_command(ctx, config):
    """My command implementation."""
    info_message(f"Processing config: {config}")
    # Command implementation
    success_message("Command completed successfully!")
```

### Error Handling

Consistent error handling across all commands:

- **User Errors**: Clear messages with suggestions
- **System Errors**: Logged with context
- **Debug Mode**: Full stack traces when `--debug` is enabled
- **Exit Codes**: Standard Unix exit codes

### Progress Indication

Commands provide visual feedback:

```python
with click.progressbar(items, label='Processing') as bar:
    for item in bar:
        # Process item
        pass
```

### Logging Integration

Integrated with PANTHER's logging system:

```python
def setup_logging(debug: bool = False, verbose: bool = False) -> None:
    """Configure logging based on flags."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(level=level)
```

## Entry Points

The CLI is accessible through multiple entry points:

### Primary Entry Point
```bash
panther [command] [options]
```

### Python Module
```bash
python -m panther.cli_click [command] [options]
```

### Programmatic Access
```python
from panther.cli_click.core.main import cli
cli(['run', '--config', 'experiment.yaml'])
```

## Configuration

### pyproject.toml Integration

The CLI is configured through `pyproject.toml`:

```toml
[project.scripts]
panther = "panther.__main__:main"
```

### Environment Variables

- `PANTHER_DEBUG`: Enable debug mode
- `PANTHER_CONFIG_DIR`: Default configuration directory
- `PANTHER_PLUGIN_DIR`: Default plugin directory

## Testing

### Command Testing

Commands are tested using Click's testing utilities:

```python
from click.testing import CliRunner
from panther.cli_click.core.main import cli

def test_run_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--config', 'test.yaml', '--dry-run'])
    assert result.exit_code == 0
    assert 'DRY RUN' in result.output
```

### Integration Testing

Full workflow testing ensures commands work together:

```python
def test_workflow():
    runner = CliRunner()

    # Generate template
    result = runner.invoke(cli, ['create', 'template', 'experiment'])
    assert result.exit_code == 0

    # Validate config
    result = runner.invoke(cli, ['config', 'validate', '--config', 'test.yaml'])
    assert result.exit_code == 0

    # Run experiment
    result = runner.invoke(cli, ['run', '--config', 'test.yaml', '--dry-run'])
    assert result.exit_code == 0
```

## Migration from Argparse

The Click CLI replaces the previous argparse-based implementation:

### Benefits
- **Better UX**: Enhanced user experience with visual feedback
- **Easier Testing**: Click's testing utilities
- **Better Documentation**: Auto-generated help and documentation
- **Extensibility**: Easier to add new commands and options

### Backward Compatibility
- Configuration files remain unchanged
- Plugin system compatibility maintained
- Core functionality preserved

For migration details, see [Migration Guide](../../docs/cli_migration_guide.md).

## Development

### Adding New Commands

1. Create command module in `commands/`
2. Implement using Click decorators
3. Register with main CLI
4. Add tests and documentation

Example:
```python
# panther/cli_click/commands/my_command.py
import click
from panther.cli_click.core.base import handle_errors

@click.command()
@click.option('--option', help='Command option')
@handle_errors
def my_command(option):
    """My new command."""
    click.echo(f"Option: {option}")

# Register in main.py
from panther.cli_click.commands.my_command import my_command
cli.add_command(my_command)
```

### Best Practices

1. **Use decorators**: Leverage base decorators for consistency
2. **Provide help**: Include comprehensive help text
3. **Handle errors**: Use error decorators and appropriate messages
4. **Test thoroughly**: Include unit and integration tests
5. **Document examples**: Provide clear usage examples

## Documentation

- [CLI Documentation](../../docs/cli_click.md): Comprehensive user guide
- [Migration Guide](../../docs/cli_migration_guide.md): Migration from old CLI
- [Examples](../../docs/cli_examples.md): Usage examples and workflows
- [Quick Reference](../../docs/cli_quick_reference.md): Command reference

## Contributing

When contributing to the CLI:

1. **Follow patterns**: Use established command patterns
2. **Include tests**: Add comprehensive test coverage
3. **Update docs**: Update relevant documentation
4. **Consider UX**: Focus on user experience improvements
5. **Maintain compatibility**: Preserve backward compatibility

## Future Enhancements

Planned improvements:

- **Real-time monitoring**: Live experiment status
- **Enhanced completion**: Dynamic completion for plugin names
- **Workflow automation**: Command chaining and pipelines
- **Cloud integration**: Remote execution capabilities
- **Enhanced visualization**: Built-in result visualization

## Support

For CLI support:

- Use `panther --help` for command help
- Check [documentation](../../docs/cli_click.md)
- Run `panther tools doctor` for diagnostics
- Use `panther tutorial interactive` for learning
- Report issues on [GitHub](https://github.com/ElNiak/PANTHER/issues)
