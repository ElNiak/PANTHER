# Command Processor Quickstart Tutorial

## Overview

This tutorial walks you through the essential features of the PANTHER command processor module. You'll learn how to process commands, detect their properties, and build complex command structures.

## Prerequisites

- Python 3.8+
- PANTHER framework installed
- Basic understanding of shell commands

## Step 1: Basic Command Processing

Let's start with processing a simple command structure:

```python
from panther.core.command_processor import CommandProcessor

# Create a processor instance
processor = CommandProcessor()

# Define a simple command structure
commands = {
    "pre_run_cmds": ["echo 'Setting up environment'"],
    "run_cmd": {
        "command_args": "python hello.py",
        "working_dir": "/tmp",
        "timeout": 30
    },
    "post_run_cmds": ["echo 'Cleanup complete'"]
}

# Process the commands
result = processor.process_commands(commands)
print("Processed commands:", result)
```

**What happens here?**
- The processor validates the command structure
- Each command type is processed according to its format
- The `run_cmd` gets special handling for its dictionary structure
- Pre and post commands are processed as lists

## Step 2: Working with ShellCommand Objects

The `ShellCommand` class provides rich command representation:

```python
from panther.core.command_processor.models import ShellCommand

# Create from string
simple_cmd = ShellCommand.from_string("echo 'Hello World'")
print(f"Command: {simple_cmd.command}")
print(f"Is Critical: {simple_cmd.metadata.is_critical}")

# Create a complex command
complex_cmd = ShellCommand.from_string("""
function backup_data() {
    if [ -d /data ]; then
        tar -czf backup.tar.gz /data
        echo "Backup completed"
    else
        echo "Data directory not found"
    fi
}
""")

print(f"Is multiline: {complex_cmd.metadata.is_multiline}")
print(f"Is function: {complex_cmd.metadata.is_function_definition}")
```

**Key points:**
- Commands are automatically analyzed for properties
- Metadata includes execution context and command characteristics
- Complex shell constructs are properly detected

## Step 3: Command Property Detection

Learn how the system detects different command types:

```python
from panther.core.command_processor import CommandProcessor

processor = CommandProcessor()

# Test different command types
test_commands = [
    "echo 'simple command'",
    "VAR=value",
    "if [ -f file.txt ]; then echo 'found'; fi",
    """
    for i in {1..5}; do
        echo "Number: $i"
    done
    """,
    """
    deploy() {
        docker build -t myapp .
        docker run myapp
    }
    """
]

for cmd in test_commands:
    properties = processor.detect_command_properties(cmd)
    print(f"\nCommand: {cmd[:30]}...")
    for prop, value in properties.items():
        if value:  # Only show True properties
            print(f"  {prop}: {value}")
```

**Expected output:**
- Simple commands have minimal properties
- Variable assignments are detected
- Control structures (if, for) are identified
- Function definitions are recognized

## Step 4: Using the Builder Pattern

Build commands programmatically with the builder pattern:

```python
from panther.core.command_processor.builders import CommandBuilder

# Build a simple command
command = (CommandBuilder()
           .set_command("python manage.py migrate")
           .set_working_directory("/app")
           .set_environment({"DATABASE_URL": "postgresql://..."})
           .set_timeout(300)
           .set_critical(True)
           .build())

print("Built command:", command.to_dict())

# Build a service command
from panther.core.command_processor.builders import ServiceCommandBuilder

service_cmd = (ServiceCommandBuilder()
               .set_command("docker run nginx")
               .set_service_name("web-server")
               .set_restart_policy("always")
               .build())

print("Service command:", service_cmd.to_dict())
```

**Benefits of builders:**
- Fluent, readable command construction
- Type safety and validation
- Extensible for specialized command types

## Step 5: Handling Complex Command Structures

Process commands with advanced shell features:

```python
from panther.core.command_processor import CommandProcessor

processor = CommandProcessor()

# Complex command structure with shell constructs
advanced_commands = {
    "pre_run_cmds": [
        "export NODE_ENV=production",
        "mkdir -p /tmp/logs",
        """
        if ! command -v docker &> /dev/null; then
            echo "Docker not installed"
            exit 1
        fi
        """
    ],
    "run_cmd": {
        "command_args": "npm start 2>&1 | tee /tmp/logs/app.log",
        "working_dir": "/app",
        "environment": {
            "PORT": "3000",
            "LOG_LEVEL": "info"
        },
        "timeout": 600
    },
    "post_run_cmds": [
        "docker system prune -f",
        "rm -rf /tmp/build/*"
    ]
}

result = processor.process_commands(advanced_commands)

# Examine the processed structure
for cmd_type, processed_cmds in result.items():
    print(f"\n{cmd_type}:")
    if cmd_type == "run_cmd":
        print(f"  Working dir: {processed_cmds['working_dir']}")
        print(f"  Command: {processed_cmds['command_args']}")
        print(f"  Environment: {processed_cmds['environment']}")
    else:
        for i, cmd in enumerate(processed_cmds):
            print(f"  {i+1}. {cmd['command'][:50]}...")
            if cmd.get('is_multiline'):
                print(f"     (multiline command)")
```

