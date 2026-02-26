# Task 01: Scaffold panther-ivy-types Package

## Goal
Create the `packages/panther-ivy-types/` directory with pyproject.toml and empty module structure.

## Prerequisites
- None (first task)

## Context
`panther-ivy-types` is a zero-dependency package containing only pure Python dataclasses shared across the Ivy formal verification toolchain (panther_ivy, ivy-lsp, panther-serena).

## Steps

### Step 1: Create directory structure
```bash
mkdir -p packages/panther-ivy-types/panther_ivy_types
mkdir -p packages/panther-ivy-types/tests
```

### Step 2: Create pyproject.toml
```toml
# packages/panther-ivy-types/pyproject.toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "panther-ivy-types"
version = "0.1.0"
description = "Shared data structures for the PANTHER Ivy formal verification toolchain"
license = "MIT"
requires-python = ">=3.10"
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
include = ["panther_ivy_types*"]
```

### Step 3: Create __init__.py with public API
```python
# packages/panther-ivy-types/panther_ivy_types/__init__.py
"""Shared data structures for the PANTHER Ivy formal verification toolchain.

This package contains pure Python dataclasses used across:
- panther_ivy: PANTHER framework Ivy tester plugin
- ivy-lsp: Ivy Language Server Protocol implementation
- panther-serena: Serena code intelligence integration
"""

from panther_ivy_types.api import (
    CommandResult,
    CompileResult,
    DiagnosticItem,
    ExecutionResult,
    TestInfo,
    TestRunResult,
)
from panther_ivy_types.analysis import ActionNode, PropertyNode, RequirementNode, StateVarNode
from panther_ivy_types.scope import ExportImportInfo, TestScope

__all__ = [
    "CommandResult",
    "CompileResult",
    "DiagnosticItem",
    "ExecutionResult",
    "TestInfo",
    "TestRunResult",
    "ActionNode",
    "PropertyNode",
    "RequirementNode",
    "StateVarNode",
    "ExportImportInfo",
    "TestScope",
]
```

### Step 4: Create empty module files
```python
# packages/panther-ivy-types/panther_ivy_types/api.py
"""API data types for the panther_ivy plugin."""

# packages/panther-ivy-types/panther_ivy_types/analysis.py
"""Analysis data types for Ivy requirement graphs."""

# packages/panther-ivy-types/panther_ivy_types/scope.py
"""Scope data types for Ivy test scope analysis."""
```

### Step 5: Create empty test file
```python
# packages/panther-ivy-types/tests/__init__.py
# (empty)

# packages/panther-ivy-types/tests/test_types.py
"""Tests for panther-ivy-types package."""
```

## Verification
```bash
# Directory structure should look like:
ls -la packages/panther-ivy-types/
# pyproject.toml
# panther_ivy_types/
# tests/

ls -la packages/panther-ivy-types/panther_ivy_types/
# __init__.py
# api.py
# analysis.py
# scope.py
```

## Commit Message
```
feat: scaffold panther-ivy-types package structure

Create packages/panther-ivy-types/ with pyproject.toml (zero external
deps, Python >=3.10) and empty module files for api, analysis, and
scope types.
```

## Files Created
- `packages/panther-ivy-types/pyproject.toml`
- `packages/panther-ivy-types/panther_ivy_types/__init__.py`
- `packages/panther-ivy-types/panther_ivy_types/api.py`
- `packages/panther-ivy-types/panther_ivy_types/analysis.py`
- `packages/panther-ivy-types/panther_ivy_types/scope.py`
- `packages/panther-ivy-types/tests/__init__.py`
- `packages/panther-ivy-types/tests/test_types.py`
