import json
import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.timeline import cli

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
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "commits.jsonl").write_text("\n".join(records) + "\n")
    (corpus_dir / "files.jsonl").write_text("")
    return corpus_dir


def test_writes_timeline_and_reports_summary(tmp_path: Path, capsys):
    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    out = tmp_path / "timeline"
    assert cli.main([str(corpus), "--out", str(out)]) == 0
    assert (out / "timeline.json").exists()
    summary = capsys.readouterr().err
    assert "1 cluster" in summary or "clusters" in summary


def test_unclusterable_corpus_exits_one_with_reason(tmp_path: Path, capsys):
    corpus = _corpus(
        tmp_path,
        [_record("aa", []), _record("bb", ["aa"]), _record("cc", ["aa"])],
    )
    assert cli.main([str(corpus), "--out", str(tmp_path / "out")]) == 1
    assert "tip" in capsys.readouterr().err


def test_repo_head_mismatch_exits_one_naming_both(tmp_path: Path, capsys):
    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "--allow-empty", "-m", "root"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    assert (
        cli.main([str(corpus), "--repo", str(repo), "--out", str(tmp_path / "o")]) == 1
    )
    err = capsys.readouterr().err
    assert "bb" in err
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head in err
