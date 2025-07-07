# PANTHER CLI API Reference

Generated from docstrings following PEP 257 and Google style conventions.

## Quick Navigation

| Section | Description | Related Documents |
|---------|-------------|-------------------|
| [Core Classes](#core-classes) | Base interfaces and patterns | [Architecture explanation](README.md#architectural-foundations) |
| [Main Entry Points](#main-entry-points) | CLI initialization and parsing | [Development setup](DEVELOPER_GUIDE.md#development-environment-setup) |
| [Command Classes](#command-classes) | Individual command implementations | [Command development](DEVELOPER_GUIDE.md#contributing-new-cli-commands) |
| [Interactive Components](#interactive-components) | User interface helpers | [Tutorial](tutorial/README.md#step-3-create-your-first-configuration) |
| [Error Handling](#error-handling) | Exit codes and error patterns | [Troubleshooting](DEVELOPER_GUIDE.md#debugging-cli-issues) |

## Related Documentation

- **[README.md](README.md)** - Architecture and design philosophy
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Development procedures and patterns
- **[tutorial/README.md](tutorial/README.md)** - Step-by-step user guide
- **[VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md)** - Quality assurance summary

## Core Classes

### BaseCommand

**Module**: `panther.cli.base` | **Inherits**: `ABC` | **Used by**: [All CLI commands](#command-classes)

Provide consistent interface for all CLI subcommands.

BaseCommand establishes a uniform contract for all PANTHER CLI subcommands,
ensuring consistent argument parsing, error handling, and command execution
patterns across the entire command-line interface.

The Command pattern implementation requires subclasses to implement two
essential methods: register_parser() for CLI argument definition and
handle() for command execution logic.

#### Design Principles

- **Separation of Concerns**: Parser registration separate from execution
- **Consistent Interface**: All commands follow identical method signatures
- **Error Handling**: Standardized return codes and exception management
- **Testability**: Clear separation enables isolated unit testing

#### Implementation Requirements

Each subclass must implement:
1. register_parser(): Define command arguments and subcommands
2. handle(): Execute command logic with proper error handling

#### Return Code Conventions

- 0: Success
- 1: General error or validation failure
- 130: Interrupted by user (Ctrl+C)

#### Methods

##### register_parser(subparsers) → ArgumentParser

Register the subcommand parser with arguments and options.

**See also**: [Command development patterns](DEVELOPER_GUIDE.md#command-development-checklist)

Defines the command-line interface for this command including all
arguments, options, and subcommands. This method is called during
CLI initialization to build the complete argument parser hierarchy.

**Parser Configuration Requirements**:
- Use descriptive help text for user guidance
- Set appropriate argument types and validation
- Include usage examples in description when helpful
- Configure formatter_class for complex help text

**Argument Design Patterns**:
- Required arguments: Use positional arguments or required=True
- Optional flags: Use action='store_true' for boolean flags
- Choice validation: Use choices parameter for restricted values
- File paths: Use type=Path for automatic path validation

**Args:**
- subparsers: The subparsers object from main argument parser, used to register this command as a subcommand with its own argument structure and help documentation.

**Returns:**
ArgumentParser: The configured parser for this command, which will be used to parse command-line arguments specific to this subcommand.

##### handle(args) → int

Execute the subcommand with parsed arguments.

**See also**: [Error handling strategy](DEVELOPER_GUIDE.md#error-handling-strategy) | [Exit codes](#exit-codes)

Implements the core command logic using the parsed command-line
arguments. This method contains the actual functionality of the
command and is responsible for proper error handling and user feedback.

**Implementation Guidelines**:
- Validate arguments before processing
- Provide clear progress feedback for long operations
- Use consistent error messages with emoji indicators
- Return appropriate exit codes for shell scripting
- Log errors with appropriate detail level

**Error Handling Strategy**:
- Catch specific exceptions and provide helpful error messages
- Use debug mode for detailed stack traces
- Return non-zero exit codes for any failure condition
- Provide suggestions for fixing common errors

**Args:**
- args: Parsed command-line arguments from argparse. Contains all options, flags, and positional arguments defined in register_parser() method.

**Returns:**
int: Exit code following Unix conventions: 0 for success, non-zero for various error conditions. Should match shell scripting expectations.

### CLIActionDispatchMixin

**Module**: `panther.cli.base`

Provide standardized action dispatch for CLI commands.

CLIActionDispatchMixin implements a reusable pattern for commands that
have multiple subactions (like 'plugins list', 'plugins info', etc.).
It provides consistent error handling, validation, and user feedback
across all commands that use the action dispatch pattern.

#### Usage Pattern

Commands with multiple subactions inherit from this mixin and use
dispatch_action() to route to appropriate handler methods based on
the parsed action argument.

#### Benefits

- **Consistency**: Same error messages and patterns across commands
- **DRY Principle**: Eliminates duplicate dispatch logic
- **Error Handling**: Standardized validation and error reporting
- **Maintainability**: Single place to update dispatch behavior

#### Methods

##### dispatch_action(args, action_attr, action_handlers, command_name) → int

Dispatch command to appropriate action handler.

Routes parsed command-line arguments to the correct handler method
based on the specified action attribute. Provides consistent error
handling and user feedback for commands with multiple subactions.

**Dispatch Flow**:
1. Validate that action attribute exists and has a value
2. Look up handler method in action_handlers dictionary
3. Call handler method if found, return error if not found
4. Provide consistent error messages with command context

**Error Conditions**:
- Missing action attribute: User didn't specify a subaction
- Unknown action: User specified invalid subaction name
- Handler exceptions: Propagated from individual handler methods

**Args:**
- args: Parsed command-line arguments from argparse containing all options and the action attribute to dispatch on.
- action_attr: Name of the attribute containing the action to dispatch (e.g., 'plugins_action', 'config_action').
- action_handlers: Dictionary mapping action names to their corresponding handler methods or functions.
- command_name: Human-readable command name for error messages and help text (e.g., 'plugins', 'config').

**Returns:**
int: Exit code from the handler method: 0 for successful execution, 1 for validation errors or unknown actions

## Main Entry Points

### create_parser() → ArgumentParser

**Module**: `panther.cli.main`

Create and configure the main argument parser.

Builds the hierarchical argument parser structure with global options
and subcommand registration. Uses argparse subparsers for modular
command organization and consistent help text formatting.

#### Parser Architecture

- Global options (--debug, --version) available to all commands
- Subparser registration for modular command system
- Rich help text with practical examples
- Raw description formatter for preserved formatting

#### Command Registration

Each command class registers itself via CommandClass.register_parser(subparsers),
following the Command pattern for consistent interface and error handling.

**Returns:**
argparse.ArgumentParser: Configured main parser with all subcommands registered

**Note:**
argcomplete.autocomplete() must be called on the returned parser
to enable bash completion support.

### main() → int

**Module**: `panther.cli.main`

Main CLI entry point and command dispatcher.

Orchestrates the complete CLI experience including:
- Global argument parsing and validation
- Debug logging initialization with LoggerFactory integration
- Command discovery and dispatch through command_map
- Consistent error handling and user feedback
- Bash completion support via argcomplete

#### Command Dispatch Architecture

Uses a command_map dictionary to dispatch to appropriate command handlers,
following the Command pattern for consistent interface and error handling.
Each command implements:
- register_parser(subparsers): Define CLI arguments and subcommands
- handle(args): Execute command logic with structured error handling

#### Error Handling Strategy

- KeyboardInterrupt: Graceful cancellation with user message (exit 130)
- General exceptions: User-friendly error messages in normal mode
- Debug mode: Full stacktraces for development and troubleshooting
- Unknown commands: Help text display with error indication

#### Debug Mode Integration

When --debug is specified, initializes LoggerFactory with:
- DEBUG level logging across all components
- Colored output for better development experience
- Detailed exception information via exc_info=True

**Returns:**
int: Exit code following Unix conventions:
     0 = success
     1 = general error
     130 = terminated by Control-C

## Command Classes

### RunCommand

**Module**: `panther.cli.subcommands.run`

Handle experiment execution commands.

Execute PANTHER experiments using configuration files with comprehensive
options for validation, parallel execution, metrics collection, and
output management.

#### Features

- Configuration validation before execution
- Parallel test execution with configurable workers
- Comprehensive metrics collection and reporting
- Flexible output directory management
- Dry-run mode for validation without execution

### ConfigCommand

**Module**: `panther.cli.subcommands.config`

Handle configuration management commands.

Provides comprehensive configuration file management including validation,
schema documentation, template generation, and interactive configuration
design through a wizard-based interface.

#### Subcommands

- **validate**: Validate configuration syntax and schema
- **schema**: Display configuration schema documentation
- **generate**: Create configuration templates
- **design**: Interactive configuration wizard

### PluginsCommand

**Module**: `panther.cli.subcommands.plugins`

Handle plugin management commands.

Discover, inspect, and manage PANTHER plugins with support for filtering,
detailed information display, parameter documentation, and validation.

#### Subcommands

- **list**: Display available plugins with filtering options
- **info**: Show detailed plugin information and capabilities
- **params**: List configurable parameters with types and defaults
- **validate**: Validate plugin structure and dependencies

### CreateCommand

**Module**: `panther.cli.subcommands.create`

Handle plugin and resource creation commands.

Generate scaffolding for new plugins and resources with proper directory
structure, manifest files, example code, and optional test templates.

#### Subcommands

- **plugin**: Create new plugin scaffolding
- **subplugin**: Create protocol-specific implementations

### TutorialCommand

**Module**: `panther.cli.subcommands.tutorial`

Handle interactive tutorial commands.

Provide guided learning experiences for PANTHER framework features
through interactive tutorials, step-by-step guidance, and progress tracking.

#### Subcommands

- **run**: Execute specific tutorial types
- **interactive**: Menu-driven tutorial selection
- **list**: Show available tutorials and completion status

### AdminCommand

**Module**: `panther.cli.subcommands.admin`

Handle administrative and maintenance commands.

System administration tools for cleaning up resources, resetting to
default state, performing diagnostics, and updating components.

#### Subcommands

- **clean**: Clean up temporary resources
- **reset**: Reset system to default state
- **doctor**: Run system diagnostics
- **upgrade**: Update framework components

### CheckCommand

**Module**: `panther.cli.subcommands.check`

Handle code quality and validation commands.

Comprehensive code quality checking including linting, type checking,
test execution, and security scanning with configurable rules and
detailed reporting.

### MetricsCommand

**Module**: `panther.cli.subcommands.metrics`

Handle metrics collection and analysis commands.

Manage experiment metrics including collection configuration, analysis
tools, export capabilities, and integration with monitoring systems.

### ToolsCommand

**Module**: `panther.cli.subcommands.tools`

Handle development and operational tools.

Utility commands for development workflow including Docker optimization,
dependency management, and development environment setup.

## Interactive Components

### ExperimentDesigner

**Module**: `panther.cli.interactive.experiment_designer`

Interactive configuration designer with step-by-step wizard.

Provides guided configuration creation through progressive disclosure,
validation at each step, and intelligent defaults based on user selections.

### ValidationHelper

**Module**: `panther.cli.interactive.validation_helper`

Enhanced validation with detailed error explanations.

Provides context-aware error messages, suggestions for common fixes,
and links to relevant documentation for configuration issues.

### Configuration Builders

**Module**: `panther.cli.interactive.builders`

Modular builders for different configuration sections.

- **BaseBuilder**: Foundation for all configuration builders
- **GlobalConfigBuilder**: Global configuration section
- **TestConfigBuilder**: Test case configuration section

## Error Handling

### Exit Codes

The CLI follows Unix conventions for exit codes:

- **0**: Success
- **1**: General error (validation, execution failures)
- **2**: Misuse of shell command (incorrect arguments)
- **126**: Command cannot execute (permissions, missing dependencies)
- **127**: Command not found
- **130**: Interrupted by signal (Ctrl+C)

### Error Message Patterns

All commands use consistent error message formatting:

- ✅ Success messages with green checkmark
- ❌ Error messages with red X
- ⚠️ Warning messages with yellow warning
- 🔍 Information/searching with magnifying glass
- 💡 Suggestions with light bulb

### Debug Mode

Enable debug mode with `--debug` or `PANTHER_DEBUG=1` for:

- Full stack traces for all exceptions
- Detailed logging from all components
- Colored output for better readability
- Performance timing information

## Best Practices

### Command Development

1. **Inherit from BaseCommand**: Ensures consistent interface
2. **Use CLIActionDispatchMixin**: For commands with multiple subactions
3. **Follow PEP 257**: Docstring formatting standards
4. **Include Examples**: Practical usage examples in docstrings
5. **Test Thoroughly**: Unit and integration tests for all commands

### User Experience

1. **Progressive Disclosure**: Simple commands for common tasks
2. **Helpful Defaults**: Sensible default values for most options
3. **Clear Error Messages**: Actionable feedback with suggestions
4. **Consistent Patterns**: Same UX patterns across all commands
5. **Rich Help Text**: Comprehensive help with examples

### Integration

1. **LoggerFactory**: Use centralized logging configuration
2. **Configuration System**: Integrate with PANTHER configuration
3. **Plugin System**: Support plugin discovery and management
4. **Error Handling**: Consistent exception handling patterns
5. **Testing Framework**: Integration with PANTHER test infrastructure

---

*This API reference is generated from source code docstrings and provides comprehensive documentation for all public interfaces in the PANTHER CLI module.*
