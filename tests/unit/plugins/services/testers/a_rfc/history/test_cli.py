import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.history.cli import main
from panther.plugins.services.testers.a_rfc.history.index import INDEX_FILE
from panther.plugins.services.testers.a_rfc.history.store import (
    COMMITS_FILE,
    FILES_FILE,
    REPORT_FILE,
)

pytestmark = pytest.mark.unit


def test_extracts_and_indexes(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    assert main([str(corpus_repo), "--out", str(out)]) == 0
    assert (out / COMMITS_FILE).exists()
    assert (out / FILES_FILE).exists()
    assert (out / REPORT_FILE).exists()
    assert (out / INDEX_FILE).exists()


def test_no_index_flag_skips_the_index(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    assert main([str(corpus_repo), "--out", str(out), "--no-index"]) == 0
    assert (out / COMMITS_FILE).exists()
    assert not (out / INDEX_FILE).exists()


def test_shallow_repository_returns_one_and_says_why(
    shallow_repo: Path, tmp_path: Path, capsys
):
    assert main([str(shallow_repo), "--out", str(tmp_path / "corpus")]) == 1
    assert "shallow" in capsys.readouterr().err.lower()


def test_missing_repository_returns_one(tmp_path: Path):
    assert main([str(tmp_path / "absent"), "--out", str(tmp_path / "corpus")]) == 1


def test_truncation_is_reported_on_stderr(corpus_repo: Path, tmp_path: Path, capsys):
    """Trap 3: a cap that is not announced makes a huge commit look small."""
    code = main([str(corpus_repo), "--out", str(tmp_path / "corpus"), "--cap", "2"])
    assert code == 0
    assert "truncated" in capsys.readouterr().err.lower()


def test_no_truncation_message_when_nothing_is_capped(
    corpus_repo: Path, tmp_path: Path, capsys
):
    main([str(corpus_repo), "--out", str(tmp_path / "corpus"), "--cap", "1000"])
    assert "truncated" not in capsys.readouterr().err.lower()


def test_cap_is_recorded_in_the_report(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    main([str(corpus_repo), "--out", str(out), "--cap", "2"])
    payload = json.loads((out / REPORT_FILE).read_text())
    assert payload["truncated_count"] == 1
