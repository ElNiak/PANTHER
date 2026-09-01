import pytest

from panther.plugins.services.testers.ai_rfc.timeline.build import build_timeline
from panther.plugins.services.testers.ai_rfc.timeline.corpus import (
    CorpusCommit,
    TimelineError,
)

pytestmark = pytest.mark.unit


def _c(sha, parents, at="2026-01-01T00:00:00+00:00", subject=None, truncated=False):
    return CorpusCommit(
        sha=sha,
        parents=tuple(parents),
        authored_at=at,
        subject=subject if subject is not None else f"s {sha}",
        is_merge=len(parents) > 1,
        files_truncated=truncated,
    )


def test_merge_and_direct_pushes_partition_into_pr_and_epoch():
    commits = [_c("r", []), _c("f", ["r"]), _c("d", ["r"]), _c("m", ["d", "f"])]
    clusters = build_timeline(commits)
    shape = [(cluster.kind, [m.sha for m in cluster.members]) for cluster in clusters]
    assert shape == [("epoch", ["r", "d"]), ("pr", ["f", "m"])]
    assert clusters[0].id.startswith("c0001-epoch-")
    assert clusters[1].id.startswith("c0002-pr-")
    assert clusters[1].anchor_sha == "m"
    assert clusters[1].spine_prev_sha == "d"
    assert clusters[0].spine_prev_sha is None
    assert [m.role for m in clusters[1].members] == ["branch", "anchor"]
    assert [m.role for m in clusters[0].members] == ["spine", "spine"]
    assert [m.position for m in clusters[1].members] == [0, 1]


def test_every_commit_appears_exactly_once():
    commits = [
        _c("r", []),
        _c("f1", ["r"]),
        _c("f2", ["f1"]),
        _c("d", ["r"]),
        _c("m", ["d", "f2"]),
        _c("t", ["m"]),
    ]
    clusters = build_timeline(commits)
    seen = [m.sha for cluster in clusters for m in cluster.members]
    assert sorted(seen) == sorted(commit.sha for commit in commits)
    assert len(seen) == len(set(seen))


def test_spine_concatenation_reproduces_the_spine():
    commits = [
        _c("r", []),
        _c("f", ["r"]),
        _c("m1", ["r", "f"]),
        _c("d1", ["m1"]),
        _c("d2", ["d1"]),
        _c("g", ["d2"]),
        _c("m2", ["d2", "g"]),
    ]
    clusters = build_timeline(commits)
    spine_members = [
        m.sha
        for cluster in clusters
        for m in cluster.members
        if m.role in ("spine", "anchor")
    ]
    assert spine_members == ["r", "m1", "d1", "d2", "m2"]


def test_octopus_merge_gathers_all_side_parents():
    commits = [_c("r", []), _c("f", ["r"]), _c("g", ["r"]), _c("m", ["r", "f", "g"])]
    (cluster,) = [cl for cl in build_timeline(commits) if cl.kind == "pr"]
    assert {m.sha for m in cluster.members} == {"f", "g", "m"}


def test_nested_merge_counts_but_stays_a_member():
    commits = [
        _c("r", []),
        _c("f1", ["r"]),
        _c("u", ["f1", "r"]),
        _c("m", ["r", "u"]),
    ]
    (cluster,) = [cl for cl in build_timeline(commits) if cl.kind == "pr"]
    assert cluster.nested_merge_count == 1
    assert {m.sha for m in cluster.members} == {"f1", "u", "m"}


def test_parent_absent_from_corpus_is_loud():
    with pytest.raises(TimelineError) as excinfo:
        build_timeline([_c("r", []), _c("m", ["r", "ghost"])])
    assert "ghost" in str(excinfo.value)


def test_order_is_topological_not_chronological():
    commits = [
        _c("r", [], at="2026-01-02T00:00:00+00:00"),
        _c("d", ["r"], at="2026-01-01T00:00:00+00:00"),
    ]
    (epoch,) = build_timeline(commits)
    assert [m.sha for m in epoch.members] == ["r", "d"]


