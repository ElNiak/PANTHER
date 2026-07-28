from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.anchors import (
    AnchorError,
    UnknownCommitError,
    verify,
)
from panther.plugins.services.testers.a_rfc.models import Anchor, EvidenceClass

pytestmark = pytest.mark.unit

ABSENT_SHA = "0" * 40


def _head(repo: Path) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_path_present_at_its_pinned_commit_verifies(fixture_repo: Path):
    anchor = Anchor(EvidenceClass.CODE, "first.txt", commit=_head(fixture_repo))
    assert verify(anchor, fixture_repo) is True


def test_path_absent_at_its_pinned_commit_returns_false(fixture_repo: Path):
    first_sha = (fixture_repo / "FIRST_SHA").read_text().strip()
    anchor = Anchor(EvidenceClass.CODE, "second.txt", commit=first_sha)
    assert verify(anchor, fixture_repo) is False


def test_anchor_without_a_commit_is_refused(fixture_repo: Path):
    anchor = Anchor(EvidenceClass.CODE, "first.txt")
    with pytest.raises(AnchorError) as excinfo:
        verify(anchor, fixture_repo)
    assert "commit" in str(excinfo.value)


def test_unknown_commit_is_distinguishable_from_a_missing_path(fixture_repo: Path):
    anchor = Anchor(EvidenceClass.CODE, "first.txt", commit=ABSENT_SHA)
    with pytest.raises(UnknownCommitError):
        verify(anchor, fixture_repo)


def test_unknown_commit_error_is_an_anchor_error(fixture_repo: Path):
    anchor = Anchor(EvidenceClass.CODE, "first.txt", commit=ABSENT_SHA)
    with pytest.raises(AnchorError):
        verify(anchor, fixture_repo)


def test_non_repository_evidence_is_not_verifiable_here(fixture_repo: Path):
    anchor = Anchor(EvidenceClass.PAPER, "10.1000/xyz")
    with pytest.raises(AnchorError) as excinfo:
        verify(anchor, fixture_repo)
    assert "paper" in str(excinfo.value)
