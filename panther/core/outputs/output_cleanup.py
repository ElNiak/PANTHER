"""Utility for cleaning up empty directories after experiment runs.

Docker bind mounts and entrypoint mkdir -p commands create directories
that may never receive files. This module provides safe cleanup of those
empty directories using Path.rmdir() which only succeeds on empty dirs.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_empty_directories(root: Path) -> int:
    """Remove empty directories under root, walking bottom-up.

    Uses Path.rmdir() which only succeeds on empty directories, making
    this operation safe by design - it cannot delete directories with files.

    Args:
        root: Root directory to clean. The root itself is also removed if empty.

    Returns:
        Number of directories removed.
    """
    if not root.exists() or not root.is_dir():
        return 0

    removed = 0

    # Collect all directories, sorted deepest-first for bottom-up removal
    dirs = sorted(
        (p for p in root.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for d in dirs:
        try:
            d.rmdir()
            removed += 1
            logger.debug("Removed empty directory: %s", d)
        except OSError:
            # Directory not empty or permission issue - skip
            pass

    # Try root itself
    try:
        root.rmdir()
        removed += 1
        logger.debug("Removed empty root directory: %s", root)
    except OSError:
        pass

    if removed > 0:
        logger.info("Removed %d empty directories under %s", removed, root)

    return removed
