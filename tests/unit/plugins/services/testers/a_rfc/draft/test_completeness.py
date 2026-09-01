"""Tests for the deterministic completeness gate."""

from __future__ import annotations

import json
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
