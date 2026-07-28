import logging
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.cli import main

pytestmark = pytest.mark.unit

OVERSTATED = """\
rfc: SPEC-1
title: 'An Example Specification'
requirements:
  'spec:1.1':
    text: 'A claim recorded above what its evidence supports.'
    section: '1.1'
    level: MUST
    layer: timing
    status: confirmed
    anchors:
      - evidence_class: adr
        locator: adr/0007.md
"""


def test_valid_manifest_writes_all_artifacts(extended_manifest: Path, tmp_path: Path):
    out = tmp_path / "out"
    assert main([str(extended_manifest), "--out", str(out)]) == 0
    assert (out / "report.json").exists()
    assert (out / "report.yaml").exists()
    assert (out / "report.md").exists()


def test_malformed_manifest_returns_one_rather_than_raising(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("rfc: SPEC-1\n")
    assert main([str(bad), "--out", str(tmp_path / "out")]) == 1


def test_missing_manifest_returns_one(tmp_path: Path):
    assert main([str(tmp_path / "absent.yaml"), "--out", str(tmp_path / "out")]) == 1


def test_violations_are_reported_but_tolerated_by_default(tmp_path: Path):
    manifest = tmp_path / "overstated.yaml"
    manifest.write_text(OVERSTATED)
    out = tmp_path / "out"
    assert main([str(manifest), "--out", str(out)]) == 0
    assert "spec:1.1" in (out / "report.md").read_text()


def test_violations_fail_under_strict(tmp_path: Path):
    manifest = tmp_path / "overstated.yaml"
    manifest.write_text(OVERSTATED)
    out = tmp_path / "out"
    assert main([str(manifest), "--out", str(out), "--strict"]) == 2
    assert (out / "report.md").exists()


def test_violations_are_named_on_the_console(tmp_path: Path, caplog):
    """A gate that exits non-zero must say why, not only write it to a file."""
    manifest = tmp_path / "overstated.yaml"
    manifest.write_text(OVERSTATED)
    with caplog.at_level(logging.WARNING):
        main([str(manifest), "--out", str(tmp_path / "out"), "--strict"])
    assert "spec:1.1" in caplog.text
    assert "supports only inferred" in caplog.text


def test_unreadable_repo_returns_one(extended_manifest: Path, tmp_path: Path):
    assert (
        main(
            [
                str(extended_manifest),
                "--out",
                str(tmp_path / "out"),
                "--repo",
                str(tmp_path / "not_a_repo"),
            ]
        )
        == 1
    )
