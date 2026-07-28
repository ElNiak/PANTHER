"""Fixtures for the commit-corpus tests.

Every fixture builds its own repository in ``tmp_path``. Nothing here reaches
the network or reads the project's own history.
"""

import subprocess
from pathlib import Path

import pytest

D1 = "2026-01-01T00:00:00+00:00"
D2 = "2026-02-01T00:00:00+00:00"
SHARED = "2026-03-01T00:00:00+00:00"


def _run(repo: Path, *args: str, when: str | None = None) -> str:
    env = None
    if when is not None:
        import os

        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return result.stdout.strip()


@pytest.fixture
def corpus_repo(tmp_path: Path) -> Path:
    """A repository with four commits, two authors, one rename.

    Commit 1 (Author One, D1): adds src/a.txt and src/b.txt
    Commit 2 (Author Two, D2): renames src/a.txt to src/renamed.txt
    Commit 3 (Author One, SHARED): adds bulk/f0.txt … bulk/f4.txt
    Commit 4 (Author Two, SHARED): deletes src/b.txt

    Commits 3 and 4 share an authored timestamp on purpose.
    """
    repo = tmp_path / "corpus_repo"
    repo.mkdir()
    _run(repo, "init", "-q", "-b", "main")
    _run(repo, "config", "user.name", "Author One")
    _run(repo, "config", "user.email", "one@example.invalid")
    # Pinned, not assumed: with diff.renames disabled globally a rename is
    # reported as D + A, and the rename test in Task 3 would fail for a reason
    # that has nothing to do with the parser it exists to guard.
    _run(repo, "config", "diff.renames", "true")

    src = repo / "src"
    src.mkdir()
    (src / "a.txt").write_text("a\n")
    (src / "b.txt").write_text("b\n")
    _run(repo, "add", "src/a.txt", "src/b.txt")
    _run(repo, "commit", "-q", "-m", "first", "-m", "a body line", when=D1)

    _run(repo, "config", "user.name", "Author Two")
    _run(repo, "config", "user.email", "two@example.invalid")
    _run(repo, "mv", "src/a.txt", "src/renamed.txt")
    _run(repo, "commit", "-q", "-m", "rename a", when=D2)

    _run(repo, "config", "user.name", "Author One")
    _run(repo, "config", "user.email", "one@example.invalid")
    bulk = repo / "bulk"
    bulk.mkdir()
    for i in range(5):
        (bulk / f"f{i}.txt").write_text(f"{i}\n")
    _run(repo, "add", "bulk")
    _run(repo, "commit", "-q", "-m", "bulk add", when=SHARED)

    _run(repo, "config", "user.name", "Author Two")
    _run(repo, "config", "user.email", "two@example.invalid")
    _run(repo, "rm", "-q", "src/b.txt")
    _run(repo, "commit", "-q", "-m", "drop b", when=SHARED)

    return repo


@pytest.fixture
def shallow_repo(corpus_repo: Path, tmp_path: Path) -> Path:
    """A depth-1 clone of ``corpus_repo`` — history deliberately truncated."""
    shallow = tmp_path / "shallow_repo"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--depth",
            "1",
            f"file://{corpus_repo}",
            str(shallow),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return shallow


@pytest.fixture
def tricky_message_repo(tmp_path: Path) -> Path:
    """One commit whose body contains the unit separator and newlines.

    Guards trap 1: a naive delimiter would split this into two records.
    """
    repo = tmp_path / "tricky_repo"
    repo.mkdir()
    _run(repo, "init", "-q", "-b", "main")
    _run(repo, "config", "user.name", "Author One")
    _run(repo, "config", "user.email", "one@example.invalid")
    (repo / "f.txt").write_text("x\n")
    _run(repo, "add", "f.txt")
    body = "line one\n\nline two with \x1f a unit separator\nline three"
    _run(repo, "commit", "-q", "-m", "tricky subject", "-m", body, when=D1)
    return repo
