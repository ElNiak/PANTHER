"""Throwaway probes for the parity audit; lives only in a scratch snapshot.

Each probe drives arm A's tool and arm B's verb over twin workspaces on an
input no twin in test_parity.py exercises, and prints what each arm did. The
probes assert nothing about the outcome: they record it.
"""

import json
import sys


def say(*parts):
    sys.__stdout__.write(" ".join(str(x) for x in parts) + "\n")
    sys.__stdout__.flush()

from ai_rfc import cli
from ai_rfc.server import tools


def _twins(make_workspace):
    build, use = make_workspace
    return build("tool-arm"), build("cli-arm"), use


def _run(label, call):
    try:
        return {"ok": call()}
    except Exception as error:  # noqa: BLE001 - recorded, not judged
        return {"error": f"{type(error).__name__}: {error}"}


def test_probe_schema_read(make_workspace, capsys):
    tool_arm, cli_arm, use = _twins(make_workspace)
    sql = "SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
    use(tool_arm)
    from_tool = _run("tool", lambda: tools.ai_rfc_corpus_query(sql))
    use(cli_arm)
    code = cli.main(["corpus", "query", sql])
    captured = capsys.readouterr()
    say("PROBE schema tool:", json.dumps(from_tool)[:600])
    say("PROBE schema cli exit:", code, "out:", captured.out[:600], "err:", captured.err[:300])


def test_probe_guardrail_refusal(make_workspace, capsys):
    tool_arm, cli_arm, use = _twins(make_workspace)
    sql = "DELETE FROM commits"
    use(tool_arm)
    from_tool = _run("tool", lambda: tools.ai_rfc_corpus_query(sql))
    use(cli_arm)
    code = cli.main(["corpus", "query", sql])
    captured = capsys.readouterr()
    say("PROBE refusal tool:", json.dumps(from_tool)[:400])
    say("PROBE refusal cli exit:", code, "err:", captured.err[:400])


def test_probe_anchor_upsert(make_workspace, capsys):
    tool_arm, cli_arm, use = _twins(make_workspace)
    code_anchor = {
        "evidence_class": "code",
        "locator": "src/a.py",
        "commit": "0" * 40,
        "line": 1,
    }
    adr_anchor = {"evidence_class": "adr", "locator": "0" * 40}
    fields = {"text": "Thing six.", "section": "6.1", "level": "MAY", "layer": "core"}
    use(tool_arm)
    from_tool = _run(
        "tool",
        lambda: tools.ai_rfc_claim_upsert(
            "t:6.1", {**fields, "anchors": [code_anchor, adr_anchor]}
        ),
    )
    use(cli_arm)
    code = cli.main(
        [
            "claim",
            "upsert",
            "t:6.1",
            "--text",
            fields["text"],
            "--section",
            fields["section"],
            "--level",
            fields["level"],
            "--layer",
            fields["layer"],
            "--anchor",
            json.dumps(code_anchor),
            "--anchor",
            json.dumps(adr_anchor),
        ]
    )
    captured = capsys.readouterr()
    same = (tool_arm / "manifest.yaml").read_bytes() == (
        cli_arm / "manifest.yaml"
    ).read_bytes()
    written = "t:6.1" in (tool_arm / "manifest.yaml").read_text()
    say("PROBE anchors tool:", json.dumps(from_tool)[:400])
    say("PROBE anchors cli exit:", code, "err:", captured.err[:300])
    say("PROBE anchors manifests byte-equal:", same, "| claim written:", written)
