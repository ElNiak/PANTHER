# PANTHER CLI Documentation Report (*In Progress*)

## Executive Summary

PANTHER (Protocol Analysis and Testing for Heterogeneous Execution and Research) is a comprehensive CLI tool for network protocol testing, formal verification, and automated analysis. This report provides detailed documentation of all CLI commands, their arguments, options, and execution traces.

**CLI Framework**: Click-based (migrated from argparse)
**Version**: 1.1.3
**Python Entry Point**: `python -m panther`

## Architecture Overview

The PANTHER CLI is built using the Click framework with a modular command structure:

- **Main Entry Point**: `panther/__main__.py` → `panther/cli_click/core/main.py`
- **Command Groups**: Organized in `panther/cli_click/commands/`
- **Core Features**: Plugin system, Docker integration, metrics collection, configuration management

## Command Structure

### Main Command
```bash
python -m panther [OPTIONS] COMMAND [ARGS]...
```

### Available Commands
- **admin** - Administrative and system management
- **check** - Code quality checks and linters
- **completion** - Shell completion setup
- **config** - Configuration management and validation
- **create** - Plugin and component creation
- **metrics** - Metrics management and analysis
- **plugins** - Plugin discovery and management
- **run** - Experiment execution
- **tools** - Development tools installation
- **tutorial** - Interactive learning platform

## Global Options

| Option | Description |
|--------|-------------|
| `--debug/--no-debug` | Enable debug logging with detailed output |
| `-v, --verbose` | Enable verbose output |
| `--version` | Show version and exit |
| `--help` | Show help message and exit |

## Command Documentation

### 1. Main Command Help Output

```
Usage: python -m panther [OPTIONS] COMMAND [ARGS]...

  PANTHER - Protocol Analysis and Testing for Heterogeneous Execution and
  Research

  Modern CLI for network protocol testing, formal verification, and automated
  analysis of protocol implementations across multiple environments.

  Key Features:
  🔬 Protocol formal analysis and verification
  🐋 Docker-based isolated testing environments
  🌐 Network simulation and testing
  📊 Comprehensive metrics and reporting
  🔧 Extensible plugin architecture

  Examples:
    panther run --config experiment.yaml          # Run experiment
    panther config validate --config config.yaml # Validate configuration
    panther plugins list                          # List available plugins
    panther create plugin service my_service      # Create new service plugin
    panther tutorial run service                  # Run service tutorial
    panther tutorial interactive                  # Interactive tutorial mode
    panther check --all                           # Run all code quality checks
    panther metrics list                          # List available metrics
    panther admin status                          # Show system status
    panther admin docker --images-all             # Clean Docker images
    panther tools install-slim                    # Install Docker optimization tool
```

### 2. run - Execute PANTHER Experiments

#### Command Usage
```bash
panther run [OPTIONS]
```

#### Required Arguments
- `-c, --config PATH` - Path to experiment configuration file [required]

#### Optional Arguments

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output-dir PATH` | Path | `outputs` | Output directory for experiment results |
| `--experiment-name TEXT` | String | - | Override experiment name from configuration |
| `--dry-run` | Flag | False | Show commands without executing |
| `-v, --verbose` | Flag | False | Enable verbose output |
| `--exec-env-dir DIRECTORY` | Path | - | Custom execution environment plugin directory |
| `--net-env-dir DIRECTORY` | Path | - | Custom network environment plugin directory |
| `--iut-dir DIRECTORY` | Path | - | Custom IUT plugin directory |
| `--tester-dir DIRECTORY` | Path | - | Custom tester plugin directory |
| `--enable-metrics/--disable-metrics` | Flag | False | Enable/disable metrics collection |
| `--metrics-output-dir PATH` | Path | `outputs/metrics` | Directory for metrics output |
| `--metrics-interval INTEGER` | Integer | 1 | Metrics collection interval in seconds |
| `--metrics-disable-resource-monitoring` | Flag | False | Disable resource monitoring |
| `--metrics-generate-report` | Flag | False | Generate metrics report after experiment |
| `--metrics-export-format [json\|csv\|yaml]` | Choice | `json` | Export format for metrics data |
| `--docker-run-as-host` | Flag | False | Run containers with host user ID |
| `--docker-user-id INTEGER` | Integer | - | Custom user ID for containers |
| `--docker-group-id INTEGER` | Integer | - | Custom group ID for containers |
| `--docker-user-name TEXT` | String | `panther` | Username for custom user creation |

#### Help Output
```
Usage: python -m panther run [OPTIONS]

  Execute PANTHER experiments with specified configuration.

  Runs protocol analysis and testing experiments using Docker-based
  environments. Supports multiple network configurations, plugin systems, and
  comprehensive metrics collection.

  Key Features:
  🚀 Experiment execution with comprehensive logging
  🐋 Docker-based isolated testing environments
  📊 Optional metrics collection and reporting
  🔧 Plugin system for custom implementations
  ⚙️  Flexible configuration management

  Examples:
    # Basic experiment execution
    panther run --config experiment.yaml

    # With custom output directory
    panther run --config tests/quic.yaml --output-dir results/

    # Dry run to validate configuration
    panther run --config experiment.yaml --dry-run

    # With metrics collection
    panther run --config experiment.yaml --enable-metrics
