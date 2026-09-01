"""Write and read the durable corpus.

JSONL is the citable artifact: append-only, greppable, diffable, and reviewable
in a pull request. Output is byte-stable, which is what makes an extraction
citable at all — see :func:`write_corpus`.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Commit, ExtractionReport, FileChange

COMMITS_FILE = "commits.jsonl"
FILES_FILE = "files.jsonl"
REPORT_FILE = "report.json"


def _commit_to_dict(commit: Commit) -> dict:
    """Render a commit, injecting derived values explicitly.

    ``dataclasses.asdict`` drops ``@property`` values, so ``is_merge`` would
    vanish from the output without complaint.
    """
    return {
        "sha": commit.sha,
        "parents": list(commit.parents),
        "author_name": commit.author_name,
        "author_email": commit.author_email,
        "authored_at": commit.authored_at,
        "committed_at": commit.committed_at,
        "subject": commit.subject,
        "body": commit.body,
        "is_merge": commit.is_merge,
        "file_count": commit.file_count,
        "files_recorded": commit.files_recorded,
        "files_truncated": commit.files_truncated,
    }


def _commit_from_dict(record: dict) -> Commit:
    """Rebuild a commit, ignoring the derived ``is_merge`` field."""
    return Commit(
        sha=record["sha"],
        parents=tuple(record["parents"]),
        author_name=record["author_name"],
        author_email=record["author_email"],
        authored_at=record["authored_at"],
        committed_at=record["committed_at"],
        subject=record["subject"],
        body=record["body"],
        file_count=record["file_count"],
        files_recorded=record["files_recorded"],
        files_truncated=record["files_truncated"],
    )


def _change_to_dict(change: FileChange) -> dict:
    return {
        "sha": change.sha,
        "path": change.path,
        "status": change.status,
        "previous_path": change.previous_path,
    }


def _change_from_dict(record: dict) -> FileChange:
    return FileChange(
        sha=record["sha"],
        path=record["path"],
        status=record["status"],
        previous_path=record["previous_path"],
    )


def _dump_line(payload: dict) -> str:
    """Serialise one record deterministically."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n"


def write_corpus(
    commits: list[Commit],
    changes: list[FileChange],
    report: ExtractionReport,
    directory: Path,
) -> None:
    """Write the corpus to ``directory``.

    Two extractions of the same repository produce identical bytes. That rests
    on the caller's ordering — :func:`git_log.extract` sorts commits by
    ``(authored_at, sha)`` and rows by ``(sha, path)`` — plus sorted keys here.

    Args:
        commits: Commits, already sorted.
        changes: File rows, already sorted.
        report: What the extraction produced and dropped.
        directory: Destination; created if absent.
    """
    directory.mkdir(parents=True, exist_ok=True)
    (directory / COMMITS_FILE).write_text(
        "".join(_dump_line(_commit_to_dict(c)) for c in commits)
    )
    (directory / FILES_FILE).write_text(
        "".join(_dump_line(_change_to_dict(c)) for c in changes)
    )
    (directory / REPORT_FILE).write_text(
        json.dumps(
            {
                "commit_count": report.commit_count,
                "file_row_count": report.file_row_count,
                "truncated": list(report.truncated),
                "truncated_count": report.truncated_count,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def read_corpus(directory: Path) -> tuple[list[Commit], list[FileChange]]:
    """Read a corpus back from ``directory``.

    Args:
        directory: A directory previously written by :func:`write_corpus`.

    Returns:
        The commits and file rows, in the order they were written.

    Raises:
        FileNotFoundError: If either JSONL file is absent.
    """
    commits_path = directory / COMMITS_FILE
    files_path = directory / FILES_FILE
    if not commits_path.exists() or not files_path.exists():
        raise FileNotFoundError(f"no corpus in {directory}")

    commits = [
        _commit_from_dict(json.loads(line))
        for line in commits_path.read_text().splitlines()
        if line
    ]
    changes = [
        _change_from_dict(json.loads(line))
        for line in files_path.read_text().splitlines()
        if line
    ]
    return commits, changes
