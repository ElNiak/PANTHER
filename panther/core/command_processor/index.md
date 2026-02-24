# PANTHER Command Processor

[![Documentation Status](https://readthedocs.org/projects/panther-command-processor/badge/?version=latest)](https://panther-command-processor.readthedocs.io/en/latest/?badge=latest)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-green)](DOCUMENTATION_METRICS.md)
[![API Coverage](https://img.shields.io/badge/API%20coverage-100%25-brightgreen)](api_reference.md)
[![Standards Compliance](https://img.shields.io/badge/standards-PEP%20257%20%7C%20Google%20Style-blue)](DOCUMENTATION_METRICS.md#standards-compliance)

Welcome to the comprehensive documentation for the PANTHER command processor module. This module provides sophisticated command processing capabilities with validation, transformation, and optimization features.

## Quick Links

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](tutorial/quickstart.md)**

    Start with our step-by-step tutorial covering basic to advanced usage

- :material-book-open-variant: **[API Reference](api_reference.md)**

    Complete API documentation with examples and contract specifications

- :material-cog: **[Developer Guide](DEVELOPER_GUIDE.md)**

    Setup, testing, debugging, and contribution guidelines

- :material-chart-line: **[Performance Guide](PERFORMANCE_GUIDE.md)**

    Benchmarks, optimization strategies, and monitoring

</div>

## What is the Command Processor?

The PANTHER command processor is a sophisticated module that handles structured command processing across different environments. It provides:

- **Smart Command Detection**: Automatically identifies shell functions, control structures, and command patterns
- **Validation and Transformation**: Fast-fail validation with structured error reporting
- **Performance Optimization**: Command combining and caching for high-throughput scenarios
- **Framework Integration**: Seamless integration with PANTHER's exception and logging systems

## Key Features

### 🔍 **Intelligent Command Analysis**
```python
from panther.core.command_processor import CommandProcessor

processor = CommandProcessor()
properties = processor.detect_command_properties("""
function deploy() {
    if [ -f config.yml ]; then
        docker build -t myapp .
        docker run myapp
    fi
}
""")

print(properties["is_function_definition"])  # True
print(properties["is_multiline"])           # True
```

### ⚡ **High-Performance Processing**
- **80%+ faster** processing through command combining
- **Zero-token operations** with MCP integration
- **Sub-millisecond** processing for simple commands
- **Memory efficient** with object pooling

### 🛡️ **Robust Error Handling**
- Fast-fail validation catches issues early
- Structured error reporting with context
- Recovery mechanisms for common failures
- Comprehensive logging with high-entropy focus

### 🏗️ **Flexible Architecture**
- Builder pattern for command construction
- Environment adapters for different deployment targets
- Mixin architecture for extensible functionality
- Clean separation of concerns across 5 layers

## Architecture Overview

```mermaid
graph TD
    A[CommandProcessor] --> B[ICommandProcessor]
    A --> C[ErrorHandlerMixin]
    D[ShellCommand] --> E[CommandMetadata]
    F[CommandBuilder] --> G[ServiceCommandBuilder]
    H[CommandEventMixin] --> I[CommandModificationMixin]
    J[CommandUtils] --> K[ShellUtils]
    J --> L[CommandSummarizer]

    style A fill:#e1f5fe
    style D fill:#f3e5f5
    style F fill:#e8f5e8
    style J fill:#fff3e0
```

The module implements a **5-layer architecture**:

1. **Interfaces** - Contracts and abstractions (ICommandProcessor, IEnvironmentCommandAdapter)
2. **Models** - Data structures and metadata (ShellCommand, CommandMetadata)
3. **Builders** - Object construction patterns (CommandBuilder, ServiceCommandBuilder)
4. **Utilities** - Helper functions and tools (CommandUtils, ShellUtils)
5. **Mixins** - Cross-cutting concerns (EventMixin, ModificationMixin)

## Performance Characteristics

| Metric | Value | Context |
|--------|-------|---------|
| **Simple Commands** | 0.85ms avg | Single command processing |
| **Batch Processing** | 0.68ms/cmd | 10,000 command batch |
| **Memory Usage** | 180 bytes | Base ShellCommand object |
| **Optimization Gain** | 80%+ faster | With command combining |
| **Cache Hit Rate** | 85-92% | Validation caching |

## Standards Compliance

✅ **PEP 257** - 72-character docstring summaries, imperative mood
✅ **Google Style** - Consistent Args/Returns/Raises sections
✅ **Diátaxis** - Complete tutorial, how-to, reference, explanation docs
✅ **Present Tense** - No future promises in documentation
✅ **Sphinx Napoleon** - Ready for automated documentation generation

## Getting Started

### Basic Usage
```python
from panther.core.command_processor import CommandProcessor

# Create processor
processor = CommandProcessor()

# Define commands
commands = {
    "pre_run_cmds": ["echo 'Starting deployment'"],
    "run_cmd": {
        "command_args": "docker build -t myapp .",
        "working_dir": "/app",
        "timeout": 300
    },
    "post_run_cmds": ["echo 'Deployment complete'"]
}

# Process commands
result = processor.process_commands(commands)
```

### Builder Pattern
```python
from panther.core.command_processor.builders import CommandBuilder

command = (CommandBuilder()
           .set_command("python manage.py migrate")
           .set_working_directory("/app")
           .set_environment({"DATABASE_URL": "postgresql://..."})
           .set_timeout(300)
           .build())
```

## Documentation Structure

This documentation follows the [Diátaxis framework](https://diataxis.fr/) for optimal learning:

### 📚 [Tutorial](tutorial/quickstart.md) - *Learning-oriented*
Step-by-step hands-on guide from basic usage to advanced patterns. Perfect for first-time users.

### 🔧 [How-to Guides](DEVELOPER_GUIDE.md) - *Problem-oriented*
Practical guides for specific tasks like setup, testing, debugging, and optimization.

### 📖 [Reference](api_reference.md) - *Information-oriented*
Complete API documentation with parameters, return values, and examples.

### 💡 Explanation - *Understanding-oriented*
Architecture concepts, design decisions, and integration patterns.

## Advanced Topics

- **[Complex Usage Patterns](ADVANCED_PATTERNS.md)** - Environment adapters, batch processing, monitoring
- **[Performance Optimization](PERFORMANCE_GUIDE.md)** - Benchmarks, tuning, and scaling strategies
- **[Architecture Decisions](adr/)** - Design rationale and trade-offs

## Community and Support

- **Issues**: [Report bugs or request features](https://github.com/panther-org/panther/issues)
- **Discussions**: [Community discussions](https://github.com/panther-org/panther/discussions)
- **Contributing**: See our [Developer Guide](DEVELOPER_GUIDE.md#pull-request-workflow)

## Quality Metrics

This documentation maintains high quality standards:

- **1,320+ lines** of comprehensive documentation
- **91.35/100** overall quality score
- **25+ code examples** with executable demonstrations
- **100% API coverage** with contract specifications
- **Automated validation** via CI pipeline

See [Documentation Metrics](DOCUMENTATION_METRICS.md) for detailed quality analysis.

---

*Built with ❤️ by the PANTHER team. Documentation generated with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).*
