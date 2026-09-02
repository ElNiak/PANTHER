import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline import cli
from panther.plugins.services.testers.ai_rfc.pipeline.state import (
    State,
    _checkpoint,
    _cluster_ids,
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


def test_a_partly_checkpointed_workspace_is_not_reported_as_finished(
    workspace: Path, capsys
):
    """The symptom itself, end to end: the answer `pipeline status` prints.

    The defect was never in a predicate a caller reads directly — it was that
    `status` said "nothing outstanding" for a reconstruction barely begun, and
    `next_stage` returned None so no driver was told to continue. Asserting the
    predicate alone would have left that unguarded, and building the chain is
    also what exercises the real cluster ids the count is taken over.
    """
    assert cli.main(["run", str(workspace)]) == 0
    (workspace / "manifest.yaml").write_text(
        "rfc: T\ntitle: 'Fixture'\nrequirements:\n"
        "  't:1':\n"
        "    text: 'A claim.'\n"
        "    section: '1'\n"
        "    level: MUST\n"
        "    layer: transport\n"
        "    status: gap\n"
    )
    ids = _cluster_ids(Workspace(root=workspace))
    assert len(ids) > 1, "a one-cluster timeline cannot express partial"
    checkpoint = workspace / "checkpoints" / ids[0]
    checkpoint.mkdir(parents=True)
    (checkpoint / "checkpoint.json").write_text("{}")

    entries = {entry.stage.name: entry for entry in state(Workspace(root=workspace))}
    assert entries["checkpoint"].state is State.PARTIAL
    assert entries["checkpoint"].reason == f"1 of {len(ids)} cluster(s) checkpointed"

    # Something is outstanding, which is the whole point. It is `prose` rather
    # than `checkpoint` because this fixture has no draft repository and prose
    # is the earlier stage — correct, and the reason the assertion is that a
    # stage is returned at all rather than which one.
    assert next_stage(Workspace(root=workspace)) is not None

    assert cli.main(["status", str(workspace)]) == 0
    printed = capsys.readouterr().out
    assert "nothing outstanding" not in printed
    assert f"partial — 1 of {len(ids)} cluster(s) checkpointed" in printed


def test_check_and_gate_are_never_reported_done(workspace: Path):
    """Both are pure and cheap, so the runner performs them rather than probing.

    Recording their doneness would need an input digest their output does not
    carry, and adding one would cost more than re-deriving the answer.
    """
    assert cli.main(["run", str(workspace)]) == 0
    states = _states(workspace)
    assert states["check"] is State.BLOCKED
    assert states["gate"] is State.BLOCKED


def _checkpointed(workspace: Path, *, of: int, frozen: int) -> tuple[State, str]:
    """Grade `checkpoint` over a timeline of ``of`` clusters, ``frozen`` done.

    Calls the predicate directly rather than through :func:`state`, because
    reaching `checkpoint` through the chain means standing up a clone, a corpus,
    a current timeline, views and a loaded manifest — none of which this
    predicate reads.
    """
    timeline = workspace / "timeline"
    timeline.mkdir(parents=True, exist_ok=True)
    timeline.joinpath("clusters.jsonl").write_text(
        "\n".join(json.dumps({"id": f"c{n:04d}"}) for n in range(1, of + 1)) + "\n"
    )
    for n in range(1, frozen + 1):
        directory = workspace / "checkpoints" / f"c{n:04d}"
        directory.mkdir(parents=True, exist_ok=True)
        # The record, not just the directory: write_checkpoint creates the
        # directory first, so one without a record is a checkpoint interrupted
        # mid-write rather than a frozen cluster.
        (directory / "checkpoint.json").write_text("{}")
    return _checkpoint(Workspace(root=workspace), State.DONE)


def test_a_partly_checkpointed_timeline_is_partial_not_done(workspace: Path):
    """The defect this state exists for: two clusters of sixty-nine read `done`.

    The predicate had the numbers in hand — it wrote "2 of 69" into its own note
    — and returned DONE beside them, so `pipeline status` answered "nothing
    outstanding" for a reconstruction that had barely started.
    """
    result, reason = _checkpointed(workspace, of=69, frozen=2)
    assert result is State.PARTIAL
    assert reason == "2 of 69 cluster(s) checkpointed"


def test_a_fully_checkpointed_timeline_is_done(workspace: Path):
    result, reason = _checkpointed(workspace, of=3, frozen=3)
    assert result is State.DONE
    assert reason == "3 of 3 cluster(s) checkpointed"


def test_no_checkpoint_at_all_is_pending(workspace: Path):
    result, _ = _checkpointed(workspace, of=3, frozen=0)
    assert result is State.PENDING


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
