from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.history.git_log import extract
from panther.plugins.services.testers.a_rfc.history.index import (
    INDEX_FILE,
    StaleIndexError,
    build_index,
    open_index,
)
from panther.plugins.services.testers.a_rfc.history.store import (
    COMMITS_FILE,
    write_corpus,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def corpus_dir(corpus_repo: Path, tmp_path: Path) -> Path:
    out = tmp_path / "corpus"
    commits, changes, report = extract(corpus_repo, cap=1000)
    write_corpus(commits, changes, report, out)
    return out


def test_build_creates_the_index(corpus_dir: Path):
    assert build_index(corpus_dir) == corpus_dir / INDEX_FILE
    assert (corpus_dir / INDEX_FILE).exists()


def test_index_row_counts_match_the_corpus(corpus_dir: Path):
    build_index(corpus_dir)
    with open_index(corpus_dir) as conn:
        commits = conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        rows = conn.execute("SELECT COUNT(*) FROM file_changes").fetchone()[0]
    assert commits == 4
    assert rows == 9


def test_index_answers_which_commits_touched_a_path(corpus_dir: Path):
    build_index(corpus_dir)
    with open_index(corpus_dir) as conn:
        found = conn.execute(
            "SELECT status FROM file_changes WHERE path = ?", ("src/renamed.txt",)
        ).fetchall()
    assert found == [("R",)]


def test_stale_index_is_refused(corpus_dir: Path):
    build_index(corpus_dir)
    (corpus_dir / COMMITS_FILE).write_text("")
    with pytest.raises(StaleIndexError) as excinfo:
        open_index(corpus_dir)
    assert "rebuild" in str(excinfo.value).lower()


def test_rebuilding_clears_staleness(corpus_dir: Path):
    build_index(corpus_dir)
    (corpus_dir / COMMITS_FILE).write_text("")
    build_index(corpus_dir)
    with open_index(corpus_dir) as conn:
        assert conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0] == 0


def test_opening_a_missing_index_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        open_index(tmp_path)
