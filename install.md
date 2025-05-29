# PANTHER Installation Guide

## Overview
This document provides instructions for installing and setting up the PANTHER system on your environment.

## Prerequisites

- Operating System: Linux, macOS
- Python 3.10 or higher
- pip (Python package manager)
- Git (for cloning the repository)

`pyproject.toml` is the source of truth for Python dependencies.
`requirements.txt` is a frozen snapshot—**do not edit**.

## Installation Steps

### Option A — From PyPI *(easiest)*

```bash
python -m venv .venv              # optional but recommended
source .venv/bin/activate
pip install panther_net
```

`panther_net` is the official PyPI package that bundles the core engine, all built-in plugins, and CLI entry-points.
Upgrade later with `pip install -U panther_net`.

### Option B — From Source *(for dev)*

#### Clone the Repository
```bash
git clone https://github.com/ElNiak/PANTHER.git;
cd PANTHER;
python -m venv .venv && source .venv/bin/activate;
```

#### 🔧 **Recommended: Using the Builder Script** *(cross-platform)*

For development work, we **highly recommend** using the included Python builder script instead of the traditional Makefile:


```bash
git clone https://github.com/ElNiak/PANTHER.git
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
- ✅ **Cross-platform**: Works on Linux, macOS, and Windows
- ✅ **Smart checks**: Automatically validates Python ≥3.10 and Docker ≥27.0
- ✅ **Integrated**: Replaces Makefile with better error handling
- ✅ **Developer-friendly**: Includes quality checks, documentation builds, and cleanup
- ✅ **Docker management**: Built-in Docker image and volume cleanup commands

#### Manually

```bash
# For regular installation
pip install --upgrade pip
pip install .

# For development installation (editable mode)
pip install -e .

# For installation with specific extras
pip install -e ".[tests]"  # Install with testing dependencies
pip install -e ".[lint]"   # Install with linting dependencies
pip install -e ".[doc]"    # Install with documentation dependencies (Python 3.8)

# Install with multiple extras
pip install -e ".[tests,lint,doc]"
```

Both methods read dependencies from **`pyproject.toml`**—**do not
manually edit `requirements.txt`**, it’s just a frozen lock.

### Verify Installation

After installation, you can verify that PANTHER was installed correctly:

```bash
# Check the installed version
python -c "import panther; print(panther.__version__)"

# Run the CLI help command
panther --help
```

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