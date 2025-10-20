# PANTHER Installation Guide

## Overview

This document provides instructions for installing and setting up the PANTHER system on your environment with the new enhanced Click-based CLI featuring improved user experience and comprehensive command structure.

## Prerequisites

!!! warning "System requirements"
    Running PANTHER requires root-level Docker access and can consume significant system resources
    during protocol testing. Ensure adequate disk space (>=20GB) for container images.

- Operating System: Linux, macOS
- Docker v27 or higher
- Python 3.10 or higher
- pip (Python package manager)
- Git (for cloning the repository)

!!! note "Dependencies"
    `pyproject.toml` is the source of truth for Python dependencies.
    `requirements.txt` is a frozen snapshot—**do not edit**.

## Installation Steps

### Option A — From PyPI *(easiest)*

!!! tip "Recommended for most users"
    This is the simplest installation method and includes all core functionality and built-in plugins.

```bash
python -m venv .venv              # optional but recommended
source .venv/bin/activate
pip install "panther-net"
```

`panther-net` is the official PyPI package that bundles the core engine, all built-in plugins, and the enhanced Click-based CLI.
Upgrade later with `pip install -U "panther-net"`.

#### CLI Verification and Setup

After installation, verify the CLI is working and set up enhanced features:

```bash
# Verify installation
panther --version

# Check system readiness
panther tools doctor

# Enable bash completion for enhanced productivity
panther completion bash > ~/.panther-complete.bash
echo 'source ~/.panther-complete.bash' >> ~/.bashrc
source ~/.bashrc

# Get help and explore commands
panther --help
panther run --help
panther config --help
```

### Option B — From Source *(for dev)*

#### Clone the Repository

```bash
git clone --recurse-submodules https://github.com/ElNiak/PANTHER.git;
# If submodule not cloned initially ;)
git submodule update --init --recursive;
cd PANTHER
python -m venv .venv && source .venv/bin/activate;
```

#### 🔧 **Recommended: Using the Builder Script** *(cross-platform)*

For development work, we **highly recommend** using the included Python builder script instead of the traditional Makefile:

```bash
git clone --recurse-submodules https://github.com/ElNiak/PANTHER.git
# If submodule not cloned initially ;)
git submodule update --init --recursive;
cd PANTHER
python -m venv .venv && source .venv/bin/activate
# After cloning and setting up your environment:
python panther_builder.py package-dev    # Install in development mode
python panther_builder.py docs           # Build documentation
python panther_builder.py check          # Run code quality checks
python panther_builder.py clean          # Clean build artifacts
```

More details with:

```bash
# (.venv)
python panther_builder.py --help         # See all available commands
usage: panther_builder.py [-h] [-v]
                          [{package,package-dev,package-test,clean,install-local,docs,serve-docs,deploy-docs,check,zip-outputs,remove-images-all,remove-images-services,remove-system-all,remove-system-services,remove-volume,help}]

PANTHER Build Script - A portable Python-based build system

positional arguments:
  {package,package-dev,package-test,clean,install-local,docs,serve-docs,deploy-docs,check,zip-outputs,remove-images-all,remove-images-services,remove-system-all,remove-system-services,remove-volume,help}
                        Command to execute

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose output

Examples:
    python panther_builder.py package           # Build and install package
    python panther_builder.py package-dev       # Install in development mode
    python panther_builder.py clean             # Clean build artifacts
    python panther_builder.py docs              # Build documentation
    python panther_builder.py serve-docs        # Serve documentation locally
    python panther_builder.py deploy-docs       # Deploy documentation to GitHub Pages
    python panther_builder.py check             # Run code quality checks
    python panther_builder.py zip-outputs       # Archive outputs directory
    python panther_builder.py remove-images-all # Remove all Docker images with 'panther'
```

**Why use the builder?**

- ✅ **Cross-platform**: Works on Linux, macOS
- ✅ **Smart checks**: Automatically validates Python ≥3.10 and Docker ≥27.0
- ✅ **Integrated**: Replaces previous Makefile with better error handling
- ✅ **Developer-friendly**: Includes quality checks, documentation builds, and cleanup
- ✅ **Docker management**: Built-in Docker image and volume cleanup commands

#### Manually

```bash
# (.venv)
# For regular installation
pip install --no-cache --upgrade pip setuptools wheel packaging build
pip install .

# For development installation (editable mode)
pip install --no-cache --upgrade pip setuptools wheel packaging build
pip install --no-cache -e .

# For installation with specific extras
pip install --no-cache -e ".[tests]"  # Install with testing dependencies
pip install --no-cache -e ".[lint]"   # Install with linting dependencies
pip install --no-cache -e ".[doc]"    # Install with documentation dependencies (Python 3.8)

# Install with multiple extras (For Mac you might want --prefer-binary)
pip install --no-cache -e ".[tests,lint,doc]"
```

Both methods read dependencies from **`pyproject.toml`**—**do not
manually edit `requirements.txt`**, it’s just a frozen lock.

!!! note "Entry point argument auto-completion"
    We have add the package `argcomplete`in the project
    You can also activate this package globally with
    `activate-global-python-argcomplete --user`

### Verify Installation

After installation, you can verify that PANTHER was installed correctly:

```bash
# (.venv)
# Check the installed version
python -c "import panther; print(panther.__version__)"

# Run the CLI help command
panther --help
```

## CLI Quick Start

### Enhanced Click-based CLI

PANTHER now features a modern, user-friendly CLI built with Click that provides:

- **Colored output** with emojis for visual feedback
- **Progress bars** for long-running operations
- **Enhanced error messages** with contextual suggestions
- **Bash completion** for improved productivity
- **Interactive tutorials** for learning
- **Comprehensive help** with examples

### Your First Experiment

Get started quickly with the new CLI:

```bash
# 1. Generate your first experiment configuration
panther create template experiment --output my-first-experiment.yaml

# 2. Validate the configuration
panther config validate --config my-first-experiment.yaml --explain

# 3. Run a dry-run to see what would happen
panther run --config my-first-experiment.yaml --dry-run

# 4. Execute the actual experiment
panther run --config my-first-experiment.yaml --enable-metrics
```

### Interactive Learning

Explore PANTHER through interactive tutorials:

```bash
# Start interactive tutorial system
panther tutorial interactive

# Or run specific tutorials
panther tutorial run service --mode guided
panther tutorial run configuration --mode quick
```

### Plugin Management

Discover and manage plugins easily:

```bash
# List available plugins
panther plugins list

# Get information about a specific plugin
panther plugins info picoquic --verbose

# Check plugin parameters
panther plugins params picoquic --type iut
```

For comprehensive CLI documentation, see [CLI Documentation](docs/cli_click.md).

## Troubleshooting

### Common Issues

- **Missing dependencies**: Make sure all prerequisites are installed
- **Permission errors**: Try using sudo for installation commands if appropriate
- **Version conflicts**: Ensure you're using compatible versions of dependencies

## Getting Help

- Documentation: [https://elniak.github.io/PANTHER](https://elniak.github.io/PANTHER)
- Issues: [GitHub Issues](https://github.com/ElNiak/PANTHER/issues)

## License

PANTHER is licensed under MIT. See the LICENSE file for more details.
