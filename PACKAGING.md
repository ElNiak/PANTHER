# PANTHER Packaging Guide

## Overview

This document provides instructions for building, packaging, and publishing the PANTHER system to PyPI and other distribution channels. PANTHER uses modern Python packaging practices based on PEP-517 and PEP-518, with setuptools as the build backend.

!!! warning "For Maintainers Only"
    This guide is intended for PANTHER maintainers and contributors who need to package and publish releases. Regular users should follow the [Installation Guide](INSTALL.md) instead.

## Package Structure

PANTHER follows the [PyOpenSci package structure guidelines](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-structure.html).

The key files related to packaging are:

- `pyproject.toml`: Primary configuration file that defines build system requirements, project metadata, dependencies, and entry points
- `MANIFEST.in`: Defines additional files to include in the source distribution
- `panther/__init__.py`: Defines the package version and public API
- `requirements.txt`: A frozen snapshot of dependencies (generated automatically)

## Versioning

PANTHER uses a single-source versioning approach:

1. The canonical version is defined in `pyproject.toml` under `[project]` section
2. The version is also available at runtime via `panther.__version__`
3. When installed, the package uses `importlib.metadata` to get the actual installed version

## Plugin System

PANTHER plugins can be discovered through two mechanisms:

1. **Entry points (recommended)**: Register plugins via entry points in your package's `pyproject.toml`:

   ```toml
   [project.entry-points]
   "panther.plugins.protocols" = [
       "my_protocol = my_package.protocol:MyProtocolClass"
   ]
   ```

2. **File-based discovery (legacy)**: Place plugin files in the appropriate directories under `panther/plugins/`

## Building the Package

!!! tip "Recommended Build Method"
    Use the included builder script for consistent, cross-platform builds:

To build the package distribution files:

```bash
# Build both wheel and source distribution
python panther_build.py package

# Alternative manual method
pip install build wheel
python -m build
```

The build process will create distribution files in the `dist/` directory.

## Testing the Package

Before publishing, it's recommended to test the package in a clean environment:

```bash
# Create a test environment
python -m venv test_env
source test_env/bin/activate

# Install the wheel
pip install "dist/panther_net-*.whl"

# Run basic verification
python -m panther --version
```

## Publishing to PyPI

Once the package has been tested and is ready for release:

```bash
# Publish to PyPI
twine upload dist/*
```

## Version Management

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Tag the release in git:

```bash
git tag -a v1.2.3 -m "Version 1.2.3"
git push origin v1.2.3
```

## CI/CD Publishing

PANTHER uses GitHub Actions for automated publishing. The workflow is triggered when a new tag is pushed or when manually triggered from the GitHub Actions interface.
