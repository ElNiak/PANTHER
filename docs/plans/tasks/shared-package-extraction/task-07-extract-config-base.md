# Task 07: Extract Config Base Classes to panther-types

## Goal
Extract `BaseConfig` (244 lines) and `BaseUnifiedModel` (109 lines) to `panther_types/config/base.py`.

## Prerequisites
- Task 06 completed (package scaffolded)

## Source Files
- `panther/config/core/base.py` (244 lines) - BaseConfig
- `panther/config/core/models/base_model.py` (109 lines) - BaseUnifiedModel

## Context
These two classes form the foundation of all PANTHER configuration models. Every config class inherits from BaseUnifiedModel, which inherits from BaseConfig. They depend ONLY on:
- pydantic (BaseModel, Field)
- omegaconf (DictConfig, OmegaConf)
- yaml (PyYAML)
- json (stdlib)
- abc (stdlib)
- pathlib (stdlib)

No panther-internal imports. Clean extraction boundary.

## Steps

### Step 1: Copy BaseConfig and BaseUnifiedModel

Read the full source of both files and copy them into a single file in panther-types:

```python
# packages/panther-types/panther_types/config/base.py
```

The file should contain:
1. All imports from both source files (deduplicated)
2. `BaseConfig` class (complete, from panther/config/core/base.py)
3. `BaseUnifiedModel` class (complete, from panther/config/core/models/base_model.py)

**Critical**: BaseUnifiedModel references `BaseConfig` via `from ..base import BaseConfig` in the original. In panther-types, both classes are in the same file, so no import is needed - just class definition order.

### Step 2: Verify the combined file works

Key things to check:
- `BaseConfig` extends `ABC` and `BaseModel` (from pydantic)
- `BaseConfig.Config` inner class has `arbitrary_types_allowed = True`, `from_attributes = True`, `populate_by_name = True`
- `BaseConfig.omega_config` field with `Field(default=None, exclude=True)`
- `BaseUnifiedModel.__init__` handles DictConfig input
- `BaseUnifiedModel.to_dict` has `exclude_defaults` parameter
- `BaseUnifiedModel.update_from_dict` uses OmegaConf merge
- `BaseUnifiedModel.has_field` and `clone` methods

### Step 3: Update __init__.py

```python
# packages/panther-types/panther_types/config/__init__.py
"""Configuration base classes and models."""
from panther_types.config.base import BaseConfig, BaseUnifiedModel

__all__ = ["BaseConfig", "BaseUnifiedModel"]
```

### Step 4: Write tests

```python
# packages/panther-types/tests/test_config_base.py
"""Tests for config base classes."""
import json
import yaml
from panther_types.config.base import BaseConfig, BaseUnifiedModel


class ConcreteConfig(BaseConfig):
    """Concrete test config."""
    name: str = "test"
    value: int = 42

    def validate_config(self):
        if self.value < 0:
            raise ValueError("value must be non-negative")
        return True


class ConcreteModel(BaseUnifiedModel):
    """Concrete test model."""
    name: str = "model"
    count: int = 0
    enabled: bool = True


class TestBaseConfig:
    def test_create(self):
        c = ConcreteConfig()
        assert c.name == "test"
        assert c.value == 42

    def test_validate(self):
        c = ConcreteConfig(value=10)
        assert c.validate_config() is True

    def test_to_dict(self):
        c = ConcreteConfig(name="foo", value=1)
        d = c.to_dict()
        assert d["name"] == "foo"
        assert d["value"] == 1

    def test_to_omega(self):
        c = ConcreteConfig()
        omega = c.to_omega()
        assert omega.name == "test"

    def test_from_omega(self):
        from omegaconf import OmegaConf
        omega = OmegaConf.create({"name": "loaded", "value": 99})
        c = ConcreteConfig.from_omega(omega)
        assert c.name == "loaded"
        assert c.value == 99

    def test_to_yaml(self):
        c = ConcreteConfig()
        y = c.to_yaml()
        data = yaml.safe_load(y)
        assert data["name"] == "test"

    def test_to_json(self):
        c = ConcreteConfig()
        j = c.to_json()
        data = json.loads(j)
        assert data["name"] == "test"

    def test_merge(self):
        c1 = ConcreteConfig(name="a", value=1)
        c2 = ConcreteConfig(name="b", value=2)
        merged = c1.merge(c2)
        assert merged.name == "b"
        assert merged.value == 2

    def test_get_schema(self):
        schema = ConcreteConfig.get_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]

    def test_update_field(self):
        c = ConcreteConfig()
        c.update_field("name", "updated")
        assert c.name == "updated"

    def test_get_field(self):
        c = ConcreteConfig(name="hello")
        assert c.get_field("name") == "hello"
        assert c.get_field("nonexistent", "default") == "default"


class TestBaseUnifiedModel:
    def test_create(self):
        m = ConcreteModel()
        assert m.name == "model"
        assert m.count == 0

    def test_to_dict(self):
        m = ConcreteModel(name="test", count=5)
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["count"] == 5

    def test_to_dict_exclude_defaults(self):
        m = ConcreteModel(name="custom")
        d = m.to_dict(exclude_defaults=True)
        assert "name" in d
        # count and enabled should be excluded (they're defaults)

    def test_update_from_dict(self):
        m = ConcreteModel()
        m.update_from_dict({"name": "updated", "count": 10})
        assert m.name == "updated"
        assert m.count == 10

    def test_has_field(self):
        m = ConcreteModel()
        assert m.has_field("name") is True
        assert m.has_field("nonexistent") is False

    def test_clone(self):
        m = ConcreteModel(name="original", count=5)
        clone = m.clone()
        assert clone.name == "original"
        assert clone.count == 5
        clone.name = "modified"
        assert m.name == "original"  # Original unchanged

    def test_from_dictconfig(self):
        from omegaconf import OmegaConf
        dc = OmegaConf.create({"name": "from_dc", "count": 3, "enabled": False})
        m = ConcreteModel(**dc)
        assert m.name == "from_dc"
```

## Verification
```bash
cd packages/panther-types
pip install -e ".[dev]"
pytest tests/test_config_base.py -v
```

## Important Notes
- Read the ACTUAL source files before copying. The class implementations may have changed since the exploration.
- `BaseConfig.to_dict()` has Pydantic v1/v2 compatibility code (`model_dump` vs `dict`). Preserve this.
- `BaseConfig.save()` and `load()` use file I/O. Include them in the extraction.
- The `omega_config` field is excluded from serialization (`Field(default=None, exclude=True)`).

## Commit Message
```
feat(panther-types): extract BaseConfig and BaseUnifiedModel

Move the configuration base classes from panther/config/core/ into
the panther-types shared package. These are the foundation for all
PANTHER configuration models.
```

## Files Modified
- `packages/panther-types/panther_types/config/base.py` (new)
- `packages/panther-types/panther_types/config/__init__.py` (updated)
- `packages/panther-types/tests/test_config_base.py` (new)
