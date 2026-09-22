# ai_rfc Ground-Truth Measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ai_rfc measure a draft against a window-anchored, cited, reachability-aware ground
truth. This covers the scorer, the datasets, the `ground-truth` verb, `analyze`, the campaign report,
the transcript audit's future-material verdict, and the judge's completeness caveat.

**Architecture:** The datasets become self-describing: they carry a target, a window, an anchor
commit, a declared spec, pinned spec texts, and a citation and reachability record per fact.
`ground_truth.py` selects a dataset by target and window and scores with named/absent outcomes and
reachability-aware figures. A new `future.py` classifies each transcript for future material. The
audit carries that verdict, `analyze` attaches a ground-truth record per run, and arms leave out
touched runs. The report gains a "Ground truth" section.

**Tech Stack:** Python 3.10 (`<wt>/.venv`), pytest + xdist, PyYAML, git (subprocess, read-only
`git show` / `git rev-list` / `git log`).

**Spec:** `docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md` (PANTHER). The
rulings behind it are the tickets of the map `.scratch/ground-truth-yardstick/` (PANTHER `6b2e70f14`).
This plan implements the spec's **measurement** half: §3–§6, §7.3 and §8–§10. The **prevention**
half (§7.1 future-free `workspace prepare`, §7.2 `cluster_get` window check, §7.4 path guard) is
`docs/superpowers/plans/2026-09-22-arfc-future-free-workspace.md`, written 2026-09-22 after the
user settled research 11's open questions. It runs **after** this plan, because both edit
`experiment/audit.py`.

`<wt>` = the PANTHER worktree `…/PANTHER/master/.claude/worktrees/iut-ai-rfc`.
`<ai_rfc>` = `<wt>/panther/plugins/services/testers/ai_rfc` (ai_rfc repo, branch `main`).
`<map>` = `<wt>/.scratch/ground-truth-yardstick`.
`<pristine>` = `~/ai-rfc-experiments/pristine/aioquic-w02-11`. It holds all 342 aioquic clusters,
and its `clone/` holds both anchors, `509065a` and `6d36838`. **Read-only evidence: never write
there.**

## Global Constraints

- **Cost and credentials:** $0. No `claude` call, and never an Anthropic API key.
- **Tests:** run every test with `SSLKEYLOGFILE= <wt>/.venv/bin/python -m pytest <paths> -q -n 4
  --basetemp /tmp/claude-501/pytest-gtm-<task>`, from `<ai_rfc>`. Never `-n auto`, which hangs.
  Report collected / passed / failed / skipped separately, never as a total.
- **Git discipline:**
  - Stage by explicit path, and run `git status --short` in every repo you touch before each commit.
  - Never `git add -A` / `git add .`, `--no-verify`, `git stash`, or amending a commit on the
    branch.
  - Commit with the paths as a pathspec: `git commit -m … -- <paths>`.
- **No compatibility shims:** a replaced field or function is removed, and every caller is updated
  in the same task.
- **Unmeasured is never zero:** a figure nobody measured is `None`/null in JSON, and "—" plus a
  status in text or tables.
- **Naming:** the scorer's figure is `claim_accuracy`, never "precision"; the judge owns that word.
- **Byte-exact spec texts:** pinned spec texts are never edited. Each is verified against
  `SHA256SUMS`, and nothing may rewrite them (check pre-commit in Task 0).
- **Evidence trees are read-only:** never re-run `audit` or `analyze` on a campaign under
  `~/ai-rfc-experiments/campaigns/` or `~/arfc-experiments/`. Acceptance runs copy the campaign under
  `/tmp/claude-501/` first.
- **Code citations:** cite code by function name. Line numbers drift, because the owed-fixes row
  changes these files.
- **Docstrings:** Google-style (Args/Returns/Raises) on every public function.
- **Commit messages** carry no attribution lines.

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `<ai_rfc>/ai_rfc/experiment/ground_truth.py` | Datasets (list, load, select), scoring, figures, per-run scoring. Anchor resolution through git objects. | 1–4, 6 |
| `<ai_rfc>/ai_rfc/experiment/groundtruth/aioquic-w02-11-at-509065a.yaml` | **New.** The window-anchored w02-11 dataset. | 3 |
| `<ai_rfc>/ai_rfc/experiment/groundtruth/aioquic-h3-at-6d36838.yaml` | **Renamed and migrated** from `aioquic-w02-11.yaml` (tip anchor, window [1, 342]). | 3 |
| `<ai_rfc>/ai_rfc/experiment/groundtruth/targets.yaml` | **New.** Targets whose code declares no spec (ticket 07). | 3 |
| `<ai_rfc>/ai_rfc/experiment/groundtruth/specs/` | **New.** Pinned spec texts + `SHA256SUMS`. | 3 |
| `<ai_rfc>/pyproject.toml` | Package data for `groundtruth/specs/`. | 3 |
| `<ai_rfc>/ai_rfc/experiment/future.py` | **New.** Window end, and the future-material verdict for one transcript. | 5 |
| `<ai_rfc>/ai_rfc/experiment/audit.py` | Records read-tool paths; `audit_run` carries `future_material`. | 5 |
| `<ai_rfc>/ai_rfc/experiment/metrics.py` | `analyze_run` adds `ground_truth`; `_arm_summary` adds pooled figures (clean runs only); `DEFINITIONS`. | 6 |
| `<ai_rfc>/ai_rfc/experiment/report.py` | "Ground truth" section. | 7 |
| `<ai_rfc>/ai_rfc/experiment/cli.py` | The verb's dataset arguments and output; the judge caveat. | 2, 3, 8 |
| `<ai_rfc>/tests/experiment/test_ground_truth.py`, `test_cli_ground_truth.py`, `test_future.py` (new), `test_audit.py`, `test_metrics.py`, `test_report.py`, `test_cli_judge.py` | Tests | 1–8 |
| `<ai_rfc>/CONTEXT.md` | **New.** Glossary. | 9 |
| `<ai_rfc>/docs/experiments/2026-09-21-sp7d-phase5.md` | **Not written here.** The SP7d Phase 5 write-up carries the recall correction; Task 9 only confirms it landed. The instrument recording is never edited. | 9 |
| `<wt>/docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md`, `<wt>/docs/superpowers/plans/2026-09-15-arfc-sp7d-deviations.md` | D-row; deviation entry (PANTHER). | 9 |

---

## Task 0: Entry gate (no code)

- [ ] **Step 1 — the owed-fixes row has landed.** This plan edits `ground_truth.py`, `metrics.py`,
  `audit.py`, `report.py` and `cli.py`, which that row's Tasks 7 and 8 also change. Do not start
  until its hand-over (its Task 13) is done and ai_rfc `main` is clean. Check with `ListAgents` and
  the row's handoff memory file. If the row is still running, stop and report.
- [ ] **Step 2 — re-read the sites by name.** Confirm these exist on `main`:
  - in `ground_truth.py`: `load_dataset`, `resolve_anchors`, `GroundTruthReport`, `score_draft`,
    `_tokens_near`, `_inside_a_longer_symbol`;
  - in `experiment/cli.py`: `_write_ground_truth`, `_ground_truth_run`, `_judge_run`;
  - in `metrics.py`: `analyze_run`, `_arm_summary`, `DEFINITIONS`;
  - in `report.py`: `render_report`;
  - in `audit.py`: `audit_run`, and the read-tool branch of the call classifier (today it returns
    `"read", name, ""`);
  - `tool_uses` and `tool_results` in `driver/stream.py`; `draft_text` and `latest_tag` in
    `draft/gate.py`.

  For each one that moved or was renamed, record the new name in this plan's deviation log before
  using it.
- [ ] **Step 3 — pre-commit on pinned texts.** `ls <ai_rfc>/.pre-commit-config.yaml`. If it exists
  and runs `trailing-whitespace` or `end-of-file-fixer`, add
  `ai_rfc/experiment/groundtruth/specs/` to their `exclude`, as its own commit
  (`chore(pre-commit): leave pinned spec texts byte-exact`). This is how PANTHER `030f1d0c5` fixed
  the same problem.
- [ ] **Step 4 — the environment.** `/usr/bin/git --version` exits 0 (an unaccepted Xcode licence
  fails about 60 tests). `<pristine>/clone` exists and `git -C <pristine>/clone cat-file -e
  509065a` and `… 6d36838` both succeed.
- [ ] **Step 5 — the baseline.** Run the full suite (`tests/`) with the Global Constraints command.
  Record collected / passed / failed / skipped. Known flakes pass alone.

## Task 1: Whole tokens in the proximity window

The fix for the edge-truncation bug (spec §4.6, found in ticket 03). `_tokens_near` slices the body
and then runs `findall`, so a hex token straddling the slice's end is cut short (`0x10A` is read as
`0x1`).

**Files:**
- Modify: `<ai_rfc>/ai_rfc/experiment/ground_truth.py` (`_tokens_near`)
- Test: `<ai_rfc>/tests/experiment/test_ground_truth.py`

**Interfaces:** Consumes: nothing new. Produces: `_tokens_near(body, symbol, token, named) ->
list[str]`, same signature and new semantics (whole tokens whose span meets the window).

- [ ] **Step 1: Write the failing test** (append to `test_ground_truth.py`)

```python
def test_a_token_straddling_the_window_edge_is_read_whole_not_cut():
    # "H3_NO_ERROR " is 12 characters, so the token starts at 13 + k. The window ends
    # NEARBY_CHARS after the symbol's end (11), so it closes at 11 + NEARBY_CHARS.
    # k = NEARBY_CHARS - 5 starts "0x10A" three characters before the window closes:
    # a slice there keeps "0x1", which the old matcher read as a whole token.
    k = NEARBY_CHARS - 5
    entry = {
        "id": "straddle",
        "statement": "",
        "symbol": "H3_NO_ERROR",
        "value": "0x1",
        "kind": "error_code",
        "source": {"path": "p", "line": 1},
    }
    report = score_draft(f"H3_NO_ERROR {'a' * k} 0x10A", [entry])
    assert report.matched == ()
    assert report.attempted == ("straddle",)
```

- [ ] **Step 2: Run it and see it fail**

Run: `SSLKEYLOGFILE= <wt>/.venv/bin/python -m pytest tests/experiment/test_ground_truth.py -q -n 4 --basetemp /tmp/claude-501/pytest-gtm-1 -k straddling`
Expected: FAIL. `report.matched == ("straddle",)`, because the cut token `0x1` equals the value.

- [ ] **Step 3: Implement** (replace the loop body in `_tokens_near`; keep its docstring, and add
  one paragraph saying tokens are found in the whole body and kept when their span meets the window)

```python
    found: list[str] = []
    for match in symbol.finditer(body):
        if _inside_a_longer_symbol(match.span(), named):
            continue
        low = max(0, match.start() - NEARBY_CHARS)
        high = match.end() + NEARBY_CHARS
        # Found in the whole body, then kept when the span meets the window: a
        # slice cuts a token that straddles its edge ("0x10A" read as "0x1"),
        # and the cut token can equal the value and be credited as a match.
        found += [
            candidate.group(0)
            for candidate in token.finditer(body)
            if candidate.start() < high and candidate.end() > low
        ]
    return found
```

