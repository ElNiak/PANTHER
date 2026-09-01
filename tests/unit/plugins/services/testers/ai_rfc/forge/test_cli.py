import json
import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.forge import cli

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
            "fetch",
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
            "fetch",
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
            "fetch",
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


def test_fetch_is_a_verb_not_a_bare_positional(clone: Path, tmp_path: Path):
    """The bare form is gone; a caller passing a URL first must now say fetch.

    pipeline/run.py builds this argv, so the two must not drift — a bare URL
    has to fail loudly rather than be read as a verb name.
    """
    with pytest.raises(SystemExit) as exit_info:
        cli.main(
            [
                "https://github.com/aiortc/aioquic",
                "--repo",
                str(clone),
                "--out",
                str(tmp_path / "forge"),
            ],
            transport=_transport_empty,
        )
    assert exit_info.value.code == 2


def test_an_unknown_verb_exits_two(tmp_path: Path):
    """2 belongs to argparse alone, so an unknown verb must not reach the body."""
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["harvest", "https://example.com/o/r"])
    assert exit_info.value.code == 2


def _adopt(clone: Path, out: Path, records: Path, *extra: str) -> int:
    return cli.main(
        [
            "adopt",
            str(records),
            "https://github.com/aiortc/aioquic",
            "--repo",
            str(clone),
            "--out",
            str(out),
            *extra,
        ]
    )


def test_adopt_writes_a_snapshot_declaring_its_route(
    clone: Path, tmp_path: Path, capsys
):
    """The whole wiring — records, declaration, exit code, report — in one pass.

    Every field below is read by a downstream stage, so a snapshot that adopts
    records without them is indistinguishable from a full authenticated fetch.
    """
    records = tmp_path / "records.json"
    records.write_text(
        json.dumps({"pulls": [{"number": 7, "merged_at": "x"}], "reviews": []})
    )
    out = tmp_path / "forge"

    assert _adopt(clone, out, records) == 0

    snapshots = list((out / "github.com__aiortc__aioquic").iterdir())
    assert len(snapshots) == 1
    meta = json.loads((snapshots[0] / "meta.json").read_text())
    assert meta["acquisition"] == "adopt"
    assert meta["fidelity_ceiling"] == "pulls"
    assert meta["authenticated"] is False
    assert len(meta["clone_head"]) == 40
    assert "1 pull" in capsys.readouterr().err


def test_adopt_can_declare_a_higher_ceiling(clone: Path, tmp_path: Path):
    """Records from a credentialed dump carry discussion a pulls-only one cannot."""
    records = tmp_path / "records.json"
    records.write_text(json.dumps({"pulls": []}))
    out = tmp_path / "forge"

    assert _adopt(clone, out, records, "--fidelity-ceiling", "pulls+discussion") == 0

    snapshot = next((out / "github.com__aiortc__aioquic").iterdir())
    meta = json.loads((snapshot / "meta.json").read_text())
    assert meta["fidelity_ceiling"] == "pulls+discussion"


def test_adopt_reports_an_unreadable_records_file_rather_than_raising(
    clone: Path, tmp_path: Path, capsys
):
    """A latin-1 dump or a binary file must exit 1 with a diagnostic."""
    records = tmp_path / "records.json"
    records.write_bytes(b'{"pulls": []}\xff\xfe')

    assert _adopt(clone, tmp_path / "forge", records) == 1
    assert "error" in capsys.readouterr().err


def test_adopt_refuses_a_missing_records_file(clone: Path, tmp_path: Path, capsys):
    assert _adopt(clone, tmp_path / "forge", tmp_path / "absent.json") == 1
    assert "error" in capsys.readouterr().err
