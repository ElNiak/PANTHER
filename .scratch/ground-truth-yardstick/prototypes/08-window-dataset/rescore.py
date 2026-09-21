"""PROTOTYPE (ticket 08): score the pilot and v2 drafts against the w02-11 dataset built to the rules.

This prints the full per-fact state: matched / mismatched / named / absent / excluded, whether the
fact is reachable, and ticket 06's figures (reachable recall, all-facts recall, the ceiling, and
claim accuracy with its counts, per kind). It runs two checks:
- reproduction: the OLD dataset against the pilot draft must give SP7d's 8/35;
- truncation: re-score with whole tokens (research 03's edge-cut bug fixed) and list what changes.

PROVISIONAL until ticket 12's audit clears the drafts. Throwaway.
Run: ~/ai-rfc-experiments/code-pins/venv-3406985/bin/python rescore.py
"""

import json
import subprocess
from pathlib import Path

import yaml

import ai_rfc.experiment.ground_truth as gt

HERE = Path(__file__).resolve().parent
T11 = Path("/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/"
           ".claude/worktrees/iut-ai-rfc/panther/plugins/services/testers/ai_rfc/.superpowers/sdd/"
           "2026-09-15-arfc-sp7d/t11")
PILOT_DRAFT = (Path.home() / "arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831/runs/A1/"
               "workspace/draft")
VCS = "g" + "it"


def pilot(run: str, tag: str) -> str:
    """A pilot run's final draft, read with `git show` only (the evidence tree is never written)."""
    repo = str(PILOT_DRAFT).replace("/runs/A1/", f"/runs/{run}/")
    return subprocess.run(
        [VCS, "-C", repo, "show", f"{tag}:draft-elniak-aioquic-reconstructed.md"],
        capture_output=True, text=True, check=True).stdout


def drafts() -> dict[str, str]:
    # Each run's final draft is its revision for the window's last cluster, c0011: pilot A1
    # numbers it -10, pilot A2 -11 (both recorded in that run's revisions.yaml).
    return {"pilot v1 A1": pilot("A1", "draft-elniak-aioquic-reconstructed-10"),
            "pilot v1 A2": pilot("A2", "draft-elniak-aioquic-reconstructed-11"),
            "v2 A1": (T11 / "armA-drafts/A1-10.md").read_text(),
            "v2 A2": (T11 / "armA-drafts/A2-10.md").read_text()}


def named_ids(text: str, entries: list[dict], missed: tuple[str, ...]) -> set[str]:
    """Missed entries whose symbol the draft does name, outside any longer dataset symbol."""
    body = gt._normalised(text)
    patterns = [gt._symbol_pattern(e["symbol"]) for e in entries]
    spans = gt._symbol_spans(body, patterns)
    out = set()
    for entry, pattern in zip(entries, patterns):
        if entry["id"] in missed and any(
                not gt._inside_a_longer_symbol(m.span(), spans) for m in pattern.finditer(body)):
            out.add(entry["id"])
    return out


def outcomes(text: str, entries: list[dict]) -> dict[str, str]:
    report = gt.score_draft(text, entries)
    named = named_ids(text, entries, report.missed)
    state = {}
    for entry in entries:
        i = entry["id"]
        if i in report.matched:
            state[i] = "matched"
        elif i in report.attempted:
            state[i] = "mismatched"
        elif i in named:
            state[i] = "named"
        elif i in report.missed:
            state[i] = "absent"
        else:
            state[i] = "excluded"
    return state


def whole_token_tokens_near(body, symbol, token, named):
    """_tokens_near with research 03's edge-cut bug fixed: whole tokens that meet the window."""
    found = []
    for match in symbol.finditer(body):
        if gt._inside_a_longer_symbol(match.span(), named):
            continue
        low, high = max(0, match.start() - gt.NEARBY_CHARS), match.end() + gt.NEARBY_CHARS
        found += [t.group(0) for t in token.finditer(body) if t.start() < high and t.end() > low]
    return found


def figures(state: dict[str, str], entries: list[dict]) -> dict:
    scored = [e for e in entries if state[e["id"]] != "excluded"]
    reachable = [e for e in scored if e.get("reachable")]
    matched = [e for e in scored if state[e["id"]] == "matched"]
    attempted = [e for e in scored if state[e["id"]] in ("matched", "mismatched")]
    per_kind = {}
    for e in scored:
        row = per_kind.setdefault(e["kind"], {"scored": 0, "matched": 0, "mismatched": 0,
                                              "named": 0, "absent": 0})
        row["scored"] += 1
        row[state[e["id"]]] += 1
    fraction = lambda a, b: f"{len(a)}/{len(b)} = {len(a) / len(b):.3f}" if b else "None"  # noqa: E731
    return {
        "reachable recall": fraction([e for e in matched if e.get("reachable")], reachable),
        "all-facts recall": fraction(matched, scored),
        "ceiling": fraction(reachable, scored),
        "claim accuracy": (f"{len(matched) / len(attempted):.3f} ({len(attempted)} attempted of "
                           f"{len(reachable)} reachable)" if attempted else "None (nothing attempted)"),
        "named (diagnostic)": sum(1 for e in scored if state[e["id"]] == "named"),
        "per kind": per_kind,
    }


def main() -> None:
    new = yaml.safe_load((HERE / "aioquic-w02-11-at-509065a.PROTOTYPE.yaml").read_text())["entries"]
    old = gt.load_dataset()["entries"]
    texts = drafts()

    print("## Reproduction check: OLD dataset (tip 6d36838), pilot v1 A1")
    old_state = outcomes(texts["pilot v1 A1"], old)
    old_matched = sorted(i for i, s in old_state.items() if s == "matched")
    sp7d = sorted(json.loads((T11 / "gt-pilot/ground-truth.json").read_text())["matched"])
    scored_old = [i for i, s in old_state.items() if s != "excluded"]
    print(f"matched {len(old_matched)}/{len(scored_old)}; identical to SP7d t11/gt-pilot: "
          f"{old_matched == sp7d}\n")

    print("## NEW dataset (anchor 509065a), per draft")
    table = {}
    for name, text in texts.items():
        state = outcomes(text, new)
        table[name] = state
        print(f"\n### {name}")
        print(json.dumps(figures(state, new), indent=2))
    print("\n## Per-fact state (scored facts only; all 26 reachable)")
    names = list(texts)
    print("| fact | kind | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    for e in new:
        if table[names[0]][e["id"]] == "excluded":
            continue
        print(f"| `{e['symbol']}` = {e['value']} | {e['kind']} | "
              + " | ".join(table[n][e["id"]] for n in names) + " |")

    print("\n## Truncation check: whole-token scorer vs the pinned scorer")
    original = gt._tokens_near
    gt._tokens_near = whole_token_tokens_near
    try:
        changes = []
        for label, entries in (("old", old), ("new", new)):
            for name, text in texts.items():
                fixed = outcomes(text, entries)
                gt._tokens_near = original
                base = outcomes(text, entries)
                gt._tokens_near = whole_token_tokens_near
                changes += [f"{label} / {name} / {i}: {base[i]} -> {fixed[i]}"
                            for i in base if base[i] != fixed[i]]
    finally:
        gt._tokens_near = original
    print("\n".join(changes) if changes else "no outcome changes on either dataset")


if __name__ == "__main__":
    main()