## Step 6: Error Handling and Validation

Learn how the processor handles errors:

```python
from panther.core.command_processor import CommandProcessor
from panther.core.exceptions.fast_fail import PantherException

processor = CommandProcessor()

# Test invalid command structures
invalid_commands = [
    # Wrong type - should be dict
    "invalid string command",

    # Invalid run_cmd structure
    {"run_cmd": "should be dict not string"},

    # Invalid command list items
    {"pre_run_cmds": [123, None, {}]}
]

for invalid_cmd in invalid_commands:
    try:
        result = processor.process_commands(invalid_cmd)
        print("Unexpected success")
    except PantherException as e:
        print(f"Caught expected error: {e.message}")
        print(f"Error category: {e.category}")
        print(f"Error severity: {e.severity}")
    except Exception as e:
        print(f"Other error: {e}")
```

**Error handling features:**
- Fast-fail validation catches structural issues early
- Detailed error context for debugging
- Categorized errors with severity levels

## Step 7: Shell Utilities

Use utility functions for shell command manipulation:

```python
from panther.core.command_processor.utils.shell_utils import (
    escape_shell_command,
    parse_command_with_redirections,
    split_complex_command
)

# Escape dangerous commands
dangerous_cmd = "rm -rf $(cat user_input.txt)"
safe_cmd = escape_shell_command(dangerous_cmd)
print(f"Original: {dangerous_cmd}")
print(f"Escaped: {safe_cmd}")

# Parse commands with redirections
redirected_cmd = "python script.py > output.log 2>&1"
parsed = parse_command_with_redirections(redirected_cmd)
print(f"Parsed command: {parsed}")

# Split complex commands
complex_cmd = "cd /app && npm install && npm test"
components = split_complex_command(complex_cmd)
print(f"Command components: {components}")
```

## Step 8: Integration with PANTHER Framework

See how command processing integrates with the broader framework:

```python
from panther.core.command_processor import CommandProcessor
from panther.core.command_processor.mixins import CommandEventMixin

# Create processor with event handling
class EventAwareProcessor(CommandProcessor, CommandEventMixin):
    def process_commands(self, commands, target_format="generic"):
        # Emit start event
        self.emit_command_event("processing_started", {
            "command_count": len(commands),
            "target_format": target_format
        })

        # Process normally
        result = super().process_commands(commands, target_format)

        # Emit completion event
        self.emit_command_event("processing_completed", {
            "result": result
        })

        return result

# Use the enhanced processor
processor = EventAwareProcessor()
commands = {"run_cmd": {"command_args": "echo 'test'"}}
result = processor.process_commands(commands)
```

## Next Steps

Now that you've completed the quickstart tutorial, you can:

1. **Explore Advanced Features**: Check the API reference for detailed method documentation
2. **Build Custom Processors**: Extend the base classes for domain-specific needs
3. **Create Environment Adapters**: Implement `IEnvironmentCommandAdapter` for specific deployment targets
4. **Integrate with Services**: Use the command processor in your PANTHER services

## Common Patterns

### Pattern 1: Batch Command Processing
```python
# Process multiple command sets
command_sets = [commands1, commands2, commands3]
results = [processor.process_commands(cmds) for cmds in command_sets]
```

### Pattern 2: Command Validation Before Execution
```python
try:
    validated_commands = processor.process_commands(raw_commands)
    # Commands are valid, proceed with execution
except PantherException:
    # Handle validation errors
    pass
```

### Pattern 3: Dynamic Command Building
```python
def build_deployment_commands(env, version):
    return (CommandBuilder()
            .set_command(f"docker run myapp:{version}")
            .set_environment({"ENV": env})
            .set_critical(env == "production")
            .build())
```

## Troubleshooting

### Common Issues

1. **Commands not detected as multiline**: Ensure proper newline characters in command strings
2. **Function detection failing**: Check that function syntax follows shell conventions
3. **Environment variables not set**: Use the environment parameter in run_cmd structure
4. **Timeout issues**: Set appropriate timeout values for long-running commands

### Debug Tips

- Enable debug logging to see detailed processing information
- Use `detect_command_properties()` to verify command detection
- Check the `to_dict()` output of ShellCommand objects
- Validate command structure before processing

This concludes the quickstart tutorial. You now have the knowledge to effectively use the PANTHER command processor module!
