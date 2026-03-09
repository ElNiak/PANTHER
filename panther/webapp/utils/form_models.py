"""Utilities for creating NiceCRUD-compatible form models from PANTHER Pydantic models.

PANTHER config models inherit ``omega_config: Optional[DictConfig]`` from
``BaseUnifiedModel``.  OmegaConf's ``DictConfig`` cannot produce a JSON Schema,
which NiceCRUD requires internally.

``build_form_model`` recursively strips ``omega_config`` and unsupported types,
keeping nested BaseModel fields intact (NiceCRUD v2.12.5+ handles them natively
via edit-button → recursive dialog).  Union[BaseModel...] is also preserved
(NiceCRUD model-type switcher dropdown).

Usage::

    from panther.config.core.models.global_config import LoggingConfig
    from panther.webapp.utils.form_models import build_form_model, pick_id_field

    FormModel = build_form_model(LoggingConfig)
    crud = NiceCRUD(FormModel, id_field=pick_id_field(LoggingConfig))
"""

from __future__ import annotations

import logging
from typing import Any, NamedTuple, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field, create_model
from pydantic_core import PydanticUndefined

logger = logging.getLogger(__name__)


class ComplexFieldInfo(NamedTuple):
    """Metadata for a field that needs a custom widget (not rendered by NiceCRUD)."""

    category: str  # "dict_str" | "dict_model" | "list_model"
    annotation: Any  # raw type annotation
    value_type: type  # inner type (str, ServiceConfig, etc.)
    description: str  # from Pydantic Field


# ── UI metadata for GlobalConfig sections ────────────────────────────

GLOBAL_SECTION_META: dict[str, tuple[str, str]] = {
    "logging": ("description", "Global log level and format settings."),
    "paths": ("folder", "Output, log, and plugin directory paths."),
    "docker": ("dns", "Build flags, Buildx, and user mapping configuration."),
    "progress": ("hourglass_top", "Progress bar and spinner display options."),
    "fast_fail": ("flash_on", "Stop execution early on critical failures."),
    "metrics": ("monitor_heart", "System metrics collection and export."),
    "observers": ("visibility", "Observer pipeline configurations."),
}

# ── id_field override map ────────────────────────────────────────────

_ID_FIELD_OVERRIDES: dict[str, str] = {
    "LoggingConfig": "level",
    "PathsConfig": "output_dir",
    "ExperimentMetadata": "name",
    "StepsConfig": "wait",
}


# ── Public API ───────────────────────────────────────────────────────


def build_form_model(model_cls: type[BaseModel]) -> type[BaseModel]:
    """Create a NiceCRUD-safe copy of *model_cls*.

    * Removes ``omega_config``
    * Skips unsupported types (``List[BaseModel]``, all ``Dict[...]``)
    * Keeps nested ``BaseModel`` fields intact (NiceCRUD handles recursively)
    * Keeps ``Union[BaseModel...]`` intact (NiceCRUD model switcher)
    * Recursively cleans nested annotations via ``_clean_annotation()``
    * Required fields get sensible defaults so NiceCRUD can instantiate
    """
    fields: dict = {}
    for name, field_info in model_cls.model_fields.items():
        if name == "omega_config":
            continue
        annotation = field_info.annotation
        if _is_unsupported_for_nicecrud(annotation):
            continue

        cleaned = _clean_annotation(annotation)
        default = _resolve_default(field_info, cleaned)
        fields[name] = (cleaned, default)

    return create_model(f"{model_cls.__name__}Form", **fields)


def pick_id_field(model_cls: type[BaseModel]) -> str:
    """Pick the best id_field for NiceCRUD.

    Priority: explicit override → field named ``name``/``id`` → ``enabled`` → first field.
    """
    cls_name = model_cls.__name__
    if cls_name in _ID_FIELD_OVERRIDES:
        return _ID_FIELD_OVERRIDES[cls_name]

    field_names = [n for n in model_cls.model_fields if n != "omega_config"]
    for candidate in ("name", "id"):
        if candidate in field_names:
            return candidate
    if "enabled" in field_names:
        return "enabled"
    return field_names[0] if field_names else "id"


def get_skipped_fields(model_cls: type[BaseModel]) -> list[str]:
    """Return names of fields that NiceCRUD cannot render (List[BaseModel], Dict types)."""
    return list(get_complex_fields(model_cls).keys())


