import hashlib
import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.draft.checkpoint import (
    CheckpointError,
    verify_checkpoint,
    write_checkpoint,
)
from panther.plugins.services.testers.a_rfc.timeline.store import read_clusters

pytestmark = pytest.mark.unit


def _pr_cluster_id(timeline_dir: Path) -> str:
    return [
        cluster["id"]
        for cluster in read_clusters(timeline_dir)
        if cluster["kind"] == "pr"
    ][0]


def test_checkpoint_records_ordinal_prev_and_digests(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path
):
    out = tmp_path / "checkpoints"
    cluster_id = _pr_cluster_id(timeline_dir)
    checkpoint_dir = write_checkpoint(manifest_path, timeline_dir, cluster_id, out)
    assert checkpoint_dir == out / cluster_id
    record = json.loads((checkpoint_dir / "checkpoint.json").read_text())
    assert record["cluster_id"] == cluster_id
    assert record["ordinal"] == 2
    assert record["prev_cluster_id"].startswith("c0001-epoch-")
    stored = (checkpoint_dir / "manifest.yaml").read_bytes()
    assert record["manifest_sha256"] == hashlib.sha256(stored).hexdigest()
    timeline_bytes = (timeline_dir / "timeline.json").read_bytes()
    assert record["timeline_sha256"] == hashlib.sha256(timeline_bytes).hexdigest()


def test_checkpoint_adjudication_summary(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path
):
    checkpoint_dir = write_checkpoint(
        manifest_path, timeline_dir, _pr_cluster_id(timeline_dir), tmp_path / "c"
    )
    record = json.loads((checkpoint_dir / "checkpoint.json").read_text())
    adjudication = record["adjudication"]
    assert adjudication["count_by_stored"] == {"gap": 2, "inferred": 0, "confirmed": 0}
    assert adjudication["count_by_supported"] == {
        "gap": 1,
        "inferred": 0,
        "confirmed": 1,
    }
    assert adjudication["promotable_count"] == 1
    assert adjudication["violation_count"] == 0


def test_unknown_cluster_is_refused(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path
):
    with pytest.raises(CheckpointError) as excinfo:
        write_checkpoint(
            manifest_path, timeline_dir, "c9999-pr-000000000000", tmp_path / "c"
        )
    assert "c9999" in str(excinfo.value)


def test_existing_checkpoint_is_never_overwritten(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path
):
    cluster_id = _pr_cluster_id(timeline_dir)
    write_checkpoint(manifest_path, timeline_dir, cluster_id, tmp_path / "c")
    with pytest.raises(CheckpointError):
        write_checkpoint(manifest_path, timeline_dir, cluster_id, tmp_path / "c")


def test_verify_detects_a_stale_manifest_copy(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path
):
    checkpoint_dir = write_checkpoint(
        manifest_path, timeline_dir, _pr_cluster_id(timeline_dir), tmp_path / "c"
    )
    assert verify_checkpoint(checkpoint_dir) is None
    stored = checkpoint_dir / "manifest.yaml"
    stored.write_bytes(stored.read_bytes() + b"# drift\n")
    reason = verify_checkpoint(checkpoint_dir)
    assert reason is not None
    assert "manifest.yaml" in reason


def test_two_checkpoints_of_same_manifest_are_byte_identical(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path
):
    cluster_id = _pr_cluster_id(timeline_dir)
    first = write_checkpoint(manifest_path, timeline_dir, cluster_id, tmp_path / "one")
    second = write_checkpoint(manifest_path, timeline_dir, cluster_id, tmp_path / "two")
    for name in ("manifest.yaml", "checkpoint.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
