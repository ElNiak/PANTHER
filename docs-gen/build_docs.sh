#!/usr/bin/env bash

# This script organizes the documentation structure and builds the documentation

set -e

# Step 1: Organize the documentation structure
echo "Organizing documentation structure..."
python docs-gen/mkdocs/docs_structure.py

# Step 2: Use mkgendocs to copy files from sources to docs
echo "Using mkgendocs to process documentation..."
gendocs --config mkgendocs.yml

# Step 3: Build the documentation
echo "Building documentation..."
mkdocs build --verbose --config-file mkdocs.yml

# Step 4: Serve the documentation (optional)
if [[ "$1" == "--serve" ]]; then
  echo "Starting documentation server..."
  mkdocs serve --verbose --config-file mkdocs.yml
fi

echo "Documentation built successfully!"
