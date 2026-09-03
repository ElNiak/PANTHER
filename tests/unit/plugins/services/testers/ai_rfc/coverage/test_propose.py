import json
import subprocess
from pathlib import Path

import pytest
import yaml

from panther.plugins.services.testers.ai_rfc.anchors import verify_detailed
from panther.plugins.services.testers.ai_rfc.coverage import cli
from panther.plugins.services.testers.ai_rfc.models import Anchor, EvidenceClass
from panther.plugins.services.testers.ai_rfc.schema import load

from .conftest import manifest_text

pytestmark = pytest.mark.unit


def _manifest(tmp_path: Path, commit: str, line: int) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(manifest_text(line).format(commit=commit))
    return path


def _argv(manifest: Path, coverage: Path, repo: Path, commit: str, out: Path):
    return [
        str(manifest),
        "--coverage",
        str(coverage),
        "--repo",
        str(repo),
        "--commit",
        commit,
        "--out",
        str(out),
    ]


def test_an_executed_cited_line_yields_a_self_verifying_anchor(
    java_repo, coverage_report, tmp_path: Path
):
    """The digest is computed the way `anchors.verify_detailed` checks it.

    An anchor that would not verify is worse than no anchor: it is primary
    evidence pointing at something that is not there.
    """
    repo, commit = java_repo
    manifest = _manifest(tmp_path, commit, line=5)
    out = tmp_path / "out"
    assert cli.main(_argv(manifest, coverage_report, repo, commit, out)) == 0

    fragment = yaml.safe_load((out / "runtime-anchors.yaml").read_text())
    (proposed,) = fragment["requirements"]["mark:alg.1"]["anchors"]
    assert proposed["evidence_class"] == "runtime"
    assert proposed["line"] == 5
    assert proposed["locator"].startswith("server/src/main/java/")

    anchor = Anchor(
        EvidenceClass.RUNTIME,
        proposed["locator"],
        commit=proposed["commit"],
        line=proposed["line"],
        line_sha256=proposed["line_sha256"],
    )
    assert verify_detailed(anchor, repo) is None


def test_a_cited_line_the_run_never_reached_yields_nothing(
    java_repo, coverage_report, tmp_path: Path
):
    """This is MARK's actual situation, so it is the case that must be right."""
    repo, commit = java_repo
    manifest = _manifest(tmp_path, commit, line=6)
    out = tmp_path / "out"
    assert cli.main(_argv(manifest, coverage_report, repo, commit, out)) == 0

    fragment = yaml.safe_load((out / "runtime-anchors.yaml").read_text())
    assert fragment["requirements"] == {}
    record = json.loads((out / "runtime-anchors.json").read_text())
    assert record["proposed"] == []
    assert record["skipped"][0]["reason"] == "the run did not reach this line"


def test_the_manifest_is_never_edited(java_repo, coverage_report, tmp_path: Path):
    """A runtime anchor takes a claim to confirmed; the merge stays a decision."""
    repo, commit = java_repo
    manifest = _manifest(tmp_path, commit, line=5)
    before = manifest.read_bytes()
    assert cli.main(_argv(manifest, coverage_report, repo, commit, tmp_path / "o")) == 0
    assert manifest.read_bytes() == before
    assert load(manifest).claims[0].evidence_classes == {EvidenceClass.CODE}


def test_the_provenance_names_what_the_anchor_actually_claims(
    java_repo, coverage_report, tmp_path: Path
):
    repo, commit = java_repo
    out = tmp_path / "out"
    manifest = _manifest(tmp_path, commit, line=5)
    assert cli.main(_argv(manifest, coverage_report, repo, "HEAD", out)) == 0
    record = json.loads((out / "runtime-anchors.json").read_text())
    assert record["criterion"] == "line-executed"
    assert record["tool"] == "jacoco"
    assert len(record["report_sha256"]) == 64
    assert record["commit"] != "HEAD"
    assert len(record["commit"]) == 40


def test_a_dirty_tree_is_refused(java_repo, coverage_report, tmp_path: Path, capsys):
    """The lines that ran are not the lines the commit contains."""
    repo, commit = java_repo
    (repo / "scratch.txt").write_text("uncommitted\n")
    manifest = _manifest(tmp_path, commit, line=5)
    assert cli.main(_argv(manifest, coverage_report, repo, commit, tmp_path / "o")) == 1
    assert "uncommitted changes" in capsys.readouterr().err


def test_a_moved_head_is_refused(java_repo, coverage_report, tmp_path: Path, capsys):
    repo, commit = java_repo
    (repo / "later.txt").write_text("later\n")
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "later"],
        check=True,
        capture_output=True,
    )
    manifest = _manifest(tmp_path, commit, line=5)
    assert cli.main(_argv(manifest, coverage_report, repo, commit, tmp_path / "o")) == 1
    assert "different checkout" in capsys.readouterr().err


def test_an_ambiguous_suffix_is_refused_rather_than_guessed(
    java_repo, coverage_report, tmp_path: Path
):
    """MARK's aggregate report merges seven modules; a repeated package is live.

    Picking either match would attach a claim's evidence to the wrong file, and
    nothing downstream could tell.
    """
    repo, _ = java_repo
    twin = repo / "core" / "src" / "main" / "java" / "be" / "cylab" / "mark"
    (twin / "detection").mkdir(parents=True)
    (twin / "detection" / "OWAverage.java").write_text("// a second copy\n")
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "twin"],
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    out = tmp_path / "out"
    manifest = _manifest(tmp_path, commit, line=5)
    assert cli.main(_argv(manifest, coverage_report, repo, commit, out)) == 0
    record = json.loads((out / "runtime-anchors.json").read_text())
    assert record["proposed"] == []
    assert "ambiguous" in record["skipped"][0]["reason"]
