"""Tests for the deterministic completeness gate."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.draft import completeness


def test_load_clusters_returns_rows_ordered_by_ordinal(timeline_dir: Path) -> None:
    rows = completeness.load_clusters(timeline_dir)

    assert [row["ordinal"] for row in rows] == [1, 2]
    assert all("id" in row for row in rows)


def test_load_clusters_raises_when_timeline_missing(tmp_path: Path) -> None:
    with pytest.raises(completeness.CompletenessError):
        completeness.load_clusters(tmp_path / "absent")


def test_checkpoint_records_sorted_by_ordinal_not_directory_name(
    tmp_path: Path,
) -> None:
    root = tmp_path / "checkpoints"
    for name, ordinal in (("zzz-late", 9), ("aaa-early", 2)):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "checkpoint.json").write_text(
            json.dumps(
                {
                    "adjudication": {},
                    "cluster_id": name,
                    "manifest_sha256": f"{ordinal:064d}",
                    "ordinal": ordinal,
                    "prev_cluster_id": None,
                    "timeline_sha256": "1" * 64,
                },
                sort_keys=True,
            )
        )

    records = completeness.checkpoint_records(root)

    assert [record["ordinal"] for _, record in records] == [2, 9]


def test_checkpoint_records_is_empty_when_root_absent(tmp_path: Path) -> None:
    assert completeness.checkpoint_records(tmp_path / "absent") == ()


def test_sparse_workspace_has_one_checkpoint_for_two_clusters(
    sparse_workspace: dict[str, Path],
) -> None:
    clusters = completeness.load_clusters(sparse_workspace["timeline"])
    records = completeness.checkpoint_records(sparse_workspace["checkpoints"])

    assert len(clusters) == 2
    assert len(records) == 1


def test_first_checkpoint_owns_every_claim_it_holds(
    draft_workspace: dict[str, Path],
) -> None:
    rows = completeness.attribute_claims(
        draft_workspace["timeline"], draft_workspace["checkpoints"]
    )
    by_ordinal = {row.ordinal: row for row in rows}

    assert by_ordinal[1].new_claim_ids == ("spec:1.1",)
    assert by_ordinal[1].checkpointed is True


def test_later_checkpoint_owns_only_its_additions(
    draft_workspace: dict[str, Path],
) -> None:
    rows = completeness.attribute_claims(
        draft_workspace["timeline"], draft_workspace["checkpoints"]
    )
    by_ordinal = {row.ordinal: row for row in rows}

    assert by_ordinal[2].new_claim_ids == ("spec:2.1",)
    assert by_ordinal[2].manifest_changed is True


def test_uncheckpointed_clusters_are_reported_as_such(
    sparse_workspace: dict[str, Path],
) -> None:
    rows = completeness.attribute_claims(
        sparse_workspace["timeline"], sparse_workspace["checkpoints"]
    )

    assert [row.checkpointed for row in rows] == [True, False]
    assert rows[1].new_claim_ids == ()


def test_attribution_covers_every_cluster_in_the_timeline(
    sparse_workspace: dict[str, Path],
) -> None:
    clusters = completeness.load_clusters(sparse_workspace["timeline"])
    rows = completeness.attribute_claims(
        sparse_workspace["timeline"], sparse_workspace["checkpoints"]
    )

    assert [row.cluster_id for row in rows] == [row["id"] for row in clusters]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_gate_clean_workspace_has_no_citation_gaps(
    draft_workspace: dict[str, Path],
) -> None:
    uncited, never = completeness.citation_gaps(
        draft_workspace["repo"],
        draft_workspace["revisions"],
        frozenset({"spec:1.1", "spec:2.1"}),
    )

    assert uncited == ()
    assert never == ()


def test_uncited_at_head_lists_claims_the_latest_tag_omits(
    sparse_workspace: dict[str, Path],
) -> None:
    uncited, never = completeness.citation_gaps(
        sparse_workspace["repo"],
        sparse_workspace["revisions"],
        frozenset({"spec:1.1"}),
    )

    assert uncited == ("spec:1.1",)
    assert never == ("spec:1.1",)


def test_never_cited_excludes_a_claim_cited_then_dropped(
    draft_workspace: dict[str, Path],
) -> None:
    """spec:2.1 is cited at -01; a -02 that drops it is uncited but not never."""
    repo = draft_workspace["repo"]
    (repo / "draft-test-spec.md").write_text(
        "# Spec\n\nThe system does the thing. `a_rfc:spec:1.1`\n"
    )
    _git(repo, "add", "draft-test-spec.md")
    _git(repo, "commit", "-m", "revision 02")
    _git(repo, "tag", "draft-test-spec-02")
    pr_id = completeness.load_clusters(draft_workspace["timeline"])[1]["id"]
    revisions = draft_workspace["revisions"]
    revisions.write_text(
        revisions.read_text()
        + "  draft-test-spec-02:\n"
        + f"    cluster_id: {pr_id}\n"
        + f"    checkpoint_manifest_sha256: {'0' * 64}\n"
        + "    normative_change: true\n"
        + "    note: 'drops the second behaviour'\n"
    )

    uncited, never = completeness.citation_gaps(
        repo, revisions, frozenset({"spec:1.1", "spec:2.1"})
    )

    assert uncited == ("spec:2.1",)
    assert never == ()


def test_build_on_a_clean_workspace_reports_nothing_outstanding(
    draft_workspace: dict[str, Path], tmp_path: Path
) -> None:
    report = completeness.build(
        draft_workspace["timeline"],
        draft_workspace["checkpoints"],
        tmp_path / "m2.yaml",
        draft_workspace["revisions"],
        draft_workspace["repo"],
    )

    assert report.unprocessed_clusters == ()
    assert report.uncited_at_head == ()
    assert report.manifest_drift == ()
    assert report.totals["processed_fraction"] == 1.0
    assert completeness.findings(report) == ()


def test_build_on_a_sparse_workspace_reports_the_gaps(
    sparse_workspace: dict[str, Path],
) -> None:
    report = completeness.build(
        sparse_workspace["timeline"],
        sparse_workspace["checkpoints"],
        sparse_workspace["manifest"],
        sparse_workspace["revisions"],
        sparse_workspace["repo"],
    )

    assert len(report.unprocessed_clusters) == 1
    assert report.uncited_at_head == ("spec:1.1",)
    assert report.totals["clusters_total"] == 2
    assert report.totals["clusters_processed"] == 1
    assert report.totals["processed_fraction"] == 0.5
    assert any("1 of 2" in finding for finding in completeness.findings(report))


def test_to_json_is_byte_stable(sparse_workspace: dict[str, Path]) -> None:
    args = (
        sparse_workspace["timeline"],
        sparse_workspace["checkpoints"],
        sparse_workspace["manifest"],
        sparse_workspace["revisions"],
        sparse_workspace["repo"],
    )

    first = completeness.to_json(completeness.build(*args))
    second = completeness.to_json(completeness.build(*args))

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["totals"]["clusters_total"] == 2
