"""Field partitioning utility using Pydantic v2 model_fields introspection.

Replaces hardcoded ``known_fields`` sets in builders.py and service.py.
"""

from typing import Any, Dict, Tuple, Type

from pydantic import BaseModel


def partition_fields(
    data: Dict[str, Any], model_cls: Type[BaseModel]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split data into (declared_fields, extra_fields) using model introspection.

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
