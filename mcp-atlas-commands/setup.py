#!/usr/bin/env python
"""Setup script for ATLAS Commands MCP Server."""

from setuptools import setup, find_packages

setup(
    name="atlas-commands",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
)