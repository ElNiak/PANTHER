"""Field partitioning utility using Pydantic v2 model_fields introspection.

Replaces hardcoded ``known_fields`` sets in builders.py and service.py.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from pydantic import BaseModel


def partition_fields(
    data: Dict[str, Any], model_cls: Type[BaseModel]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split data into (declared_fields, extra_fields) using model introspection.

    Note: Uses Python field names, not serialization aliases. If ``model_cls``
    uses ``Field(alias=...)``, the alias won't be recognized as a declared field.

    Fields declared on ``model_cls`` go into the first dict.
    Everything else goes into the second dict (plugin-specific fields).

    Args:
        data: Raw dictionary from YAML or user input.
        model_cls: Pydantic model class to introspect.

    Returns:
        Tuple of (declared_data, extra_data).
    """
    declared_names = set(model_cls.model_fields.keys())
    declared_data = {k: v for k, v in data.items() if k in declared_names}
    extra_data = {k: v for k, v in data.items() if k not in declared_names}
    return declared_data, extra_data


def warn_extra_fields(
    data: Dict[str, Any],
    model_cls: Type[BaseModel],
    context_label: str = "",
    logger: Optional[logging.Logger] = None,
    exclude: Optional[Set[str]] = None,
) -> List[str]:
    """Check for undeclared fields and log warnings.

    Args:
        data: Raw dictionary from YAML or user input.
        model_cls: Pydantic model class to introspect.
        context_label: Label for log messages (e.g. ``"protocol"``).
        logger: Logger instance; defaults to ``panther.config``.
        exclude: Field names to skip (e.g. builder-injected fields).

    Returns:
        List of extra field names found.
    """
    _logger = logger or logging.getLogger("panther.config")
    declared_names = set(model_cls.model_fields.keys())
    skip = exclude or set()
    extra_names = [k for k in data if k not in declared_names and k not in skip]
    if extra_names:
        label = f" in {context_label}" if context_label else ""
        _logger.warning(
            "Unknown field(s)%s: %s. Check for typos. " "Valid fields: %s",
            label,
            extra_names,
            sorted(declared_names),
        )
    return extra_names
