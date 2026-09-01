import json
import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.timeline import cli

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


def test_omitting_repo_is_noted_and_recorded(tmp_path: Path, capsys):
    """An unverified tip must not be indistinguishable from a verified one.

    Every other optional input says so when it is missing; this one skipped the
    corpus-tip check silently, on stderr and on disk alike.
    """
    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    out = tmp_path / "timeline"

    assert cli.main([str(corpus), "--out", str(out)]) == 0

    assert "note: --repo not given" in capsys.readouterr().err
    assert json.loads((out / "timeline.json").read_text())["tip_verified"] is False


def test_passing_repo_records_the_tip_as_verified(tmp_path: Path, capsys):
    repo = tmp_path / "clone"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "c"], check=True)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    corpus = _corpus(tmp_path, [_record(head, [])])
    out = tmp_path / "timeline-verified"

    assert cli.main([str(corpus), "--out", str(out), "--repo", str(repo)]) == 0

    assert "note: --repo not given" not in capsys.readouterr().err
    assert json.loads((out / "timeline.json").read_text())["tip_verified"] is True


def test_unclusterable_corpus_exits_one_with_reason(tmp_path: Path, capsys):
    corpus = _corpus(
        tmp_path,
        [_record("aa", []), _record("bb", ["aa"]), _record("cc", ["aa"])],
    )
    assert cli.main([str(corpus), "--out", str(tmp_path / "out")]) == 1
    assert "tip" in capsys.readouterr().err


def _snapshot(tmp_path: Path, clone_head: str, pulls: list) -> Path:
    from panther.plugins.services.testers.ai_rfc.forge.store import write_snapshot

    return write_snapshot(
        tmp_path / "forge",
        host="github.com",
        owner="o",
        repo="r",
        kind="github",
        clone_head=clone_head,
        fetched_at="2026-08-25T10-00-00Z",
        authenticated=False,
        pulls=pulls,
        reviews=[],
        comments=[],
    )


def _merged_pull(number: int, sha: str) -> dict:
    return {
        "number": number,
        "title": f"pull {number}",
        "state": "merged",
        "merged_at": "2026-01-02T00:00:00Z",
        "merge_commit_sha": sha,
        "squash_commit_sha": None,
    }


def test_forge_head_mismatch_exits_one(tmp_path: Path, capsys):
    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    snapshot = _snapshot(tmp_path, "f" * 40, [])
    code = cli.main(
        [str(corpus), "--forge", str(snapshot), "--out", str(tmp_path / "out")]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "bb" in err
    assert "f" * 40 in err


def test_forge_rescue_recorded_and_reported(tmp_path: Path, capsys):
    import json as json_module

    corpus = _corpus(tmp_path, [_record("aa", []), _record("bb", ["aa"])])
    snapshot = _snapshot(
        tmp_path, "bb", [_merged_pull(12, "bb"), _merged_pull(13, "z" * 40)]
    )
    out = tmp_path / "out"
    assert cli.main([str(corpus), "--forge", str(snapshot), "--out", str(out)]) == 0
    timeline = json_module.loads((out / "timeline.json").read_text())
    assert timeline["forge_snapshot"]["dir_name"].endswith(
        "snapshot-2026-08-25T10-00-00Z"
    )
    assert len(timeline["forge_snapshot"]["meta_sha256"]) == 64
    assert timeline["pr_count"] == 1
    err = capsys.readouterr().err
    assert "1 squash-rescued" in err
    assert "1 of 2 merged pull(s) unmatched" in err
    assert "13" in err


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
