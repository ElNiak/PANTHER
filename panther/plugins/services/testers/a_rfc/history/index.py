"""A queryable index over the corpus.

Derived and disposable. The JSONL files are the durable record; this exists so
questions like "which commits touched this path" do not require a full scan.
It is **rebuilt, never migrated** — if its sources have moved on it refuses to
answer, because a stale index answers confidently from old data and nothing
about the answer looks wrong.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from .store import COMMITS_FILE, FILES_FILE, read_corpus

INDEX_FILE = "index.sqlite"

_SCHEMA = """
CREATE TABLE commits (
    sha TEXT PRIMARY KEY,
    authored_at TEXT NOT NULL,
    author_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    is_merge INTEGER NOT NULL,
    file_count INTEGER NOT NULL,
    files_truncated INTEGER NOT NULL
);
CREATE TABLE file_changes (
    sha TEXT NOT NULL,
    path TEXT NOT NULL,
    status TEXT NOT NULL,
    previous_path TEXT
);
CREATE INDEX file_changes_path ON file_changes (path);
CREATE TABLE corpus_source (
    name TEXT PRIMARY KEY,
    digest TEXT NOT NULL
);
"""


class StaleIndexError(RuntimeError):
    """Raised when an index no longer matches the corpus it was built from."""


def _digest(path: Path) -> str:
    """Return a hex digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_index(directory: Path) -> Path:
    """Build the index from the corpus in ``directory``, replacing any existing one.

    Args:
        directory: A directory written by :func:`store.write_corpus`.

    Returns:
        Path to the index that was written.

    Raises:
        FileNotFoundError: If the corpus is absent.
    """
    commits, changes = read_corpus(directory)
    index_path = directory / INDEX_FILE
    index_path.unlink(missing_ok=True)

    conn = sqlite3.connect(index_path)
    try:
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO commits VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    c.sha,
                    c.authored_at,
                    c.author_email,
                    c.subject,
                    int(c.is_merge),
                    c.file_count,
                    int(c.files_truncated),
                )
                for c in commits
            ],
        )
        conn.executemany(
            "INSERT INTO file_changes VALUES (?, ?, ?, ?)",
            [(c.sha, c.path, c.status, c.previous_path) for c in changes],
        )
        conn.executemany(
            "INSERT INTO corpus_source VALUES (?, ?)",
            [
                (COMMITS_FILE, _digest(directory / COMMITS_FILE)),
                (FILES_FILE, _digest(directory / FILES_FILE)),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return index_path


def open_index(directory: Path) -> sqlite3.Connection:
    """Open the index, refusing if its sources have changed since it was built.

    Args:
        directory: A directory containing a corpus and its index.

    Returns:
        An open connection. Its context-manager protocol commits or rolls back
        a transaction; it does not close the connection, so close it yourself.

    Raises:
        FileNotFoundError: If the index does not exist.
        StaleIndexError: If either JSONL file no longer matches the digest
            recorded when the index was built.
    """
    index_path = directory / INDEX_FILE
    if not index_path.exists():
        raise FileNotFoundError(f"no index in {directory}; run build_index first")

    conn = sqlite3.connect(index_path)
    recorded = dict(conn.execute("SELECT name, digest FROM corpus_source").fetchall())
    for name in (COMMITS_FILE, FILES_FILE):
        current = _digest(directory / name)
        if recorded.get(name) != current:
            conn.close()
            raise StaleIndexError(
                f"{name} has changed since the index was built; "
                f"rebuild it rather than trusting these answers"
            )
    return conn
