"""Utilities for creating NiceCRUD-compatible form models from PANTHER Pydantic models.

PANTHER config models inherit ``omega_config: Optional[DictConfig]`` from
``BaseUnifiedModel``.  OmegaConf's ``DictConfig`` cannot produce a JSON Schema,
which NiceCRUD requires internally.  The ``strip_omega_config`` helper
recursively removes these fields and returns a clean ``BaseModel`` subclass
that NiceCRUD can render.

Nested ``BaseModel`` fields (depth=1) are **flattened** into the parent form
using a ``prefix__field`` naming convention so NiceCRUD can render them as
scalar inputs.  Use ``unflatten_dict`` to reconstruct nested dicts for YAML
export.

Usage::

    from panther.config.core.models.global_config import LoggingConfig
    from panther.webapp.utils.form_models import strip_omega_config

    FormModel = strip_omega_config(LoggingConfig)
    crud = NiceCRUD(FormModel, id_field="level")
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field, create_model
from pydantic_core import PydanticUndefined


class NetworkEnvironmentType(str, Enum):
    """Supported network environment types for the config form."""

    docker_compose = "docker_compose"
    localhost = "localhost"
    shadow_ns = "shadow_ns"


class TestConfigForm(BaseModel):
    """Hand-crafted form model for TestConfig.

    Replaces the complex TestConfig (which has unions, nested dicts, etc.)
    with simple scalar fields that NiceCRUD can render.  Complex fields
    (services, execution_environment) are edited via the YAML tab.
    """

    name: str = "my_test"
    description: Optional[str] = None
    network_environment_type: NetworkEnvironmentType = (
        NetworkEnvironmentType.docker_compose
    )
    iterations: int = 1
    timeout: Optional[int] = None
    fast_fail_enabled: Optional[bool] = None
    continue_on_failure: bool = False
    collect_artifacts: bool = True


def _is_unsupported_dict(annotation) -> bool:
    """Return True for ``Dict[str, X]`` where X is not a BaseModel.

    Also handles ``Optional[Dict[str, X]]``.  These fields cannot be
    rendered by NiceCRUD and should be skipped (users edit them in YAML).
    """
    origin = get_origin(annotation)

    # Unwrap Optional[T] -> T
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _is_unsupported_dict(args[0])
        return False

    if origin is dict:
        args = get_args(annotation)
        if len(args) == 2:
            value_type = args[1]
            if isinstance(value_type, type) and issubclass(value_type, BaseModel):
                return False
            return True

    return False


def _is_nested_base_model(annotation) -> bool:
    """Return True if annotation is a concrete BaseModel subclass (not Dict/Optional wrapper)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return True
    # Unwrap Optional[SomeModel]
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if (
            len(args) == 1
            and isinstance(args[0], type)
            and issubclass(args[0], BaseModel)
        ):
            return True
    return False


def _get_nested_model_class(annotation) -> type[BaseModel] | None:
    """Extract the BaseModel class from an annotation (handles Optional)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if (
            len(args) == 1
            and isinstance(args[0], type)
            and issubclass(args[0], BaseModel)
        ):
            return args[0]
    return None


def _flatten_nested_model(prefix: str, model_cls: type[BaseModel]) -> dict:
    """Extract scalar/enum/Optional fields from a nested BaseModel as ``prefix__field`` entries.

    Returns a dict of ``{name: (annotation, FieldInfo_or_default)}`` suitable for
    ``create_model(**fields)``.  Skips Dict fields and nested-nested BaseModels
    (depth limit = 1).
    """
    flattened: dict = {}
    for name, field_info in model_cls.model_fields.items():
        if name == "omega_config":
            continue
        if _is_unsupported_dict(field_info.annotation):
            continue
        if _is_nested_base_model(field_info.annotation):
            continue  # depth limit: don't flatten nested-nested

        flat_name = f"{prefix}__{name}"
        flattened[flat_name] = _make_field_tuple(field_info)
    return flattened


def _make_field_tuple(field_info):
    """Build a ``(annotation, default_or_FieldInfo)`` tuple for ``create_model``.

    Handles ``default_factory`` correctly — when ``field_info.default`` is
    ``PydanticUndefined`` but ``default_factory`` exists, wraps in ``Field()``.
    """
    annotation = field_info.annotation
    if field_info.default is not PydanticUndefined:
        return (annotation, field_info.default)
    if field_info.default_factory is not None:
        return (annotation, Field(default_factory=field_info.default_factory))
    # Required field (no default at all)
    return (annotation, ...)


def strip_omega_config(model_cls: type[BaseModel]) -> type[BaseModel]:
    """Create a NiceCRUD-safe copy of *model_cls* by removing ``omega_config`` fields.

    The function walks the model tree recursively so nested sub-models that
    also carry ``omega_config`` are cleaned as well.  Also skips
    ``Dict[str, primitive]`` fields that NiceCRUD cannot render.

    Nested BaseModel fields (depth=1) are **flattened** into the parent using
    ``prefix__field`` naming, so NiceCRUD can render their scalar fields.

    Returns a dynamically-created ``BaseModel`` subclass named
    ``<OriginalName>Form``.
    """
    fields: dict = {}
    for name, field_info in model_cls.model_fields.items():
        if name == "omega_config":
            continue
        if _is_unsupported_dict(field_info.annotation):
            continue

        # Flatten nested BaseModel fields (depth=1)
        if _is_nested_base_model(field_info.annotation):
            nested_cls = _get_nested_model_class(field_info.annotation)
            if nested_cls is not None:
                fields.update(_flatten_nested_model(name, nested_cls))
                continue

        fields[name] = _make_field_tuple(field_info)

    return create_model(f"{model_cls.__name__}Form", **fields)


def _clean_annotation(annotation):
    """Recursively strip omega_config from nested model annotations."""
    origin = get_origin(annotation)

    if origin in (Optional, Union):
        args = get_args(annotation)
        cleaned = tuple(_clean_annotation(a) for a in args)
        return Union[cleaned]  # type: ignore[valid-type]

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if "omega_config" in getattr(annotation, "model_fields", {}):
            return strip_omega_config(annotation)

    return annotation


def unflatten_dict(d: dict) -> dict:
    """Reconstruct nested dicts from ``prefix__field`` keys.

    Example::

        >>> unflatten_dict({"user_mapping__run_as_host_user": True, "force_build": True})
        {"user_mapping": {"run_as_host_user": True}, "force_build": True}
    """
    result: dict = {}
    for key, value in d.items():
        if "__" in key:
            prefix, subkey = key.split("__", 1)
            result.setdefault(prefix, {})[subkey] = value
        else:
            result[key] = value
    return result
