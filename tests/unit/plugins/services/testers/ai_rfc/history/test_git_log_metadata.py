from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.history.git_log import (
    ShallowRepositoryError,
    assert_complete,
    extract_commits,
)

pytestmark = pytest.mark.unit


def test_reads_every_commit(corpus_repo: Path):
    assert len(extract_commits(corpus_repo)) == 4


def test_commits_are_sorted_by_time_then_sha(corpus_repo: Path):
    commits = extract_commits(corpus_repo)
    keys = [(c.authored_at, c.sha) for c in commits]
    assert keys == sorted(keys)


def test_shared_timestamps_are_broken_by_sha(corpus_repo: Path):
    """Two commits share authored_at; order must still be total and stable.

    Groups by whatever git rendered rather than comparing to a literal: git
    renders a UTC ``%aI`` as ``…Z``, not ``+00:00``, and the exact spelling has
    changed across versions. The property under test is the tiebreak, not the
    timezone format.
    """
    commits = extract_commits(corpus_repo)
    by_stamp: dict[str, list[str]] = {}
    for commit in commits:
        by_stamp.setdefault(commit.authored_at, []).append(commit.sha)

    shared = [shas for shas in by_stamp.values() if len(shas) > 1]
    assert len(shared) == 1, "fixture must contain exactly one shared timestamp"
    assert shared[0] == sorted(shared[0])
    assert [c.sha for c in extract_commits(corpus_repo)] == [c.sha for c in commits]


def test_captures_both_authors(corpus_repo: Path):
    emails = {c.author_email for c in extract_commits(corpus_repo)}
    assert emails == {"one@example.invalid", "two@example.invalid"}


def test_subject_and_body_are_separated(corpus_repo: Path):
    first = next(c for c in extract_commits(corpus_repo) if c.subject == "first")
    assert first.body == "a body line"


def test_parents_are_recorded(corpus_repo: Path):
    commits = extract_commits(corpus_repo)
    roots = [c for c in commits if not c.parents]
    assert len(roots) == 1
    assert all(len(c.parents) == 1 for c in commits if c.parents)


def test_body_containing_the_unit_separator_does_not_split_the_record(
    tricky_message_repo: Path,
):
    """Trap 1: a body carrying the delimiter must stay one commit."""
    commits = extract_commits(tricky_message_repo)
    assert len(commits) == 1
    assert commits[0].subject == "tricky subject"
    assert "unit separator" in commits[0].body


def test_shallow_clone_is_refused(shallow_repo: Path):
    with pytest.raises(ShallowRepositoryError) as excinfo:
        extract_commits(shallow_repo)
    assert "shallow" in str(excinfo.value).lower()


def test_the_shallow_remedy_does_not_assume_network_access(shallow_repo: Path):
    """An operator working from a bundle cannot run git fetch --unshallow.

    The remedy text is the only thing that reaches them at this point, so it
    has to name a route that needs no credentials and no reachable remote.
    """
    with pytest.raises(ShallowRepositoryError) as excinfo:
        assert_complete(shallow_repo)
    assert "bundle" in str(excinfo.value)


def test_assert_complete_passes_on_a_full_clone(corpus_repo: Path):
    assert assert_complete(corpus_repo) is None
