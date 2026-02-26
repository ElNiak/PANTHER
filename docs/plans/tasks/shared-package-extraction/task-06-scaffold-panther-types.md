# Task 06: Scaffold panther-types Package

## Goal
Create the `packages/panther-types/` directory with pyproject.toml and module structure.

## Prerequisites
- Phase 1 complete (task 05 verified)

## Context
`panther-types` contains shared configuration models, event types, plugin interfaces, and exception hierarchy for the PANTHER framework. Unlike panther-ivy-types, this package has external dependencies (pydantic, omegaconf).

## Steps

### Step 1: Create directory structure
```bash
mkdir -p packages/panther-types/panther_types/config
mkdir -p packages/panther-types/panther_types/events
mkdir -p packages/panther-types/panther_types/exceptions
mkdir -p packages/panther-types/panther_types/plugin
mkdir -p packages/panther-types/panther_types/interfaces
mkdir -p packages/panther-types/tests
# Note: observer/ directory omitted - no tasks populate it.
# Add it later if needed for observer Protocol interfaces.
```

### Step 2: Create pyproject.toml

```toml
# packages/panther-types/pyproject.toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "panther-types"
version = "0.1.0"
description = "Shared configuration models, event types, and interfaces for the PANTHER framework"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "omegaconf>=2.3",
    "PyYAML>=6.0",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "mypy>=1.0"]

[tool.setuptools.packages.find]
include = ["panther_types*"]
```

### Step 3: Create __init__.py files

```python
# packages/panther-types/panther_types/__init__.py
"""Shared types and interfaces for the PANTHER framework.

Provides configuration models, event types, exception hierarchy,
and plugin interfaces used across PANTHER ecosystem projects.
"""

# packages/panther-types/panther_types/config/__init__.py
"""Configuration base classes and models."""

# packages/panther-types/panther_types/events/__init__.py
"""Event system base types."""

# packages/panther-types/panther_types/exceptions/__init__.py
"""Exception hierarchy."""

# packages/panther-types/panther_types/plugin/__init__.py
"""Plugin type definitions."""

# packages/panther-types/panther_types/interfaces/__init__.py
"""Protocol and ABC interfaces for cross-project contracts."""

# packages/panther-types/tests/__init__.py
# (empty)

# Note: panther_types/observer/ is NOT scaffolded.
# No task populates it. Add later if observer Protocol interfaces are needed.
```

## Verification
```bash
ls -R packages/panther-types/
# Should show full directory tree with all __init__.py files

pip install -e packages/panther-types/
python -c "import panther_types; print('OK')"
```

## Commit Message
```
feat: scaffold panther-types package structure

Create packages/panther-types/ with pyproject.toml (deps: pydantic>=2,
omegaconf>=2.3, PyYAML>=6.0) and module structure for config, events,
exceptions, plugin, and interfaces.
```

## Files Created
- `packages/panther-types/pyproject.toml`
- `packages/panther-types/panther_types/__init__.py`
- `packages/panther-types/panther_types/config/__init__.py`
- `packages/panther-types/panther_types/events/__init__.py`
- `packages/panther-types/panther_types/exceptions/__init__.py`
- `packages/panther-types/panther_types/plugin/__init__.py`
- `packages/panther-types/panther_types/interfaces/__init__.py`
- `packages/panther-types/tests/__init__.py`

Note: `panther_types/observer/` intentionally omitted - no task populates it.
