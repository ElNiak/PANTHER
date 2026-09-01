"""Adopt pull records obtained without this tool's forge client.

A repository we hold no credentials for can still be reconstructed when its
records reach us some other way — a forge project export, a glab/gh dump, or
another operator's snapshot. Only reading happens here: the records are handed
to :func:`write_snapshot`, which owns comment-kind validation, the write-once
rule and the layout downstream discovery depends on, so an adopted snapshot
cannot carry anything a fetched one could not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import ForgeError

Record = dict[str, Any]

_SECTIONS = ("pulls", "reviews", "comments")


def read_records(path: Path) -> tuple[list[Record], list[Record], list[Record]]:
    """Read a records file into the three sequences a snapshot carries.

    A section that is absent reads as empty rather than raising: a forge with
    no reviews omits the key, and that is not a malformed file.

    Args:
        path: A JSON file holding ``{pulls, reviews, comments}``.

    Returns:
        The pulls, reviews and comments, in that order.

    Raises:
        ForgeError: If the file cannot be read as JSON, does not hold an
            object, or names a section that is not a list of objects.
    """
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        # ValueError subsumes JSONDecodeError and UnicodeDecodeError; a dump
        # from a non-UTF-8 toolchain must reach the CLI's handler as a
        # ForgeError rather than escaping it as a traceback.
        raise ForgeError(f"{path} could not be read as JSON: {error}") from error

    if not isinstance(payload, dict):
        raise ForgeError(
            f"{path} holds {type(payload).__name__}; an object with "
            f"{', '.join(_SECTIONS)} keys is required"
        )

    sections: list[list[Record]] = []
    for name in _SECTIONS:
        rows = payload.get(name, [])
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ForgeError(f"{path}: {name} must be a list of objects")
        sections.append(rows)

    pulls, reviews, comments = sections
    return pulls, reviews, comments