- [ ] **Step 4: Run the module and see everything pass**

Run: `… -m pytest tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py -q -n 4 --basetemp /tmp/claude-501/pytest-gtm-1`
Expected: all pass. Ticket 08 measured that the fix changes no existing outcome.

- [ ] **Step 5: Commit** (`git status --short` first)

```bash
git add tests/experiment/test_ground_truth.py ai_rfc/experiment/ground_truth.py
git commit -m "fix(experiment): read a value near a symbol whole, not cut at the window edge" -- tests/experiment/test_ground_truth.py ai_rfc/experiment/ground_truth.py
```

## Task 2: Named and absent outcomes, reachability-aware figures, per-kind counts, and the verb's output

Spec §4.4, §4.5 (dataset-declared exclusions) and §5 (tickets 02, 06).

**Files:**
- Modify: `ground_truth.py`: `GroundTruthReport`, `score_draft`, plus a new `_mentioned` and a new
  `figures`
- Modify: `experiment/cli.py`: `_write_ground_truth` and `_ground_truth_run`
- Test: `tests/experiment/test_ground_truth.py`, `tests/experiment/test_cli_ground_truth.py`

**Interfaces:**
- Produces: `GroundTruthReport` fields `matched, attempted, named, absent, excluded_because,
  reachable, kinds`. `missed` and `recall` are removed.
- Produces: properties `excluded, scored, mismatched, all_facts_recall, reachable_recall, ceiling,
  claim_accuracy`, and the method `per_kind() -> dict[str, dict[str, int]]`.
- Produces: `figures(report: GroundTruthReport) -> dict[str, Any]`, the JSON-ready figures shared by
  the verb (this task) and `score_run` (Task 6).

- [ ] **Step 1: Write the failing tests** (append to `test_ground_truth.py`)

```python
def _entry(entry_id, symbol, value, *, kind="error_code", reachable=True, **extra):
    return {
        "id": entry_id,
        "statement": "",
        "symbol": symbol,
        "value": value,
        "kind": kind,
        "source": {"path": "p", "line": 1},
        "reachable": {"cluster": "c0005-x", "diff_line": 1} if reachable else None,
        **extra,
    }


def test_a_symbol_named_without_a_value_is_named_not_absent_and_not_attempted():
    entries = [_entry("wrong", "HTTP_WRONG_STREAM", "0x0A"), _entry("gone", "HTTP_ID_ERROR", "0x0B")]
    report = score_draft("close with error HTTP_WRONG_STREAM on any other frame.", entries)
    assert report.named == ("wrong",)
    assert report.absent == ("gone",)
    assert report.attempted == ()
    assert report.claim_accuracy is None


def test_a_symbol_inside_a_longer_dataset_symbol_is_not_named():
    entries = [_entry("settings", "SETTINGS", "0x4", kind="frame_type"),
               _entry("err", "HTTP_SETTINGS_ERROR", "0xFF")]
    report = score_draft("the peer sent HTTP_SETTINGS_ERROR.", entries)
    assert "settings" in report.absent
    assert "err" in report.named


def test_reachable_recall_counts_reachable_facts_and_the_ceiling_says_how_many():
    entries = [
        _entry("a", "HTTP_NO_ERROR", "0x00"),
        _entry("b", "HTTP_ID_ERROR", "0x0B"),
        _entry("c", "HTTP_EARLY_RESPONSE", "0x11", reachable=False),
    ]
    report = score_draft("HTTP_NO_ERROR is 0x00 and HTTP_EARLY_RESPONSE is 0x11.", entries)
    assert report.matched == ("a", "c")
    assert report.reachable == ("a", "b")
    assert report.reachable_recall == 0.5
    assert report.all_facts_recall == 2 / 3
    assert report.ceiling == 2 / 3


def test_reachable_recall_is_none_when_nothing_is_reachable_never_zero():
    report = score_draft("nothing", [_entry("a", "HTTP_NO_ERROR", "0x00", reachable=False)])
    assert report.reachable_recall is None
    assert report.ceiling == 0.0


def test_per_kind_partitions_every_scored_entry_by_outcome():
    entries = [
        _entry("a", "HTTP_NO_ERROR", "0x00"),
        _entry("b", "HTTP_WRONG_STREAM", "0x0A"),
        _entry("d", "DATA", "0x0", kind="frame_type"),
    ]
    # Spaced beyond the proximity window, so each symbol sees only its own value:
    # otherwise HTTP_WRONG_STREAM would read 0x00 as an attempt, not a naming.
    gap = " lorem" * (NEARBY_CHARS // 3)
    report = score_draft(
        f"HTTP_NO_ERROR is 0x00.{gap} HTTP_WRONG_STREAM closes it.{gap} DATA is 0x1.", entries
    )
    assert report.per_kind() == {
        "error_code": {"scored": 2, "matched": 1, "mismatched": 0, "named": 1, "absent": 0},
        "frame_type": {"scored": 1, "matched": 0, "mismatched": 1, "named": 0, "absent": 0},
    }


def test_an_entry_the_dataset_declares_unscored_is_excluded_with_its_reason():
    entry = _entry("dgram", "H3_DATAGRAM", "0x33",
                   unscored_reason="cited spec RFC 9297 is not declared by the code")
    report = score_draft("H3_DATAGRAM is 0x33.", [entry])
    assert report.excluded_because == (("dgram", "cited spec RFC 9297 is not declared by the code"),)
    assert report.scored == 0
```

And in `test_cli_ground_truth.py`, replace the `recall`/`missed` assertions with the new fields.
(`test_the_report_carries_every_id_the_two_ratios_were_taken_over` and the terminal tests are the
ones affected.) Add:

```python
def test_the_report_carries_the_figures_their_counts_and_the_per_kind_table(tmp_path):
    code, path = _score(tmp_path, DRAFT)
    payload = json.loads(path.read_text())
    for key in ("reachable_recall", "all_facts_recall", "ceiling", "claim_accuracy",
                "claim_accuracy_counts", "per_kind", "named", "absent", "reachable"):
        assert key in payload
    assert "missed" not in payload and "recall" not in payload
    assert set(payload["claim_accuracy_counts"]) == {"attempted", "reachable"}


def test_the_terminal_prints_claim_accuracy_with_its_counts(tmp_path, capsys):
    _score(tmp_path, DRAFT)
    out = capsys.readouterr().out
    assert "claim accuracy: " in out and " attempted of " in out and " reachable)" in out
```

- [ ] **Step 2: Run them and see them fail**

Run: `… -m pytest tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py -q -n 4 --basetemp /tmp/claude-501/pytest-gtm-2`
Expected: FAIL (`GroundTruthReport` has no attribute `named`, and the payload has no `reachable_recall`).

- [ ] **Step 3: Implement the report type** (replace the dataclass fields and properties; keep the
  class docstring, rewritten for the new partition)

```python
@dataclass(frozen=True)
class GroundTruthReport:
    """One draft's standing against the entries a dataset could score.

    The scored entries are partitioned four ways. ``matched`` and the derived
    ``mismatched`` make up ``attempted``: the symbol was named beside a value of
    the right shape. ``named`` means the symbol was named with no such value
    nearby, which is a diagnostic and not an attempt. ``absent`` means the
    symbol was never named. ``reachable`` lists the scored entries whose source
    line an in-window diff adds (ticket 02). ``kinds`` records each scored
    entry's kind, for the per-kind table.

    Attributes:
        matched: Ids stated with the value the pinned source spells.
        attempted: Ids named beside some value of the right shape.
        named: Ids named with no value of the right shape nearby.
        absent: Ids never named.
        excluded_because: One ``(id, reason)`` pair per entry nothing scored.
        reachable: Scored ids whose source line an in-window diff adds.
        kinds: One ``(id, kind)`` pair per scored entry, in dataset order.
    """

    matched: tuple[str, ...]
    attempted: tuple[str, ...]
    named: tuple[str, ...]
    absent: tuple[str, ...]
    excluded_because: tuple[tuple[str, str], ...]
    reachable: tuple[str, ...]
    kinds: tuple[tuple[str, str], ...]

    @property
    def excluded(self) -> tuple[str, ...]:
        """The ids of the excluded entries alone, in dataset order."""
        return tuple(name for name, _ in self.excluded_because)

    @property
    def scored(self) -> int:
        """How many entries the draft was scored against."""
        return len(self.attempted) + len(self.named) + len(self.absent)

    @property
    def mismatched(self) -> tuple[str, ...]:
        """Attempted ids whose stated value is not the one the source spells."""
        matched = set(self.matched)
        return tuple(name for name in self.attempted if name not in matched)

    @property
    def all_facts_recall(self) -> float | None:
        """Matched over scored, or ``None`` when nothing was scored."""
        return len(self.matched) / self.scored if self.scored else None

    @property
    def reachable_recall(self) -> float | None:
        """Matched reachable facts over reachable facts, or ``None`` when none is reachable."""
        if not self.reachable:
            return None
        reachable = set(self.reachable)
        return sum(1 for name in self.matched if name in reachable) / len(self.reachable)

    @property
    def ceiling(self) -> float | None:
        """Reachable over scored: the most all-facts recall can reach."""
        return len(self.reachable) / self.scored if self.scored else None

    @property
    def claim_accuracy(self) -> float | None:
        """Matched over attempted, or ``None`` when nothing was attempted.

        Not called precision: ``JUDGE_DIMENSIONS`` grades a dimension by that
        name on another scale.
        """
        if not self.attempted:
            return None
        return len(self.matched) / len(self.attempted)

    def per_kind(self) -> dict[str, dict[str, int]]:
        """Matched / mismatched / named / absent per kind, over the scored entries.

        Returns:
            One row per kind: ``scored`` and a count per outcome.
        """
        outcome = {name: "absent" for name in self.absent}
        outcome.update({name: "named" for name in self.named})
        outcome.update({name: "mismatched" for name in self.mismatched})
        outcome.update({name: "matched" for name in self.matched})
        table: dict[str, dict[str, int]] = {}
        for name, kind in self.kinds:
            row = table.setdefault(
                kind, {"scored": 0, "matched": 0, "mismatched": 0, "named": 0, "absent": 0}
            )
            row["scored"] += 1
            row[outcome[name]] += 1
        return table
```

- [ ] **Step 4: Implement the scoring loop** (in `score_draft`, after `symbols` is built; the spans
  local is renamed `spans` so that `named` means the outcome)

```python
    spans = _symbol_spans(body, symbols)
    matched: list[str] = []
    attempted: list[str] = []
    named: list[str] = []
    absent: list[str] = []
    excluded: list[tuple[str, str]] = []
    reachable: list[str] = []
    kinds: list[tuple[str, str]] = []
    for entry, symbol in zip(entries, symbols):
        value = _text(entry, "value")
        shape = _value_shape(value)
        if shape is None:
            excluded.append((entry["id"], _why_not_scored(value)))
            continue
        declared = entry.get("unscored_reason")
        if declared:
            # The dataset's own exclusion: a citation that disagrees with the
            # code or cites a spec the code does not declare (tickets 01, 07).
            excluded.append((entry["id"], str(declared)))
            continue
        kinds.append((entry["id"], str(entry.get("kind", ""))))
        if entry.get("reachable"):
            reachable.append(entry["id"])
        token, base = shape
        tokens = _tokens_near(body, symbol, token, spans)
        if not tokens:
            (named if _mentioned(body, symbol, spans) else absent).append(entry["id"])
            continue
        attempted.append(entry["id"])
        wanted = int(value, base)
        if any(int(found, base) == wanted for found in tokens):
            matched.append(entry["id"])
    return GroundTruthReport(
        matched=tuple(matched),
        attempted=tuple(attempted),
        named=tuple(named),
        absent=tuple(absent),
        excluded_because=tuple(excluded),
        reachable=tuple(reachable),
        kinds=tuple(kinds),
    )
```

