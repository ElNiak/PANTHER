import hashlib
import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.timeline.build import build_timeline
from panther.plugins.services.testers.a_rfc.timeline.corpus import (
    find_tip,
    read_commits,
)
from panther.plugins.services.testers.a_rfc.timeline.store import (
    read_clusters,
    read_timeline,
    write_timeline,
)

pytestmark = pytest.mark.unit


def _record(sha: str, parents: list[str]) -> str:
    return json.dumps(
        {
            "sha": sha,
            "parents": parents,
            "author_name": "a",
            "author_email": "a@a",
            "authored_at": "2026-01-01T00:00:00+00:00",
            "committed_at": "2026-01-01T00:00:00+00:00",
            "subject": f"s {sha}",
            "body": "",
            "is_merge": len(parents) > 1,
            "file_count": 1,
            "files_recorded": 1,
            "files_truncated": False,
        },
        sort_keys=True,
    )


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    records = [
        _record("aa", []),
        _record("ff", ["aa"]),
        _record("dd", ["aa"]),
        _record("mm", ["dd", "ff"]),
    ]
    (corpus_dir / "commits.jsonl").write_text("\n".join(records) + "\n")
    (corpus_dir / "files.jsonl").write_text(
        json.dumps(
            {"path": "a.txt", "previous_path": None, "sha": "ff", "status": "A"},
            sort_keys=True,
        )
        + "\n"
    )
    return corpus_dir


def _build_and_write(corpus: Path, out: Path) -> None:
    commits = read_commits(corpus)
    write_timeline(build_timeline(commits), find_tip(commits), corpus, out)


def test_writes_three_artifacts_with_corpus_digests(corpus: Path, tmp_path: Path):
    out = tmp_path / "timeline"
    _build_and_write(corpus, out)
    assert (out / "clusters.jsonl").exists()
    assert (out / "members.jsonl").exists()
    timeline = read_timeline(out)
    assert timeline["tip_sha"] == "mm"
    assert timeline["cluster_count"] == 2
    assert timeline["pr_count"] == 1
    assert timeline["epoch_count"] == 1
    assert timeline["member_count"] == 4
    assert timeline["forge_snapshot"] is None
    for name, key in (
        ("commits.jsonl", "commits_sha256"),
        ("files.jsonl", "files_sha256"),
    ):
        expected = hashlib.sha256((corpus / name).read_bytes()).hexdigest()
        assert timeline[key] == expected


def test_two_runs_are_byte_identical(corpus: Path, tmp_path: Path):
    first, second = tmp_path / "one", tmp_path / "two"
    _build_and_write(corpus, first)
    _build_and_write(corpus, second)
    for name in ("clusters.jsonl", "members.jsonl", "timeline.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_read_clusters_round_trips_in_ordinal_order(corpus: Path, tmp_path: Path):
    out = tmp_path / "timeline"
    _build_and_write(corpus, out)
    clusters = read_clusters(out)
    assert [cluster["ordinal"] for cluster in clusters] == [1, 2]
    assert "members" not in clusters[0]
    rows = [
        json.loads(line) for line in (out / "members.jsonl").read_text().splitlines()
    ]
    assert [row["sha"] for row in rows] == ["aa", "dd", "ff", "mm"]
    assert all(row["cluster_id"] for row in rows)