def test_subject_pr_hint_recorded_on_pr_anchor_only():
    commits = [
        _c("r", []),
        _c("f", ["r"]),
        _c("m", ["r", "f"], subject="Merge thing (#12)"),
        _c("s", ["m"], subject="feat: squashed thing (#34)"),
    ]
    clusters = build_timeline(commits)
    pr = [cl for cl in clusters if cl.kind == "pr"][0]
    epochs = [cl for cl in clusters if cl.kind == "epoch"]
    assert pr.subject_pr_hint == 12
    assert all(cl.subject_pr_hint is None for cl in epochs)
    assert all(cl.provenance == "epoch" for cl in epochs)
    assert pr.provenance == "merge_commit"


def test_truncated_member_marks_cluster_incomplete():
    commits = [_c("r", [], truncated=True)]
    (epoch,) = build_timeline(commits)
    assert epoch.files_complete is False
    assert epoch.anchor_sha == "r"


def _pull(number: int, merge_sha: str | None, squash_sha: str | None = None) -> dict:
    return {
        "number": number,
        "title": f"pull {number}",
        "state": "merged",
        "merged_at": "2026-01-02T00:00:00Z",
        "merge_commit_sha": merge_sha,
        "squash_commit_sha": squash_sha,
    }


def test_forge_squash_rescue_splits_epochs():
    commits = [_c("r", []), _c("s", ["r"]), _c("t", ["s"])]
    clusters = build_timeline(commits, forge_pulls=[_pull(12, "s")])
    shape = [
        (cluster.kind, cluster.provenance, [m.sha for m in cluster.members])
        for cluster in clusters
    ]
    assert shape == [
        ("epoch", "epoch", ["r"]),
        ("pr", "forge_squash", ["s"]),
        ("epoch", "epoch", ["t"]),
    ]
    assert clusters[1].pr_number == 12
    assert clusters[1].members[0].role == "anchor"
    seen = [m.sha for cluster in clusters for m in cluster.members]
    assert sorted(seen) == ["r", "s", "t"]


def test_forge_enriches_existing_merge_cluster():
    commits = [_c("r", []), _c("f", ["r"]), _c("m", ["r", "f"])]
    clusters = build_timeline(commits, forge_pulls=[_pull(7, "m")])
    pr = [cluster for cluster in clusters if cluster.kind == "pr"][0]
    assert pr.pr_number == 7
    assert pr.provenance == "merge_commit"


def test_gitlab_squash_sha_takes_priority():
    commits = [_c("r", []), _c("s", ["r"])]
    clusters = build_timeline(commits, forge_pulls=[_pull(3, "0" * 40, squash_sha="s")])
    pr = [cluster for cluster in clusters if cluster.kind == "pr"][0]
    assert pr.provenance == "forge_squash"
    assert pr.pr_number == 3


def test_unmatched_and_unmerged_pulls_change_nothing():
    commits = [_c("r", []), _c("d", ["r"])]
    unmatched = _pull(1, "z" * 40)
    unmerged = dict(_pull(2, "d"), state="open", merged_at=None)
    clusters = build_timeline(commits, forge_pulls=[unmatched, unmerged])
    assert [cluster.kind for cluster in clusters] == ["epoch"]
    assert clusters[0].pr_number is None


def test_subject_hint_never_clusters_even_with_forge_data():
    commits = [_c("r", []), _c("s", ["r"], subject="feat: thing (#12)")]
    clusters = build_timeline(commits, forge_pulls=[])
    assert [cluster.kind for cluster in clusters] == ["epoch"]


def test_epoch_between_two_merges_has_the_right_prev():
    commits = [
        _c("r", []),
        _c("f", ["r"]),
        _c("m1", ["r", "f"]),
        _c("d", ["m1"]),
        _c("g", ["d"]),
        _c("m2", ["d", "g"]),
    ]
    clusters = build_timeline(commits)
    kinds = [cluster.kind for cluster in clusters]
    assert kinds == ["epoch", "pr", "epoch", "pr"]
    middle_epoch = clusters[2]
    assert [m.sha for m in middle_epoch.members] == ["d"]
    assert middle_epoch.spine_prev_sha == "m1"
    assert clusters[3].spine_prev_sha == "d"