Add the helper and the shared figures:

```python
def _mentioned(body: str, symbol: Pattern[str], spans: tuple[tuple[int, int], ...]) -> bool:
    """Whether the draft names the symbol anywhere outside a longer dataset symbol.

    Args:
        body: The normalised draft.
        symbol: The symbol pattern.
        spans: Every span at which the dataset's symbols occur in ``body``.

    Returns:
        ``True`` when some mention of the symbol is its own.
    """
    return any(not _inside_a_longer_symbol(m.span(), spans) for m in symbol.finditer(body))


def figures(report: GroundTruthReport) -> dict[str, Any]:
    """The report's figures and id lists, JSON-ready and shared by every writer.

    Args:
        report: What :func:`score_draft` produced.

    Returns:
        The figures (``None`` where unmeasured), their counts, the per-kind
        table and the id lists.
    """
    return {
        "scored": report.scored,
        "reachable_recall": report.reachable_recall,
        "all_facts_recall": report.all_facts_recall,
        "ceiling": report.ceiling,
        "claim_accuracy": report.claim_accuracy,
        "claim_accuracy_counts": {
            "attempted": len(report.attempted),
            "reachable": len(report.reachable),
        },
        "per_kind": report.per_kind(),
        "matched": list(report.matched),
        "attempted": list(report.attempted),
        "mismatched": list(report.mismatched),
        "named": list(report.named),
        "absent": list(report.absent),
        "reachable": list(report.reachable),
        "excluded": list(report.excluded),
        "excluded_because": dict(report.excluded_because),
    }
```

- [ ] **Step 5: Implement the verb's output.** In `_write_ground_truth`, replace the payload keys
  from `"scored"` through `"claim_accuracy"` with `**figures(report)`. Keep `draft`, `scored_at`,
  `dataset` and `nearby_chars`. In `_ground_truth_run`, replace the two figure lines with:

```python
    reachable = len(report.reachable)
    reachable_ids = set(report.reachable)
    hits = sum(1 for name in report.matched if name in reachable_ids)
    if reachable:
        print(f"reachable recall: {hits} of {reachable} reachable")
    else:
        print("reachable recall: not measured; the dataset marks no entry reachable")
    print(f"all-facts recall: {len(report.matched)} of {report.scored} scored "
          f"(ceiling {reachable} of {report.scored})")
    if report.claim_accuracy is None:
        print("claim accuracy: not measured; the draft attempted no entry")
    else:
        print(f"claim accuracy: {report.claim_accuracy:.3f} "
              f"({len(report.attempted)} attempted of {reachable} reachable)")
    for kind, row in report.per_kind().items():
        print(f"  {kind}: {row['matched']} matched / {row['mismatched']} mismatched / "
              f"{row['named']} named / {row['absent']} absent of {row['scored']}")
    print(f"named without a value: {len(report.named)} (not an attempt)")
```

- [ ] **Step 6: Run the tests and see them pass**

Run: `… -m pytest tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py -q -n 4 --basetemp /tmp/claude-501/pytest-gtm-2`
Expected: all pass. Fix any other reader of `report.recall` or `report.missed` found by
`grep -rn "\.recall\b\|\.missed\b\|\"missed\"" ai_rfc tests`: every one is updated here, and none is
left behind.

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(experiment): score named and absent apart, reachable recall, counts and kinds" -- ai_rfc/experiment/ground_truth.py ai_rfc/experiment/cli.py tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py
```

(`git add` the same paths first, and add any other file the grep in Step 6 made you touch.)

## Task 3: Datasets v2 (window-anchored w02-11, the migrated tip dataset, selection)

Spec §3, §4.1 (tickets 01, 07, 08, 10, 13).

**Files:**
- Create: `ai_rfc/experiment/groundtruth/aioquic-w02-11-at-509065a.yaml`, `targets.yaml`,
  `specs/draft-ietf-quic-http-22.txt`, `specs/rfc9114.txt`, `specs/rfc9204.txt`,
  `specs/SHA256SUMS`
- Rename and rewrite: `groundtruth/aioquic-w02-11.yaml` → `groundtruth/aioquic-h3-at-6d36838.yaml`
- Modify: `pyproject.toml`, `ground_truth.py`, `experiment/cli.py` (the verb's arguments)
- Test: `tests/experiment/test_ground_truth.py`, `tests/experiment/test_cli_ground_truth.py`

**Interfaces:**
- Produces: `datasets() -> tuple[str, ...]`; `load_dataset(name: str) -> dict[str, Any]` (no default
  any more); `spec_text(name: str) -> str`.
- Produces: `Selection(name: str | None, dataset: dict | None, status: str | None, reason: str |
  None)`; `select_dataset(target: str, window: tuple[int, int]) -> Selection`.
- Produces: the constants `STATUS_SCORED = "scored"`, `STATUS_NO_DECLARED_SPEC = "no declared
  spec"`, `STATUS_NO_DATASET = "no dataset for this window"`, `STATUS_DRAFT_UNREADABLE = "draft
  unreadable"`.
- Removes: `DATASET`.

**Dataset format v2 (every file must satisfy it).**
- **Top level:** `repository`, `target`, `window: [a, b]`, `commit` (the full sha of the anchor),
  `declared_spec {version, evidence: [str], normative_references: [str]}`,
  `specs {file: sha256}`, `entries`.
- **Per entry:** `id, statement, symbol, value, kind, source {path, line}`, `citation {doc, section,
  line} | null`, `citation_agrees: bool | null`, `reachable {cluster, diff_line} | null`, and
  optionally `unscored_reason`.
- **Rule:** an entry whose value is hex and that carries no `unscored_reason` must have a citation
  and `citation_agrees: true`.

- [ ] **Step 1: Fetch and pin the tip dataset's specs** (network: `www.rfc-editor.org`; allow it in
  the sandbox)

```bash
mkdir -p ai_rfc/experiment/groundtruth/specs
curl -sSf -o ai_rfc/experiment/groundtruth/specs/rfc9114.txt https://www.rfc-editor.org/rfc/rfc9114.txt
curl -sSf -o ai_rfc/experiment/groundtruth/specs/rfc9204.txt https://www.rfc-editor.org/rfc/rfc9204.txt
git -C <wt> show 6b2e70f14:.scratch/ground-truth-yardstick/assets/specs/draft-ietf-quic-http-22.txt > ai_rfc/experiment/groundtruth/specs/draft-ietf-quic-http-22.txt
cd ai_rfc/experiment/groundtruth/specs && shasum -a 256 draft-ietf-quic-http-22.txt rfc9114.txt rfc9204.txt > SHA256SUMS && cd -
```

Check: the http-22 sha256 must equal `86081a2e8c79888a0917ddb11f1d387dd3126544bc8783c2071e833eb8df3f12`
(PANTHER `<map>/assets/specs/SHA256SUMS`). If it differs, stop.

- [ ] **Step 2: Add the w02-11 dataset** from the map asset, byte-for-byte:

```bash
git -C <wt> show 6b2e70f14:.scratch/ground-truth-yardstick/assets/09/aioquic-w02-11-at-509065a.yaml > ai_rfc/experiment/groundtruth/aioquic-w02-11-at-509065a.yaml
```

It already has the v2 shape except `declared_spec.normative_references`. Add
`normative_references: []` under `declared_spec`: none of its 26 scored facts is a QPACK fact.
Ticket 10 found that http-22 names qpack-10, which was published after the window.

- [ ] **Step 3: Migrate the tip dataset** (ticket 01 ruling 7, and the user's choice to migrate
  fully). `git mv ai_rfc/experiment/groundtruth/aioquic-w02-11.yaml
  ai_rfc/experiment/groundtruth/aioquic-h3-at-6d36838.yaml`. Then run this one-off script from
  `/tmp/claude-501/gtm-migrate/` (it is not committed; it writes only the renamed file):

```python
"""One-off: rewrite the tip dataset into format v2 (ticket 01, ruling 7).

Declared spec: the tip code declares ALPN "h3" (`src/aioquic/h3/connection.py`, `H3_ALPN =
["h3"]`), which is RFC 9114. RFC 9114 normatively references RFC 9204 (QPACK), the same pairing
tickets 01 and 10 used for h3-22 and QPACK. The code names no RFC anywhere (grep found none at
6d36838), so entries citing RFC 9220 or RFC 9297 are unscored, with that reason (ticket 07).
"""

import hashlib
import re
import subprocess
from pathlib import Path

import yaml

from ai_rfc.experiment.ground_truth import _symbol_pattern

AI_RFC = Path("<ai_rfc>")                         # substitute the real path
GT = AI_RFC / "ai_rfc/experiment/groundtruth"
PRISTINE = Path.home() / "ai-rfc-experiments/pristine/aioquic-w02-11"
TIP = "6d36838d008c2202c337142fa07e8bf80e96bac8"
WINDOW = (1, 342)
DOCS = {"RFC 9114": "rfc9114.txt", "RFC 9204": "rfc9204.txt"}
HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.\s")
HEX = re.compile(r"(?<![0-9a-z_])0x[0-9a-f]+(?![0-9a-z_])")


def lines_of(name):
    return (GT / "specs" / name).read_text().split("\n")  # not splitlines(): form feeds


def cite(lines, section, symbol, value):
    """First line inside `section` naming the symbol beside a hex token equal to the value."""
    inside, start = False, None
    for index, line in enumerate(lines):
        heading = HEADING.match(line)
        if heading:
            inside = heading.group(1) == section or (inside and heading.group(1).startswith(section + "."))
            continue
        if inside and _symbol_pattern(symbol).search(line.casefold()) and any(
                int(t, 16) == int(value, 16) for t in HEX.findall(line.casefold())):
            return index + 1
    return None


def quoted(lines, line):
    block = []
    for text in lines[line - 1:]:
        if not text.strip():
            break
        block.append(text.strip())
    return " ".join(" ".join(block).split())


def former_paths(path):
    out = subprocess.run(["git", "-C", str(PRISTINE / "clone"), "log", "--follow",
                          "--name-only", "--format=", TIP, "--", path],
                         capture_output=True, text=True, check=True).stdout
    return {p for p in out.split("\n") if p} | {path}


def reachable(path, content, window):
    names = former_paths(path)
    for cluster in sorted((PRISTINE / "clusters").iterdir()):
        if not window[0] <= int(cluster.name[1:5]) <= window[1]:
            continue
        current = None
        for number, line in enumerate((cluster / "span.diff").read_text(errors="replace").split("\n"), 1):
            if line.startswith("+++ "):
                current = line[4:].removeprefix("b/")
            elif line.startswith("+") and current in names and line[1:].strip() == content:
                return {"cluster": cluster.name, "diff_line": number}
    return None


old = yaml.safe_load((GT / "aioquic-h3-at-6d36838.yaml").read_text())
problems = []
for entry in old["entries"]:
    rfc = entry.pop("rfc", None) or {}
    source = subprocess.run(["git", "-C", str(PRISTINE / "clone"), "show",
                             f"{TIP}:{entry['source']['path']}"],
                            capture_output=True, text=True, check=True).stdout.split("\n")
    content = source[entry["source"]["line"] - 1].strip()
    entry["reachable"] = reachable(entry["source"]["path"], content, WINDOW)
    entry["citation"], entry["citation_agrees"] = None, None
    if not str(entry["value"]).lower().startswith("0x"):
        continue  # not a number or a decimal: the scorer excludes it and names why
    doc = rfc.get("doc")
    if doc not in DOCS:
        entry["unscored_reason"] = (f"cited spec {doc} is not declared by the code at "
                                    f"{TIP[:7]} (ticket 07)")
        continue
    lines = lines_of(DOCS[doc])
    line = cite(lines, str(rfc.get("section")), entry["symbol"], entry["value"])
    if line is None:
        problems.append(f"{entry['id']}: no line in {doc} §{rfc.get('section')} states {entry['value']}")
        entry["unscored_reason"] = f"no statement of the value in {doc} §{rfc.get('section')}"
        entry["citation_agrees"] = False
        continue
    entry["citation"] = {"doc": DOCS[doc].removesuffix(".txt"), "section": rfc["section"], "line": line}
    entry["citation_agrees"] = True
    entry["statement"] = quoted(lines, line)
document = {
    "repository": old["repository"],
    "target": "aioquic",
    "window": list(WINDOW),
    "commit": TIP,
    "declared_spec": {
        "version": "h3 (RFC 9114)",
        "evidence": ['src/aioquic/h3/connection.py: H3_ALPN = ["h3"]'],
        "normative_references": ["RFC 9204"],
    },
    "specs": {name: hashlib.sha256((GT / "specs" / name).read_bytes()).hexdigest()
              for name in ("rfc9114.txt", "rfc9204.txt")},
    "entries": old["entries"],
}
(GT / "aioquic-h3-at-6d36838.yaml").write_text(
    "# Migrated to format v2 on <date>; see docs/superpowers/specs/"
    "2026-09-21-arfc-ground-truth-yardstick-design.md (PANTHER).\n"
    + yaml.safe_dump(document, sort_keys=False, width=100, allow_unicode=True))
print("\n".join(problems) or "every hex entry cited")
```

