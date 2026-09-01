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


def test_a_plain_directory_inside_a_repository_is_not_mistaken_for_a_clone(
    workspace: Path,
):
    """``git rev-parse`` answers for the nearest enclosing repository.

    A clone that was never made is the likeliest substrate error, and the
    workspace usually sits inside some other checkout — so a check that asks
    git without bounding the answer calls the empty directory healthy and
    leaves ``_pin`` to catch it a stage later, which is what this verb exists
    to prevent.
    """
    nested = workspace / "clone" / "never-cloned"
    nested.mkdir()
    assert any("not a git repository" in p for p in check(nested))


def test_a_shallow_enclosing_repository_is_not_reported_as_the_clone(
    workspace: Path, tmp_path: Path
):
    """Answering from an ancestor also invents problems, not just hides them."""
    truncated = _clone(workspace / "clone", tmp_path / "enclosing", "--depth", "1")
    nested = truncated / "never-cloned"
    nested.mkdir()
    problems = check(nested)
    assert any("not a git repository" in p for p in problems)
    assert not any("is shallow" in p for p in problems)


def test_the_verb_exits_one_when_the_clone_cannot_carry_a_reconstruction(
    tmp_path: Path, capsys
):
    """Exit 2 belongs to argparse alone, so a found problem is 1."""
    assert cli.main(["substrate", str(tmp_path / "empty-workspace")]) == 1
    assert "error" in capsys.readouterr().err


def test_the_verb_exits_zero_on_a_healthy_workspace(workspace: Path):
    assert cli.main(["substrate", str(workspace)]) == 0
