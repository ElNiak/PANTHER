from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.history.aggregates import history_shape
from panther.plugins.services.testers.ai_rfc.history.git_log import extract

pytestmark = pytest.mark.unit


@pytest.fixture
def commits(corpus_repo: Path):
    extracted, _, _ = extract(corpus_repo, cap=1000)
    return extracted


def test_counts_commits(commits):
    assert history_shape(commits).commit_count == 4


def test_counts_merges(commits):
    assert history_shape(commits).merge_count == 0


def test_reports_the_span(commits):
    shape = history_shape(commits)
    stamps = sorted(commit.authored_at for commit in commits)
    assert shape.first_authored == stamps[0]
    assert shape.last_authored == stamps[-1]
    assert shape.first_authored < shape.last_authored
    # Pin the dates without pinning git's timezone rendering: a UTC %aI comes
    # back as "…Z", not "+00:00", and that spelling varies across versions.
    assert shape.first_authored.startswith("2026-01")
    assert shape.last_authored.startswith("2026-03")


def test_groups_by_year(commits):
    assert history_shape(commits).commits_by_year == {"2026": 4}


def test_empty_history_raises_rather_than_returning_zeros():
    """An empty corpus is a fetch failure wearing a disguise."""
    with pytest.raises(ValueError) as excinfo:
        history_shape([])
    assert "empty" in str(excinfo.value).lower()
