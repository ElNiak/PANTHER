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
