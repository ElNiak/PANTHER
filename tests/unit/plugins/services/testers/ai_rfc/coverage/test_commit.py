"""The refusal that binds a coverage report to one checkout.

``require_clean_checkout`` is the only thing standing between a report and an
anchor that cites a commit it does not describe, and every one of its branches
is a refusal — so a regression here does not fail loudly, it silently promotes
claims on evidence from some other tree.
"""

import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.coverage.commit import (
    PinError,
    require_clean_checkout,
)

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_a_clean_tree_at_the_commit_is_accepted(java_repo):
    repo, head = java_repo
    assert require_clean_checkout(repo, head) is None


def test_a_directory_that_is_not_a_repository_is_refused(tmp_path):
    with pytest.raises(PinError) as excinfo:
        require_clean_checkout(tmp_path / "not-a-clone", "HEAD")
    assert "not a git repository" in str(excinfo.value)


def test_a_name_that_does_not_resolve_is_refused(java_repo):
    repo, _ = java_repo
    with pytest.raises(PinError) as excinfo:
        require_clean_checkout(repo, "no-such-ref")
    assert "is not a commit" in str(excinfo.value)


def test_a_well_formed_sha_no_object_matches_is_still_refused(java_repo):
    """The safety property holds even though the diagnostic misses.

    ``git rev-parse`` exits 0 for any 40-hex string, echoing it back without
    checking an object exists, so a fabricated or mistyped commit never reaches
    the "is not a commit" branch — it falls through to the HEAD comparison and
    is refused as a different checkout. The refusal is what matters and it
    holds; the message names the wrong reason, which is worth knowing when
    reading one in anger.
    """
    repo, _ = java_repo
    with pytest.raises(PinError) as excinfo:
        require_clean_checkout(repo, "0" * 40)
    assert "different checkout" in str(excinfo.value)


def test_a_head_that_moved_past_the_commit_is_refused(java_repo):
    repo, first = java_repo
    (repo / "later.txt").write_text("added after the coverage run\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "second")

    with pytest.raises(PinError) as excinfo:
        require_clean_checkout(repo, first)
    assert "different checkout" in str(excinfo.value)


def test_an_uncommitted_edit_is_refused(java_repo):
    repo, head = java_repo
    source = repo / "server/src/main/java/be/cylab/mark/detection/OWAverage.java"
    source.write_text(source.read_text() + "// edited after the run\n")

    with pytest.raises(PinError) as excinfo:
        require_clean_checkout(repo, head)
    assert "uncommitted changes" in str(excinfo.value)


def test_an_untracked_file_counts_as_dirty(java_repo):
    """``--porcelain`` reports untracked paths, and the refusal must honour it.

    A build that leaves an artifact beside the source is the ordinary way a
    tree goes dirty without any tracked file changing.
    """
    repo, head = java_repo
    (repo / "target-classes.tmp").write_text("build output\n")

    with pytest.raises(PinError) as excinfo:
        require_clean_checkout(repo, head)
    assert "uncommitted changes" in str(excinfo.value)
