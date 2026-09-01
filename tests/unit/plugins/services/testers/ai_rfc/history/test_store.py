import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.history.git_log import extract
from panther.plugins.services.testers.ai_rfc.history.store import (
    COMMITS_FILE,
    FILES_FILE,
    REPORT_FILE,
    read_corpus,
    write_corpus,
)

pytestmark = pytest.mark.unit


def _write(repo: Path, out: Path, cap: int = 1000):
    commits, changes, report = extract(repo, cap=cap)
    write_corpus(commits, changes, report, out)
    return commits, changes, report


def test_writes_all_three_artifacts(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    _write(corpus_repo, out)
    assert (out / COMMITS_FILE).exists()
    assert (out / FILES_FILE).exists()
    assert (out / REPORT_FILE).exists()


def test_round_trips(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    commits, changes, _ = _write(corpus_repo, out)
    assert read_corpus(out) == (commits, changes)


def test_output_is_byte_stable(corpus_repo: Path, tmp_path: Path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    _write(corpus_repo, first)
    _write(corpus_repo, second)
    assert (first / COMMITS_FILE).read_bytes() == (second / COMMITS_FILE).read_bytes()
    assert (first / FILES_FILE).read_bytes() == (second / FILES_FILE).read_bytes()


def test_one_json_object_per_line(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    commits, _, _ = _write(corpus_repo, out)
    lines = (out / COMMITS_FILE).read_text().splitlines()
    assert len(lines) == len(commits)
    assert all(json.loads(line)["sha"] for line in lines)


def test_derived_is_merge_is_serialised(corpus_repo: Path, tmp_path: Path):
    """dataclasses.asdict drops properties; is_merge must be injected."""
    out = tmp_path / "corpus"
    _write(corpus_repo, out)
    records = [
        json.loads(line) for line in (out / COMMITS_FILE).read_text().splitlines()
    ]
    assert all("is_merge" in record for record in records)


def test_report_records_truncation(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    _write(corpus_repo, out, cap=2)
    payload = json.loads((out / REPORT_FILE).read_text())
    assert payload["truncated_count"] == 1
    assert len(payload["truncated"]) == 1


def test_keys_are_sorted_within_each_record(corpus_repo: Path, tmp_path: Path):
    out = tmp_path / "corpus"
    _write(corpus_repo, out)
    line = (out / COMMITS_FILE).read_text().splitlines()[0]
    keys = list(json.loads(line).keys())
    assert keys == sorted(keys)


def test_reading_a_missing_corpus_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_corpus(tmp_path / "absent")
