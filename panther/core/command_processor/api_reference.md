# API Reference - Command Processor Module

## Core Interfaces

### ICommandProcessor

Abstract base class defining the command processing contract.

#### Methods

##### process_commands(commands, target_format="generic")
Process a command structure into a target format.

**Parameters:**
- `commands` (Dict[str, Any]): Dictionary containing command structure
- `target_format` (str, optional): Target format identifier. Defaults to "generic"

**Returns:**
- `Dict[str, Any]`: Dictionary with processed commands

**Raises:**
- `PantherException`: If command structure is invalid

**Example:**
```python
processor = CommandProcessor()
commands = {
    "pre_run_cmds": ["echo setup"],
    "run_cmd": {"command_args": "python script.py"},
    "post_run_cmds": ["echo cleanup"]
}
result = processor.process_commands(commands)
```

##### process_command_list(commands, detect_properties=True)
Process a list of commands into structured format.

**Parameters:**
- `commands` (List[Any]): List of commands (strings, ShellCommand objects, etc.)
- `detect_properties` (bool, optional): Whether to detect properties like multiline, function definitions. Defaults to True

**Returns:**
- `List[Dict[str, Any]]`: List of processed command dictionaries

##### detect_command_properties(command)
Detect properties of a command string.

**Parameters:**
- `command` (str): Command string to analyze

**Returns:**
- `Dict[str, bool]`: Dictionary of detected properties including:
  - `is_multiline`: Whether command spans multiple lines
  - `is_function_definition`: Whether command defines a function
  - `is_control_structure`: Whether command is a control structure

### IEnvironmentCommandAdapter

Abstract interface for environment-specific command adaptations.

#### Methods

##### adapt_commands(commands)
Adapt commands for a specific environment.

**Parameters:**
- `commands` (Dict[str, Any]): Processed commands

**Returns:**
- `Dict[str, Any]`: Environment-adapted commands

## Core Classes

### CommandProcessor

Main implementation of ICommandProcessor with validation and transformation logic.

**Inherits:** ICommandProcessor, ErrorHandlerMixin

#### Constructor
```python
CommandProcessor()
```

Creates a new command processor instance with feature logger.

#### Methods

All methods from ICommandProcessor plus:

##### _validate_command_structure(commands)
Validate command structure before processing (internal method).

**Parameters:**
- `commands` (Dict[str, Any]): Dictionary containing command structure

**Raises:**
- `PantherException`: If command structure is invalid

**Pre-conditions:**
- Commands must be a dictionary
- Command types must be strings
- run_cmd must be a dictionary if present

**Post-conditions:**
- Command structure is validated as correct
- No side effects if validation passes

### ShellCommand

Primary command representation with rich metadata.

#### Constructor
```python
ShellCommand(command, metadata=None)
```

**Parameters:**
- `command` (str): The shell command string
- `metadata` (CommandMetadata, optional): Command metadata

#### Class Methods

##### from_string(command_str, is_critical=True)
Create ShellCommand from string with automatic property detection.

**Parameters:**
- `command_str` (str): Command string to parse
- `is_critical` (bool, optional): Whether command failure is critical. Defaults to True

**Returns:**
- `ShellCommand`: New ShellCommand instance

**Example:**
```python
cmd = ShellCommand.from_string("echo 'hello world'")
print(cmd.command)  # "echo 'hello world'"
print(cmd.metadata.is_critical)  # True
```

##### from_dict(command_dict)
Create ShellCommand from dictionary representation.

**Parameters:**
- `command_dict` (Dict[str, Any]): Dictionary with command and metadata

**Returns:**
- `ShellCommand`: New ShellCommand instance

#### Instance Methods

##### to_dict()
Convert ShellCommand to dictionary representation.

**Returns:**
- `Dict[str, Any]`: Dictionary representation including command and metadata

##### escape_command()
Escape shell command for safe execution.

**Returns:**
- `str`: Escaped command string

**Post-conditions:**
- Command is safe for shell execution
- Special characters are properly escaped

### CommandMetadata

Metadata container for shell commands.

#### Attributes

**Core Metadata:**
- `is_critical` (bool): Whether command failure is critical. Defaults to True
- `timeout` (Optional[int]): Command timeout in seconds
- `retry_count` (int): Number of retries on failure. Defaults to 0
- `environment` (Dict[str, str]): Environment variables
- `working_directory` (Optional[str]): Working directory for execution
- `description` (Optional[str]): Human-readable description
- `tags` (List[str]): Command tags for categorization

**Detection Metadata:**
- `is_multiline` (bool): Whether command spans multiple lines
- `is_function_definition` (bool): Whether command defines a function
- `is_function_call` (bool): Whether command calls a function
- `has_control_operators` (bool): Whether command uses control operators
- `control_operators` (List[str]): List of detected control operators
- `is_variable_assignment` (bool): Whether command assigns variables
- `is_shell_builtin` (bool): Whether command uses shell builtins

## Builder Classes

### CommandBuilder

Base builder for command construction using fluent interface.

#### Methods

##### set_command(command)
Set the main command string.

**Parameters:**
- `command` (str): Command string

**Returns:**
- `CommandBuilder`: Self for method chaining

##### set_working_directory(directory)
Set working directory for command execution.

**Parameters:**
- `directory` (str): Directory path

**Returns:**
- `CommandBuilder`: Self for method chaining

