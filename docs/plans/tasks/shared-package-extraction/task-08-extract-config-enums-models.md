# Task 08: Extract Config Enums and Simple Models to panther-types

## Goal
Extract `ImplementationType`, `ProtocolRole`, `VersionBase`, and `Parameter` from `service.py` into `panther_types/config/service.py`.

## Prerequisites
- Task 07 completed (BaseConfig + BaseUnifiedModel in panther-types)

## Source File
`panther/config/core/models/service.py` (550 lines)

Extract only (lines 16-43):
- `Parameter` (lines 16-20) - simple Pydantic BaseModel
- `VersionBase` (lines 23-28) - simple Pydantic BaseModel
- `ImplementationType` (lines 31-35) - str Enum
- `ProtocolRole` (lines 38-43) - str Enum

Leave in panther:
- `NetworkConfig` (depends on BaseUnifiedModel field validators)
- `ProtocolConfig` (depends on validators module)
- `ImplementationConfig` (depends on validators)
- `ServiceConfig` (550 lines, deeply coupled to panther internals)

## Context
These 4 types are the most imported cross-project. `panther_ivy/config_schema.py` imports `ImplementationType` and `VersionBase`. `ProtocolRole` is used throughout panther for role-based logic.

## Steps

### Step 1: Create panther_types/config/service.py

```python
# packages/panther-types/panther_types/config/service.py
"""Service configuration enums and simple models.

These types define the fundamental building blocks for service configuration
in the PANTHER framework: implementation types, protocol roles, version info,
and configuration parameters.
"""
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class Parameter(BaseModel):
    """A configuration parameter with value and description."""

    value: Any = None
    description: str = ""


class VersionBase(BaseModel):
    """Base version information for an implementation."""

    version: str = ""
    commit: str = ""
    dependencies: dict = {}


class ImplementationType(str, Enum):
    """Type of service implementation."""

    IUT = "iut"
    TESTERS = "testers"


class ProtocolRole(str, Enum):
    """Role a service plays in the protocol interaction."""

    SERVER = "server"
    CLIENT = "client"
    PEER = "peer"
```

**Critical**: Read the actual source file to verify exact field definitions and enum values. The above is based on exploration but the source is authoritative.

### Step 2: Update __init__.py

```python
# packages/panther-types/panther_types/config/__init__.py
"""Configuration base classes and models."""
from panther_types.config.base import BaseConfig, BaseUnifiedModel
from panther_types.config.service import (
    ImplementationType,
    Parameter,
    ProtocolRole,
    VersionBase,
)

__all__ = [
    "BaseConfig",
    "BaseUnifiedModel",
    "ImplementationType",
    "Parameter",
    "ProtocolRole",
    "VersionBase",
]
```

### Step 3: Write tests

```python
# packages/panther-types/tests/test_config_service.py
"""Tests for service config types."""
from panther_types.config.service import (
    ImplementationType,
    Parameter,
    ProtocolRole,
    VersionBase,
)


class TestImplementationType:
    def test_values(self):
        assert ImplementationType.IUT == "iut"
        assert ImplementationType.TESTERS == "testers"

    def test_from_string(self):
        assert ImplementationType("iut") == ImplementationType.IUT
        assert ImplementationType("testers") == ImplementationType.TESTERS

    def test_is_str(self):
        """ImplementationType is a str enum, so it should be usable as a string."""
        t = ImplementationType.IUT
        assert isinstance(t, str)
        assert t.upper() == "IUT"


class TestProtocolRole:
    def test_values(self):
        assert ProtocolRole.SERVER == "server"
        assert ProtocolRole.CLIENT == "client"
        assert ProtocolRole.PEER == "peer"

    def test_from_string(self):
        assert ProtocolRole("server") == ProtocolRole.SERVER


class TestVersionBase:
    def test_defaults(self):
        v = VersionBase()
        assert v.version == ""
        assert v.commit == ""
        assert v.dependencies == {}

    def test_create(self):
        v = VersionBase(version="1.0", commit="abc123", dependencies={"z3": "4.8"})
        assert v.version == "1.0"
        assert v.dependencies["z3"] == "4.8"


class TestParameter:
    def test_defaults(self):
        p = Parameter()
        assert p.value is None
        assert p.description == ""

    def test_create(self):
        p = Parameter(value=42, description="timeout in seconds")
        assert p.value == 42
```

## Verification
```bash
cd packages/panther-types
pytest tests/test_config_service.py -v
```

## Commit Message
```
feat(panther-types): extract service config enums and simple models

Move ImplementationType, ProtocolRole, VersionBase, and Parameter
from panther/config/core/models/service.py into panther-types.
These are the most commonly imported types across the PANTHER ecosystem.
```

## Files Modified
- `packages/panther-types/panther_types/config/service.py` (new)
- `packages/panther-types/panther_types/config/__init__.py` (updated)
- `packages/panther-types/tests/test_config_service.py` (new)
