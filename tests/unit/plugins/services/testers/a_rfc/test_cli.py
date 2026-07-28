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


def test_violations_are_named_on_stderr(tmp_path: Path, capsys):
    """A gate that exits non-zero must say why, not only write it to a file.

    Asserts on stderr rather than on log capture deliberately: every
    ``panther.*`` logger sets ``propagate=False`` with an ERROR-level handler,
    so a logged warning here would be discarded before anyone saw it.
    """
    manifest = tmp_path / "overstated.yaml"
    manifest.write_text(OVERSTATED)
    assert main([str(manifest), "--out", str(tmp_path / "out"), "--strict"]) == 2
    stderr = capsys.readouterr().err
    assert "spec:1.1" in stderr
    assert "supports only inferred" in stderr


def test_broken_anchor_alone_gates_and_is_named(
    fixture_repo: Path, tmp_path: Path, capsys
):
    """An anchor absent at its pinned commit fails --strict on its own.

    Guards the case a manifest with both faults cannot: here there is no
    promotion violation, so only the anchor can be driving the exit code.
    """
    manifest = tmp_path / "anchor_only.yaml"
    manifest.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'Correctly inferred; its anchor is simply broken.'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    status: inferred\n"
        "    anchors:\n"
        "      - evidence_class: code\n"
        "        locator: does_not_exist.txt\n"
        f"        commit: '{(fixture_repo / 'FIRST_SHA').read_text().strip()}'\n"
    )
    out = tmp_path / "out"
    code = main(
        [str(manifest), "--out", str(out), "--repo", str(fixture_repo), "--strict"]
    )
    assert code == 2
    stderr = capsys.readouterr().err
    assert "unverified" in stderr
    assert "does_not_exist.txt" in stderr


def test_broken_anchor_alone_is_tolerated_without_strict(
    fixture_repo: Path, tmp_path: Path
):
    manifest = tmp_path / "anchor_only.yaml"
    manifest.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'Correctly inferred; its anchor is simply broken.'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    status: inferred\n"
        "    anchors:\n"
        "      - evidence_class: code\n"
        "        locator: does_not_exist.txt\n"
        f"        commit: '{(fixture_repo / 'FIRST_SHA').read_text().strip()}'\n"
    )
    assert (
        main(
            [
                str(manifest),
                "--out",
                str(tmp_path / "out"),
                "--repo",
                str(fixture_repo),
            ]
        )
        == 0
    )


def test_unreadable_manifest_says_why_on_stderr(tmp_path: Path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("rfc: SPEC-1\n")
    assert main([str(bad), "--out", str(tmp_path / "out")]) == 1
    assert "error:" in capsys.readouterr().err


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
