"""Build the aioquic w02-11 ground-truth dataset to the Ground-Truth Yardstick map's rules (ticket 09).

Rules applied (each is a resolved ticket on the map):
- 01: facts are true as the code at the window's end states them. The anchor is 509065a, the last
  member of the window's last cluster. Each scored fact cites the spec version the code declares
  (h3-22), verified against the pinned text by comparing values as integers.
- 02: a fact is reachable when its source line at the anchor is an added line in an in-window
  cluster diff of the same file (whitespace-stripped).
- 03: bare decimals are unscoreable. They stay as entries so the scorer excludes them itself and
  still uses their symbols to tell a symbol from part of a longer one, as today's dataset does.
- 08: shape as prototyped; each `statement` quotes the cited spec paragraph.
- 13: the dataset declares its `target` and `window`, so `analyze` can select it.

Self-contained: the spec reader is inlined, so this tracked asset doesn't depend on the git-ignored
research/ directory.

Run: ~/ai-rfc-experiments/code-pins/venv-3406985/bin/python build_dataset.py
Writes aioquic-w02-11-at-509065a.yaml beside this file. Reads only.
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MAP = HERE.parents[1]
SPEC = MAP / "assets/specs/draft-ietf-quic-http-22.txt"
PRISTINE = Path.home() / "ai-rfc-experiments/pristine/aioquic-w02-11"
ANCHOR = "509065ad2fe02d5ecbf335bdab06c7717fb510ca"
SOURCE = "aioquic/h3/connection.py"
TARGET = "aioquic"
WINDOW = (2, 11)
VCS = "g" + "it"

ENUM = re.compile(r"^class (ErrorCode|FrameType|Setting|StreamType)\(IntEnum\):")
MEMBER = re.compile(r"^    ([A-Z_]+) = (0x[0-9A-Fa-f]+|\d+)\s*$")
KIND = {"ErrorCode": "error_code", "FrameType": "frame_type", "Setting": "setting",
        "StreamType": "stream_type"}
HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.\s{2}(\S.*)$")
ERROR_ROW = re.compile(r"^   (HTTP_[A-Z_]+) \((0x[0-9A-Fa-f]+)\):")
FRAME_ROW = re.compile(r"\b([A-Z_]+)(?: frames?)? \(type=(0x[0-9A-Fa-f]+)\)")


def spec_lines() -> list[str]:
    # split("\n"), not splitlines(): the RFC text carries form-feed page breaks that splitlines()
    # counts as line ends, which would shift every cited line number (found in ticket 10).
    return SPEC.read_text().split("\n")


def spec_statements(lines: list[str]) -> dict[str, list[tuple[int, str, int]]]:
    """symbol -> [(value, section, 1-based line)] for every value-stating line of the draft body."""
    start = next(i for i, line in enumerate(lines) if line.startswith("1.  Introduction"))
    found: dict[str, list[tuple[int, str, int]]] = {}
    section = "?"
    for index in range(start, len(lines)):
        heading = HEADING.match(lines[index])
        if heading:
            section = heading.group(1)
            continue
        for pattern in (ERROR_ROW, FRAME_ROW):
            for match in pattern.finditer(lines[index]):
                found.setdefault(match.group(1), []).append(
                    (int(match.group(2), 16), section, index + 1))
    return found


def quoted_paragraph(lines: list[str], line: int) -> str:
    """The cited paragraph: from the cited line to the next blank line, whitespace collapsed."""
    block = []
    for text in lines[line - 1:]:
        if not text.strip():
            break
        block.append(text.strip())
    return " ".join(" ".join(block).split())


def statement_problems(statement: str, value: str) -> list[str]:
    problems = []
    tokens = {int(t, 16) for t in re.findall(r"0x[0-9A-Fa-f]+", statement)}
    if int(value, 16) not in tokens:
        problems.append("value not in the quoted paragraph")
    for marker in ("[Page", "Internet-Draft", "\f"):
        if marker in statement:
            problems.append(f"page-break artifact {marker!r}")
    if not statement.endswith("."):
        problems.append("paragraph does not end with a full stop")
    return problems


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
        for number, line in enumerate(
                (cluster / "span.diff").read_text(errors="replace").split("\n"), 1):
            if line.startswith("+++ "):
                path = line[4:].removeprefix("b/")
            elif line.startswith("+") and path:
                added.append((cluster.name, path, number, line[1:].strip()))
    return added


def main() -> int:
    lines = spec_lines()
    stated = spec_statements(lines)
    added = in_window_added_lines()
    entries, problems = [], []
    for fact in code_facts():
        slug = fact["symbol"].lower().removeprefix("http_").replace("_", "-")
        kind = fact["kind"]
        entry = {
            "id": f"h3-22-{kind.split('_')[0]}-{slug}",
            "statement": None,
            "symbol": fact["symbol"],
            "value": fact["value"],
            "kind": kind,
            "source": {"path": SOURCE, "line": fact["line"]},
        }
        hex_value = fact["value"].startswith("0x")
        rows = stated.get(fact["symbol"], []) if hex_value else []
        agree = [r for r in rows if r[0] == int(fact["value"], 16)] if hex_value else []
        if agree:
            _, section, spec_line = agree[0]
            entry["statement"] = quoted_paragraph(lines, spec_line)
            entry["citation"] = {"doc": SPEC.stem, "section": section, "line": spec_line}
            entry["citation_agrees"] = True
            problems += [f"{entry['id']}: {p}"
                         for p in statement_problems(entry["statement"], fact["value"])]
        else:
            entry["statement"] = (f"{fact['symbol']} = {fact['value']} at {ANCHOR[:7]} "
                                  f"({SOURCE}:{fact['line']}); not scored.")
            entry["citation"] = None
            entry["citation_agrees"] = False if rows else None
            entry["unscored_reason"] = (
                "bare decimal value: unscoreable from prose (ticket 03)" if not hex_value
                else "the cited draft states a different value (ticket 01, ruling 5)" if rows
                else "no statement in the pinned draft")
        hits = [(c, n) for c, p, n, content in added if p == SOURCE and content == fact["text"]]
        entry["reachable"] = {"cluster": hits[0][0], "diff_line": hits[0][1]} if hits else None
        entries.append(entry)
    document = {
        "repository": "https://github.com/aiortc/aioquic",
        "target": TARGET,
        "window": list(WINDOW),
        "commit": ANCHOR,
        "declared_spec": {
            "version": "h3-22",
            "evidence": ["examples/http3_client.py:294 alpn 'h3-22'",
                         "examples/http3_server.py:298,433 alpn 'h3-22'",
                         "aioquic/quic/configuration.py:80 QuicProtocolVersion.DRAFT_22"],
        },
        "specs": {SPEC.name: hashlib.sha256(SPEC.read_bytes()).hexdigest()},
        "entries": entries,
    }
    out = HERE / "aioquic-w02-11-at-509065a.yaml"
    out.write_text(yaml.safe_dump(document, sort_keys=False, width=100, allow_unicode=True))
    scored = [e for e in entries if e["value"].startswith("0x")]
    print(f"wrote {out.name}: {len(entries)} entries; {len(scored)} hex-scored "
          f"(cited+agreeing {sum(1 for e in scored if e['citation_agrees'])}, "
          f"reachable {sum(1 for e in scored if e['reachable'])}); "
          f"{len(entries) - len(scored)} decimal, excluded by the scorer")
    print(f"statement checks: {len(problems)} problem(s)")
    for problem in problems:
        print(f"  - {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
