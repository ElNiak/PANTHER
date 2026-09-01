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
