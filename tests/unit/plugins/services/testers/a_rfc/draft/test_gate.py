from pathlib import Path

import pytest
import yaml

from panther.plugins.services.testers.a_rfc.draft.gate import GateError, run_gate

from .conftest import git

pytestmark = pytest.mark.unit


def _gate(workspace: dict[str, Path]) -> tuple[str, ...]:
    return run_gate(
        workspace["repo"],
        workspace["timeline"],
        workspace["checkpoints"],
        workspace["questions"],
        workspace["revisions"],
    )


def _patch_revisions(workspace: dict[str, Path], tag: str, **changes) -> None:
    document = yaml.safe_load(workspace["revisions"].read_text())
    document["revisions"][tag].update(changes)
    workspace["revisions"].write_text(yaml.safe_dump(document, sort_keys=True))


def test_clean_workspace_gates_clean(draft_workspace):
    assert _gate(draft_workspace) == ()


def test_register_tag_missing_from_repo_is_found(draft_workspace):
    git(draft_workspace["repo"], "tag", "-d", "draft-test-spec-01")
    findings = _gate(draft_workspace)
    assert any("draft-test-spec-01" in finding for finding in findings)


def test_repo_revision_tag_missing_from_register_is_found(draft_workspace):
    git(draft_workspace["repo"], "tag", "draft-test-spec-02")
    findings = _gate(draft_workspace)
    assert any("draft-test-spec-02" in finding for finding in findings)


def test_non_increasing_cluster_ordinals_are_found(draft_workspace):
    document = yaml.safe_load(draft_workspace["revisions"].read_text())
    first = document["revisions"]["draft-test-spec-00"]
    _patch_revisions(
        draft_workspace,
        "draft-test-spec-01",
        cluster_id=first["cluster_id"],
        checkpoint_manifest_sha256=first["checkpoint_manifest_sha256"],
    )
    findings = _gate(draft_workspace)
    assert any("ordinal" in finding for finding in findings)


def test_unknown_cluster_id_is_found(draft_workspace):
    _patch_revisions(
        draft_workspace, "draft-test-spec-01", cluster_id="c9999-pr-000000000000"
    )
    findings = _gate(draft_workspace)
    assert any("c9999" in finding for finding in findings)


def test_edited_checkpoint_manifest_is_found(draft_workspace):
    document = yaml.safe_load(draft_workspace["revisions"].read_text())
    cluster_id = document["revisions"]["draft-test-spec-01"]["cluster_id"]
    stored = draft_workspace["checkpoints"] / cluster_id / "manifest.yaml"
    stored.write_bytes(stored.read_bytes() + b"# drift\n")
    findings = _gate(draft_workspace)
    assert any("edited" in finding or "immutable" in finding for finding in findings)


def test_citation_of_unknown_claim_is_found(draft_workspace):
    repo = draft_workspace["repo"]
    git(repo, "tag", "-d", "draft-test-spec-01")
    draft_file = repo / "draft-test-spec.md"
    draft_file.write_text(draft_file.read_text() + "\nGhost. `a_rfc:spec:9.9`\n")
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "revision 01 with a ghost citation")
    git(repo, "tag", "draft-test-spec-01")
    findings = _gate(draft_workspace)
    assert any("spec:9.9" in finding for finding in findings)


def test_no_change_marker_with_changed_citations_is_found(draft_workspace):
    _patch_revisions(draft_workspace, "draft-test-spec-01", normative_change=False)
    findings = _gate(draft_workspace)
    assert any("normative" in finding for finding in findings)


def test_unregistered_question_id_is_found(draft_workspace, timeline_dir: Path):
    from panther.plugins.services.testers.a_rfc.draft.checkpoint import write_checkpoint

    from .conftest import _checkpoint_sha, _manifest_text

    document = yaml.safe_load(draft_workspace["revisions"].read_text())
    cluster_id = document["revisions"]["draft-test-spec-01"]["cluster_id"]
    manifest = timeline_dir.parent / "m2-bad-question.yaml"
    manifest.write_text(_manifest_text(with_second_claim=True, question_id="q-404"))
    stale = draft_workspace["checkpoints"] / cluster_id
    (stale / "manifest.yaml").unlink()
    (stale / "checkpoint.json").unlink()
    stale.rmdir()
    checkpoint_dir = write_checkpoint(
        manifest, timeline_dir, cluster_id, draft_workspace["checkpoints"]
    )
    _patch_revisions(
        draft_workspace,
        "draft-test-spec-01",
        checkpoint_manifest_sha256=_checkpoint_sha(checkpoint_dir),
    )
    findings = _gate(draft_workspace)
    assert any("q-404" in finding for finding in findings)


def test_missing_revisions_file_is_a_gate_error(draft_workspace):
    draft_workspace["revisions"].unlink()
    with pytest.raises((GateError, OSError)):
        _gate(draft_workspace)


def test_malformed_register_entry_is_a_gate_error(draft_workspace):
    document = yaml.safe_load(draft_workspace["revisions"].read_text())
    del document["revisions"]["draft-test-spec-01"]["normative_change"]
    draft_workspace["revisions"].write_text(yaml.safe_dump(document, sort_keys=True))
    with pytest.raises(GateError) as excinfo:
        _gate(draft_workspace)
    assert "normative_change" in str(excinfo.value)
