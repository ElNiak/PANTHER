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

### 1. Clone the Repository
```bash
git clone https://github.com/ElNiak/PANTHER.git
cd PANTHER
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

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

### 4. Verify Installation

After installation, you can verify that PANTHER was installed correctly:

```bash
# Check the installed version
python -c "import panther; print(panther.__version__)"

# Run the CLI help command
panther --help
```

## Configuration
1. Copy the example configuration file:
    ```bash
    cp experiment-config/experiment_config_example experiment-config/config.yml
    ```

2. Edit the configuration file with your preferred settings:

    ```bash
    nano experiment-config/config.yml
    ```

## Verification

To verify that PANTHER was installed correctly:

```bash
python -m panther --version
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