Run it with the worktree venv. **Report every line it prints.** A "no line … states" entry is left
unscored with that reason, and is not fixed by hand. Then check that the migrated file's scored count
(hex, no `unscored_reason`) is **35 minus the 3 RFC 9297/9220 entries, minus any "no line" entries**,
and record the number in the plan's deviation log.

- [ ] **Step 4: Add `targets.yaml`** (ticket 07)

```yaml
# Targets whose code declares no spec (ticket 07 of the ground-truth yardstick map): no dataset can
# exist for them, and their ground truth reports status "no declared spec", never zero.
no_declared_spec:
  mark:
    checked_at: b901f36095d746ee99dfa85b3d2ad1fbe5f2c533
    reason: >-
      No ALPN, protocol-version constant or reference to a versioned document in the code at
      b901f36; the repository's own API_Doc_classification.md is named by no code.
```

- [ ] **Step 5: Package data.** In `pyproject.toml`, under `[tool.setuptools.package-data]`, change
  `"ai_rfc.experiment.groundtruth" = ["*.yaml"]` to
  `"ai_rfc.experiment.groundtruth" = ["*.yaml", "specs/*.txt", "specs/SHA256SUMS"]`. Reinstall the
  editable package if the resource test in Step 6 fails (`<wt>/.venv/bin/python -m pip install -e
  <ai_rfc> --no-deps`).

- [ ] **Step 6: Write the failing tests.** Replace the old dataset-integrity tests in
  `test_ground_truth.py` (those from `test_every_entry_has_a_unique_id_and_the_required_fields`
  through `test_the_dataset_names_a_repository_and_a_commit_shaped_pin`) with tests that
  parametrize over every dataset:

```python
import hashlib
from importlib import resources

from ai_rfc.experiment.ground_truth import (
    STATUS_NO_DATASET,
    STATUS_NO_DECLARED_SPEC,
    _symbol_pattern,
    datasets,
    select_dataset,
    spec_text,
)

HEX = re.compile(r"(?<![0-9a-z_])0x[0-9a-f]+(?![0-9a-z_])")


def test_the_package_ships_both_aioquic_datasets():
    assert set(datasets()) == {"aioquic-w02-11-at-509065a.yaml", "aioquic-h3-at-6d36838.yaml"}


@pytest.mark.parametrize("name", datasets())
def test_every_dataset_declares_its_target_window_anchor_and_spec(name):
    doc = load_dataset(name)
    assert isinstance(doc["target"], str) and doc["target"]
    assert len(doc["window"]) == 2 and doc["window"][0] <= doc["window"][1]
    assert re.fullmatch(r"[0-9a-f]{40}", doc["commit"])
    assert doc["declared_spec"]["version"] and doc["declared_spec"]["evidence"]
    assert doc["specs"], "a dataset with no pinned spec cannot verify a citation"


@pytest.mark.parametrize("name", datasets())
def test_every_pinned_spec_is_byte_exact(name):
    # Bytes, not text: reading as text could translate line endings, and the
    # pin is over what the IETF served.
    specs = resources.files("ai_rfc.experiment.groundtruth").joinpath("specs")
    for file, digest in load_dataset(name)["specs"].items():
        assert hashlib.sha256(specs.joinpath(file).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("name", datasets())
def test_every_scored_entry_cites_a_line_that_states_its_value(name):
    doc = load_dataset(name)
    for entry in doc["entries"]:
        scored = str(entry["value"]).lower().startswith("0x") and not entry.get("unscored_reason")
        if not scored:
            continue
        citation = entry["citation"]
        assert entry["citation_agrees"] is True, entry["id"]
        lines = spec_text(citation["doc"] + ".txt").split("\n")
        line = lines[citation["line"] - 1].casefold()
        assert _symbol_pattern(entry["symbol"]).search(line), entry["id"]
        assert int(entry["value"], 16) in {int(t, 16) for t in HEX.findall(line)}, entry["id"]


@pytest.mark.parametrize("name", datasets())
def test_every_entry_has_a_unique_id_and_the_v2_fields(name):
    entries = load_dataset(name)["entries"]
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))
    for entry in entries:
        assert {"id", "statement", "symbol", "value", "kind", "source",
                "citation", "citation_agrees", "reachable"} <= entry.keys()
        assert entry["kind"] in KINDS
        assert isinstance(entry["symbol"], str) and isinstance(entry["value"], str)


def test_selection_finds_the_dataset_for_an_exact_target_and_window():
    found = select_dataset("aioquic", (2, 11))
    assert found.name == "aioquic-w02-11-at-509065a.yaml" and found.status is None


def test_selection_names_a_window_with_no_dataset():
    found = select_dataset("aioquic", (2, 12))
    assert found.dataset is None and found.status == STATUS_NO_DATASET


def test_selection_names_a_target_that_declares_no_spec():
    found = select_dataset("mark", (1, 69))
    assert found.dataset is None and found.status == STATUS_NO_DECLARED_SPEC
    assert "b901f36" in found.reason
```

In `test_cli_ground_truth.py`, `_score` passes `--dataset aioquic-w02-11-at-509065a.yaml`, and
`DRAFT` states window-end facts (`HTTP_NO_ERROR is 0x00`, `HTTP_INTERNAL_ERROR is 0x03`). Update
every test that asserted RFC-final ids. Add:

```python
def test_the_verb_refuses_without_a_dataset_or_a_target_and_window(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("x")
    code = cli.main(["ground-truth", str(draft), "--out", str(tmp_path / "o")])
    assert code != 0


def test_the_verb_selects_by_target_and_window(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text(DRAFT)
    code = cli.main(["ground-truth", str(draft), "--out", str(tmp_path / "o"),
                     "--target", "aioquic", "--window", "2-11"])
    assert code == 0
    payload = json.loads((tmp_path / "o" / "ground-truth.json").read_text())
    assert payload["dataset"]["name"] == "aioquic-w02-11-at-509065a.yaml"
```

- [ ] **Step 7: Run them and see them fail** (`… -k "dataset or selection or pinned or cites or
  verb"`). Expected: ImportError for `datasets`, `select_dataset` and `spec_text`.

- [ ] **Step 8: Implement in `ground_truth.py`** (delete `DATASET`)

```python
STATUS_SCORED = "scored"
STATUS_NO_DECLARED_SPEC = "no declared spec"
STATUS_NO_DATASET = "no dataset for this window"
STATUS_DRAFT_UNREADABLE = "draft unreadable"
TARGETS_FILE = "targets.yaml"


@dataclass(frozen=True)
class Selection:
    """Which dataset scores a target's window, or why none does.

    Attributes:
        name: The dataset's file name, or ``None``.
        dataset: The loaded document, or ``None``.
        status: ``None`` when a dataset was found; otherwise
            :data:`STATUS_NO_DECLARED_SPEC` or :data:`STATUS_NO_DATASET`.
        reason: Why no dataset scores it, in words; ``None`` when one does.
    """

    name: str | None
    dataset: dict[str, Any] | None
    status: str | None
    reason: str | None


def datasets() -> tuple[str, ...]:
    """The file names of every packaged dataset, sorted.

    Returns:
        Every ``*.yaml`` in the ``groundtruth`` package except the targets registry.
    """
    root = resources.files(PACKAGE)
    return tuple(sorted(item.name for item in root.iterdir()
                        if item.name.endswith(".yaml") and item.name != TARGETS_FILE))


def load_dataset(name: str) -> dict[str, Any]:
    """Read one packaged dataset.

    Args:
        name: The dataset's file name within the ``groundtruth`` package.

    Returns:
        The dataset document.
    """
    return yaml.safe_load(resources.files(PACKAGE).joinpath(name).read_text(encoding="utf-8"))


def spec_text(name: str) -> str:
    """One pinned spec text, exactly as fetched.

    Args:
        name: Its file name under ``groundtruth/specs/``.

    Returns:
        The text. It is split on ``\\n`` by readers, never with ``splitlines()``,
        because RFC text carries form feeds.
    """
    return resources.files(PACKAGE).joinpath("specs", name).read_text(encoding="utf-8")


def select_dataset(target: str, window: tuple[int, int]) -> Selection:
    """The dataset that scores ``target`` over exactly ``window``, or why none does.

    Args:
        target: The campaign's target name.
        window: The campaign's window ``(a, b)``.

    Returns:
        The selection. A target the registry says declares no spec is reported
        so before any dataset is looked for.
    """
    registry = yaml.safe_load(
        resources.files(PACKAGE).joinpath(TARGETS_FILE).read_text(encoding="utf-8")
    ) or {}
    undeclared = (registry.get("no_declared_spec") or {}).get(target)
    if undeclared is not None:
        return Selection(None, None, STATUS_NO_DECLARED_SPEC, str(undeclared.get("reason", "")))
    for name in datasets():
        doc = load_dataset(name)
        if doc.get("target") == target and tuple(doc.get("window", ())) == tuple(window):
            return Selection(name, doc, None, None)
    return Selection(None, None, STATUS_NO_DATASET,
                     f"no dataset declares target {target!r} with window {list(window)}")
```

