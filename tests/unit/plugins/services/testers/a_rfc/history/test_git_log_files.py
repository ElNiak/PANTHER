from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.history.git_log import (
    extract,
    read_commits,
    read_file_changes,
)

pytestmark = pytest.mark.unit


def _by_subject(repo: Path, subject: str) -> str:
    return next(c.sha for c in read_commits(repo) if c.subject == subject)


def test_records_added_paths(corpus_repo: Path):
    changes, _ = read_file_changes(corpus_repo)
    first = changes[_by_subject(corpus_repo, "first")]
    assert {c.path for c in first} == {"src/a.txt", "src/b.txt"}
    assert {c.status for c in first} == {"A"}


def test_rename_keeps_the_new_path_and_records_the_old(corpus_repo: Path):
    """Trap 2: a two-field parser would store the source as the changed file."""
    changes, _ = read_file_changes(corpus_repo)
    renamed = changes[_by_subject(corpus_repo, "rename a")]
    assert len(renamed) == 1
    change = renamed[0]
    assert change.status == "R"
    assert change.path == "src/renamed.txt"
    assert change.previous_path == "src/a.txt"


def test_status_letters_have_similarity_scores_stripped(corpus_repo: Path):
    changes, _ = read_file_changes(corpus_repo)
    for rows in changes.values():
        for change in rows:
            assert len(change.status) == 1
            assert change.status.isalpha()


def test_deletion_is_recorded(corpus_repo: Path):
    changes, _ = read_file_changes(corpus_repo)
    dropped = changes[_by_subject(corpus_repo, "drop b")]
    assert [(c.status, c.path) for c in dropped] == [("D", "src/b.txt")]


def test_cap_limits_rows_but_not_the_true_count(corpus_repo: Path):
    changes, totals = read_file_changes(corpus_repo, cap=2)
    bulk_sha = _by_subject(corpus_repo, "bulk add")
    assert totals[bulk_sha] == 5
    assert len(changes[bulk_sha]) == 2


def test_uncapped_extraction_records_everything(corpus_repo: Path):
    changes, totals = read_file_changes(corpus_repo, cap=1000)
    bulk_sha = _by_subject(corpus_repo, "bulk add")
    assert totals[bulk_sha] == 5
    assert len(changes[bulk_sha]) == 5


def test_extract_marks_truncated_commits(corpus_repo: Path):
    commits, changes, report = extract(corpus_repo, cap=2)
    bulk = next(c for c in commits if c.subject == "bulk add")
    assert bulk.file_count == 5
    assert bulk.files_recorded == 2
    assert bulk.files_truncated is True
    assert bulk.sha in report.truncated
    assert report.truncated_count == 1


def test_extract_leaves_small_commits_untruncated(corpus_repo: Path):
    commits, _, report = extract(corpus_repo, cap=1000)
    assert all(not c.files_truncated for c in commits)
    assert report.truncated == ()


def test_extract_report_counts_match_the_data(corpus_repo: Path):
    commits, changes, report = extract(corpus_repo, cap=1000)
    assert report.commit_count == len(commits)
    assert report.file_row_count == len(changes)


def test_extract_file_rows_are_sorted(corpus_repo: Path):
    _, changes, _ = extract(corpus_repo, cap=1000)
    keys = [(c.sha, c.path) for c in changes]
    assert keys == sorted(keys)