##### set_environment(env_vars)
Set environment variables for command.

**Parameters:**
- `env_vars` (Dict[str, str]): Environment variables

**Returns:**
- `CommandBuilder`: Self for method chaining

##### set_timeout(timeout)
Set command timeout.

**Parameters:**
- `timeout` (int): Timeout in seconds

**Returns:**
- `CommandBuilder`: Self for method chaining

##### set_critical(is_critical)
Set whether command failure is critical.

**Parameters:**
- `is_critical` (bool): Critical flag

**Returns:**
- `CommandBuilder`: Self for method chaining

##### build()
Build and return the configured ShellCommand.

**Returns:**
- `ShellCommand`: Configured command instance

**Example:**
```python
command = (CommandBuilder()
           .set_command("python script.py")
           .set_working_directory("/app")
           .set_timeout(300)
           .set_critical(True)
           .build())
```

### ServiceCommandBuilder

Specialized builder for service commands.

**Inherits:** CommandBuilder

Additional methods for service-specific configuration:

##### set_service_name(name)
Set service name for the command.

##### set_restart_policy(policy)
Set restart policy for service commands.

## Utility Classes

### CommandUtils

General command manipulation utilities.

#### Class Methods

##### validate_command(command)
Validate command structure and syntax.

##### sanitize_command(command)
Sanitize command for safe execution.

##### extract_variables(command)
Extract variable assignments from command.

### CommandSummarizer

Command analysis and summarization utilities.

#### Methods

##### summarize_commands(commands)
Generate summary of command structure.

**Parameters:**
- `commands` (Dict[str, Any]): Command structure

**Returns:**
- `str`: Human-readable summary

##### analyze_complexity(commands)
Analyze command complexity metrics.

**Returns:**
- `Dict[str, Any]`: Complexity analysis

## Mixin Classes

### CommandEventMixin

Provides event handling capabilities for command processors.

#### Methods

##### emit_command_event(event_type, command_data)
Emit command-related events.

### CommandModificationMixin

Provides command modification capabilities.

#### Methods

##### modify_command(command, modifications)
Apply modifications to a command.

## Utility Functions

### Shell Utilities

#### escape_shell_command(command)
Escape shell command for safe execution.

**Parameters:**
- `command` (str): Command to escape

**Returns:**
- `str`: Escaped command

#### normalize_command_ending(command)
Normalize command line endings.

#### parse_command_with_redirections(command)
Parse command and extract redirections.

#### split_complex_command(command)
Split complex command into components.

#### combine_shell_constructs(commands)
Combine related shell constructs for optimization.

**Parameters:**
- `commands` (List[ShellCommand]): Commands to combine

**Returns:**
- `List[ShellCommand]`: Combined commands

**Pre-conditions:**
- Commands must be valid ShellCommand instances
- Commands should be logically related

**Post-conditions:**
- Related constructs are combined into single commands
- Command semantics are preserved

## Constants

### Shell Constants

#### SHELL_BUILTINS
List of shell builtin commands:
```python
SHELL_BUILTINS = [
    "echo", "cd", "pwd", "export", "set", "unset",
    "alias", "unalias", "history", "exit", "return",
    "source", ".", "eval", "exec", "test", "[", "[[",
    "true", "false", ":", "break", "continue"
]
```

#### SHELL_CONTROL_OPERATORS
Shell control operators:
```python
SHELL_CONTROL_OPERATORS = ["&&", "||", "|", ";", "&"]
```

#### SHELL_CONTROL_STRUCTURES
Shell control structure keywords:
```python
SHELL_CONTROL_STRUCTURES = [
    "if", "then", "else", "elif", "fi",
    "for", "while", "until", "do", "done",
    "case", "esac", "function"
]
```

#### REDIRECTION_OPERATORS
Shell redirection operators:
```python
REDIRECTION_OPERATORS = [">", ">>", "<", "<<", "2>", "2>>", "&>", "&>>"]
```

## Exceptions

### CommandGenerationError

Exception raised when command generation fails.

**Inherits:** Exception

#### Constructor
```python
CommandGenerationError(message, command_data=None)
```

**Parameters:**
- `message` (str): Error message
- `command_data` (Any, optional): Related command data

## Usage Examples

### Basic Command Processing
```python
from panther.core.command_processor import CommandProcessor

processor = CommandProcessor()
commands = {
    "pre_run_cmds": ["echo Starting"],
    "run_cmd": {
        "command_args": "python -m mymodule",
        "working_dir": "/app",
        "environment": {"ENV": "production"}
    },
    "post_run_cmds": ["echo Finished"]
}

result = processor.process_commands(commands)
```

### Building Commands with Builder Pattern
```python
from panther.core.command_processor.builders import ServiceCommandBuilder

command = (ServiceCommandBuilder()
           .set_command("docker run myimage")
           .set_service_name("web-service")
           .set_restart_policy("always")
           .set_environment({"PORT": "8080"})
           .build())
```

### Command Property Detection
```python
from panther.core.command_processor import CommandProcessor

processor = CommandProcessor()
properties = processor.detect_command_properties("""
function deploy() {
    if [ -f deploy.sh ]; then
        ./deploy.sh
    fi
}
""")

print(properties["is_function_definition"])  # True
print(properties["is_multiline"])  # True
print(properties["is_control_structure"])  # False (it's a function, not a control structure)
```