def classify_complex_field(annotation) -> str | None:
    """Classify a type annotation into a custom-widget category.

    Returns:
        ``"dict_str"`` for Dict[str, str] / Dict[str, Any],
        ``"dict_model"`` for Dict[str, BaseModel],
        ``"list_model"`` for List[BaseModel],
        ``None`` for types NiceCRUD handles natively.
    """
    origin = get_origin(annotation)

    # Unwrap Optional[T]
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return classify_complex_field(args[0])
        return None

    if origin is dict:
        args = get_args(annotation)
        if len(args) == 2:
            value_type = args[1]
            if isinstance(value_type, type) and issubclass(value_type, BaseModel):
                return "dict_model"
        return "dict_str"

    if origin is list:
        args = get_args(annotation)
        if args:
            elem = args[0]
            if isinstance(elem, type) and issubclass(elem, BaseModel):
                return "list_model"
        return None

    return None


def get_complex_fields(model_cls: type[BaseModel]) -> dict[str, ComplexFieldInfo]:
    """Return fields that need custom widgets (not rendered by NiceCRUD).

    Maps field_name → ComplexFieldInfo for each Dict or List[BaseModel] field.
    """
    result: dict[str, ComplexFieldInfo] = {}
    for name, field_info in model_cls.model_fields.items():
        if name == "omega_config":
            continue
        category = classify_complex_field(field_info.annotation)
        if category is None:
            continue
        value_type = _extract_inner_type(field_info.annotation)
        result[name] = ComplexFieldInfo(
            category=category,
            annotation=field_info.annotation,
            value_type=value_type,
            description=field_info.description or "",
        )
    return result


def _extract_inner_type(annotation) -> type:
    """Extract the value/element type from a Dict or List annotation."""
    origin = get_origin(annotation)

    # Unwrap Optional
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _extract_inner_type(args[0])

    if origin is dict:
        args = get_args(annotation)
        if len(args) == 2:
            return args[1]
        return str

    if origin is list:
        args = get_args(annotation)
        if args:
            return args[0]
        return str

    return str


def _is_unsupported_for_nicecrud(annotation) -> bool:
    """Return True for types NiceCRUD cannot render.

    Unsupported: ``List[BaseModel]``, all ``Dict[K, V]`` types.
    Supported: ``Union[BaseModel...]``, ``list[str]``, scalar types, nested BaseModel.
    """
    origin = get_origin(annotation)

    # Unwrap Optional[T] → check inner
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _is_unsupported_for_nicecrud(args[0])
        # Union[BaseModel...] (multi-member) → supported (model switcher)
        return False

    # Dict[K, V] → always unsupported
    if origin is dict:
        return True

    # List/list → check element type
    if origin is list:
        args = get_args(annotation)
        if args:
            elem = args[0]
            if isinstance(elem, type) and issubclass(elem, BaseModel):
                return True  # List[BaseModel] unsupported
        return False  # list[str], list[int] etc. supported

    return False


# ── Internal helpers ─────────────────────────────────────────────────


def _make_field_tuple(field_info):
    """Build a ``(annotation, default_or_FieldInfo)`` tuple for ``create_model``."""
    annotation = field_info.annotation
    if field_info.default is not PydanticUndefined:
        return (annotation, field_info.default)
    if field_info.default_factory is not None:
        return (annotation, Field(default_factory=field_info.default_factory))
    return (annotation, ...)


def _resolve_default(field_info, cleaned_annotation):
    """Return a default value suitable for NiceCRUD instantiation.

    If the field already has a default or default_factory, use it.
    Otherwise, synthesize a sensible default based on the cleaned annotation.
    """
    if field_info.default is not PydanticUndefined:
        return field_info.default
    if field_info.default_factory is not None:
        return Field(default_factory=field_info.default_factory)

    # Required field → synthesize default
    return _synthesize_default(cleaned_annotation)


def _synthesize_default(annotation):
    """Generate a sensible default for a required field based on its type."""
    origin = get_origin(annotation)

    # Optional[X] → None
    if origin is Union:
        args = get_args(annotation)
        if type(None) in args:
            return None
        # Union[BaseModel...] → factory of first member
        non_none = [a for a in args if a is not type(None)]
        if (
            non_none
            and isinstance(non_none[0], type)
            and issubclass(non_none[0], BaseModel)
        ):
            first = non_none[0]
            return Field(default_factory=first)
        return None

    # BaseModel → default_factory
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return Field(default_factory=annotation)

    # Scalars
    if annotation is str or annotation == str:
        return ""
    if annotation is int or annotation == int:
        return 0
    if annotation is float or annotation == float:
        return 0.0
    if annotation is bool or annotation == bool:
        return False

    # list[X] → []
    if origin is list:
        return Field(default_factory=list)

    return None


