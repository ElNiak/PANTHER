import subprocess
from pathlib import Path

import pytest


def _run(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace root holding only a pinned clone, as stage 0 leaves it.

    The clone is a real repository with one merge, so the timeline stage has
    both a PR cluster and an epoch cluster to find — the same shape the views
    fixture builds, because the pipeline's job is to reproduce by chaining what
    those stages already do when driven by hand.
    """
    root = tmp_path / "ws"
    clone = root / "clone"
    clone.mkdir(parents=True)
    _run(clone, "init", "-b", "main")
    _run(clone, "config", "user.email", "t@t")
    _run(clone, "config", "user.name", "t")
    (clone / "a.txt").write_text("one\n")
    _run(clone, "add", "a.txt")
    _run(clone, "commit", "-m", "root")
    _run(clone, "checkout", "-b", "feat")
    (clone / "b.txt").write_text("two\n")
    _run(clone, "add", "b.txt")
    _run(clone, "commit", "-m", "feat work")
    _run(clone, "checkout", "main")
    (clone / "c.txt").write_text("three\n")
    _run(clone, "add", "c.txt")
    _run(clone, "commit", "-m", "direct push")
    _run(clone, "merge", "--no-ff", "feat", "-m", "Merge branch 'feat'")
    return root
