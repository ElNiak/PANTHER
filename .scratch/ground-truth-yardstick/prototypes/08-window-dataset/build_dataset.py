"""PROTOTYPE (ticket 08): build the aioquic w02-11 dataset to the map's rules. Throwaway.

Rules applied:
- 01: facts are true as the code at the window's end states them; anchor 509065a; each scored fact
  cites the spec version the code declares (h3-22), verified against the pinned text.
- 02: a fact is reachable when its source line is an added line in an in-window cluster diff of the
  same file (whitespace-stripped).
- 03: bare decimals are unscoreable. They stay as entries so the scorer excludes them itself and
  still uses their symbols for longer-symbol disambiguation, exactly as today's dataset does.

Run: ~/ai-rfc-experiments/code-pins/venv-3406985/bin/python build_dataset.py
Writes aioquic-w02-11-at-509065a.PROTOTYPE.yaml beside this file. Reads only.
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MAP = HERE.parents[1]
sys.path.insert(0, str(MAP / "research/10-pin"))
from agree import spec_statements  # noqa: E402  (ticket 10's exact-pattern spec reader)

PRISTINE = Path.home() / "ai-rfc-experiments/pristine/aioquic-w02-11"
ANCHOR = "509065ad2fe02d5ecbf335bdab06c7717fb510ca"
SOURCE = "aioquic/h3/connection.py"
WINDOW = (2, 11)
VCS = "g" + "it"

ENUM = re.compile(r"^class (ErrorCode|FrameType|Setting|StreamType)\(IntEnum\):")
MEMBER = re.compile(r"^    ([A-Z_]+) = (0x[0-9A-Fa-f]+|\d+)\s*$")
KIND = {"ErrorCode": "error_code", "FrameType": "frame_type", "Setting": "setting",
        "StreamType": "stream_type"}
NOUN = {"error_code": "error code", "frame_type": "frame type", "setting": "setting",
        "stream_type": "stream type"}


def code_facts() -> list[dict]:
    text = subprocess.run([VCS, "-C", str(PRISTINE / "clone"), "show", f"{ANCHOR}:{SOURCE}"],
                          capture_output=True, text=True, check=True).stdout
    facts, kind = [], None
    for number, line in enumerate(text.split("\n"), 1):
        start = ENUM.match(line)
        if start:
            kind = KIND[start.group(1)]
            continue
        if kind and line and not line.startswith(" "):
            kind = None
        member = MEMBER.match(line) if kind else None
        if member:
            facts.append({"kind": kind, "symbol": member.group(1), "value": member.group(2),
                          "line": number, "text": line.strip()})
    return facts


def in_window_added_lines() -> list[tuple[str, str, int, str]]:
    """(cluster, path, diff line, stripped content) for every added line in c0002..c0011."""
    added = []
    for cluster in sorted(PRISTINE.joinpath("clusters").iterdir()):
        ordinal = int(cluster.name[1:5])
        if not WINDOW[0] <= ordinal <= WINDOW[1]:
            continue
        path = None
        for number, line in enumerate((cluster / "span.diff").read_text(errors="replace")
                                      .split("\n"), 1):
            if line.startswith("+++ "):
                path = line[4:].removeprefix("b/")
            elif line.startswith("+") and path:
                added.append((cluster.name, path, number, line[1:].strip()))
    return added


def main() -> None:
    facts = code_facts()
    stated = spec_statements()
    added = in_window_added_lines()
    spec = MAP / "assets/specs/draft-ietf-quic-http-22.txt"
    entries = []
    for fact in facts:
        slug = fact["symbol"].lower().removeprefix("http_").replace("_", "-")
        kind = fact["kind"]
        entry = {
            "id": f"h3-22-{kind.split('_')[0]}-{slug}",
            "statement": f"In aioquic at 509065a (h3-22), {fact['symbol']} is the HTTP/3 "
                         f"{NOUN[kind]} with value {fact['value']}.",
            "symbol": fact["symbol"],
            "value": fact["value"],
            "kind": kind,
            "source": {"path": SOURCE, "line": fact["line"]},
        }
        rows = stated.get(fact["symbol"], [])
        hex_value = fact["value"].startswith("0x")
        if hex_value and rows:
            value = int(fact["value"], 16)
            agree = [r for r in rows if r[0] == value]
            entry["citation"] = ({"doc": spec.stem, "section": agree[0][1], "line": agree[0][2]}
                                 if agree else None)
            entry["citation_agrees"] = bool(agree)
        else:
            entry["citation"] = None
            entry["unscored_reason"] = ("bare decimal value: unscoreable from prose (ticket 03)"
                                        if not hex_value else "no statement in the pinned draft")
        hits = [(c, n) for c, p, n, content in added if p == SOURCE and content == fact["text"]]
        entry["reachable"] = ({"cluster": hits[0][0], "diff_line": hits[0][1]} if hits else None)
        entries.append(entry)
    document = {
        "prototype": "ticket 08 of the Ground-Truth Yardstick map; throwaway",
        "repository": "https://github.com/aiortc/aioquic",
        "commit": ANCHOR,
        "window": list(WINDOW),
        "declared_spec": {
            "version": "h3-22",
            "evidence": ["examples/http3_client.py:294 alpn 'h3-22'",
                         "examples/http3_server.py:298,433 alpn 'h3-22'",
                         "aioquic/quic/configuration.py:80 QuicProtocolVersion.DRAFT_22"],
        },
        "specs": {spec.name: hashlib.sha256(spec.read_bytes()).hexdigest()},
        "entries": entries,
    }
    out = HERE / "aioquic-w02-11-at-509065a.PROTOTYPE.yaml"
    out.write_text(yaml.safe_dump(document, sort_keys=False, width=100))
    scored = [e for e in entries if e["value"].startswith("0x")]
    print(f"wrote {out.name}: {len(entries)} entries ({len(scored)} hex-scored, "
          f"{len(entries) - len(scored)} decimal, excluded by the scorer); "
          f"cited+agreeing {sum(1 for e in scored if e.get('citation_agrees'))}, "
          f"reachable {sum(1 for e in scored if e['reachable'])}")


if __name__ == "__main__":
    main()
