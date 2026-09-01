import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline import cli
from panther.plugins.services.testers.ai_rfc.pipeline.state import (
    State,
    next_stage,
    state,
)
from panther.plugins.services.testers.ai_rfc.pipeline.workspace import Workspace

pytestmark = pytest.mark.unit


def _states(root: Path) -> dict[str, State]:
    return {entry.stage.name: entry.state for entry in state(Workspace(root=root))}


def test_a_bare_clone_blocks_everything_downstream(workspace: Path):
    states = _states(workspace)
    assert states["pin"] is State.DONE
    assert states["history"] is State.PENDING
    assert states["timeline"] is State.BLOCKED
    assert states["views"] is State.BLOCKED


def test_next_stage_names_the_first_outstanding_stage(workspace: Path):
    action = next_stage(Workspace(root=workspace))
    assert action is not None
    assert action.stage.name == "history"
    assert action.is_agent is False


def test_an_absent_clone_is_pending_not_blocked(tmp_path: Path):
    action = next_stage(Workspace(root=tmp_path / "empty"))
    assert action is not None
    assert action.stage.name == "pin"
    assert action.stage.performer.value == "manual"


def test_a_dirty_clone_is_reported_but_does_not_block(workspace: Path):
    """Nothing downstream reads the working tree, so dirt must not cascade.

    history extracts from ``git log``, views reads git objects, and anchors
    resolve through ``git show <commit>:<path>``. Blocking here would hide a
    corpus and timeline that are perfectly current.
    """
    (workspace / "clone" / "uncommitted.txt").write_text("scratch\n")
    entry = next(e for e in state(Workspace(root=workspace)) if e.stage.name == "pin")
    assert entry.state is State.DONE
    assert "uncommitted" in entry.reason
    assert next_stage(Workspace(root=workspace)).stage.name == "history"


def test_a_moved_corpus_makes_the_timeline_stale(workspace: Path):
    """The digests the substrate already records are what detect this.

    Nothing tracks that the timeline was run; ``timeline.json`` carries the
    corpus digests, so a corpus edited afterwards is derivable rather than
    recorded.
    """
    assert cli.main(["run", str(workspace), "--until", "timeline"]) == 0
    assert _states(workspace)["timeline"] is State.DONE

    commits = workspace / "corpus" / "commits.jsonl"
    commits.write_text(commits.read_text() + "\n")
    states = _states(workspace)
    assert states["timeline"] is State.STALE
    assert states["views"] is State.BLOCKED


def test_views_emitted_from_an_older_timeline_are_stale(workspace: Path):
    assert cli.main(["run", str(workspace)]) == 0
    assert _states(workspace)["views"] is State.DONE

    timeline_json = workspace / "timeline" / "timeline.json"
    timeline_json.write_text(timeline_json.read_text() + "\n")
    assert _states(workspace)["views"] is State.STALE


def test_adjudicate_and_gate_are_never_reported_done(workspace: Path):
    """Both are pure and cheap, so the runner performs them rather than probing.

    Recording their doneness would need an input digest their output does not
    carry, and adding one would cost more than re-deriving the answer.
    """
    assert cli.main(["run", str(workspace)]) == 0
    states = _states(workspace)
    assert states["adjudicate"] is State.BLOCKED
    assert states["gate"] is State.BLOCKED


def _write_forge_meta(workspace: Path, **overrides) -> None:
    snapshot = workspace / "forge" / "gitlab__o__r" / "snapshot-2026-09-01T00-00-00Z"
    snapshot.mkdir(parents=True)
    meta = {
        "clone_head": "a" * 40,
        "complete": False,
        "denied_subfetches": 18,
        **overrides,
    }
    (snapshot / "meta.json").write_text(json.dumps(meta))


def test_a_snapshot_incomplete_at_its_ceiling_is_done(workspace: Path):
    """No credential exists that would improve it, so it is not stale.

    Reporting STALE here tells the operator to set a token they may not be
    able to get, and hides that the reconstruction is as good as this route
    allows.
    """
    _write_forge_meta(workspace, fidelity_ceiling="pulls", acquisition="api")
    entry = next(e for e in state(Workspace(root=workspace)) if e.stage.name == "forge")
    assert entry.state is State.DONE
    assert "ceiling" in entry.reason


def test_a_snapshot_incomplete_below_its_ceiling_is_stale(workspace: Path):
    """A token was used and calls were still refused, so a retry may help."""
    _write_forge_meta(workspace, fidelity_ceiling="pulls+discussion", acquisition="api")
    entry = next(e for e in state(Workspace(root=workspace)) if e.stage.name == "forge")
    assert entry.state is State.STALE


def test_a_complete_snapshot_below_full_fidelity_still_names_its_ceiling(
    workspace: Path,
):
    """An adopted pulls-only dump must not read like an authenticated fetch.

    Adoption refuses nothing, so ``complete`` is true while the records still
    carry no discussion. Grading on completeness alone would report it exactly
    as a full fetch, losing the one distinction this declaration exists to make.
    """
    _write_forge_meta(
        workspace,
        complete=True,
        denied_subfetches=0,
        fidelity_ceiling="pulls",
        acquisition="adopt",
    )
    entry = next(e for e in state(Workspace(root=workspace)) if e.stage.name == "forge")
    assert entry.state is State.DONE
    assert "pulls" in entry.reason


def test_a_snapshot_without_a_declaration_grades_as_before(workspace: Path):
    """Snapshots are immutable, so older ones keep their recorded meaning."""
    _write_forge_meta(workspace)
    entry = next(e for e in state(Workspace(root=workspace)) if e.stage.name == "forge")
    assert entry.state is State.STALE
    assert "GITLAB_TOKEN" in entry.reason
