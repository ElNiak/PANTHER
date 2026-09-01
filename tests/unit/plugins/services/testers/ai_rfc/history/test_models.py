import dataclasses

import pytest

from panther.plugins.services.testers.ai_rfc.history.models import (
    Commit,
    ExtractionReport,
    FileChange,
)

pytestmark = pytest.mark.unit

SHA = "a" * 40


def _commit(**overrides) -> Commit:
    base = dict(
        sha=SHA,
        parents=(),
        author_name="Author One",
        author_email="one@example.invalid",
        authored_at="2026-01-01T00:00:00+00:00",
        committed_at="2026-01-01T00:00:00+00:00",
        subject="a subject",
        body="",
    )
    base.update(overrides)
    return Commit(**base)


def test_records_are_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _commit().sha = "b" * 40


def test_is_merge_is_derived_from_parent_count():
    assert _commit(parents=()).is_merge is False
    assert _commit(parents=("b" * 40,)).is_merge is False
    assert _commit(parents=("b" * 40, "c" * 40)).is_merge is True


def test_file_counts_default_to_zero_and_untruncated():
    commit = _commit()
    assert commit.file_count == 0
    assert commit.files_recorded == 0
    assert commit.files_truncated is False


def test_file_change_defaults_previous_path_to_none():
    change = FileChange(sha=SHA, path="src/a.py", status="M")
    assert change.previous_path is None


def test_file_change_carries_a_rename_source():
    change = FileChange(
        sha=SHA, path="src/new.py", status="R", previous_path="src/old.py"
    )
    assert change.previous_path == "src/old.py"
    assert change.path == "src/new.py"


def test_report_counts_truncated_commits():
    report = ExtractionReport(
        commit_count=3, file_row_count=7, truncated=(SHA, "b" * 40)
    )
    assert report.truncated_count == 2


def test_report_with_no_truncation_reports_zero():
    assert (
        ExtractionReport(commit_count=1, file_row_count=1, truncated=()).truncated_count
        == 0
    )
