import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline import cli


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


@pytest.fixture
def mined_workspace(workspace: Path) -> Path:
    """A workspace carrying a manifest whose stored status its evidence denies.

    `check` is re-derivable and so never `DONE`; the point of this fixture is a
    workspace where the walk stops at an agent boundary while a manifest sits on
    disk overstating a claim. If `check` does not run, nothing notices.
    """
    assert cli.main(["run", str(workspace)]) == 0
    (workspace / "manifest.yaml").write_text(
        "rfc: T\ntitle: 'Fixture'\nrequirements:\n"
        "  't:1':\n"
        "    text: 'A claim.'\n"
        "    section: '1'\n"
        "    level: MUST\n"
        "    layer: transport\n"
        "    status: confirmed\n"
        "    anchors:\n"
        "      - evidence_class: adr\n"
        "        locator: 'doc:fixture'\n"
    )
    return workspace
