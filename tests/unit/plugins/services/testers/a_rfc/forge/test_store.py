import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.forge.store import (
    ForgeError,
    read_snapshot,
    write_snapshot,
)

pytestmark = pytest.mark.unit


def _pull(number: int) -> dict:
    return {
        "number": number,
        "title": f"pull {number}",
        "body": "",
        "state": "merged",
        "author": "dev",
        "created_at": "2026-01-01T00:00:00Z",
        "merged_at": "2026-01-02T00:00:00Z",
        "merge_commit_sha": "a" * 40,
        "squash_commit_sha": None,
        "head_sha": "b" * 40,
        "base_ref": "main",
        "url": f"https://example/pulls/{number}",
        "labels": [],
    }


def _comment(pr_number: int, comment_id: int, kind: str = "issue_comment") -> dict:
    return {
        "pr_number": pr_number,
        "id": comment_id,
        "kind": kind,
        "author": "dev",
        "created_at": "2026-01-03T00:00:00Z",
        "body": "looks good",
        "path": None,
        "line": None,
    }


def _write(out: Path, pulls: list, comments: list | None = None) -> Path:
    return write_snapshot(
        out,
        host="github.com",
        owner="aiortc",
        repo="aioquic",
        kind="github",
        clone_head="c" * 40,
        fetched_at="2026-08-25T10-00-00Z",
        authenticated=True,
        pulls=pulls,
        reviews=[],
        comments=comments or [],
    )


def test_writes_four_sorted_files(tmp_path: Path):
    snapshot = _write(tmp_path, [_pull(7), _pull(3)], [_comment(7, 2), _comment(3, 1)])
    assert snapshot == (
        tmp_path / "github.com__aiortc__aioquic" / "snapshot-2026-08-25T10-00-00Z"
    )
    pulls = [
        json.loads(line) for line in (snapshot / "pulls.jsonl").read_text().splitlines()
    ]
    assert [pull["number"] for pull in pulls] == [3, 7]
    comments = [
        json.loads(line)
        for line in (snapshot / "comments.jsonl").read_text().splitlines()
    ]
    assert [comment["pr_number"] for comment in comments] == [3, 7]
    meta = json.loads((snapshot / "meta.json").read_text())
    assert meta["complete"] is True
    assert meta["authenticated"] is True
    assert meta["clone_head"] == "c" * 40
    assert meta["kind"] == "github"
    assert "token" not in (snapshot / "meta.json").read_text().lower()


def test_permuted_input_is_byte_identical(tmp_path: Path):
    first = _write(tmp_path / "one", [_pull(7), _pull(3)], [_comment(7, 2)])
    second = _write(tmp_path / "two", [_pull(3), _pull(7)], [_comment(7, 2)])
    for name in ("pulls.jsonl", "reviews.jsonl", "comments.jsonl", "meta.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_existing_snapshot_is_refused(tmp_path: Path):
    _write(tmp_path, [_pull(1)])
    with pytest.raises(ForgeError) as excinfo:
        _write(tmp_path, [_pull(1)])
    assert "snapshot" in str(excinfo.value)


def test_unknown_comment_kind_is_refused(tmp_path: Path):
    with pytest.raises(ForgeError) as excinfo:
        _write(tmp_path, [_pull(1)], [_comment(1, 1, kind="reaction")])
    assert "reaction" in str(excinfo.value)


def test_read_snapshot_round_trips(tmp_path: Path):
    snapshot = _write(tmp_path, [_pull(3), _pull(7)], [_comment(3, 1)])
    data = read_snapshot(snapshot)
    assert [pull["number"] for pull in data["pulls"]] == [3, 7]
    assert data["meta"]["owner"] == "aiortc"
    assert len(data["comments"]) == 1
    assert data["reviews"] == []
