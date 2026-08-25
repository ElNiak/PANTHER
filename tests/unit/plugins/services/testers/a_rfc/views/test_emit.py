import hashlib
import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.views.emit import ViewsError, emit_views

pytestmark = pytest.mark.unit


def _emit(pipeline: dict[str, Path], out: Path, **kwargs) -> tuple[str, ...]:
    return emit_views(
        pipeline["timeline"], pipeline["corpus"], pipeline["repo"], out, **kwargs
    )


def test_emits_one_folder_per_cluster_with_span_diff(pipeline, tmp_path: Path):
    out = tmp_path / "clusters"
    ids = _emit(pipeline, out)
    assert len(ids) == 2
    assert all((out / cluster_id / "span.diff").exists() for cluster_id in ids)
    pr_id = [cluster_id for cluster_id in ids if "-pr-" in cluster_id][0]
    view = json.loads((out / pr_id / "view.json").read_text())
    assert [entry["path"] for entry in view["file_set"]] == ["b.txt"]
    diff = (out / pr_id / "span.diff").read_text()
    assert "b/b.txt" in diff
    assert "+two" in diff


def test_merge_cluster_file_set_is_union_over_members(pipeline, tmp_path: Path):
    ids = _emit(pipeline, tmp_path / "clusters")
    pr_id = [cluster_id for cluster_id in ids if "-pr-" in cluster_id][0]
    view = json.loads((tmp_path / "clusters" / pr_id / "view.json").read_text())
    assert view["file_set"], "trap 7: merge commits have zero file rows of their own"
    assert view["files_complete"] is True


def test_root_epoch_diffs_against_the_empty_tree(pipeline, tmp_path: Path):
    ids = _emit(pipeline, tmp_path / "clusters")
    epoch_id = [cluster_id for cluster_id in ids if "-epoch-" in cluster_id][0]
    diff = (tmp_path / "clusters" / epoch_id / "span.diff").read_text()
    assert "+one" in diff
    assert "+three" in diff


def test_patch_digest_matches_bytes(pipeline, tmp_path: Path):
    out = tmp_path / "clusters"
    for cluster_id in _emit(pipeline, out):
        view = json.loads((out / cluster_id / "view.json").read_text())
        raw = (out / cluster_id / "span.diff").read_bytes()
        (patch,) = view["patches"]
        assert patch["name"] == "span.diff"
        assert patch["sha256"] == hashlib.sha256(raw).hexdigest()
        assert patch["bytes"] == len(raw)
        assert view["git_version"].startswith("git version")
        assert view["source"]["timeline_sha256"]


def test_stale_corpus_is_refused(pipeline, tmp_path: Path):
    (pipeline["corpus"] / "commits.jsonl").write_text("tampered\n")
    with pytest.raises(ViewsError) as excinfo:
        _emit(pipeline, tmp_path / "clusters")
    assert "commits.jsonl" in str(excinfo.value)


def test_moved_clone_head_is_refused(pipeline, tmp_path: Path):
    import subprocess

    subprocess.run(
        ["git", "-C", str(pipeline["repo"]), "commit", "--allow-empty", "-m", "new"],
        check=True,
        capture_output=True,
    )
    with pytest.raises(ViewsError) as excinfo:
        _emit(pipeline, tmp_path / "clusters")
    assert "tip" in str(excinfo.value)


def _forge_pipeline(pipeline: dict[str, Path], tmp_path: Path) -> Path:
    import subprocess

    from panther.plugins.services.testers.a_rfc.forge.store import write_snapshot
    from panther.plugins.services.testers.a_rfc.timeline import cli as timeline_cli

    head = subprocess.run(
        ["git", "-C", str(pipeline["repo"]), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    snapshot = write_snapshot(
        tmp_path / "forge",
        host="github.com",
        owner="o",
        repo="r",
        kind="github",
        clone_head=head,
        fetched_at="2026-08-25T10-00-00Z",
        authenticated=False,
        pulls=[
            {
                "number": 42,
                "title": "the feature",
                "body": "adds b.txt",
                "state": "merged",
                "author": "dev",
                "created_at": "2026-01-01T00:00:00Z",
                "merged_at": "2026-01-02T00:00:00Z",
                "merge_commit_sha": head,
                "squash_commit_sha": None,
                "head_sha": "0" * 40,
                "base_ref": "main",
                "url": "https://example/pull/42",
                "labels": [],
            }
        ],
        reviews=[],
        comments=[
            {
                "pr_number": 42,
                "id": 1,
                "kind": "issue_comment",
                "author": "reviewer",
                "created_at": "2026-01-01T12:00:00Z",
                "body": "nice",
                "path": None,
                "line": None,
            }
        ],
    )
    assert (
        timeline_cli.main(
            [
                str(pipeline["corpus"]),
                "--forge",
                str(snapshot),
                "--out",
                str(pipeline["timeline"]),
            ]
        )
        == 0
    )
    return snapshot


def test_member_patches_and_forge_evidence(pipeline, tmp_path: Path):
    snapshot = _forge_pipeline(pipeline, tmp_path)
    out = tmp_path / "clusters"
    ids = emit_views(
        pipeline["timeline"],
        pipeline["corpus"],
        pipeline["repo"],
        out,
        forge_snapshot=snapshot,
        patches="members",
    )
    pr_id = [cluster_id for cluster_id in ids if "-pr-" in cluster_id][0]
    view = json.loads((out / pr_id / "view.json").read_text())
    assert view["pr_number"] == 42
    member_patches = sorted((out / pr_id / "members").iterdir())
    assert len(member_patches) == 2
    names = {patch["name"] for patch in view["patches"]}
    assert "span.diff" in names
    assert any(name.startswith("members/") for name in names)
    for patch in view["patches"]:
        raw = (out / pr_id / patch["name"]).read_bytes()
        assert patch["sha256"] == hashlib.sha256(raw).hexdigest()
    evidence = json.loads((out / pr_id / "evidence" / "pr.json").read_text())
    assert evidence["pull"]["number"] == 42
    assert evidence["comments"][0]["body"] == "nice"
    assert view["evidence"]["pr_number"] == 42
    assert view["evidence"]["comment_count"] == 1


def test_verify_covers_member_patches(pipeline, tmp_path: Path):
    snapshot = _forge_pipeline(pipeline, tmp_path)
    from panther.plugins.services.testers.a_rfc.views.emit import verify_views

    out = tmp_path / "clusters"
    ids = emit_views(
        pipeline["timeline"],
        pipeline["corpus"],
        pipeline["repo"],
        out,
        forge_snapshot=snapshot,
        patches="members",
    )
    assert (
        verify_views(
            pipeline["timeline"],
            pipeline["corpus"],
            pipeline["repo"],
            out,
            forge_snapshot=snapshot,
            patches="members",
        )
        == ()
    )
    pr_id = [cluster_id for cluster_id in ids if "-pr-" in cluster_id][0]
    victim = sorted((out / pr_id / "members").iterdir())[0]
    victim.write_bytes(victim.read_bytes() + b"x")
    drifted = verify_views(
        pipeline["timeline"],
        pipeline["corpus"],
        pipeline["repo"],
        out,
        forge_snapshot=snapshot,
        patches="members",
    )
    assert drifted == (pr_id,)


def test_only_limits_emission(pipeline, tmp_path: Path):
    all_ids = _emit(pipeline, tmp_path / "all")
    ids = _emit(pipeline, tmp_path / "one", only=all_ids[0])
    assert ids == (all_ids[0],)
    with pytest.raises(ViewsError):
        _emit(pipeline, tmp_path / "bad", only="c9999-pr-000000000000")