In `experiment/cli.py`, add to the `ground-truth` parser a mutually exclusive `--dataset NAME`,
plus `--target NAME` and `--window A-B` (parse the window with the same function `workspace prepare
--window` uses; find it with `grep -n '"--window"' ai_rfc/experiment/cli.py`). In
`_ground_truth_run`:
- with `--dataset`, call `load_dataset(args.dataset)`;
- with `--target` and `--window`, call `select_dataset(...)`, and raise `ExperimentError(f"{status}:
  {reason}")` when `dataset is None`;
- with neither, raise `ExperimentError("name a dataset (--dataset) or a target and window
  (--target, --window)")`.

Pass the dataset's name to `_write_ground_truth` as a new keyword-only `name` parameter, and write
`"dataset": {"name": name, "repository": …, "commit": …, "target": …, "window": …}`.

- [ ] **Step 9: Update the tests that still name the old dataset, then run the module pair.**
  - **Delete here:** `CHECKOUT`, `_checkout_commit`, the `pinned_checkout` fixture, and the three
    tests that use it: `test_every_source_resolves_to_a_real_line`,
    `test_every_cited_line_spells_the_assignment_it_claims` and
    `test_resolve_anchors_agrees_with_the_two_anchor_tests`. Task 4 adds their replacements.
  - **Keep:** `test_resolve_anchors_names_every_entry_the_checkout_does_not_bear` and
    `test_resolve_anchors_refuses_a_path_that_leaves_the_checkout` use the old
    `resolve_anchors(entries, clone)` signature. They stay until Task 4 replaces them.
  - **Update:** every other call of `load_dataset()` with no argument
    (`grep -n "load_dataset()" tests/`) now names `"aioquic-h3-at-6d36838.yaml"`. Any count it
    asserted (for example "35 scored") becomes the migrated count recorded in Step 3.

  Run: `… -m pytest tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py -q -n 4 --basetemp /tmp/claude-501/pytest-gtm-3`
  Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add ai_rfc/experiment/groundtruth pyproject.toml ai_rfc/experiment/ground_truth.py ai_rfc/experiment/cli.py tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py
git commit -m "feat(experiment): window-anchored ground-truth datasets, pinned specs and selection by target and window" -- ai_rfc/experiment/groundtruth pyproject.toml ai_rfc/experiment/ground_truth.py ai_rfc/experiment/cli.py tests/experiment/test_ground_truth.py tests/experiment/test_cli_ground_truth.py
```

## Task 4: Anchors through git objects, and reachability verified

Spec §4.2 and §4.3 (research 04's question 7; ticket 02).

**Files:** Modify `ground_truth.py` (`resolve_anchors`). Test `tests/experiment/test_ground_truth.py`.

**Interfaces:** Produces `resolve_anchors(entries: list[dict], repo: Path, commit: str) ->
tuple[str, ...]`, with a new signature. The old `(entries, clone)` form is removed.

- [ ] **Step 1: Write the failing tests** (replacing `pinned_checkout`, `_checkout_commit` and the
  old anchor tests)

```python
import os
import subprocess

REPO = Path(os.environ.get("AI_RFC_AIOQUIC_CLONE",
                           str(Path.home() / "ai-rfc-experiments/pristine/aioquic-w02-11/clone")))
PRISTINE = REPO.parent


def _has(commit: str) -> bool:
    return REPO.is_dir() and subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "-e", commit], capture_output=True).returncode == 0


@pytest.mark.parametrize("name", datasets())
def test_every_source_line_spells_its_assignment_at_the_anchor(name):
    doc = load_dataset(name)
    if not _has(doc["commit"]):
        pytest.skip(f"no aioquic clone holding {doc['commit'][:7]} at {REPO}")
    assert resolve_anchors(doc["entries"], REPO, doc["commit"]) == ()


@pytest.mark.parametrize("name", datasets())
def test_every_reachable_record_points_at_an_added_line_in_a_window_cluster(name):
    doc = load_dataset(name)
    if not (PRISTINE / "clusters").is_dir() or not _has(doc["commit"]):
        pytest.skip(f"no aioquic pristine at {PRISTINE}")
    a, b = doc["window"]
    for entry in doc["entries"]:
        where = entry["reachable"]
        if where is None:
            continue
        assert a <= int(where["cluster"][1:5]) <= b, entry["id"]
        diff = (PRISTINE / "clusters" / where["cluster"] / "span.diff").read_text(errors="replace").split("\n")
        added = diff[where["diff_line"] - 1]
        source = subprocess.run(["git", "-C", str(REPO), "show", f"{doc['commit']}:{entry['source']['path']}"],
                                capture_output=True, text=True, check=True).stdout.split("\n")
        assert added.startswith("+") and added[1:].strip() == source[entry["source"]["line"] - 1].strip(), entry["id"]


