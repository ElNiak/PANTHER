from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.anchors import (
    AnchorError,
    UnknownCommitError,
    verify,
    verify_detailed,
)
from panther.plugins.services.testers.ai_rfc.models import Anchor, EvidenceClass

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


def test_line_within_file_verifies(fixture_repo: Path):
    anchor = Anchor(EvidenceClass.CODE, "first.txt", commit=_head(fixture_repo), line=1)
    assert verify_detailed(anchor, fixture_repo) is None


def test_line_beyond_end_of_file_is_named(fixture_repo: Path):
    anchor = Anchor(
        EvidenceClass.CODE, "first.txt", commit=_head(fixture_repo), line=9999
    )
    reason = verify_detailed(anchor, fixture_repo)
    assert reason is not None
    assert "9999" in reason
    assert "first.txt" in reason


def test_line_digest_mismatch_is_named(fixture_repo: Path):
    anchor = Anchor(
        EvidenceClass.CODE,
        "first.txt",
        commit=_head(fixture_repo),
        line=1,
        line_sha256="ab" * 32,
    )
    reason = verify_detailed(anchor, fixture_repo)
    assert reason is not None
    assert "digest" in reason


def test_matching_line_digest_verifies(fixture_repo: Path):
    import hashlib
    import subprocess

    head = _head(fixture_repo)
    raw = subprocess.run(
        ["git", "-C", str(fixture_repo), "show", f"{head}:first.txt"],
        capture_output=True,
        check=True,
    ).stdout
    digest = hashlib.sha256(raw.split(b"\n")[0]).hexdigest()
    anchor = Anchor(
        EvidenceClass.CODE, "first.txt", commit=head, line=1, line_sha256=digest
    )
    assert verify_detailed(anchor, fixture_repo) is None


def test_missing_path_reason_names_path_and_commit(fixture_repo: Path):
    first_sha = (fixture_repo / "FIRST_SHA").read_text().strip()
    anchor = Anchor(EvidenceClass.CODE, "second.txt", commit=first_sha)
    reason = verify_detailed(anchor, fixture_repo)
    assert reason is not None
    assert "second.txt" in reason
    assert first_sha in reason


def test_verify_still_reports_line_failures_as_false(fixture_repo: Path):
    anchor = Anchor(
        EvidenceClass.CODE, "first.txt", commit=_head(fixture_repo), line=9999
    )
    assert verify(anchor, fixture_repo) is False
