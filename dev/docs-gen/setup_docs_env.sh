#!/usr/bin/env bash
# setup_docs_env.sh - Script to set up and use Python 3.8 for documentation generation

set -e

# Check if Python 3.8 is available
if ! command -v python3.8 &> /dev/null; then
    echo "Error: Python 3.8 is not installed or not in your PATH."
    echo "Please install Python 3.8 before continuing."
    exit 1
fi

# Create a virtual environment specifically for documentation if it doesn't exist
VENV_NAME="docs_venv_py38"
if [ ! -d "$VENV_NAME" ]; then
    echo "Creating Python 3.8 virtual environment for documentation..."
    python3.8 -m venv "$VENV_NAME"
fi

# Activate the virtual environment
echo "Activating documentation virtual environment..."
source "$VENV_NAME/bin/activate"

# Verify Python version
PYTHON_VERSION=$(python --version)
echo "Using $PYTHON_VERSION"

# Install the package with documentation dependencies
echo "Installing PANTHER with documentation dependencies..."
pip install -e ".[doc]"

# Optional: Install additional tools if needed
# pip install pre-commit

echo ""
echo "Documentation environment setup complete!"
echo ""
echo "You can now run documentation commands, for example:"
echo "  mkdocs serve"
echo ""
echo "When you're done, deactivate the virtual environment with:"
echo "  deactivate"
echo ""
echo "To use this environment again later, run:"
echo "  source $VENV_NAME/bin/activate"
