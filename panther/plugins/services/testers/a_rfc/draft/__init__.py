"""Checkpoints, the question register and the citation gate for prose drafts.

Manifest-side stage: it imports the parent package's ``schema`` and
``promotion`` (same domain) but reads timeline artifacts only as files on
disk — never through an import from the corpus-side subpackages.
"""

from .checkpoint import CheckpointError, verify_checkpoint, write_checkpoint
from .questions import (
    Question,
    QuestionError,
    QuestionStatus,
    dump_questions,
    load_questions,
)

__all__ = [
    "CheckpointError",
    "Question",
    "QuestionError",
    "QuestionStatus",
    "dump_questions",
    "load_questions",
    "verify_checkpoint",
    "write_checkpoint",
]
