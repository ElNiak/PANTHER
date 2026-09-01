"""Checkpoints, the question register and the gates over prose drafts.

Manifest-side stage: it imports the parent package's ``schema`` and
``promotion`` (same domain) but reads timeline artifacts only as files on
disk — never through an import from the corpus-side subpackages.

Two gates, asking different questions: ``gate`` checks that a draft is
internally consistent, and ``completeness`` checks how much of the timeline it
covers. Consistency is preserved by doing nothing, so neither substitutes for
the other. ``completeness``'s ``build``, ``to_json`` and ``findings`` are
reached through the module rather than re-exported here, because this namespace
names its verbs for what they act on.
"""

from .checkpoint import CheckpointError, verify_checkpoint, write_checkpoint
from .completeness import ClusterCompleteness, CompletenessError, CompletenessReport
from .gate import (
    CITATION,
    GateError,
    RevisionEntry,
    cited_ids,
    load_revisions,
    run_gate,
)
from .questions import (
    Question,
    QuestionError,
    QuestionStatus,
    dump_questions,
    load_questions,
)

__all__ = [
    "CITATION",
    "CheckpointError",
    "ClusterCompleteness",
    "CompletenessError",
    "CompletenessReport",
    "GateError",
    "Question",
    "QuestionError",
    "QuestionStatus",
    "RevisionEntry",
    "cited_ids",
    "dump_questions",
    "load_questions",
    "load_revisions",
    "run_gate",
    "verify_checkpoint",
    "write_checkpoint",
]