def _clean_annotation(annotation):
    """Recursively create form-safe versions of nested model annotations."""
    origin = get_origin(annotation)

    if origin in (Optional, Union):
        args = get_args(annotation)
        cleaned = tuple(_clean_annotation(a) for a in args)
        return Union[cleaned]  # type: ignore[valid-type]

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        # Create form-safe version for any BaseModel with required fields
        # so NiceCRUD can instantiate them without arguments.
        model_fields = getattr(annotation, "model_fields", {})
        has_required = any(f.is_required() for f in model_fields.values())
        if has_required:
            return build_form_model(annotation)

    return annotation


# ── Dict ↔ Form conversion helpers ──────────────────────────────────


def dict_to_form_instance(model_cls: type[BaseModel], data: dict) -> BaseModel:
    """Create a FormModel instance populated from a raw config dict.

    Calls ``build_form_model()``, filters *data* to FormModel fields only,
    and recursively handles nested BaseModel fields.
    Complex fields (Dict/List[BaseModel]) are skipped -- those go to widgets.
    """
    FormModel = build_form_model(model_cls)
    form_fields = set(FormModel.model_fields.keys())
    filtered: dict[str, Any] = {}
    for key, value in data.items():
        if key not in form_fields:
            continue
        field_info = FormModel.model_fields[key]
        ann = field_info.annotation
        # Recursively convert nested BaseModel dicts
        if (
            isinstance(value, dict)
            and isinstance(ann, type)
            and issubclass(ann, BaseModel)
        ):
            try:
                filtered[key] = ann(**value)
            except Exception:
                logger.debug("Failed to convert nested field %s", key)
                continue
        else:
            filtered[key] = value
    try:
        return FormModel(**filtered)
    except Exception:
        logger.debug(
            "Failed to create form instance for %s, using defaults", model_cls.__name__
        )
        return FormModel()


def form_instance_to_dict(
    instance: BaseModel,
    widgets: dict[str, Any] | None = None,
) -> dict:
    """Serialize a FormModel instance + widget values back to a config dict.

    Calls ``instance.model_dump()``, then merges in ``widget.get_value()``
    for each widget key.
    """
    data = instance.model_dump()
    if widgets:
        for field_name, widget in widgets.items():
            data[field_name] = widget.get_value()
    return data


def populate_panel_from_dict(
    panel: Any, model_cls: type[BaseModel], data: dict
) -> None:
    """Populate an existing ``FormPanelResult`` (crud + widgets) from a dict.

    Handles:
    - Singleton (SingletonForm): replaces the single instance via ``set_instance()``
    - Multi-instance NiceCRUD: replaces ``basemodels`` list
    - Widgets: calls ``widget.set_value()`` with the relevant sub-dict/list
    """
    from panther.webapp.components.singleton_crud import SingletonForm

    simple, complex_data = split_simple_and_complex(model_cls, data)
    instance = dict_to_form_instance(model_cls, simple)

    crud = panel.crud
    if isinstance(crud, SingletonForm):
        crud.set_instance(instance)
    else:
        crud.basemodels = [instance]

    # Populate widgets with complex field data
    for field_name, widget in panel.widgets.items():
        if field_name in complex_data:
            widget.set_value(complex_data[field_name])


def extract_section_data(config_dict: dict, section_path: str) -> Any | None:
    """Extract nested section using dot notation.

    E.g. ``'tests.0.services'`` → ``cfg['tests'][0]['services']``.
    Returns ``None`` if the path doesn't exist.
    """
    current: Any = config_dict
    for part in section_path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def split_simple_and_complex(
    model_cls: type[BaseModel], data: dict
) -> tuple[dict, dict]:
    """Split a config dict into simple fields (for NiceCRUD) and complex fields (for widgets).

    Returns ``(simple_data, complex_data)`` where:
    - *simple_data*: only fields that ``build_form_model`` keeps
    - *complex_data*: only fields classified as complex (Dict, List[BaseModel])
    """
    complex = get_complex_fields(model_cls)
    complex_names = set(complex.keys())

    simple_data: dict[str, Any] = {}
    complex_data: dict[str, Any] = {}
    for key, value in data.items():
        if key == "omega_config":
            continue
        if key in complex_names:
            complex_data[key] = value
        else:
            simple_data[key] = value
    return simple_data, complex_data
