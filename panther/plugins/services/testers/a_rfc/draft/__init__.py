"""Checkpoints, the question register and the citation gate for prose drafts.

Manifest-side stage: it imports the parent package's ``schema`` and
``promotion`` (same domain) but reads timeline artifacts only as files on
disk — never through an import from the corpus-side subpackages.
"""

from .checkpoint import CheckpointError, verify_checkpoint, write_checkpoint

__all__ = ["CheckpointError", "verify_checkpoint", "write_checkpoint"]
