from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.views import cli

pytestmark = pytest.mark.unit


def _argv(pipeline: dict[str, Path], out: Path, *extra: str) -> list[str]:
    return [
        str(pipeline["timeline"]),
        "--corpus",
        str(pipeline["corpus"]),
        "--repo",
        str(pipeline["repo"]),
        "--out",
        str(out),
        *extra,
    ]


def test_emits_views_and_reports_summary(pipeline, tmp_path: Path, capsys):
    out = tmp_path / "clusters"
    assert cli.main(_argv(pipeline, out)) == 0
    assert len(list(out.iterdir())) == 2
    assert "2 cluster" in capsys.readouterr().err


def test_verify_passes_on_untouched_views(pipeline, tmp_path: Path):
    out = tmp_path / "clusters"
    assert cli.main(_argv(pipeline, out)) == 0
    assert cli.main(_argv(pipeline, out, "--verify")) == 0


def test_verify_names_drifted_cluster_and_exits_two(pipeline, tmp_path: Path, capsys):
    out = tmp_path / "clusters"
    assert cli.main(_argv(pipeline, out)) == 0
    victim = sorted(out.iterdir())[0]
    span = victim / "span.diff"
    span.write_bytes(span.read_bytes() + b"x")
    assert cli.main(_argv(pipeline, out, "--verify")) == 2
    assert victim.name in capsys.readouterr().err


def test_missing_timeline_exits_one(pipeline, tmp_path: Path, capsys):
    argv = _argv(pipeline, tmp_path / "clusters")
    argv[0] = str(tmp_path / "nowhere")
    assert cli.main(argv) == 1
    assert "error" in capsys.readouterr().err