```

### 3. config - Configuration Management

#### Command Usage
```bash
panther config [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

##### 3.1 config validate
```bash
panther config validate [OPTIONS]
```

**Required Arguments:**
- `-c, --config PATH` - Path to configuration file to validate [required]

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--strict` | Enable strict validation mode |
| `--show-schema` | Show configuration schema information |
| `--explain` | Show detailed explanations for validation errors |
| `--format [text\|json\|yaml]` | Output format for validation results |

##### 3.2 config generate
```bash
panther config generate [OPTIONS]
```

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--template [minimal\|basic\|advanced\|performance\|security]` | Choice | `basic` | Configuration template type |
| `-o, --output PATH` | Path | - | Output file path |
| `--overwrite` | Flag | False | Overwrite existing file without confirmation |

##### 3.3 config schema
```bash
panther config schema [OPTIONS]
```

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format [json\|yaml\|text]` | Choice | `text` | Output format for schema |
| `--section TEXT` | String | - | Show specific schema section |
| `--examples` | Flag | False | Include configuration examples |

##### 3.4 config design
```bash
panther config design [OPTIONS]
```

**Required Arguments:**
- `-o, --output PATH` - Output file path for generated configuration [required]

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--from-file PATH` | Start from existing configuration file |
| `--quick` | Quick mode - use defaults and skip optional configurations |
| `--non-interactive` | Non-interactive mode for automated usage |

### 4. plugins - Plugin Management

#### Command Usage
```bash
panther plugins [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

##### 4.1 plugins list
```bash
panther plugins list [OPTIONS]
```

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--type [all\|iut\|testers\|network_environment\|execution_environment]` | Choice | `all` | Filter plugins by type |
| `--format [table\|json\|simple]` | Choice | `table` | Output format |
| `--show-path` | Flag | False | Include plugin file paths in output |

##### 4.2 plugins params
```bash
panther plugins params [OPTIONS] PLUGIN_NAME
```

**Required Arguments:**
- `PLUGIN_NAME` - Name of the plugin

**Optional Arguments:**
| Option | Type | Description |
|--------|------|-------------|
| `--type [iut\|testers\|network_environment\|execution_environment]` | Choice | Plugin type (auto-detected if not specified) |
| `--protocol TEXT` | String | Protocol name for filtering parameters |
| `--format [text\|json]` | Choice | Output format for parameters |

##### 4.3 plugins scan
```bash
panther plugins scan [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--directory PATH` | Custom directory to scan for plugins |
| `--recursive` | Scan directories recursively |

##### 4.4 plugins validate
```bash
panther plugins validate [OPTIONS] PLUGIN_PATH
```

**Required Arguments:**
- `PLUGIN_PATH` - Path to plugin file or directory

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--strict` | Enable strict validation mode |
| `--check-imports` | Validate all import statements |

##### 4.5 plugins check-deps
```bash
panther plugins check-deps [OPTIONS] PLUGIN_PATH
```

**Required Arguments:**
- `PLUGIN_PATH` - Path to plugin file or directory

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--fix` | Attempt to install missing dependencies |
| `--requirements-file PATH` | Output missing dependencies to requirements file |

### 5. create - Plugin and Component Creation

#### Command Usage
```bash
panther create [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

##### 5.1 create plugin
```bash
panther create plugin [OPTIONS] PLUGIN_TYPE PLUGIN_NAME
```

**Required Arguments:**
- `PLUGIN_TYPE` - Type of plugin: `service`, `environment`, `protocol`
- `PLUGIN_NAME` - Name of the plugin to create

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dev-mode` | Flag | False | Create plugin in development mode |
| `--production-mode` | Flag | False | Create plugin in production mode |
| `--with-subplugins` | Flag | False | Create plugin with subplugin support |
| `--output-dir PATH` | Path | - | Custom output directory |
| `--template [minimal\|standard\|advanced]` | Choice | `standard` | Plugin template complexity |
| `--force` | Flag | False | Force creation even if plugin exists |

##### 5.2 create subplugin
```bash
panther create subplugin [OPTIONS] PLUGIN_TYPE PLUGIN_NAME SUBPLUGIN_NAME
```

**Required Arguments:**
- `PLUGIN_TYPE` - Type of parent plugin
- `PLUGIN_NAME` - Name of existing parent plugin
- `SUBPLUGIN_NAME` - Name of subplugin to create

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dev-mode` | Flag | False | Create subplugin in development mode |
| `--production-mode` | Flag | False | Create subplugin in production mode |
| `--template [minimal\|standard\|advanced]` | Choice | `standard` | Subplugin template complexity |
| `--force` | Flag | False | Force creation even if subplugin exists |

##### 5.3 create template
```bash
panther create template [OPTIONS] TEMPLATE_TYPE
```

**Required Arguments:**
- `TEMPLATE_TYPE` - Type of template: `experiment`, `service`, `environment`

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output PATH` | Path | - | Output file path |
| `--format [yaml\|json]` | Choice | `yaml` | Output format |
| `--minimal` | Flag | False | Generate minimal template |
| `--interactive` | Flag | False | Interactive template creation |

### 6. tutorial - Interactive Learning Platform

#### Command Usage
```bash
panther tutorial [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

##### 6.1 tutorial run
```bash
panther tutorial run [OPTIONS] TUTORIAL_TYPE
```

**Required Arguments:**
- `TUTORIAL_TYPE` - Type of tutorial: `service`, `environment`, `protocol`, `configuration`

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--mode [guided\|quick\|reference]` | Choice | `guided` | Learning mode |
| `--level [beginner\|intermediate\|advanced]` | Choice | `beginner` | Skill level |
| `--output-dir PATH` | Path | - | Directory to create tutorial artifacts |
| `--interactive/--no-interactive` | Flag | True | Enable interactive prompts |

##### 6.2 tutorial list
```bash
panther tutorial list [OPTIONS]
```

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format [table\|json\|detail]` | Choice | `detail` | Output format |
| `--level [beginner\|intermediate\|advanced\|all]` | Choice | `all` | Filter by skill level |
| `--category [service\|environment\|protocol\|configuration\|all]` | Choice | `all` | Filter by category |

##### 6.3 tutorial interactive
```bash
panther tutorial interactive [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--quick-start/--full-menu` | Skip introductions and jump to tutorial selection |

### 7. admin - Administrative Commands

#### Command Usage
```bash
panther admin [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

##### 7.1 admin status
```bash
panther admin status [OPTIONS]
```

**No additional arguments required**

##### 7.2 admin teardown
```bash
panther admin teardown [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--force` | Force cleanup without confirmation |

##### 7.3 admin clean
```bash
panther admin clean [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--logs` | Clean log files |
| `--cache` | Clean cache files |
| `--all` | Clean all temporary files |

##### 7.4 admin docker
```bash
panther admin docker [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--images-all` | Remove all Docker images with 'panther' in name |
| `--images-services` | Remove Docker images with '_panther' in name |
| `--system-all` | Remove images and prune system data with 'panther' label |
| `--system-services` | Remove images and prune system data with '_panther' label |
| `--volumes` | Remove Docker volumes with 'panther' in name |
| `--containers` | Remove stopped containers with 'panther' label |
| `--show-registry` | Show Docker registry statistics |
| `--prune-cache` | Prune old Docker build cache entries |
| `--export-registry PATH` | Export Docker registry to file |
| `--import-registry PATH` | Import Docker registry from file |
| `--cache-max-age INTEGER` | Maximum age in days for cache entries (default: 7) |

### 8. check - Code Quality Checks

#### Command Usage
```bash
panther check [OPTIONS]
```

#### Optional Arguments

| Option | Description |
|--------|-------------|
| `--fix` | Automatically fix issues where possible |
| `--all` | Run all available checks |
| `--format` | Check code formatting with black |
| `--imports` | Check import sorting with isort |
| `--lint` | Run linting with flake8 |
| `--type` | Run type checking with mypy |
| `--security` | Run security checks with bandit |
| `--test` | Run tests with pytest |
| `--coverage` | Include coverage report with tests |
| `--path PATH` | Path to check (default: panther/) |
| `--config PATH` | Path to configuration file for checks |

### 9. metrics - Metrics Management

#### Command Usage
```bash
panther metrics [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

##### 9.1 metrics list
```bash
panther metrics list [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--filter TEXT` | Filter metrics by name pattern (regex supported) |

##### 9.2 metrics show
```bash
panther metrics show [OPTIONS]
```

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--metric TEXT` | String | - | Specific metric name to show |
| `--limit INTEGER` | Integer | 10 | Limit number of values shown per metric |

##### 9.3 metrics export
```bash
panther metrics export [OPTIONS]
```

**Optional Arguments:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output PATH` | Path | - | Output file path (auto-generated if not specified) |
| `--format [json\|csv\|txt]` | Choice | `json` | Export format |

##### 9.4 metrics clear
```bash
panther metrics clear [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--force` | Clear without confirmation prompt |

##### 9.5 metrics summary
```bash
panther metrics summary [OPTIONS]
```

**No additional arguments required**

### 10. tools - Development Tools

#### Command Usage
```bash
panther tools [OPTIONS] COMMAND [ARGS]...
```

#### Global Options
| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose output |

#### Subcommands

##### 10.1 tools install-slim
```bash
panther tools install-slim [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--force` | Force reinstallation even if already present |

##### 10.2 tools install-precommit
```bash
panther tools install-precommit [OPTIONS]
```

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--update` | Update hooks to latest versions |

##### 10.3 tools status
```bash
panther tools status [OPTIONS]
```

**No additional arguments required**

##### 10.4 tools list
```bash
panther tools list [OPTIONS]
```

**No additional arguments required**

##### 10.5 tools uninstall
```bash
panther tools uninstall [OPTIONS] TOOL_NAME
```

**Required Arguments:**
- `TOOL_NAME` - Tool to uninstall: `slim`, `pre-commit`

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `--confirm` | Skip confirmation prompt |

### 11. completion - Shell Completion

#### Command Usage
```bash
panther completion [OPTIONS] [SHELL]
```

#### Optional Arguments
- `SHELL` - Shell type: `bash`, `zsh`, `fish` (auto-detected if not specified)

**Optional Arguments:**
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output format for shell completion |

## Sample Execution Traces

### Version Information
```bash
$ python -m panther --version
panther, version 1.1.3
```

### Basic Help
```bash
$ python -m panther --help
Usage: python -m panther [OPTIONS] COMMAND [ARGS]...

  PANTHER - Protocol Analysis and Testing for Heterogeneous Execution and
  Research

  Modern CLI for network protocol testing, formal verification, and automated
  analysis of protocol implementations across multiple environments.
```

### Command Structure Discovery
```bash
$ python -m panther
# Shows main help with all available commands

$ python -m panther run --help
# Shows detailed help for run command with all options

$ python -m panther config validate --help
# Shows help for config validate subcommand
```

### Error Handling
- Commands require appropriate arguments (e.g., `run` requires `--config`)
- Invalid options show helpful error messages
- Missing tools show installation suggestions
- File path validation with clear error messages

## Integration Notes

### Plugin System
- Supports multiple plugin types: `iut`, `testers`, `network_environment`, `execution_environment`
- Plugin discovery and validation capabilities
- Extensible architecture for custom implementations

### Docker Integration
- Comprehensive Docker resource management
- Container lifecycle management
- Image optimization with slim tool
- Network and volume management

### Metrics Collection
- Real-time metrics collection during experiments
- Multiple export formats (JSON, CSV, TXT)
- Resource usage monitoring
- Performance analytics

### Configuration Management
- YAML-based configuration system
- Schema validation and documentation
- Template generation for common scenarios
- Interactive configuration designer

## Development Tools

### Code Quality
- Comprehensive linting with flake8
- Code formatting with black
- Import sorting with isort
- Type checking with mypy
- Security scanning with bandit

### Testing
- pytest integration
- Coverage reporting
- Test automation

### Documentation
- Interactive tutorial system
- Command-line help system
- Schema documentation

## Conclusion

The PANTHER CLI provides a comprehensive, well-structured interface for protocol testing and analysis. The Click-based architecture ensures consistent command patterns, extensive help documentation, and robust error handling. The modular design allows for easy extension and maintenance while providing powerful functionality for network protocol research and development.

All commands follow Unix conventions for exit codes:
- 0: Success
- 1: General error
- 2: Command line usage error
- 130: Interrupted by user (Ctrl+C)

The CLI is designed for both interactive use and automation, with appropriate verbosity levels, dry-run modes, and machine-readable output formats where applicable.