def test_resolve_anchors_names_an_entry_whose_line_does_not_spell_it(tmp_path):
    repo = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "f.py").write_text("X = 0x1\n")
    subprocess.run(["git", "-C", str(repo), "add", "f.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "c"], check=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    good = {"id": "g", "symbol": "X", "value": "0x1", "source": {"path": "f.py", "line": 1}}
    bad = {"id": "b", "symbol": "X", "value": "0x2", "source": {"path": "f.py", "line": 1}}
    assert resolve_anchors([good, bad], repo, head) == ("b",)


def test_resolve_anchors_refuses_an_escaping_path_without_asking_git(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("git was asked about a path that leaves the repository")
    monkeypatch.setattr(subprocess, "run", refuse)
    entries = [{"id": "up", "symbol": "X", "value": "0x1", "source": {"path": "../x", "line": 1}},
               {"id": "abs", "symbol": "X", "value": "0x1", "source": {"path": "/etc/hosts", "line": 1}}]
    assert resolve_anchors(entries, tmp_path, "0" * 40) == ("up", "abs")
```

(The `git commit` in the fixture repo writes only under `tmp_path`.)

- [ ] **Step 2: Run and see failure** (a TypeError from the old signature).

- [ ] **Step 3: Implement** (replace `resolve_anchors`; add `import subprocess`)

```python
def resolve_anchors(entries: list[dict], repo: Path, commit: str) -> tuple[str, ...]:
    """The entries whose anchor ``commit`` does not bear, read from git objects.

    Read with ``git show <commit>:<path>`` rather than from a working tree, so
    any clone holding the commit can check a dataset, whatever it has checked
    out (research 04). A path that is absolute or climbs with ``..`` is
    reported unresolved without asking git.

    Args:
        entries: The dataset's ``entries``.
        repo: Any clone of the repository that holds ``commit``.
        commit: The dataset's anchor.

    Returns:
        The ids that did not resolve, in the given order.
    """
    unresolved: list[str] = []
    for entry in entries:
        path = str(entry["source"]["path"])
        if path.startswith("/") or ".." in Path(path).parts:
            unresolved.append(entry["id"])
            continue
        shown = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                               capture_output=True, text=True)
        lines = shown.stdout.split("\n") if shown.returncode == 0 else []
        line = entry["source"]["line"]
        if not 1 <= line <= len(lines) or lines[line - 1].strip() != f"{entry['symbol']} = {entry['value']}":
            unresolved.append(entry["id"])
    return tuple(unresolved)
```

- [ ] **Step 4: Run the module and see it pass.** With `<pristine>` present, the anchor and
  reachability tests **must run**, not skip. Check the `-rs` output shows no skip.

- [ ] **Step 5: Commit** — `fix(experiment): resolve dataset anchors from git objects and verify
  reachability`, with paths `ai_rfc/experiment/ground_truth.py tests/experiment/test_ground_truth.py`.

## Task 5: The audit's future-material verdict

Spec §7.3 (tickets 05 and 12). The reference implementation is
`<map>/research/12-audit/audit.py`, which is git-ignored in PANTHER. Read it; it is local to the
worktree that ran it.

**Amended 2026-09-22 (user ruling).** Only clusters **after the window's top** count as future. A
cluster before the window, such as the pre-seeded c0001, is the run's past and its context, the
same rule `cluster_get` follows in the prevention plan. This amendment doesn't move ticket 12's
results, whose future-content findings all came from `corpus_query`. So Task 10's expected
`touching` counts (2 and 6) stand.

**Files:**
- Create: `ai_rfc/experiment/future.py`
- Modify: `ai_rfc/experiment/audit.py` (the read-tool branch records its path; `audit_run` adds
  `future_material`)
- Test: `tests/experiment/test_future.py` (new), `tests/experiment/test_audit.py`

**Interfaces:**
- Produces: `window_end(workspace: Path, window: tuple[int, int]) -> str | None`.
- Produces: `classify_future(events: list[dict], workspace: Path, window: tuple[int, int]) ->
  dict[str, Any]`, returning `{"verdict": "clean" | "touched" | "unmeasured", "end": str | None,
  "reason": str | None, "touching": [{"call": int, "tool": str, "route": str, "evidence": [str]}],
  "metadata": int}`.
- The audit record gains `future_material` (that dict).

- [ ] **Step 1: Write the failing tests** (`tests/experiment/test_future.py`)

```python
import json
import subprocess
from pathlib import Path

import pytest

from ai_rfc.experiment.future import classify_future, window_end

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A clone with two commits: the window ends at the first, and the second is the future."""
    # Named "workspace": the classifier finds a path's place in the run by "/workspace/".
    ws = tmp_path / "workspace"
    clone = ws / "clone"
    clone.mkdir(parents=True)
    _git(clone, "init", "-q")
    for n, body in ((1, "A = 0x1\n"), (2, "A = 0x1\nB = 0x100\n")):
        (clone / "c.py").write_text(body)
        _git(clone, "add", "c.py")
        _git(clone, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", f"c{n}")
    first, second = _git(clone, "rev-list", "--reverse", "HEAD").split()
    (ws / "timeline").mkdir()
    (ws / "timeline" / "members.jsonl").write_text(
        json.dumps({"cluster_id": "c0001-epoch-aaaaaaaaaaaa", "position": 0, "role": "spine", "sha": first}) + "\n"
        + json.dumps({"cluster_id": "c0002-epoch-bbbbbbbbbbbb", "position": 0, "role": "spine", "sha": second}) + "\n")
    ws.joinpath("future_sha").write_text(second)
    return ws


def _call(tool: str, tool_input: dict, text: str, call_id: str = "t1") -> list[dict]:
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": call_id, "name": tool, "input": tool_input}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": text}]}},
    ]


def test_window_end_is_the_last_member_of_the_window_s_last_cluster(workspace):
    first = _git(workspace / "clone", "rev-list", "--reverse", "HEAD").split()[0]
    assert window_end(workspace, (1, 1)) == first


def test_a_corpus_row_naming_a_future_commit_touches(workspace):
    future = (workspace / "future_sha").read_text()
    events = _call("mcp__ai_rfc__ai_rfc_corpus_query", {"sql": "SELECT sha FROM commits"},
                   json.dumps({"result": [{"sha": future}]}))
    verdict = classify_future(events, workspace, (1, 1))
    assert verdict["verdict"] == "touched"
    assert verdict["touching"][0]["route"] == "corpus"


def test_a_clone_file_that_changed_after_the_end_touches_when_read(workspace):
    events = _call("Read", {"file_path": str(workspace / "clone" / "c.py")}, "A = 0x1\nB = 0x100\n")
    assert classify_future(events, workspace, (1, 1))["verdict"] == "touched"


def test_a_cluster_after_the_window_touches(workspace):
    events = _call("mcp__ai_rfc__ai_rfc_cluster_get", {"cluster_id": "c0002-epoch-bbbbbbbbbbbb"}, "{}")
    assert classify_future(events, workspace, (1, 1))["verdict"] == "touched"


def test_a_cluster_before_the_window_is_context_not_future(workspace):
    events = _call("mcp__ai_rfc__ai_rfc_cluster_get", {"cluster_id": "c0001-epoch-aaaaaaaaaaaa"},
                   json.dumps({"view": {"id": "c0001-epoch-aaaaaaaaaaaa"}}))
    assert classify_future(events, workspace, (2, 2))["verdict"] == "clean"


def test_a_file_name_in_a_listing_does_not_touch(workspace):
    events = _call("Glob", {"pattern": "*"}, str(workspace / "clone" / "c.py"))
    assert classify_future(events, workspace, (1, 1))["verdict"] == "clean"


def test_a_status_naming_the_tip_is_metadata_not_touched(workspace):
    future = (workspace / "future_sha").read_text()
    events = _call("mcp__ai_rfc__ai_rfc_status", {}, json.dumps({"tip_sha": future}))
    verdict = classify_future(events, workspace, (1, 1))
    assert verdict["verdict"] == "clean" and verdict["metadata"] == 1


def test_no_timeline_is_unmeasured_never_clean(tmp_path):
    verdict = classify_future([], tmp_path, (1, 1))
    assert verdict["verdict"] == "unmeasured" and verdict["reason"]
```

In `tests/experiment/test_audit.py`, add a test that `audit_run`'s record carries `future_material`
with a `verdict`, and that a `Read` call's recorded path is its `file_path` (use the file's existing
campaign fixtures).

- [ ] **Step 2: Run and see failure** (ModuleNotFoundError: `ai_rfc.experiment.future`).

- [ ] **Step 3: Implement `ai_rfc/experiment/future.py`**

```python
"""Future material: what a run's tool results told the model about its repository after the window.

A run touched future material when a tool result delivered content describing
the repository after the window's end commit (ticket 05 of the ground-truth
yardstick map). A bare file name in a listing does not count. Five routes reach
it: the clone's working tree, clusters after the window's top, the forge
snapshot, the corpus, and git. A cluster before the window is the run's past,
not its future. The verdict is ``unmeasured`` rather than clean when the
workspace cannot say where the window ends.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_rfc.driver.stream import tool_results, tool_uses

_SHA = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")
_DATE = re.compile(r"(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d:\d\d)(Z|[+-]\d\d:?\d\d)?")
_CLUSTER = re.compile(r"\bc(\d{4})-(?:pr|epoch)-[0-9a-f]{12}\b")


def window_end(workspace: Path, window: tuple[int, int]) -> str | None:
    """The last member commit of the window's last cluster.

    Args:
        workspace: A run or pristine workspace holding ``timeline/members.jsonl``.
        window: The window ``(a, b)``.

    Returns:
        The member with the highest ``position`` in the cluster whose ordinal is
        ``b``, or ``None`` when the timeline is absent or has no such cluster.
    """
    members = workspace / "timeline" / "members.jsonl"
    if not members.is_file():
        return None
    last: dict[str, Any] | None = None
    for line in members.read_text().splitlines():
        row = json.loads(line)
        ordinal = str(row.get("cluster_id", ""))[1:5]
        if ordinal.isdigit() and int(ordinal) == window[1]:
            if last is None or row["position"] > last["position"]:
                last = row
    return None if last is None else str(last["sha"])


def _git(clone: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True).stdout


def classify_future(
    events: list[dict[str, Any]], workspace: Path, window: tuple[int, int]
) -> dict[str, Any]:
    """Whether any tool result delivered future content, and which calls did.

    Args:
        events: The run's parsed transcript.
        workspace: The run's workspace (its ``clone/`` and ``timeline/``).
        window: The campaign's window.

    Returns:
        ``verdict``, ``end``, ``reason``, ``touching`` (one record per touching
        call) and ``metadata`` (calls that named future commits or clusters after
        the window without carrying content, such as a status naming the tip).
    """
    end = window_end(workspace, window)
    clone = workspace / "clone"
    if end is None or not (clone / ".git").exists():
        return {"verdict": "unmeasured", "end": end, "touching": [], "metadata": 0,
                "reason": "the workspace has no timeline or clone to say where the window ends"}
    past = set(_git(clone, "rev-list", end).split())
    every = _git(clone, "rev-list", "--all").split()
    future = {sha for sha in every if sha not in past}
    end_time = datetime.fromisoformat(_git(clone, "log", "-1", "--format=%aI", end).strip())
    tip = _git(clone, "rev-parse", "HEAD").strip()

    def future_evidence(text: str, dates: bool) -> list[str]:
        found = []
        for token in set(_SHA.findall(text)):
            hits = [sha for sha in every if sha.startswith(token)]
            if len(hits) == 1 and hits[0] in future and (len(token) >= 12 or re.search("[a-f]", token)):
                found.append(f"future commit {token}")
        if dates:
            for day, clock, zone in _DATE.findall(text):
                zone = "+00:00" if zone in ("", "Z") else (zone if ":" in zone else zone[:3] + ":" + zone[3:])
                try:
                    if datetime.fromisoformat(f"{day}T{clock}{zone}") > end_time:
                        found.append(f"date after the end {day}T{clock}{zone}")
                except ValueError:
                    continue
        for ordinal in {int(o) for o in _CLUSTER.findall(text)}:
            if ordinal > window[1]:
                found.append(f"cluster after the window c{ordinal:04d}")
        return sorted(set(found))

    results = tool_results(events)
    touching: list[dict[str, Any]] = []
    metadata = 0
    for use in tool_uses(events):
        result = results.get(str(use["id"]))
        if result is None:
            continue
        name = use["name"].rsplit("__", 1)[-1]
        tool_input = use["input"] or {}
        text = result["text"]
        route, evidence = None, []
        if name == "Glob" or (name == "Grep" and tool_input.get("output_mode", "files_with_matches")
                              == "files_with_matches"):
            continue  # names only (ticket 05, ruling 3)
        if name in ("Read", "Grep"):
            path = str(tool_input.get("file_path") or tool_input.get("path") or "")
            rel = path.split("/workspace/", 1)[1] if "/workspace/" in path else path
            if rel.startswith("clone/") and rel != "clone/":
                inner = rel[len("clone/"):]
                end_blob = subprocess.run(["git", "-C", str(clone), "show", f"{end}:{inner}"],
                                          capture_output=True)
                tip_blob = subprocess.run(["git", "-C", str(clone), "show", f"{tip}:{inner}"],
                                          capture_output=True)
                if end_blob.returncode != 0 or end_blob.stdout != tip_blob.stdout:
                    route, evidence = "clone", [f"{inner} differs at the window end"]
            elif rel.startswith("clusters/"):
                ordinal = rel.split("/")[1][1:5]
                if ordinal.isdigit() and int(ordinal) > window[1]:
                    route, evidence = "clusters", [rel]
            elif rel.startswith(("forge/", "corpus/", "timeline/")):
                evidence = future_evidence(text, dates=True)
                route = rel.split("/")[0] if evidence else None
        elif name.endswith("cluster_get"):
            cluster = str(tool_input.get("cluster_id", ""))
            ordinal = cluster[1:5]
            if ordinal.isdigit() and int(ordinal) > window[1]:
                route, evidence = "clusters", [cluster]
        elif name.endswith("corpus_query"):
            evidence = future_evidence(text, dates=True)
            route = "corpus" if evidence else None
        elif future_evidence(text, dates=False):
            metadata += 1
        if route:
            touching.append({"call": use["index"], "tool": name, "route": route, "evidence": evidence[:4]})
    return {"verdict": "touched" if touching else "clean", "end": end, "reason": None,
            "touching": touching, "metadata": metadata}
```

In `audit.py`:
- the read-tool branch of the call classifier becomes
  `return "read", name, str(tool_input.get("file_path") or tool_input.get("path") or "")`, so the
  path is recorded;
- in `audit_run`, add `"future_material": classify_future(events, run_dir / "workspace",
  campaign.window),` to the `audit` dict (`from .future import classify_future`).

- [ ] **Step 4: Run** `tests/experiment/test_future.py tests/experiment/test_audit.py` and see them
  pass. Then run the whole `tests/experiment` directory, because the audit record gained a key and
  some fixture comparisons may be exact.

- [ ] **Step 5: Commit** — `feat(experiment): the audit names every tool result that delivered
  future material`, with the three or four paths touched.

## Task 6: `analyze` scores every run's final draft

Spec §6.1 and §6.2 (ticket 13).

**Files:** Modify `ground_truth.py` (new `score_run`) and `metrics.py` (`analyze_run`,
`_arm_summary`, `DEFINITIONS`). Test `tests/experiment/test_metrics.py`.

**Interfaces:**
- Produces: `score_run(target: str, window: tuple[int, int], workspace: Path) -> dict[str, Any]`,
  returning `{"status", "error", "dataset", "tag", **figures(...)}`. Every figure is `None` when the
  status isn't `scored`.
- Produces: in the aggregate, `runs[id]["ground_truth"]`, and in `arms[arm]`:
  - `ground_truth_runs`, the clean scored runs used;
  - `ground_truth_left_out`, a dict `{"touched": n, "unaudited": n}`;
  - `reachable_recall_mean`, `reachable_recall_min`;
  - `claim_accuracy_pooled`, with `claim_accuracy_pooled_counts {"matched", "attempted"}`.

- [ ] **Step 1: Write the failing tests** (in `test_metrics.py`, using its campaign fixtures; the
  fixture campaign's target is not in any dataset)

```python
def test_a_run_with_no_dataset_reports_its_status_never_a_zero(tmp_path):
    from ai_rfc.experiment import ground_truth
    record = ground_truth.score_run("fixture", (2, 11), tmp_path)
    assert record["status"] == "no dataset for this window"
    assert record["reachable_recall"] is None and record["claim_accuracy"] is None


def test_a_target_that_declares_no_spec_is_named_so(tmp_path):
    from ai_rfc.experiment import ground_truth
    record = ground_truth.score_run("mark", (1, 69), tmp_path)
    assert record["status"] == "no declared spec" and "b901f36" in record["error"]


def test_score_run_scores_the_draft_at_the_latest_tag(tmp_path, monkeypatch):
    from ai_rfc.experiment import ground_truth
    entries = [{"id": "e", "statement": "", "symbol": "HTTP_NO_ERROR", "value": "0x00",
                "kind": "error_code", "source": {"path": "p", "line": 1},
                "citation": {"doc": "d", "section": "1", "line": 1}, "citation_agrees": True,
                "reachable": {"cluster": "c0002-x", "diff_line": 1}}]
    monkeypatch.setattr(ground_truth, "select_dataset",
                        lambda target, window: ground_truth.Selection("fixture.yaml", {"entries": entries}, None, None))
    monkeypatch.setattr(ground_truth, "latest_tag", lambda workspace: "draft-x-01")
    monkeypatch.setattr(ground_truth, "draft_text", lambda repo, tag: ("d.md", "HTTP_NO_ERROR is 0x00."))
    record = ground_truth.score_run("t", (2, 11), tmp_path)
    assert record["status"] == "scored" and record["tag"] == "draft-x-01"
    assert record["reachable_recall"] == 1.0


def test_an_unreadable_final_draft_is_a_status_not_a_zero(tmp_path, monkeypatch):
    from ai_rfc.draft.gate import GateError
    from ai_rfc.experiment import ground_truth
    monkeypatch.setattr(ground_truth, "select_dataset",
                        lambda target, window: ground_truth.Selection("f.yaml", {"entries": []}, None, None))
    monkeypatch.setattr(ground_truth, "latest_tag", lambda workspace: "draft-x-38")
    def unreadable(repo, tag):
        raise GateError("no such tag")
    monkeypatch.setattr(ground_truth, "draft_text", unreadable)
    record = ground_truth.score_run("t", (1, 69), tmp_path)
    assert record["status"] == "draft unreadable" and "no such tag" in record["error"]


def test_the_arm_leaves_touched_and_unaudited_runs_out_and_counts_them():
    def run(verdict, recall, matched, attempted):
        return {"surface": {"intact": True}, "clusters": [], "completed_fraction": 0.0,
                "artifacts_fraction": 0.0, "gates": {"clean": True}, "audit": {
                    "integrity": True, "bypass_attempts": {"count": 0}, "errors": {"class1": 0, "class2": 0},
                    "hand_edits": {}, "future_material": {"verdict": verdict}},
                "cost": {"total_cost_usd": 1.0}, "trajectory": {"tokens_to_first_completion": None, "auc": 0.0},
                "status": {"timed_out": False, "exit_code": 0},
                "ground_truth": {"status": "scored", "reachable_recall": recall,
                                 "matched": ["x"] * matched, "attempted": ["x"] * attempted}}
    summary = metrics._arm_summary(
        [run("clean", 0.5, 1, 1), run("touched", 0.9, 9, 9), run("unmeasured", 0.1, 0, 1)], [], 3)
    assert summary["ground_truth_runs"] == 1
    assert summary["ground_truth_left_out"] == {"touched": 1, "unaudited": 1}
    assert summary["reachable_recall_mean"] == 0.5 and summary["claim_accuracy_pooled"] == 1.0
```

Also add one assertion to the existing analyze test in `test_metrics.py` that already inspects a
run's `quality` (`grep -n '"quality"' tests/experiment/test_metrics.py`): the same run has a
`ground_truth` key whose `status` is `no dataset for this window`. This pins that `analyze_run`
attaches the record, without a new fixture.

- [ ] **Step 2: Run and see failure.**

- [ ] **Step 3: Implement `score_run`** (in `ground_truth.py`; add `from ai_rfc.draft.gate import
  GateError, draft_text, latest_tag`)

```python
def _unmeasured_figures() -> dict[str, Any]:
    return {"scored": None, "reachable_recall": None, "all_facts_recall": None, "ceiling": None,
            "claim_accuracy": None, "claim_accuracy_counts": None, "per_kind": None,
            "matched": None, "attempted": None, "mismatched": None, "named": None,
            "absent": None, "reachable": None, "excluded": None, "excluded_because": None}


def score_run(target: str, window: tuple[int, int], workspace: Path) -> dict[str, Any]:
    """Ground truth for one run's final draft, or the status that says why there is none.

    Args:
        target: The campaign's target.
        window: The campaign's window.
        workspace: The run's workspace; its draft is read at ``latest_tag``.

    Returns:
        ``status`` (:data:`STATUS_SCORED` or one of the unmeasured statuses),
        ``error``, ``dataset``, ``tag``, and the figures of :func:`figures`,
        all ``None`` unless scored.
    """
    selection = select_dataset(target, window)
    if selection.dataset is None:
        return {"status": selection.status, "error": selection.reason, "dataset": None,
                "tag": None, **_unmeasured_figures()}
    tag = latest_tag(workspace)
    try:
        _, text = draft_text(workspace / "draft", tag)
    except GateError as error:
        return {"status": STATUS_DRAFT_UNREADABLE, "error": str(error), "dataset": selection.name,
                "tag": tag, **_unmeasured_figures()}
    report = score_draft(text, selection.dataset["entries"])
    return {"status": STATUS_SCORED, "error": None, "dataset": selection.name, "tag": tag,
            **figures(report)}
```

In `metrics.analyze_run`, add `"ground_truth": score_run(campaign.target, campaign.window,
workspace),` beside `"quality"`. In `_arm_summary`, before the `return`:

```python
    scored_gt = [r for r in runs if (r.get("ground_truth") or {}).get("status") == STATUS_SCORED]

    def _verdict(r: dict[str, Any]) -> str | None:
        return ((r.get("audit") or {}).get("future_material") or {}).get("verdict")

    # Left out, and counted beside the figures, like a broken surface above: a
    # touched run saw future material (ticket 13, ruling 3), and an unaudited
    # one cannot say that it did not.
    clean_gt = [r for r in scored_gt if _verdict(r) == "clean"]
    left_out = {
        "touched": sum(1 for r in scored_gt if _verdict(r) == "touched"),
        "unaudited": sum(1 for r in scored_gt if _verdict(r) not in ("clean", "touched")),
    }
    recalls = [r["ground_truth"]["reachable_recall"] for r in clean_gt
               if r["ground_truth"]["reachable_recall"] is not None]
    pooled_matched = sum(len(r["ground_truth"]["matched"]) for r in clean_gt)
    pooled_attempted = sum(len(r["ground_truth"]["attempted"]) for r in clean_gt)
```

and add these keys to the returned dict:

```python
        "ground_truth_runs": len(clean_gt),
        "ground_truth_left_out": left_out,
        "reachable_recall_mean": _mean(recalls),
        "reachable_recall_min": min(recalls, default=None),
        "claim_accuracy_pooled": (pooled_matched / pooled_attempted) if pooled_attempted else None,
        "claim_accuracy_pooled_counts": {"matched": pooled_matched, "attempted": pooled_attempted},
```

Add `DEFINITIONS` entries for:
- `ground_truth_status` (the four statuses);
- `reachable_recall`, `all_facts_recall`, `ceiling`;
- `claim_accuracy` (with its counts);
- `named`;
- `future_material` (touched / clean / unmeasured, and that touched and unaudited runs are left out
  of the arm figures).

Word them from spec §4.4 and §7.3.

- [ ] **Step 4: Run** `tests/experiment` and see it pass.

- [ ] **Step 5: Commit** — `feat(experiment): analyze scores each run's final draft against its
  window's ground truth`.

## Task 7: The report's "Ground truth" section

Spec §6.3.

**Files:** Modify `report.py`. Test `tests/experiment/test_report.py`.

**Interfaces:** Consumes the aggregate keys from Task 6. Produces three renderers:
`_ground_truth_run_rows(runs)`, `_ground_truth_kind_rows(runs)` and `_ground_truth_arm_rows(arms)`.

- [ ] **Step 1: Write the failing tests** (in `test_report.py`; extend the existing `_aggregate()`
  in a local copy, as `_quality_aggregate` does)

```python
def _gt_aggregate(status="scored", verdict="touched"):
    aggregate = copy.deepcopy(_aggregate())
    run = aggregate["runs"]["A1"]
    run["ground_truth"] = {
        "status": status, "error": None if status == "scored" else "no declared spec: reason",
        "dataset": "aioquic-w02-11-at-509065a.yaml" if status == "scored" else None,
        "tag": "draft-x-10", "reachable_recall": 9 / 26 if status == "scored" else None,
        "ceiling": 1.0 if status == "scored" else None,
        "claim_accuracy": 1.0 if status == "scored" else None,
        "claim_accuracy_counts": {"attempted": 9, "reachable": 26} if status == "scored" else None,
        "matched": ["x"] * 9 if status == "scored" else None,
        "named": ["y", "z"] if status == "scored" else None,
        "per_kind": {"error_code": {"scored": 17, "matched": 0, "mismatched": 0, "named": 2, "absent": 15}}
        if status == "scored" else None,
    }
    run["ground_truth"]["scored"] = 26 if status == "scored" else None
    run["audit"] = {**(run.get("audit") or {}),
                    "future_material": {"verdict": verdict, "touching": [{}, {}]}}
    for arm in aggregate["arms"].values():
        arm.update({"ground_truth_runs": 0, "ground_truth_left_out": {"touched": 1, "unaudited": 0},
                    "reachable_recall_mean": None, "reachable_recall_min": None,
                    "claim_accuracy_pooled": None, "claim_accuracy_pooled_counts": {"matched": 0, "attempted": 0}})
    return aggregate


def test_the_ground_truth_section_prints_recall_with_its_counts_and_the_verdict():
    rows = _section(render_report(_gt_aggregate()), "## Ground truth")
    text = "\n".join(rows)
    assert "9/26 (0.346)" in text and "26/26" in text
    assert "1.000 (9 attempted of 26 reachable)" in text
    assert "touched" in text


def test_a_run_with_no_declared_spec_shows_a_dash_and_its_status_never_zero():
    text = "\n".join(_section(render_report(_gt_aggregate(status="no declared spec")), "## Ground truth"))
    assert "no declared spec" in text
    assert "0/" not in text and "0.000" not in text


def test_the_arm_row_says_how_many_runs_it_left_out():
    text = "\n".join(_section(render_report(_gt_aggregate()), "## Ground truth"))
    assert "1 touched" in text
```

- [ ] **Step 2: Run and see failure** (no `## Ground truth` heading, so `ValueError` from `_section`).

- [ ] **Step 3: Implement.** In `render_report`, insert this after the Quality tables and before
  `## Definitions`:

```python
        "## Ground truth",
        "",
        *_ground_truth_run_rows(aggregate["runs"]),
        "",
        *_ground_truth_kind_rows(aggregate["runs"]),
        "",
        *_ground_truth_arm_rows(aggregate["arms"]),
        "",
```

and add:

```python
def _ratio(hit: int | None, of: int | None) -> str | None:
    return None if hit is None or not of else f"{hit}/{of} ({hit / of:.3f})"


def _ground_truth_run_rows(runs: dict[str, dict[str, Any]]) -> list[str]:
    """One row per run: status, recall and ceiling with counts, accuracy with counts, named, verdict.

    Args:
        runs: The aggregate's ``runs``.

    Returns:
        The header, the separator and one row per run. A missing figure renders
        as the dash ``cell`` gives ``None``, beside its status; never as zero.
    """
    header = ("| run | status | dataset | draft | reachable recall | ceiling | claim accuracy | "
              "named | future material | error |")
    rows = [header, separator(header)]
    for run_id, result in runs.items():
        gt = result.get("ground_truth") or {}
        counts = gt.get("claim_accuracy_counts") or {}
        reachable = counts.get("reachable")
        total = gt.get("scored")
        # Recovered as a count, because the table prints "hits/reachable": the
        # record keeps the ratio and the denominator, and the product is exact.
        matched_reachable = (None if gt.get("reachable_recall") is None or reachable is None
                             else round(gt["reachable_recall"] * reachable))
        accuracy = (None if gt.get("claim_accuracy") is None else
                    f"{gt['claim_accuracy']:.3f} ({counts['attempted']} attempted of {reachable} reachable)")
        verdict = ((result.get("audit") or {}).get("future_material") or {}).get("verdict")
        rows.append(
            f"| {cell(run_id)} | {cell(gt.get('status'))} | {cell(gt.get('dataset'))} "
            f"| {cell(gt.get('tag'))} | {cell(_ratio(matched_reachable, reachable))} "
            f"| {cell(_ratio(reachable, total))} | {cell(accuracy)} "
            f"| {cell(None if gt.get('named') is None else len(gt['named']))} "
            f"| {cell(verdict)} | {cell(gt.get('error'))} |"
        )
    return rows
```

```python
def _ground_truth_kind_rows(runs: dict[str, dict[str, Any]]) -> list[str]:
    """Matched / mismatched / named / absent of scored, per run and kind.

    Args:
        runs: The aggregate's ``runs``.

    Returns:
        The header, the separator and one row per (run, kind).
    """
    header = "| run | kind | matched | mismatched | named | absent | scored |"
    rows = [header, separator(header)]
    for run_id, result in runs.items():
        for kind, row in ((result.get("ground_truth") or {}).get("per_kind") or {}).items():
            rows.append(f"| {cell(run_id)} | {cell(kind)} | {cell(row['matched'])} "
                        f"| {cell(row['mismatched'])} | {cell(row['named'])} "
                        f"| {cell(row['absent'])} | {cell(row['scored'])} |")
    return rows


def _ground_truth_arm_rows(arms: dict[str, dict[str, Any]]) -> list[str]:
    """Reachable recall (mean / min) and pooled claim accuracy per arm, clean runs only.

    Args:
        arms: The aggregate's ``arms``.

    Returns:
        The header, the separator and one row per arm, naming how many runs
        were left out as touched or unaudited.
    """
    header = "| arm | runs used | reachable recall (mean / min) | claim accuracy (pooled) | left out |"
    rows = [header, separator(header)]
    for arm, summary in arms.items():
        left = summary.get("ground_truth_left_out") or {}
        mean, low = summary.get("reachable_recall_mean"), summary.get("reachable_recall_min")
        recall = None if mean is None else f"{fmt(mean)} / {fmt(low)}"
        pooled = summary.get("claim_accuracy_pooled")
        counts = summary.get("claim_accuracy_pooled_counts") or {}
        accuracy = None if pooled is None else f"{pooled:.3f} ({counts.get('matched')} of {counts.get('attempted')})"
        # Built first: a nested same-quote f-string needs Python 3.12, and this runs on 3.10.
        dropped = f"{left.get('touched', 0)} touched, {left.get('unaudited', 0)} unaudited"
        rows.append(f"| {cell(arm)} | {cell(summary.get('ground_truth_runs'))} | {cell(recall)} "
                    f"| {cell(accuracy)} | {cell(dropped)} |")
    return rows
```

- [ ] **Step 4: Run** `tests/experiment/test_report.py` and see it pass.

- [ ] **Step 5: Commit** — `feat(experiment): the report shows ground truth per run, per kind and per arm`.

## Task 8: The judge's completeness caveat

Spec §6.4 (the map's scoping ruling).

**Files:** Modify `experiment/cli.py` (`_judge_run` and its manifest). Test `tests/experiment/test_cli_judge.py`.

- [ ] **Step 1: Write the failing tests** (append to `test_cli_judge.py`; they use its `_judge`,
  `_judgement` and `lm_profile` helpers)

```python
def test_grading_completeness_records_that_it_is_not_comparable_across_windows(
    tmp_path, lm_profile, capsys
):
    _, out = _judge(
        tmp_path, lm_profile, argv=("--dimension", "completeness"),
        reply="raw", text='{"scores":{"completeness":3}}',
    )
    manifest = _judgement(out)["manifest"]
    assert any("not comparable across windows" in c for c in manifest["caveats"])
    assert "not comparable across windows" in capsys.readouterr().out


def test_grading_structure_alone_carries_no_window_caveat(tmp_path, lm_profile):
    _, out = _judge(tmp_path, lm_profile, reply="raw", text='{"scores":{"structure":4}}')
    assert _judgement(out)["manifest"]["caveats"] == []
```

- [ ] **Step 2: Run and see failure.**

- [ ] **Step 3: Implement.** Near `JUDGE_DIMENSIONS`:

```python
#: Said wherever completeness is graded: the judge never learns the window, so a
#: draft of a short window is graded for omitting what it could not show (map
#: "Ground-Truth Yardstick", scoping ruling of 2026-09-21).
JUDGE_COMPLETENESS_CAVEAT = (
    "completeness is graded without the window the draft covers; it is not comparable "
    "across windows of different sizes"
)
```

In the manifest dict, add `"caveats": [JUDGE_COMPLETENESS_CAVEAT] if "completeness" in dimensions
else []`. In `_judge_run`, after the scores line, add
`if "completeness" in dimensions: print(f"note: {JUDGE_COMPLETENESS_CAVEAT}")`.

- [ ] **Step 4: Run** `tests/experiment/test_cli_judge.py` and see it pass.

- [ ] **Step 5: Commit** — `feat(experiment): the judge says its completeness is not comparable across windows`.

## Task 9: Glossary, D-row and the documents to amend

Spec §8 and §10.

- [ ] **Step 1 — `<ai_rfc>/CONTEXT.md`** (it doesn't exist today; if the owed-fixes row created it,
  extend it instead). Add a "Ground truth" section with one-line definitions, taken from the map's
  glossary (`<map>/map.md`, "Glossary"):
  - window, anchor commit, declared spec version, citation, shown material, reachable fact;
  - reachable recall, all-facts recall, ceiling;
  - attempted, named;
  - future material, future-free workspace, touched.

  It is a glossary only, with no implementation detail.
- [ ] **Step 2 — SP7d's corrected recall reading is not this plan's to write** (amended
  2026-09-22). `<ai_rfc>/docs/experiments/2026-09-18-sp7d-instrument.md` is a recording, and it has
  no ground-truth section to correct: it never mentions recall or 8/35. The 8/35 reading was only
  ever in the git-ignored SP7d ledger. The correction is published by the SP7d Phase 5 write-up,
  `<ai_rfc>/docs/experiments/2026-09-21-sp7d-phase5.md`, a new dated file drafted in the ledger.
  - Confirm it has landed with `git -C <ai_rfc> log --oneline -- docs/experiments/2026-09-21-sp7d-phase5.md`.
  - If it hasn't, report that. Never edit the instrument doc; `docs/experiments/` recordings are
    never edited.
- [ ] **Step 3 — commit in ai_rfc** — `docs: name ground truth's terms`, with `CONTEXT.md` only.
- [ ] **Step 4 — the D-row (PANTHER).** Find the highest D-number across
  `docs/superpowers/specs/*arfc*` with `grep -ohE '\| D[0-9]+' … | sort -t D -k2 -n | tail -1`.
  Add the next one to the decision table of
  `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md`, with the text of spec §8.
- [ ] **Step 5 — the SP7d deviation (PANTHER).** Append the next `D-NN` entry to
  `docs/superpowers/plans/2026-09-15-arfc-sp7d-deviations.md`: R93, the ceiling finding, the
  re-scored figures, and pointers to the map and the spec.
- [ ] **Step 6 — commit in PANTHER**, both paths, `git status -sb` first (peers commit on this branch):
  `docs(ai_rfc): record the ground-truth D-row and SP7d's corrected recall`.

## Task 10: Gate and acceptance

- [ ] **Step 1 — the full suite**, same command as Task 0 Step 5. Report the counts against the
  baseline, as arithmetic: baseline + new tests − replaced tests.
- [ ] **Step 2 — the four drafts re-score to the map's numbers.** From `/tmp/claude-501/gtm-accept/`:
  - extract the pilot drafts read-only, with
    `git -C ~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831/runs/A1/workspace/draft show
    draft-elniak-aioquic-reconstructed-10:draft-elniak-aioquic-reconstructed.md > pilot-A1.md`, and
    A2 at tag `-11`;
  - take the v2 drafts from `<ai_rfc>/.superpowers/sdd/2026-09-15-arfc-sp7d/t11/armA-drafts/A{1,2}-10.md`;
  - run `ai-rfc experiment ground-truth <draft> --out out/<name> --target aioquic --window 2-11` on
    each.

  **Expected:** reachable recall 11, 11, 9 and 10 of 26; claim accuracy 1.000; named 0, 0, 2 and 1.
  Any difference is a finding: stop and report.
- [ ] **Step 3 — the tip dataset scores.** Run
  `ai-rfc experiment ground-truth pilot-A1.md --out out/tip --dataset aioquic-h3-at-6d36838.yaml`.
  Record the figures; this is informational. Its ceiling should be about 1.0 over window [1, 342].
- [ ] **Step 4 — `analyze` on copies, never the originals.**
  - Copy `~/ai-rfc-experiments/campaigns/aioquic-w02-11-v2-armA-sp7d-pinned` and
    `…/mark-full-1-consolidate-sp7d-v2` to `/tmp/claude-501/gtm-accept/`, then run `ai-rfc
    experiment analyze <copy>` on each (MARK takes about 18 minutes: run it detached).
  - **Expected:**
    - the v2 copy's Ground truth section shows 9/26 and 10/26, both touched, and an arm row with
      "2 touched";
    - the audits' `future_material.touching` counts are 2 and 6, which reproduces ticket 12;
    - the MARK copy shows `no declared spec` and "—", never 0.
- [ ] **Step 5 — hand over.** Stop before any gitlink bump or push; both need the user. Report:
  - every commit, per repository, with its SHA;
  - the suite counts;
  - the acceptance figures.

  The prevention plan (`docs/superpowers/plans/2026-09-22-arfc-future-free-workspace.md`) runs
  next, from its own entry gate.

---

## Self-review notes (made while writing)

- **Spec coverage:**
  - §3 → Task 3; §4.1 → Task 3; §4.2 and §4.3 → Task 4; §4.4 and §4.5 → Task 2; §4.6 → Task 1;
  - §5 → Tasks 2 and 3; §6.1 and §6.2 → Task 6; §6.3 → Task 7; §6.4 → Task 8; §7.3 → Task 5;
  - §8 and §10 → Task 9; §12 → Task 10 (acceptance).
  - §7.1, §7.2 and §11 → the prevention plan, deliberately.
- **Declared-spec rule for the tip dataset (flagged for the user):** facts citing RFC 9297 or
  RFC 9220 become unscored, because the tip code names no RFC. Only ALPN `"h3"` (RFC 9114) and its
  normative reference RFC 9204 count, the same pairing used for h3-22 and QPACK. If the user rules
  that a fact's own citation suffices, drop that branch of the migration script.
- **Python 3.10:** no nested same-quote f-strings (Task 7 builds that cell's text first).
