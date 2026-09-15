"""Directory names the build and documentation pipelines write to.

One definition, imported by every consumer, so the two build entry points
cannot drift apart. ``docs/`` is deliberately absent from ``CLEAN_DIRS``: it is
a tracked corpus of plan and spec files, not generated output, and a cleaner
that removes it destroys work no build can reproduce.

Every name here is joined onto a project root and handed to ``shutil.rmtree``,
so the module refuses to import if any entry is not a single relative segment.
Stdlib only, deliberately: ``panther_builder.py`` imports this at bootstrap,
before a single dependency has been installed.

Attributes:
    GENERATED_DOCS_DIR: Directory the documentation build writes into.
    SITE_DIR: Directory the rendered documentation site is written to.
    CLEAN_DIRS: Directory names a clean removes from the project root.
"""

import os
from collections.abc import Iterable
from pathlib import Path

GENERATED_DOCS_DIR = "docs_build"
SITE_DIR = "site"
CLEAN_DIRS = ("build", "dist", GENERATED_DOCS_DIR, SITE_DIR, "htmlcov")


def _reject_unsafe_segments(dirs: Iterable[str]) -> None:
    """Refuse any entry that a clean could follow out of the project root.

    Every entry here reaches ``shutil.rmtree(project_root / entry)`` unchecked,
    and ``pathlib`` makes that dangerous in two distinct ways: an absolute
    right operand discards the left entirely, so ``Path('/repo') / '/etc'`` is
    ``/etc``; and ``''`` or ``'.'`` resolve back to the root itself, so the
    clean would delete the project. One relative segment is the only safe
    shape.

    ``..`` needs its own clause and does not get one for free: ``Path('..')``
    is relative and its ``parts`` is ``('..',)``, one segment, so a length
    check alone admits it and ``project_root / '..'`` climbs out of the tree.

    Args:
        dirs: Directory names destined for ``project_root / name``.

    Raises:
        ValueError: If an entry is absolute, is ``..``, or is anything other
            than exactly one path segment.
    """
    for name in dirs:
        parts = Path(name).parts
        if Path(name).is_absolute() or len(parts) != 1 or parts[0] == os.pardir:
            raise ValueError(
                f"CLEAN_DIRS entries must be single relative segments: {name!r}"
            )


_reject_unsafe_segments(CLEAN_DIRS)
