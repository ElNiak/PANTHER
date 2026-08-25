import json
import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.forge import cli

pytestmark = pytest.mark.unit


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    repo = tmp_path / "clone"
    repo.mkdir()
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "--allow-empty", "-m", "root"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return repo


def _transport_empty(url: str, headers: dict) -> tuple[int, dict, bytes]:
    return 200, {}, b"[]"


def test_writes_snapshot_and_reports_counts(clone: Path, tmp_path: Path, capsys):
    out = tmp_path / "forge"
    code = cli.main(
        [
            "https://github.com/aiortc/aioquic",
            "--repo",
            str(clone),
            "--out",
            str(out),
        ],
        transport=_transport_empty,
    )
    assert code == 0
    snapshots = list((out / "github.com__aiortc__aioquic").iterdir())
    assert len(snapshots) == 1
    meta = json.loads((snapshots[0] / "meta.json").read_text())
    assert meta["authenticated"] is False
    assert len(meta["clone_head"]) == 40
    err = capsys.readouterr().err
    assert "0 pull" in err


def test_non_repo_clone_exits_one(tmp_path: Path, capsys):
    code = cli.main(
        [
            "https://github.com/aiortc/aioquic",
            "--repo",
            str(tmp_path / "nowhere"),
            "--out",
            str(tmp_path / "forge"),
        ],
        transport=_transport_empty,
    )
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_fetch_failure_exits_one(clone: Path, tmp_path: Path, capsys):
    def failing(url: str, headers: dict) -> tuple[int, dict, bytes]:
        return 500, {}, b"{}"

    code = cli.main(
        [
            "https://github.com/aiortc/aioquic",
            "--repo",
            str(clone),
            "--out",
            str(tmp_path / "forge"),
        ],
        transport=failing,
    )
    assert code == 1
    assert "500" in capsys.readouterr().err
