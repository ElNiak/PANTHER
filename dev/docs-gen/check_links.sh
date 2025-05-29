#!/bin/bash

# Script to run the verify_links.py with appropriate flags to ignore README.md references
# and handle links correctly for the current project structure

# Path to the script
SCRIPT_PATH="$(dirname "$0")/verify_links.py"

# Run the script with appropriate flags
# --ignore-readme-refs: Ignore specific links in README.md (DOIs, PDFs, academic references)
# Add other flags as passed to this script
python "$SCRIPT_PATH" --ignore-readme-refs "$@"

# Output message
echo ""
echo "Note: Academic references in README.md (DOIs, PDF files) are automatically ignored."
echo "      Use --check-external to validate external links."
echo "      Use --autofix to automatically fix common link issues."
echo ""
echo "For more information, see: docs-gen/documentation_links.md"
