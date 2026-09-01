import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline import cli
from panther.plugins.services.testers.ai_rfc.pipeline.substrate import check

pytestmark = pytest.mark.unit


def _clone(source: Path, dest: Path, *flags: str) -> Path:
    subprocess.run(
        ["git", "clone", *flags, f"file://{source}", str(dest)],
        check=True,
        capture_output=True,
    )
    return dest


def test_a_healthy_clone_reports_nothing(workspace: Path):
    assert check(workspace / "clone") == []


def test_a_shallow_clone_is_named(workspace: Path, tmp_path: Path):
    """A truncated history must be refused rather than silently believed.

    ``git log`` on a shallow clone returns fewer commits with no error at all,
    so every aggregate computed from it is quietly wrong.
    """
    shallow = _clone(workspace / "clone", tmp_path / "shallow", "--depth", "1")
    problems = check(shallow)
    assert any("shallow" in p for p in problems)


def test_the_shallow_remedy_works_without_a_remote(workspace: Path, tmp_path: Path):
    """Whoever hits this may have no network, so --unshallow is not an answer."""
    shallow = _clone(workspace / "clone", tmp_path / "shallow", "--depth", "1")
    assert any("bundle" in p for p in check(shallow))


def test_a_bare_clone_is_named(workspace: Path, tmp_path: Path):
    """A bare repository must be named here rather than two stages apart.

    ``state.py`` requires ``clone/.git`` and ``workspace.py`` runs
    ``git status``, so a bare repository otherwise fails twice, far apart.
    """
    bare = _clone(workspace / "clone", tmp_path / "bare.git", "--bare")
    assert any("bare" in p for p in check(bare))


def test_a_missing_path_is_named(tmp_path: Path):
    assert any("does not exist" in p for p in check(tmp_path / "nope"))


def test_a_directory_that_is_not_a_repository_is_named(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert any("not a git repository" in p for p in check(plain))


def test_the_verb_exits_one_when_the_clone_cannot_carry_a_reconstruction(
    tmp_path: Path, capsys
):
    """Exit 2 belongs to argparse alone, so a found problem is 1."""
    assert cli.main(["substrate", str(tmp_path / "empty-workspace")]) == 1
    assert "error" in capsys.readouterr().err


def test_the_verb_exits_zero_on_a_healthy_workspace(workspace: Path):
    assert cli.main(["substrate", str(workspace)]) == 0
