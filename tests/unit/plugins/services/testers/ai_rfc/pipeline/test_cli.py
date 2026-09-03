import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline import cli

pytestmark = pytest.mark.unit


def test_run_chains_the_deterministic_stages_and_stops_at_mining(
    workspace: Path, capsys
):
    """Reaching an agent stage is success, so the command exits 0 and says so.

    Nothing in the package proposes a claim; the run has done everything it can
    and the next move belongs to a model.
    """
    assert cli.main(["run", str(workspace)]) == 0
    stderr = capsys.readouterr().err
    assert "boundary: stage 5 (mining) is agent" in stderr
    assert "manifest.yaml" in stderr
    assert (workspace / "corpus" / "commits.jsonl").exists()
    assert (workspace / "timeline" / "timeline.json").exists()
    assert len(list((workspace / "clusters").iterdir())) == 2


def test_run_json_names_where_it_halted_and_what_it_did(workspace: Path, capsys):
    assert cli.main(["run", str(workspace), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["halted_at"] == "mining"
    assert [entry["stage"] for entry in payload["performed"]] == [
        "history",
        "timeline",
        "views",
    ]
    assert all(entry["exit_code"] == 0 for entry in payload["performed"])


def test_a_second_run_does_nothing_because_the_state_is_derived(
    workspace: Path, capsys
):
    """Idempotence falls out of reading the artifacts rather than a ledger."""
    assert cli.main(["run", str(workspace)]) == 0
    capsys.readouterr()
    assert cli.main(["run", str(workspace), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["halted_at"] == "mining"
    assert payload["performed"] == []


def test_until_stops_short_of_the_named_stage(workspace: Path):
    assert cli.main(["run", str(workspace), "--until", "history"]) == 0
    assert (workspace / "corpus").is_dir()
    assert not (workspace / "timeline").exists()


def test_forge_is_skipped_without_a_url_but_refused_when_asked_for(
    workspace: Path, capsys
):
    """Probe steps over forge; the runner must agree, or the two disagree.

    Enrichment is optional — a git-only timeline is a narrower reconstruction,
    not a broken one — but silently skipping a stage the caller explicitly
    named would be a different kind of wrong.
    """
    assert cli.main(["run", str(workspace), "--until", "timeline"]) == 0
    assert "skipping forge" in capsys.readouterr().err
    assert cli.main(["run", str(workspace), "--from", "forge"]) == 1
    assert "no --forge-url" in capsys.readouterr().err


def test_status_reports_every_stage_and_the_next_stage(workspace: Path, capsys):
    assert cli.main(["status", str(workspace)]) == 0
    out = capsys.readouterr().out
    assert "0  pin          done" in out
    assert "next: history (deterministic)" in out


def test_status_json_is_machine_readable(workspace: Path, capsys):
    assert cli.main(["status", str(workspace), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in payload["stages"]][:3] == [
        "pin",
        "history",
        "forge",
    ]
    assert payload["next_action"]["stage"] == "history"


def test_a_default_run_performs_the_manifest_check(mined_workspace, capsys):
    """The default path must not step over the one gate that reads the manifest.

    `next_stage` skips re-derivable stages, which is right for a driver asking
    what is outstanding and wrong as a description of what a run performs:
    `check` sits before the `prose` boundary and `gate` after it, so the walk
    reaches neither.
    """
    code = cli.main(["run", str(mined_workspace), "--strict", "--json"])

    assert code == 3
    performed = json.loads(capsys.readouterr().out)["performed"]
    assert "check" in [entry["stage"] for entry in performed]


def test_a_finished_workspace_still_performs_the_manifest_check(
    finished_workspace, capsys
):
    """The "nothing outstanding" case must not skip the re-derivable checks.

    `next_stage` reports nothing left to do once every stage is DONE or
    RECOMPUTED, which is right for a driver asking what remains — but a
    finished reconstruction can still carry a manifest whose evidence does
    not support what it claims, and the default `run --strict` must still
    catch that rather than trusting "nothing outstanding" as a clean exit.
    """
    code = cli.main(["run", str(finished_workspace), "--strict", "--json"])

    assert code == 3
    performed = json.loads(capsys.readouterr().out)["performed"]
    assert "check" in [entry["stage"] for entry in performed]


def test_gate_is_skipped_when_the_question_register_is_missing(
    finished_workspace, capsys
):
    """``prose`` reading DONE does not mean the question register exists.

    `_prose` (state.py) grades doneness from the draft repository and
    revisions.yaml alone; no stage this walk performs ever writes
    questions.yaml. Before this fix, `gate` ran anyway and its own CLI
    turned the missing file into an `error:` line and exit 1 — a spurious
    per-stage failure on an input `_prose` never promised. `check` must
    still run and drive the exit code, since it needs no register at all.
    """
    (finished_workspace / "questions.yaml").unlink()

    code = cli.main(["run", str(finished_workspace), "--strict", "--json"])
    captured = capsys.readouterr()

    assert code == 3
    performed = [entry["stage"] for entry in json.loads(captured.out)["performed"]]
    assert "check" in performed
    assert "gate" not in performed
    assert "error:" not in captured.err


def test_until_bounds_the_rederivable_checks_too(mined_workspace, capsys):
    """``--until``'s contract must hold for the whole command, not just the walk.

    `check` sits at ordinal 6; asking for ``--until views`` (ordinal 4) must
    keep it from running even though the walk itself performs nothing on a
    mined workspace before reaching `check`. Asking for ``--until check``
    must still run it.
    """
    code = cli.main(
        ["run", str(mined_workspace), "--until", "views", "--strict", "--json"]
    )
    assert code == 0
    performed = json.loads(capsys.readouterr().out)["performed"]
    assert "check" not in [entry["stage"] for entry in performed]

    code = cli.main(
        ["run", str(mined_workspace), "--until", "check", "--strict", "--json"]
    )
    assert code == 3
    performed = json.loads(capsys.readouterr().out)["performed"]
    assert "check" in [entry["stage"] for entry in performed]


def test_from_bounds_the_rederivable_checks_too(finished_workspace, capsys):
    """``--from``'s contract must hold for the whole command, not just the walk.

    Mirrors `test_until_bounds_the_rederivable_checks_too`: `check` sits at
    ordinal 6, three stages below `gate` at 9, so ``--from gate --until
    gate`` must keep it from running even though `_perform_rederivable`
    would otherwise perform every re-derivable stage regardless of where the
    walk started.
    """
    code = cli.main(
        [
            "run",
            str(finished_workspace),
            "--from",
            "gate",
            "--until",
            "gate",
            "--strict",
            "--json",
        ]
    )
    performed = [
        entry["stage"] for entry in json.loads(capsys.readouterr().out)["performed"]
    ]

    assert code == 0
    assert "gate" in performed
    assert "check" not in performed


def test_a_stage_the_walk_already_ran_is_not_performed_twice(mined_workspace, capsys):
    """``--from check`` puts `check` on the walk; it must not also re-run after.

    Idempotent either way — same violation, same exit code — but the JSON
    record must reflect one invocation of `check`, not two.
    """
    code = cli.main(
        ["run", str(mined_workspace), "--from", "check", "--strict", "--json"]
    )

    assert code == 3
    stages = [
        entry["stage"] for entry in json.loads(capsys.readouterr().out)["performed"]
    ]
    assert stages.count("check") == 1


def test_a_corrupt_artifact_reads_as_stale_rather_than_crashing(
    workspace: Path, capsys
):
    """Probing a half-written workspace is exactly when this happens.

    An unreadable artifact is a stage that needs re-running, which is what the
    report exists to say — not an exception for the caller to handle.
    """
    assert cli.main(["run", str(workspace), "--until", "timeline"]) == 0
    (workspace / "timeline" / "timeline.json").write_text("not json")
    capsys.readouterr()

    assert cli.main(["status", str(workspace), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    by_name = {entry["name"]: entry for entry in payload["stages"]}
    assert by_name["timeline"]["state"] == "stale"
    assert "unreadable" in by_name["timeline"]["reason"]
    assert payload["next_action"]["stage"] == "timeline"
