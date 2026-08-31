from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.draft import cli
from panther.plugins.services.testers.a_rfc.timeline.store import read_clusters

from .conftest import git

pytestmark = pytest.mark.unit


def test_checkpoint_verb_writes_a_checkpoint(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path, capsys
):
    cluster_id = read_clusters(timeline_dir)[0]["id"]
    code = cli.main(
        [
            "checkpoint",
            str(manifest_path),
            "--timeline",
            str(timeline_dir),
            "--cluster",
            cluster_id,
            "--out",
            str(tmp_path / "checkpoints"),
        ]
    )
    assert code == 0
    assert (tmp_path / "checkpoints" / cluster_id / "checkpoint.json").exists()
    assert "checkpoint written" in capsys.readouterr().err


def test_checkpoint_verb_exits_one_on_unknown_cluster(
    manifest_path: Path, timeline_dir: Path, tmp_path: Path, capsys
):
    code = cli.main(
        [
            "checkpoint",
            str(manifest_path),
            "--timeline",
            str(timeline_dir),
            "--cluster",
            "c9999-pr-000000000000",
            "--out",
            str(tmp_path / "checkpoints"),
        ]
    )
    assert code == 1
    assert "error" in capsys.readouterr().err


def _gate_argv(workspace: dict[str, Path], out: Path, *extra: str) -> list[str]:
    return [
        "gate",
        str(workspace["repo"]),
        "--timeline",
        str(workspace["timeline"]),
        "--checkpoints",
        str(workspace["checkpoints"]),
        "--questions",
        str(workspace["questions"]),
        "--revisions",
        str(workspace["revisions"]),
        "--out",
        str(out),
        *extra,
    ]


def test_gate_verb_clean_writes_report_and_exits_zero(
    draft_workspace, tmp_path: Path, capsys
):
    out = tmp_path / "out"
    assert cli.main(_gate_argv(draft_workspace, out)) == 0
    assert (out / "gate-report.json").read_text() == '{\n  "findings": []\n}\n'
    assert "gate clean" in capsys.readouterr().err


def test_gate_verb_reports_findings_without_strict(
    draft_workspace, tmp_path: Path, capsys
):
    git(draft_workspace["repo"], "tag", "-d", "draft-test-spec-01")
    assert cli.main(_gate_argv(draft_workspace, tmp_path / "out")) == 0
    assert "finding:" in capsys.readouterr().err


def test_gate_verb_strict_exits_three_on_findings(draft_workspace, tmp_path: Path):
    git(draft_workspace["repo"], "tag", "-d", "draft-test-spec-01")
    assert cli.main(_gate_argv(draft_workspace, tmp_path / "out", "--strict")) == 3


def test_gate_verb_exits_one_on_missing_inputs(draft_workspace, tmp_path: Path, capsys):
    draft_workspace["revisions"].unlink()
    assert cli.main(_gate_argv(draft_workspace, tmp_path / "out")) == 1
    assert "error" in capsys.readouterr().err
