# Task 12: Extract Plugin Structures to panther-types

## Goal
Extract `PluginType` enum and `PluginMetadata` dataclass to panther-types. NOT PluginManifest (too many deps).

## Prerequisites
- Task 06 completed (package scaffolded)

## Source Files
- `panther/plugins/core/structures/plugin_type.py` (14 lines) - self-contained, only enum import
- `panther/plugins/core/structures/plugin_metadata.py` (258 lines) - depends on PluginType only

## What NOT to Extract
- `PluginManifest` (171 lines) - depends on `PluginDependency`, `packaging.version`, and `DockerRequirements` (TYPE_CHECKING). Too many transitive deps.
- `PluginDependency` - would need to come along with PluginManifest
- `PluginMetadataLoader` class (lines 141-257 in plugin_metadata.py) - has logic for loading from modules/decorators/directories. Stays in panther.

## Steps

### Step 1: Create panther_types/plugin/types.py

```python
# packages/panther-types/panther_types/plugin/types.py
"""Plugin type definitions.

Defines the fundamental plugin type enum and metadata structures
for the PANTHER plugin system.
"""
from enum import Enum


class PluginType(Enum):
    """Types of plugins in the PANTHER framework."""

    SERVICE = "service"
    NETWORK_ENVIRONMENT = "network_environment"
    EXECUTION_ENVIRONMENT = "execution_environment"
    TESTER = "tester"
    PROTOCOL = "protocol"
    OBSERVER = "observer"
    IUT = "iut"
```

**Critical**: Read the actual source file to verify exact enum values.

### Step 2: Create panther_types/plugin/metadata.py

Extract only the `PluginStatus` enum and `PluginMetadata` dataclass from `plugin_metadata.py`. Leave `PluginMetadataLoader` in panther.

```python
# packages/panther-types/panther_types/plugin/metadata.py
"""Plugin metadata structures."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther_types.plugin.types import PluginType


class PluginStatus(Enum):
    """Lifecycle status of a plugin."""
    # Copy exact values from source

class PluginMetadata:
    """Metadata about a discovered plugin."""
    # Copy dataclass with all fields and from_dict/to_dict/has_capability/is_compatible_with methods
    # Do NOT copy PluginMetadataLoader
```

**Critical**: Read lines 16-138 of the actual source file. Copy `PluginStatus` and `PluginMetadata` exactly.

### Step 3: Update __init__.py

```python
# packages/panther-types/panther_types/plugin/__init__.py
"""Plugin type definitions."""
from panther_types.plugin.metadata import PluginMetadata, PluginStatus
from panther_types.plugin.types import PluginType

__all__ = ["PluginType", "PluginStatus", "PluginMetadata"]
```

### Step 4: Write tests

```python
# packages/panther-types/tests/test_plugin_types.py
"""Tests for plugin type definitions."""
from panther_types.plugin.types import PluginType
from panther_types.plugin.metadata import PluginMetadata, PluginStatus


class TestPluginType:
    def test_values(self):
        assert PluginType.TESTER is not None
        assert PluginType.IUT is not None
        assert PluginType.SERVICE is not None
        assert PluginType.PROTOCOL is not None

    def test_value_strings(self):
        assert PluginType.TESTER.value == "tester"
        assert PluginType.IUT.value == "iut"


class TestPluginStatus:
    def test_lifecycle(self):
        assert PluginStatus.DISCOVERED is not None
        assert PluginStatus.LOADED is not None
        assert PluginStatus.ACTIVE is not None
        assert PluginStatus.FAILED is not None


class TestPluginMetadata:
    def test_create(self):
        meta = PluginMetadata(
            name="test_plugin",
            type=PluginType.TESTER,
            path=Path("/tmp/test"),
        )
        assert meta.name == "test_plugin"
        assert meta.type == PluginType.TESTER

    def test_to_dict(self):
        meta = PluginMetadata(
            name="test",
            type=PluginType.IUT,
            path=Path("/tmp"),
        )
        d = meta.to_dict()
        assert d["name"] == "test"

    def test_from_dict(self):
        d = {
            "name": "test",
            "type": "tester",
            "path": "/tmp/test",
        }
        meta = PluginMetadata.from_dict(d)
        assert meta.name == "test"

    def test_has_capability(self):
        meta = PluginMetadata(
            name="test",
            type=PluginType.TESTER,
            path=Path("/tmp"),
            capabilities=["formal_verification"]
        )
        assert meta.has_capability("formal_verification") is True
        assert meta.has_capability("unknown") is False
```

## Verification
```bash
cd packages/panther-types
pytest tests/test_plugin_types.py -v
```

## Commit Message
```
feat(panther-types): extract plugin type and metadata structures

Move PluginType enum, PluginStatus enum, and PluginMetadata dataclass
into panther-types. PluginManifest and PluginMetadataLoader stay in
panther due to transitive dependencies.
```

## Files Modified
- `packages/panther-types/panther_types/plugin/types.py` (new)
- `packages/panther-types/panther_types/plugin/metadata.py` (new)
- `packages/panther-types/panther_types/plugin/__init__.py` (updated)
- `packages/panther-types/tests/test_plugin_types.py` (new)
