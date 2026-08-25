"""Per-cluster evidence folders: metadata, file sets and deterministic diffs.

Corpus-side stage: consumes the timeline artifacts, the corpus JSONL and the
pinned clone; shares no domain code with the manifest core.
"""

from .emit import EMPTY_TREE, ViewsError, emit_views, verify_views

__all__ = ["EMPTY_TREE", "ViewsError", "emit_views", "verify_views"]
