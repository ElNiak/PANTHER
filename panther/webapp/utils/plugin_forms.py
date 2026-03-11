"""PluginForms — bridge between the PANTHER plugin system and the webapp form layer.

Provides helpers that connect the PANTHER (Protocol ANalysis and Testing
Harness for Extensible Research) decorator-based plugin registry to the
web dashboard's form rendering layer.  The main responsibilities are:

* **Plugin discovery** — ``_ensure_plugins_discovered()`` runs
  ``PluginDiscovery.discover_plugins()`` once per process (thread-safe).
* **Config class lookup** — ``_discover_config_class()`` resolves a
  plugin name to its Pydantic config model via the schema registry
  populated by ``@register_plugin`` decorators.
* **Form info assembly** — ``get_plugin_form_info()`` bundles the config
  model, default values, enum choices, complex fields, and metadata
  into a ``PluginFormInfo`` dataclass consumed by ``PydanticForm`` and
  the ``_render_plugin_select`` widget.
* **Choice lists** — ``get_protocol_choices()``,
  ``get_implementation_choices()``, and ``get_version_choices()`` return
  sorted lists for dropdown selects, optionally filtered by protocol or
  service type.
* **Plugin listing** — ``list_available_plugins()`` returns a list of
  dicts suitable for the plugin selector dropdown.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from panther.webapp.utils.form_models import ComplexFieldInfo, get_complex_fields

logger = logging.getLogger(__name__)

# ── Cached plugin discovery ───────────────────────────────────────────
_discovery_lock = threading.Lock()
_discovery_done = False


def _ensure_plugins_discovered():
    """Run plugin discovery once per process; subsequent calls are no-ops."""
    global _discovery_done
    if _discovery_done:
        return
    with _discovery_lock:
        if _discovery_done:  # double-check under lock
            return
        try:
            from panther.plugins.core.plugin_discovery import PluginDiscovery

            PluginDiscovery().discover_plugins()
            _discovery_done = True
        except Exception:
            logger.warning("Plugin discovery failed", exc_info=True)


@dataclass
class PluginFormInfo:
    """Everything the UI layer needs to render forms for a plugin config.

    Assembled by ``get_plugin_form_info()`` and consumed by
    ``PydanticForm._render_plugin_select()`` to create a sub-form
    showing plugin-specific configuration fields.

    Attributes:
        plugin_name: Canonical plugin name (e.g. ``"picoquic"``).
        config_model: The Pydantic ``BaseModel`` subclass defining this
            plugin's configuration schema.
        defaults: Default field values obtained by instantiating the
            config model with no arguments.
        enum_choices: Mapping of field names to lists of allowed string
            values for ``Enum``-typed fields.
        complex_fields: Mapping of field names to ``ComplexFieldInfo``
            for fields requiring custom widgets (dicts, lists).
        description: Human-readable plugin description from the
            ``@register_plugin`` manifest.
        supported_protocols: Protocol names this plugin supports
            (e.g. ``["quic", "http3"]``).
    """

    plugin_name: str
    config_model: type[BaseModel]  # Original config class
    defaults: dict[str, Any]
    enum_choices: dict[str, list[str]]  # field_name -> allowed values
    complex_fields: dict[str, ComplexFieldInfo]
    description: str = ""
    supported_protocols: list[str] = field(default_factory=list)


# ── Plugin config class registry ─────────────────────────────────────
# Maps lowercase plugin name -> module path for config_schema.py imports.
# Populated lazily from _DECORATED_PLUGINS or from known paths.

_CONFIG_CLASS_CACHE: dict[str, type[BaseModel]] = {}


def _discover_config_class(plugin_name: str) -> type[BaseModel] | None:
    """Try to find the Pydantic config class for a plugin by name.

    Uses the schema registry populated by ``@register_plugin``
    auto-discovery.  Results are cached in ``_CONFIG_CLASS_CACHE``.

    Args:
        plugin_name: The plugin name to resolve.

    Returns:
        The Pydantic config model class, or ``None`` if not found.
    """
    if plugin_name in _CONFIG_CLASS_CACHE:
        return _CONFIG_CLASS_CACHE[plugin_name]

    try:
        from panther.plugins.core.plugin_decorators import get_config_model

        config_class = get_config_model(plugin_name)
        if config_class is not None:
            _CONFIG_CLASS_CACHE[plugin_name] = config_class
            return config_class
    except Exception:
        logger.warning(
            "Failed to look up plugin %s in schema registry", plugin_name, exc_info=True
        )

    return None


def _extract_enum_choices(model_cls: type[BaseModel]) -> dict[str, list[str]]:
    """Inspect field annotations for Enum subclasses and extract their string values."""
    choices: dict[str, list[str]] = {}
    for name, field_info in model_cls.model_fields.items():
        ann = field_info.annotation
        enum_cls = _find_enum_in_annotation(ann)
        if enum_cls is not None:
            choices[name] = [e.value for e in enum_cls]
    return choices


def _find_enum_in_annotation(annotation: Any) -> type[Enum] | None:
    """Recursively unwrap Optional/Union and return the Enum class if found."""
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation
    origin = get_origin(annotation)
    if origin is not None:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            found = _find_enum_in_annotation(arg)
            if found is not None:
                return found
    return None


# ── Public API ────────────────────────────────────────────────────────


def get_plugin_form_info(plugin_name: str) -> PluginFormInfo | None:
    """Get form rendering info for a plugin by name.

    Looks up the plugin's config model via the schema registry, extracts
    default values, enum choices, and complex field metadata, then
    returns a ``PluginFormInfo`` bundle.

    Args:
        plugin_name: The plugin name to look up (case-sensitive, must
            match the name used in ``@register_plugin``).

    Returns:
        A ``PluginFormInfo`` instance, or ``None`` if the plugin has no
        discoverable config model.
    """
    config_cls = _discover_config_class(plugin_name)
    if config_cls is None:
        return None

    complex = get_complex_fields(config_cls)
    enum_choices = _extract_enum_choices(config_cls)

    try:
        defaults = config_cls().model_dump(mode="json")
    except Exception:
        defaults = {}

    description = ""
    protocols: list[str] = []
    try:
        from panther.plugins.core.plugin_decorators import get_plugin_by_name

        result = get_plugin_by_name(plugin_name)
        if result is not None:
            _, manifest = result
            description = getattr(manifest, "description", "")
            protocols = getattr(manifest, "supported_protocols", [])
    except Exception:
        logger.warning(
            "Failed to load plugin metadata for %s", plugin_name, exc_info=True
        )

    return PluginFormInfo(
        plugin_name=plugin_name,
        config_model=config_cls,
        defaults=defaults,
        enum_choices=enum_choices,
        complex_fields=complex,
        description=description,
        supported_protocols=protocols,
    )


def list_available_plugins(plugin_type: str | None = None) -> list[dict[str, str]]:
    """List available plugins from the decorator registry.

    Args:
        plugin_type: Optional filter — only return plugins whose type
            matches (e.g. ``"iut"``, ``"tester"``).  When ``None``,
            returns all plugin types.

    Returns:
        A list of dicts with keys ``"name"``, ``"type"``,
        ``"description"``, and ``"protocols"`` (comma-separated string).
        Returns ``[]`` on any discovery or registry error.
    """
    _ensure_plugins_discovered()

    try:
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        results: list[dict[str, str]] = []
        for _, (_cls, manifest) in get_decorated_plugins().items():
            ptype = (
                manifest.type.value
                if hasattr(manifest.type, "value")
                else str(manifest.type)
            )
            if plugin_type and ptype != plugin_type:
                continue
            results.append(
                {
                    "name": manifest.name,
                    "type": ptype,
                    "description": manifest.description or "",
                    "protocols": ", ".join(
                        getattr(manifest, "supported_protocols", [])
                    ),
                }
            )
        return results
    except Exception:
        logger.warning("Failed to list plugins", exc_info=True)
        return []


def get_protocol_choices() -> list[str]:
    """Return a sorted list of available protocol names from the decorator registry.

    Returns:
        Sorted list of unique protocol name strings (e.g.
        ``["http3", "quic"]``).  Returns ``[]`` on error.
    """
    _ensure_plugins_discovered()
    try:
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        protocols: set[str] = set()
        for _, (_cls, manifest) in get_decorated_plugins().items():
            for p in getattr(manifest, "supported_protocols", []):
                protocols.add(p)
        return sorted(protocols)
    except Exception:
        logger.warning("Failed to get protocol choices", exc_info=True)
        return []


def get_implementation_choices(
    protocol: str | None = None, service_type: str | None = None
) -> list[str]:
    """Return implementation names, optionally filtered by protocol and service type.

    Args:
        protocol: Filter to implementations supporting this protocol.
        service_type: Filter by plugin type (``"iut"`` or ``"tester"``).
            When ``None``, returns both IUT and tester implementations.
    """
    _ensure_plugins_discovered()
    try:
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        _config_to_plugin_type = {"testers": "tester"}
        normalized = (
            _config_to_plugin_type.get(service_type, service_type)
            if service_type
            else None
        )
        allowed_types = {normalized} if normalized else {"iut", "tester"}
        names: list[str] = []
        for _, (_cls, manifest) in get_decorated_plugins().items():
            ptype = (
                manifest.type.value
                if hasattr(manifest.type, "value")
                else str(manifest.type)
            )
            if ptype not in allowed_types:
                continue
            if protocol:
                supported = getattr(manifest, "supported_protocols", [])
                if protocol not in supported:
                    continue
            names.append(manifest.name)
        return sorted(names)
    except Exception:
        logger.warning("Failed to get implementation choices", exc_info=True)
        return []


def get_version_choices(protocol_name: str) -> list[str]:
    """Return supported versions for a protocol from the protocol registry.

    Args:
        protocol_name: Protocol name to look up (e.g. ``"quic"``).

    Returns:
        List of version strings (e.g. ``["rfc9000", "rfc9001"]``).
        Returns ``[]`` on error or if the protocol is not found.
    """
    _ensure_plugins_discovered()
    try:
        from panther.plugins.core.plugin_decorators import get_protocol_versions

        return get_protocol_versions(protocol_name)
    except Exception:
        logger.warning(
            "Failed to get version choices for %s", protocol_name, exc_info=True
        )
        return []
