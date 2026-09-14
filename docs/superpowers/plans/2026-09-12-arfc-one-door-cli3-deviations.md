# CLI-3 deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-12-arfc-one-door-cli3.md`.
Three fields each: what the plan said, what the code or the tool showed, what I did.

**Entry 0 — the rulings, the measured corrections to the brief, D1–D17 and the Phase 1 baselines —
lives in the plan file itself**, under "Entry 0 — rulings carried into the row", "Measured
corrections to the brief", "D1–D17 — review findings, fixed in this plan before Task 1" and
"Baselines measured at Phase 1". It is recorded there rather than duplicated here so the two cannot
drift: the plan is the artifact a reviewer reads, and every ruling is a constraint on a task in it.

**Plan-mode transplant (CLI-2's R9 precedent).** The plan was written under plan mode, which permits
writing only the harness plan file. On approval it was copied **verbatim** to
`docs/superpowers/plans/2026-09-12-arfc-one-door-cli3.md` — verified byte-identical by sha256
`6b98961b248da18b22831f3f4b9024bbfc5c95d54ea46cdf196bbfcbeaccd5d3` — this log was opened beside it,
and both were committed in PANTHER with `git add -f` **before Task 1 ran**. The single `review-plan`
invocation was made against the harness file and is **not** repeated after the transplant.

**Summary of what entry 0 settles, for a reader who wants the shape before the detail:**

- **Four user rulings (2026-09-12).** U1 restates §6's "`checkpoint` regains 3" as "stops
  collapsing"; U2 lands CLI-2's two owed spec amendments (the `bound_reached`/`action_performed`
  D-row and §5's exit-code sentence); U3 retires the folded `status` verb's CLI form and keeps the
  MCP tool; U4 pre-authorises `--panther-repo` (Task 10) as the cut line if the row overruns.
- **Eleven rulings I made** (R1–R11), each with its cost if wrong. The load-bearing ones: the core
  calls the **API functions**, not `main(argv)` (R1, from a measured discriminator about who reads
  the report artifacts); the leaf verbs are **hidden, not deleted**, because arm C types them
  through the root door (R3); the workspace is derived from the config file's **own directory**,
  never from its `workspace:` field (R9); and `ai_rfc/server/cli.py` is **deleted**, not merely
  re-`prog`ged, because a second parser tree kept only for tests is the compat layer this codebase
  forbids (R11, with a stated fallback).
- **Seven measured corrections to the brief** (M1–M7). The largest: the captured arm-B transcript
  needs **no** regeneration — it is `arfc`-spelled, carries its own `families` key, and its own
  docstring states the principle that a recording is never edited to match a rename (M1).
- **Seventeen review findings fixed before any task ran** (D1–D17): nine Critical and five Warning
  from one `review-plan` invocation, plus three from a following adversarial read, one of which was
  an internal contradiction between Task 5 and U3. **Five of the seventeen were REDs that would
  have passed against unfixed code or could never have gone green afterwards.**

**Operational hazard noted at the Phase 0 gate.** Six peer sessions were live in this worktree at
the gate, three of them busy. Both repositories were clean, so no uncommitted `ai_rfc/server/` or
`ai_rfc/experiment/` edits existed. `git status -sb` is checked in both repositories immediately
before every commit, and BASE is recorded before every dispatch.

---

# Execution-phase deviations (D18 onward)

One entry per task, added as tasks run.

D1–D17 above were written in Phase 2 from one `review-plan` invocation plus one adversarial re-read,
**before any task ran**. What follows is the execution record: 11 tasks, 42 commits in `ai_rfc`
(`51033cc..5b3bf7b`) and 3 in PANTHER. The full per-task ledger — every ruling, RED, mutant and
measurement — is the row's SDD workspace at
`panther/plugins/services/testers/ai_rfc/.superpowers/sdd/2026-09-12-arfc-one-door-cli3/progress.md`
(gitignored, deliberately kept).

## D18 — The row's central claim, earned

`ai_rfc/server/core/` no longer runs the substrate as a program. `gates.py` and `core/build.py`
carry neither the `_run` helper nor a `subprocess` import; the surviving `subprocess` imports in
`core/draft.py` and `core/queries.py` are the git calls the spec keeps. The proof is **not** the
argv-shaped test the plan specified — that predicate misses `python3 -m`, `-c`, console scripts,
`shell=True` and every non-`run` entry point. It is the structural assertion that the modules have
no `subprocess` attribute at all, asserted for both.

## D19 — The plan's RED could never have gone green, and why that mattered twice

Task 3's specified RED patched `subprocess.run` to refuse **everything**. Measured: the substrate
shells to `git` underneath every verb (`manifest_gate` 4×, `citation_gate` 1×), so a blanket refuser
was a permanent red. Narrowed to `[sys.executable, "-m"]`, which is the property actually wanted.
Task 7 hit the same class from the other side: a check written as *"the two codepoints someone
named"* produced a real RED, would have gone green, and **nine offenders across three further
codepoints survived in files it had just cleaned**. `str.isprintable()` found all nineteen.

## D20 — Exception granularity, and the tension that turned out not to exist

In-process, an out-of-family exception propagates where a subprocess turned it into exit 1. Each
site's family is named individually; `manifest_gate`'s was previously unmeasured and is
`(SchemaError, OSError)` wrapping the load **only**. Reproducing that faithfully leaves three
`write_text` calls unwrapped — but `reported` wraps the whole verb body, so an `OSError` returns
exit 1 with a traceback list and **nothing crosses into the server framework**, byte-shape-identical
to the child process dying the same way. Fidelity and safety did not conflict.

## D21 — R2 held, and the plan's own fixture could not have shown it

`stderr` is synthesised from values and preserves the subprocess's byte shape, verified against the
**pre-refactor program** rather than against a capture: three findings produce five `stderr`
elements, because `str.splitlines()` has eleven delimiters and a newline-bearing finding becomes
three. The natural in-process spelling makes it one. Task 2's review caught that the characterisation
fixture carried no newline-bearing finding and so pinned nothing.

## D22 — Six hidden, not seven; hidden, not deleted

The plan named seven leaf verbs to retire from the help. `draft` is not one: it is a spec-named
agent group whose verbs the arm prompts render. And they are hidden rather than deleted because arm
C types `python -m ai_rfc check` and `python -m ai_rfc draft checkpoint|gate` **through the root
door** — deletion breaks it. Every `cli.py` stays registered, so the conventions test needed no edit.

## D23 — The mount is 31 files, not 11

Four per-entry conventions invariants apply to every registered entry point, and `pyproject.toml`
uses `find` rather than `find_namespace` — so a group without an `__init__.py` is **absent from an
install with no test in the source tree noticing**. Ten packages × three files, plus the package.

## D24 — Three artifacts carried something untrue, and one was executable

- A bare `print` in `draft/cli.py` let an agent-written `cluster_id` forge `note: gate clean` **while
  findings were non-empty and the exit code was 3** — an inversion, because that line is otherwise
  printed only when findings are empty. Reachable from **all three arms including arm A**, which has
  no shell, because the read-tool set grants unscoped `Write`/`Edit`.
- The regenerated skill would have **instructed a model session to run commands Task 8 deleted**,
  because seven prompt slots still named the retired door.
- The campaign shim **executed its own interpreter path**: `py$(touch forged)` ran, exit 126, marker
  written. Arbitrary command execution through generated shell text, not a forged line.

## D25 — The provenance retirement made the record lie, and the keys went

Retiring `--panther-repo` exactly as scoped leaves `git.panther` describing the **ai_rfc** repository
under a PANTHER label — measured: both candidate roots describe identically, while a real pilot
recorded genuinely different values. Three keys were retired rather than left to duplicate their
neighbour under a misleading name. `load_campaign` tolerating their absence is **reading a recording,
not a dual API**: verified by loading the real pilot record end to end, confirming the field is not
resurrected as an attribute and a re-dump emits neither field nor default.

## D26 — A guard the column never had

`docs/parity.md`'s verb column drifted for the whole row because the only test asserted **tool**
names. The new guard walks the live parser — a segment counts only when it is a *choice* of the
parser above it — and failed **20 of 20 rows** against the stale table. Its own parser had to handle
an escaped pipe inside a flag alternation: a naive `split("|")` reads that row as five cells and
checks the wrong column on exactly the longest cell.

## D27 — Methodology this row earned, and paid for

- **A measured delta is not a diagnosed delta.** A 25-module import cost decomposed to 4 from the
  suspected cause and 21 from an unavoidable one.
- **A killed mutant proves a line is load-bearing for the inputs the suite happens to use**, and
  nothing about the inputs it does not. A blank-line regression survived all six mutants because no
  test supplied an empty block.
- **A length-preserving mutation restored within a second leaves pytest's rewritten bytecode valid**,
  producing a phantom result across six runs. `-p no:cacheprovider` does not touch that cache.
- **Compare collected totals over the same selection**, never passed counts: a reported 27-test drop
  was a narrower selection, not a regression.
- **When tempted to enumerate, ask whether a predicate exists** — and check the enumeration derives
  from the artifact's *retired* shape, not its current one. Deriving retired verb names from the live
  registry flags 3 of 38; *hyphenated, or a verb the parser still owns* flags 18 and leaves two.
- **A comment carrying a measurement must carry the one that survived.** Broken three times here;
  each sent a reader somewhere untrue. The fourth case *under*-claimed: a fix described as covering
  two sites is a funnel covering all of them.
- **The editing tool normalises `\uXXXX` escapes into raw characters** — build such escapes by
  concatenation. Six files carried raw non-printing codepoints; `tests/substrate/test_source_hygiene.py`
  now forbids them by predicate.

## D28 — Owed, and not this row's

`report.py` interpolates five values into Markdown **code spans** unescaped: a backtick survives
`check-ref-format`, `git describe` and JSON intact, then breaks the span so raw HTML goes live. The
standalone module doors still forge. Exit code **1 is overloaded across six conditions**, so a caller
cannot distinguish "unusable inputs" from "crashed" — which the module docstring and the spec both
claim it can. **The spec has no decision row for the `status` ruling**: §6 still says the parity
verbs become grouped subcommands with no exception, while one of them deliberately gets no CLI verb.
