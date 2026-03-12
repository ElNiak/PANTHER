#!/usr/bin/env python3
"""PANTHER CLI - Main entry point.

This module provides the command-line interface for the PANTHER framework.
"""

import sys

# Import the main CLI function
from panther.cli.core.main import main

if __name__ == "__main__":
    sys.exit(main() or 0)
