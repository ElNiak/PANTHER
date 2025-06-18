# CLI Command Migration Summary

## Changes Made

### 1. Created New CLI Subcommands

#### `panther/cli/subcommands/tools.py`
- **install-slim**: Install Docker image optimization tool (slim)
- **install-precommit**: Install and configure pre-commit hooks
- **list**: List installed development tools and their versions

#### `panther/cli/subcommands/metrics.py`
- **list**: List available metrics with filtering
- **show**: Display detailed metrics data
- **export**: Export metrics to JSON/CSV/text formats
- **clear**: Clear stored metrics data
- **summary**: Show metrics summary and insights

#### `panther/cli/subcommands/check.py`
- **Comprehensive code quality checks** with options:
  - `--format`: Black code formatting
  - `--imports`: isort import sorting
  - `--lint`: flake8 linting
  - `--type`: mypy type checking
  - `--security`: bandit security checks
  - `--test`: pytest test execution
  - `--fix`: Auto-fix issues where possible
  - `--all`: Run all checks

### 2. Enhanced Admin Command

Extended `panther/cli/subcommands/admin.py` with Docker management:
- `panther admin docker` subcommand with options:
  - `--images-all`: Remove all PANTHER Docker images
  - `--images-services`: Remove service-specific images
  - `--system-all`: Prune system with panther label
  - `--system-services`: Prune system with _panther label
  - `--volumes`: Remove Docker volumes
  - `--containers`: Remove Docker containers

### 3. Updated Core CLI Files

- **`panther/cli/subcommands/__init__.py`**: Added new command imports
- **`panther/cli/main.py`**: 
  - Registered new commands
  - Updated help text with examples
  - Added command handlers

### 4. Modified panther_builder.py

- Removed moved commands (replaced with placeholder comments)
- Added helpful migration messages for moved commands
- Updated help text to indicate which commands were moved
- Maintained backward compatibility with informative messages

## Benefits

1. **Separation of Concerns**
   - Builder focuses on package building and installation
   - CLI handles runtime tools and operations

2. **Better User Experience**
   - All commands accessible via unified `panther` CLI
   - Consistent command structure and help system
   - Better discoverability with `panther --help`

3. **Improved Organization**
   - Logical grouping of related commands
   - Extensible architecture for future commands
   - Clean separation between build and runtime operations

4. **No Duplicate Commands**
   - Each command exists in only one place
   - Clear migration path with helpful messages
   - Maintained backward compatibility notifications

## Usage Examples

```bash
# Code quality
panther check --all --fix
panther check --format --imports --path src/

# Metrics
panther metrics list --filter "build.*"
panther metrics show --metric build.total_seconds
panther metrics export --format csv --output metrics.csv

# Tools
panther tools install-slim
panther tools install-precommit --update
panther tools list

# Docker cleanup
panther admin docker --images-all --volumes
panther admin docker --system-services
```

## Migration Path

Users attempting old commands receive helpful guidance:

```bash
$ python panther_builder.py check
ℹ️  The 'check' command has been moved to the PANTHER CLI.
   Please use: panther check --all
```