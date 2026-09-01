import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.timeline.corpus import (
    TimelineError,
    find_tip,
    read_commits,
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


def _corpus(tmp_path: Path, records: list[str]) -> Path:
    (tmp_path / "commits.jsonl").write_text("\n".join(records) + "\n")
    return tmp_path


def test_reads_commits_with_parents(tmp_path: Path):
    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    commits = read_commits(corpus)
    assert [commit.sha for commit in commits] == ["aa", "bb"]
    assert commits[1].parents == ("aa",)
    assert commits[0].is_merge is False


def test_missing_field_is_named_with_its_line(tmp_path: Path):
    broken = json.loads(_record("aa", []))
    del broken["parents"]
    corpus = _corpus(tmp_path, [json.dumps(broken, sort_keys=True)])
    with pytest.raises(TimelineError) as excinfo:
        read_commits(corpus)
    assert "parents" in str(excinfo.value)
    assert ":1" in str(excinfo.value)


def test_empty_corpus_is_refused(tmp_path: Path):
    (tmp_path / "commits.jsonl").write_text("")
    with pytest.raises(TimelineError):
        read_commits(tmp_path)


def test_tip_is_the_commit_no_one_parents(tmp_path: Path):
    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    assert find_tip(read_commits(corpus)) == "bb"


def test_two_tips_are_refused(tmp_path: Path):
    corpus = _corpus(
        tmp_path,
        [_record("aa", []), _record("bb", ["aa"]), _record("cc", ["aa"])],
    )
    with pytest.raises(TimelineError) as excinfo:
        find_tip(read_commits(corpus))
    assert "tip" in str(excinfo.value)
