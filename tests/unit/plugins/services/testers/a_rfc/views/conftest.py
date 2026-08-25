import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.history import cli as history_cli
from panther.plugins.services.testers.a_rfc.timeline import cli as timeline_cli


def _run(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture
def pipeline(tmp_path: Path) -> dict[str, Path]:
    """A real repo with one merge, its extracted corpus and its timeline."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(repo, "init", "-b", "main")
    _run(repo, "config", "user.email", "t@t")
    _run(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("one\n")
    _run(repo, "add", "a.txt")
    _run(repo, "commit", "-m", "root")
    _run(repo, "checkout", "-b", "feat")
    (repo / "b.txt").write_text("two\n")
    _run(repo, "add", "b.txt")
    _run(repo, "commit", "-m", "feat work")
    _run(repo, "checkout", "main")
    (repo / "c.txt").write_text("three\n")
    _run(repo, "add", "c.txt")
    _run(repo, "commit", "-m", "direct push")
    _run(repo, "merge", "--no-ff", "feat", "-m", "Merge branch 'feat'")
    corpus = tmp_path / "corpus"
    assert history_cli.main([str(repo), "--out", str(corpus), "--no-index"]) == 0
    timeline = tmp_path / "timeline"
    assert timeline_cli.main([str(corpus), "--out", str(timeline)]) == 0
    return {"repo": repo, "corpus": corpus, "timeline": timeline}
