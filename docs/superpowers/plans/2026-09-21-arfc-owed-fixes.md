# ai_rfc owed fixes — the 57 items the whole-branch review left: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land every item the 2026-09-15 whole-branch review of the one-door roadmap (CLI-1, CLI-2,
CLI-3) ruled on and left owed — 57 items across two repositories — in the shape the rulings map
decided: **site, ruling, check**, partitioned by **landing unit**, verified **per row as it lands
plus the CLI-3 gate once over the finished set**.

**Architecture:** Nothing here is new design. Every task below executes a ruling already made on the
post-review map (`<submodule>/.superpowers/sdd/2026-09-15-arfc-post-review-rulings/`, closed
2026-09-16); the plan's job is to name the site each ruling lands at, verified against today's tree,
and the check that discharges it. The two Criticals downgrade as **consequences of landing**, not as
decisions: C-2 (a fabricated checkpoint is indistinguishable from an earned one) once the coverage
detector ships in Task 7, C-3 (the production report's Markdown sinks) once Task 4 lands.

**Tech Stack:** Python 3.10 (`<worktree>/.venv`), pytest, argparse, PyYAML. Python 3.11
(`~/ai-rfc-experiments/venv-optimize`) for the gepa-importing selection. `fake_claude` for every
driver scenario. One `claude -p`-backed campaign at the end, capped at $25, launched only on the
user's in-session approval.

**Enumeration:** `<submodule>/.superpowers/sdd/2026-09-15-arfc-post-review-rulings/assets/ticket-23-owed-execution-audit.md`
— **the single enumeration**. Row numbers below (`#n`) are its rows. It is gitignored; do not
delete the map.

**Repositories:** PANTHER worktree `iut-ai-rfc` on `feat/arfc-pipeline-and-runtime-anchors`;
`ai_rfc` as a submodule at `panther/plugins/services/testers/ai_rfc`, on `main`. Plan opened at
PANTHER `c21a60500`, ai_rfc `df7a87e` (gitlink matches). Every site below was re-read at
`df7a87e` on 2026-09-21 — **not** inherited from the audit's pin at `329e52f`.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Zero spend, with one exception.** Nothing in Tasks 0–11 spends. Task 12 Part B is the one
  authorised spend on this row — **≤ $25**, granted by the map's gate ticket — and it launches only
  when the user approves that exact launch in the same session. No `claude -p` run happens in any
  other task. **Never use an Anthropic API key**; test presence with `test -n`, never print it.
- **Two peer sessions are live in this tree** (`post-sp7d-cleanup-gepa`, which landed the GEPA
  winner as ai_rfc `3406985` and the gitlink bump `2dcfda8d7` **while this plan was being
  reviewed**, and is now running SP7d's Phase 5; `fix-gepa-pilot-pristines`, re-preparing evidence
  roots). Those two commits are **not this row's** and are excluded from its reviews; Task 0 records
  BASE from the tree at that moment, never from this paragraph. **No task below touches
  `ai_rfc/driver/prompts/` or `plugins/ai-rfc/skills/`.** Before any task that edits
  `ai_rfc/experiment/*` (Tasks 4, 6, 7, 8, and row #29 in Task 3): `ListAgents`, `git status
  --short` in the submodule, and one factual `SendMessage` to any live peer naming the files and the
  commit message — never wait for a reply. Those tasks are **ordered last** for this reason.
- **Git discipline.** `git status --short` in every repository touched before every commit. Stage by
  explicit path; commit by explicit pathspec (`git commit -m "…" -- <paths>`). Never `git add -A`
  or `git add .`, never `--no-verify`, never `git stash`, never amend a commit on the branch, never
  move the submodule pointer backwards, never `git checkout --` a file you did not write. Check the
  recorded gitlink (`git ls-tree HEAD panther/plugins/services/testers/ai_rfc`) before any bump — a
  peer will bump for the GEPA winner. Commit messages: `type: lowercase summary` in ai_rfc,
  `type(scope): lowercase summary` in PANTHER; second `-m` carries the session trailer; use `-F` for
  a message containing backticks.
- **Evidence is read-only.** `~/ai-rfc-experiments/`, `~/arfc-experiments/` (both roots exist),
  `reconstructions/mark`, `docs/experiments/`, `tests/driver/fixtures/`: copy out, never in. Never
  run `experiment audit|analyze` against an existing campaign. Never write a synthesised record
  into an archive (the fallback ruling's own rule).
- **Never edit an artifact that testifies to a past state.** The whole-branch review report, the
  register and the tickets are not amended by fixes; severity movements are recorded in this row's
  deviation log and on the map.
- **Test invocation:** sandbox OFF for pytest and nested git; prefix `SSLKEYLOGFILE=`; `-p
  no:cacheprovider`; always `--basetemp` under `/tmp/claude-501`; **pin `-n 4`** and compare
  collected/passed/failed/skipped separately, never a total. Interpreter `<worktree>/.venv/bin/python`,
  never a pyenv shim. Full suite ≈ 4m45s at `-n 4`.
- **The suite's subprocesses reach `/usr/bin/git`** (the Xcode shim), not Homebrew's. Until the
  Xcode license is accepted on this machine, every git-shelling test fails with exit 69 — see D-2.
  That is the entry gate, not a code problem.
- **Style:** Google-style docstrings on public functions; line length 88; `from __future__ import
  annotations` where neighbours use it; comments only where the why is not obvious; no
  backward-compatibility shims; **a predicate over an enumeration** wherever a set is derivable
  from the tree (ADR 0002); `tests/substrate/test_source_hygiene.py` forbids non-printable
  codepoints — build any `\uXXXX` by concatenation.
- **New logic is a module, never a `cli.py`**: `tests/substrate/test_cli_conventions.py:148-178`
  rglobs for `cli.py` and demands each be a registered entry point (SP7d R6).
- **One `review-plan` invocation** on this file before Task 1, none after.
- **The SDD ledger is gitignored**; a `git clean -fdx` destroys it.

---

## Measured baselines (2026-09-21, row open)

| Suite | Command | Result |
|---|---|---|
| ai_rfc 3.10 full, `-n 4`, sandbox off | `pytest tests -n 4 --basetemp /tmp/claude-501/owed-baseline2` | **37 failed, 2313 passed, 12 skipped, 23 errors** in 284 s — every failure chains to `git … exited 69: You have not agreed to the Xcode license agreements` (D-2) |
| ai_rfc 3.10 full, SP7d's gate 2026-09-18 (reference) | same selection | 2373 collected: 2372 passed, 1 failed (load flake), 12 skipped |
| ai_rfc 3.11 optimize selection (reference) | `~/ai-rfc-experiments/venv-optimize/bin/python -m pytest tests/experiment/optimize tests/experiment/test_cli_optimize.py -m "not slow"` | 275 / 2 / 3 |
| PANTHER door tests (reference) | `tests/unit/test_cli/test_ai_rfc_commands.py`, sandbox off | 6 passed |

**Task 0 re-measures the first row after the license is accepted and must reproduce the reference
shape** (2373 collected, ≤ 1 failed and that one the known load flake) before Task 1 runs.

---

## Entry 0 — rulings carried into the row

- **R0.1 — The enumeration is authoritative over any ticket's own "Owed execution" list** (map
  decision 23.2). Where they disagree about ownership, the enumeration's owner lands the item.
- **R0.2 — Rows #17, #41, #51, #52 are measurements or process instructions, not tasks.** They are
  discharged as ledger entries: #17 (re-establish the undefended-sink count, scope named) at the end
  of Task 4; #41 (re-check the spec digest) immediately before Task 10's commit; #51 and #52 (two
  "not a defect today" shapes) recorded in Task 5's report with the SHA checked.
- **R0.3 — Rows #55 and #56 are Task 12** with their $25 authorisation intact; the build half runs
  first and costs nothing; the campaign half targets a **re-prepared** pristine that already carries
  both context handles (`~/ai-rfc-experiments/pristine/aioquic-w05-05` or `w06-06`), so it does not
  wait on the peers' w02-11 / MARK re-preparation.
- **R0.4 — Rows #53 and #54 are subsumed by #37** (one spec diff), and #54 is **withdrawn** by D-1
  below: D58 keeps both "judge" and "ground truth", because both now exist.
- **R0.5 — Row #29 (`--id` shape) lands inside Task 3 as the path-guard unit it belongs to**, but as
  the task's last commit, after the peer check, because it edits `experiment/cli.py`.
- **R0.6 — Docs corrections land with the code they describe** (#24 with Task 1, #13 with Task 7),
  not as a separate docs task; the citation qualifications (#44, #45, #59) are their own small task
  because they touch nine files for one reason.
- **R0.7 — `Parser` moves out of `ai_rfc/cli.py` into `ai_rfc/parser.py`** (Task 8) so the 27
  standalone doors can construct it without importing the root's parser builder. Measured: the root
  imports only `__version__` and `entrypoints` at module level, so a leaf importing `ai_rfc.cli`
  would not cycle today — but every leaf pulling the root's `USAGE`/`SECTIONS`/epilog machinery to
  get one class is the wrong direction, and R6 forbids a second `cli.py`.
- **R0.8 — `_write_once` keeps its atomic publish AND gains exclusivity** (Task 6). The naive swap
  of `path.exists()` for `open(path, "x")` loses the tmp-then-rename atomicity. The idiom that keeps
  both: write the temporary, `os.link(temporary, path)` (fails with `FileExistsError` if a holder
  exists), then unlink the temporary. State this in the task or an implementer ships the naive form.
- **R0.9 — The promoted Markdown module lives at `ai_rfc/markdown.py`** (Task 4). Measured:
  `ai_rfc/driver/__init__.py` has exactly one import (`__future__`), so `from ai_rfc.driver import
  printable` pulls in no driver submodule and creates no cycle for the substrate's `report.py`.
- **R0.10 — The coverage predicate lives at `ai_rfc/driver/coverage.py`** (Task 7), signature
  `covers(checkpoints_dir, transcripts) -> dict[cluster_id, Route | None]`, candidates supplied by
  the caller, nothing resolved by the predicate, nothing written to any archive. `lifecycle/` →
  `driver/` is an existing edge; `lifecycle/` → `experiment/` must stay at zero.

### Deviations found while planning (D-1 … D-4), fixed in this plan before Task 1

| # | What the map said | What the tree shows at `df7a87e` | What this plan does |
|---|---|---|---|
| **D-1** | Spec proposal section 4 (row #37): "no ground-truth surface was built at all; judging is a library"; ticket 22 (row #54): `ground_truth` has zero hits, D58 drops the words. | SP7d landed **after the map closed**: `ai-rfc experiment judge` (`experiment/cli.py:1533`) and `ai-rfc experiment ground-truth` (`:1601`) are verbs; `experiment/ground_truth.py` and `groundtruth/aioquic-w02-11.yaml` exist. Top-level `experiment` verbs today are **twelve**: `profile preflight render workspace campaign run audit questions analyze judge ground-truth optimize`. | Task 10 re-derives the `:57` verb list from `experiment/cli.py`'s `add_parser` calls at commit time and drops the "never built" sentence; **row #54 is withdrawn**, D58 keeps both words. Recorded so the corrected fact is not un-corrected by the proposal's text. |
| **D-2** | The row opens on a green baseline. | 37 failed + 23 errors, all `git … exited 69: You have not agreed to the Xcode license agreements`. `which -a git` → Homebrew first for the shell, but `fake_claude` and the driver scrub `PATH`, so subprocesses reach `/usr/bin/git`. Not a code regression: SP7d measured 2372 passed on 2026-09-18 on the same tree. | **Task 0 stops until the user runs `sudo xcodebuild -license accept`**, then re-measures. No task starts on a red baseline that is not the known load flake. |
| **D-3** | Row #29's site is `experiment/cli.py:909`. | `--id` is declared at **`:1354`** (SP7d added ~445 lines of verbs above it). Sink unchanged at `experiment/config.py:356`. | Site corrected in Task 3. |
| **D-4** | Row #30's site `server/paths.py:296`. | The line is **`:297`** (`workspace_path = config.workspace.expanduser().resolve()`); the peer's `missing_context_handles` change at `:295` moved it by one and did not close it. | Site corrected in Task 3. |

---

## Execution order and dependency graph

```
Task 0  entry gate (license, baseline, peers, SHAs)            — no code
Task 1  exit codes                (#19–24)                     — lifecycle/, pipeline/, check/, coverage/, draft/, history/, timeline/, README
Task 2  the stop vocabulary       (#3–5, #42)                  — cli.py, driver/stop.py, driver/sweep.py, lifecycle/run, config.py, tests/driver
Task 3  path guards               (#25–28, #30, #31; then #29) — server/core, draft/gate.py, server/paths.py; last: experiment/cli.py
Task 5  SP4 closure               (#46–50, #43; #51–52 ledger) — pipeline/state.py, draft/completeness.py, tests/ledger
Task 9  citations and stale lines (#44, #59, #58; #45 AFTER Task 7) — 9 doc/test sites; one PANTHER plan line
Task 11 ADR promotion             (#1, #2)                     — ai_rfc/docs/adr/ (new, two commits)
──── peer check before each of the following (they touch experiment/) ────
Task 4  sinks                     (#14–16; #17 ledger)         — ai_rfc/markdown.py (new), report.py, experiment/{report,quality}.py, server/core/{gates,build}.py, forge/cli.py
Task 6  run-directory claim       (#32–36)                     — driver/record.py, driver/spawn.py, experiment/runner.py, tests/driver
Task 7  coverage detector         (#6–13)                      — driver/coverage.py (new), driver/record.py, lifecycle/verify, experiment/{metrics,audit}.py
Task 8  the hardened Parser       (#18)                        — ai_rfc/parser.py (new), cli.py, 27 standalone doors, tests/substrate
Task 10 the spec diff             (#37–40, #53; #41 ledger)    — PANTHER spec + CLI-3 deviation log
Task 12 whole-row review, fix wave, then the gate (#55, #56)   — $0 build; ≤ $25 campaign on approval
Task 13 hand-over: push + gitlink, asked once
```

Tasks 1, 2, 3, 5, 9, 11 are independent of each other. Task 7 depends on nothing but is the
largest; Task 10's §5 sentence about exit codes depends on Task 1 having landed; Task 10's wall-clock
note depends on Task 2 (the field then exists). Task 12 runs last.

---

## Task 0: Entry gate — no code

- [ ] **Step 1 — the license.** Ask the user to run `sudo xcodebuild -license accept` (or switch
      the shim: `sudo xcode-select -s /Library/Developer/CommandLineTools`). Verify with
      `/usr/bin/git --version` printing a version, not the license text.
- [ ] **Step 2 — the baseline.** `SSLKEYLOGFILE= <venv>/python -m pytest tests -n 4 -q --basetemp
      /tmp/claude-501/owed-t0 -p no:cacheprovider` from the submodule root, sandbox off. Required
      shape: **2373 collected** (or more if the peer committed tests), ≤ 1 failed, and that one
      **verified passing alone** — SP7d recorded its load flake by behaviour, never by name, so no
      test is pre-excused here (D-9). Record the four figures in the ledger. Then the 3.11 selection (expect 275/2/3) and the PANTHER door
      tests (expect 6).
- [ ] **Step 3 — peers and SHAs.** `ListAgents`; `git status -sb` in both repositories; `git
      ls-tree HEAD panther/plugins/services/testers/ai_rfc` in PANTHER. Record BASE = ai_rfc HEAD
      and PANTHER HEAD in the ledger. If the GEPA winner has been committed, note its SHA so it is
      excluded from this row's reviews.
- [ ] **Step 4 — the map.** Confirm
      `.superpowers/sdd/2026-09-15-arfc-post-review-rulings/assets/ticket-23-owed-execution-audit.md`
      exists (gitignored — it is the only copy). Confirm `docs/adr/` does not yet exist in ai_rfc.
- [ ] **Step 5 — `review-plan`** on this file, once. Fix every Critical and Warning in the plan and
      record each as a D-row in the deviation log. **Stop for the user's approval before Task 1.**

---

## Task 1: Exit codes — three verdict sites, fourteen unguarded writes, `run` refuses 2

**Rows:** #19, #20, #21, #22, #23, #24. **Ruling:** *Amend the exit-code ruling* — 1 means "the
command could not complete" and stands; `verify/cli.py:26-32`'s `_outcome()` already defines 3 as
"findings"; the three verdict sites are non-conforming; all fourteen unguarded result writes are a
defect family; `run` keeps propagating 3 and refuses 2 because `test_cli_conventions.py:34`
enforces "2 belongs to argparse alone".

**Sites (re-read at `df7a87e`):**

| # | Site | Today | Change |
|---|---|---|---|
| 19 | `ai_rfc/lifecycle/doctor/cli.py:319` | `return 1 if any(not c.ok and c.severity == "error" …) else 0` | `3` |
| 20 | `ai_rfc/lifecycle/toolchain/cli.py:109` | `return 1` after reporting `reasons` | `3` (the `:99` refusal stays 1) |
| 21 | `ai_rfc/pipeline/cli.py:432` | `return 1 if problems else 0` | `3` (`:256`, `:436` stay 1) |
| 22 | `check/cli.py:109-112` (mkdir + three `write_text`), `coverage/cli.py:123,136,139`, `draft/cli.py:438-442` (mkdir + `write_bytes`), `:459` (`write_completeness_report`), `:571` (`write_lint_report`), `:593` (`write_gate_report`), `history/cli.py:89` (`write_corpus`, and `build_index` at `:91`), `timeline/cli.py:161` (`write_timeline`) | outside the verb's `try` | inside it, so `OSError` is reported through the verb's existing `report_diagnostic("error: ", …)` / `_report` path and exits 1 |
| 23 | `ai_rfc/lifecycle/run/cli.py:298` | `return result.exit_code` | `3` propagates; `2` → `report("error: stage <name> exited 2, which belongs to argparse alone …")` and return 1 |
| 24 | `README.md:138-139`; `ai_rfc/server/README.md:58`; `ai_rfc/cli.py:157` — `main()`'s docstring says "0/1/3 per the package table", and the package table is the README taxonomy being corrected (measured: **no module docstring carries "unusable input"**; the phrase exists only in the two READMEs — D-5); spec §3/§5 (**Task 10**) | "0 clean, 1 unusable input, 2 malformed invocation (argparse), 3 strict findings" | "0 clean; 1 the command could not complete (refusals, crashes, stops with work outstanding); 2 malformed invocation, argparse alone; 3 findings — the one code with a machine consumer, `driver/sweep.py:798` for `check`" |

- [ ] **Step 1 — RED for the verdict sites.** In `tests/cli/` (doctor, toolchain) and the pipeline
      test module: a fixture producing one `error`-severity check / one unverifiable toolchain / one
      `problems` entry, asserting exit **3** and the report still printed. Run: fails with 1.
- [ ] **Step 2 — RED for the writes.** One parametrized test over the seven verbs: point `--out`
      at a path whose parent is a **file**, run the verb through `python -m` at the real process
      boundary (the audit reproduced two this way), assert exit 1, an `error:` line on stderr, and
      **no `Traceback` on stderr**. Run: fails with a traceback.
- [ ] **Step 3 — RED for `run`.** A stage stub exiting 2 (monkeypatch `perform`) → `run` returns 1
      with the `argparse alone` line; a stub exiting 3 → `run` returns 3 unchanged.
- [ ] **Step 4 — implement** the three returns, move the fourteen writes, add the `run` branch.
- [ ] **Step 5 — docs**: README lines, server README, the docstring, **and the package's
      exit-code table at `ai_rfc/README.md:161-170`** plus `README.md:166,221` and
      `docs/parity.md:78,80` (D-14: the phrase grep went to zero while the table still tied 3 to
      `--strict` and narrowed 1 in paraphrase). Check: the table states the four ruled meanings,
      and no line in `README.md`, `ai_rfc/server/README.md` or `docs/parity.md` gives 1 a narrower
      one — pasted, not grepped.
- [ ] **Step 6 — verify**: `pytest tests/cli tests/substrate tests/driver -n 4`; the three REDs
      green; `test_cli_conventions.py` unchanged. **Check (#19–21):** exit 3 asserted in a test.
      **Check (#22):** the parametrized boundary test. **Check (#23):** both stubs. **Check (#24):**
      zero `unusable input` hits.
- [ ] **Step 7 — commit** in ai_rfc, two commits: `fix: report findings with exit 3 at every verdict
      site and guard every result write`, `docs: state what exit code 1 means and name exit 3's
      consumer`.

---

## Task 2: The stop vocabulary — SIGTERM, operator interrupt, and the wall clock's field

**Rows:** #3, #4, #5, #42. **Ruling:** *The spec correction pass* decision 2 (the signal gap is
built, not struck: one process-global handler at the one console-script entry point, an
operator-interrupt `StopReason` with a resume line, the test at `test_spawn.py` fixed) and *The nine
spec-correction decisions* D-2 (the wall clock is built, not struck: add the `recon.yaml` field so
`sweep.run(deadline=…)` is reachable).

**Sites:** `ai_rfc/cli.py:149` `main()` (the only console script, `pyproject.toml:30`);
`driver/stop.py:100` `StopReason` (13 members, `done` last) and `_VERB` at `:215`;
`driver/sweep.py:359` (`deadline` parameter of the sweep), `:524` (mints `wall_clock`), `:1323/:1375`
(`run()` accepts and forwards `deadline`); `lifecycle/run/cli.py:381-399` (the one `except` clause;
`KeyboardInterrupt` is not caught, so the operator gets a traceback — D59 e false);
`lifecycle/next/cli.py` (same shape); `config.py:196-217` (the `sessions.*` field table), `:402-405`
(the `Sessions` dataclass), `:631-632` (construction); `tests/driver/test_spawn.py:186`
(`test_a_systemexit_kills_the_group_too` asserts a handler "installed at the CLI entry point" that
does not exist); `tests/driver/test_stop.py:53` and `tests/driver/test_record.py:678` (the
**deliberately pinned** member lists — extend them, do not derive them).

- [ ] **Step 1 — RED: the handler.** A test that runs `ai-rfc run --config …` as a subprocess
      against `fake_claude` with a scenario long enough to be mid-session, sends **SIGTERM to the
      driver process**, and asserts: exit code 1; `status.json` written with
      `reason: operator_interrupt`; a resume line (`ai-rfc run --config …`) on stderr; the session's
      process group gone. Run: fails — no `status.json`, default SIGTERM disposition.
- [ ] **Step 2 — RED: Ctrl-C.** Same scenario with SIGINT: today a traceback; expected the same stop
      record. (SIGINT's kill-the-group half already works in `spawn.py`; the stop record does not.)
- [ ] **Step 3 — implement.** `StopReason.operator_interrupt = "operator_interrupt"` with a
      docstring in the module's own idiom (which §5 row it spells: "operator interrupt" in D59's
      list) and `_VERB[...] = "run"`. In `cli.py:main()`, install `signal.signal(signal.SIGTERM,
      handler)` where the handler raises `KeyboardInterrupt` (so one path serves both signals and
      `spawn._kill_group`'s existing `except BaseException` keeps killing the group); install it
      **only in `main()`**, never at import, **only when the current disposition is `SIG_DFL`, and
      restore the previous disposition in a `finally`** — `main()` is called in-process by tests
      and by `panther ai-rfc`, and a handler left behind in a pytest-xdist worker turns its
      shutdown into a traceback (D-7). **The catch lives inside `sweep.run`, not in the CLI.**
      `sweep.py:1355`'s docstring today says `KeyboardInterrupt: Straight through. An interrupted
      run writes no …`, and `_finish` (`:1240`) is reachable only from inside the sweep — so a
      clause in `lifecycle/run/cli.py` could never produce `status.json` (D-6). Wrap the session
      loop in `sweep.run` with `except KeyboardInterrupt:` → `_finish(StopReason.operator_interrupt,
      …)` → re-raise or return the stop's exit code (choose return, so `run`/`next` need no new
      clause and print the resume line through the existing path); rewrite that docstring.
- [ ] **Step 4 — the field.** `sessions.deadline_s` (int, optional, per sweep, `None` = no wall
      clock) in the field table (`config.py:196-230`; the optional-field precedent is
      `sessions.profile` at `:224`, which carries no `default=` — confirm the loader yields `None`
      for an absent optional int before relying on it), dataclass and construction;
      `lifecycle/run/cli.py` computes
      `time.monotonic() + deadline_s` and passes `deadline=` to `sweep.run`. RED first: a config with
      `deadline_s: 1` and a `fake_claude` scenario slower than that stops with `wall_clock`.
      `config example` gains the field; `test_config.py`'s round-trip test covers it automatically
      (confirm, do not assume).
- [ ] **Step 5 — the pinned lists.** Add `"operator_interrupt"` to `test_stop.py:53` and
      `test_record.py:678`, and a resume-line row to `test_stop.py:328`'s table. Fix
      `test_spawn.py:186` to drive the real handler rather than inject `SystemExit`.
- [ ] **Step 6 — verify**: `pytest tests/driver tests/cli tests/substrate -n 4`. **Check (#3):**
      `grep -rn "signal.signal" ai_rfc/` → exactly one hit, in `cli.py`. **Check (#4):** `StopReason`
      has 14 members, the new one in `_VERB`. **Check (#5):** the spawn test no longer constructs a
      `SystemExit`. **Check (#42):** the deadline RED is green and `grep -c deadline ai_rfc/config.py`
      > 0.
- [ ] **Step 7 — commit**, two commits: `feat(driver): stop on an operator interrupt with a resume
      line, SIGTERM included`, `feat(config): let a recon.yaml set the sweep's wall clock`.

---

## Task 3: Path guards — membership, anchoring, containment, shape

**Rows:** #25, #26, #27, #28, #30, #31, then #29. **Ruling:** *Two path inputs that miss the guard
their siblings have* — four kinds of guard, not one fix; the membership guard already exists twice
(`driver/stop.py:438` `_checked_cluster_id`, `experiment/per_cluster.py:153`) and both copies stay;
apply one at the joins; `campaign_id` ranks below the four agent-reachable sinks.

**Sites (re-read):**

| # | Site | Join | Guard |
|---|---|---|---|
| 25 | `server/core/revisions.py:66` | `ctx.workspace / "checkpoints" / cluster_id / "checkpoint.json"` | membership in the timeline's cluster ids (`ledger.clusters` or `timeline` rows), via the `driver/stop.py:438` copy or a third copy in `server/core/` if the layer boundary forbids the import — decide by measuring the import edge, record which |
| 26 | `server/core/queries.py:105` | `ctx.workspace / "clusters" / cluster_id` | membership |
| 27 | `draft/gate.py:250` | `return checkpoints_dir / entry.cluster_id` | membership; the sibling `:249` already sanitises with `Path(...).name` |
| 28 | `server/core/gates.py:~84` (`:98` guards `base` in the same function) | `cluster_id` join | *consider*: apply the same membership guard; record if declined and why |
| 30 | `server/paths.py:297` | `config.workspace.expanduser().resolve()` | anchor a relative `workspace:` to `config_path.parent`, matching `:294`'s `Layout(config_path.parent)`. **Measured (D-8): two more readers take `config.workspace` raw** — `lifecycle/init/cli.py:58` (`Layout(dest or config.workspace)`) and `lifecycle/doctor/cli.py:181` — so a relative value anchors to the cwd at `init` too. The ruling names one site; the implementer may anchor **once, in the loader** (`config.py`'s `_coerce`/`load_config`, relative to the file's own directory) so all three readers agree, recording that as a ruling with its cost (a relative `workspace:` at `init` changes meaning; a test pins it). Minimum: the ruled site. |
| 31 | `server/core/questions.py:157` | `ctx.workspace / "interviews" / transcript` | containment: `resolved.is_relative_to(ctx.workspace / "interviews")` after `resolve()`, else `CoreError` |
| 29 | `experiment/cli.py:1354` (`--id`, D-3); sink `experiment/config.py:356` | `root / "campaigns" / campaign_id` | `type=` validator at the argparse boundary: `re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", …)`, refusing absolute and `..` — an **absolute** id *replaces* the root, which defeats the frozen-once guard |

- [ ] **Step 1 — RED**, one test per join, in the module's existing test file: a `cluster_id` of
      `../..`, of an absolute path, and of a YAML-typed `'None'`/`'1'` reaching each join is refused
      with the module's error type **and the refusal names the id** — never a `FileNotFoundError`
      from a path that escaped. For #30: a `recon.yaml` with `workspace: ./ws` resolved from a
      **different** cwd. For #31: a `transcript` of `../../etc/passwd`. For #29: `--id /tmp/x` and
      `--id ../x` exit 2 with argparse's message.
- [ ] **Step 2 — implement** the guards; reuse `_checked_cluster_id`'s predicate (membership, not a
      character filter — YAML implicit typing yields values with no control character that name
      nothing).
- [ ] **Step 3 — verify**: `pytest tests/server tests/substrate tests/driver -n 4`.
      **Check (each row):** its RED is green. **Check (#28):** a sentence in the ledger.
- [ ] **Step 4 — commit** in ai_rfc: `fix: refuse a cluster id, workspace or transcript that would
      escape the workspace at every join`; then, after the peer check, `fix(experiment): validate a
      campaign id at the argparse boundary` — **its own commit, last**.

---

## Task 4: Sinks — the production report, the shared Markdown module, the stderr sites

**Rows:** #14, #15, #16; #17 as a ledger measurement. **Ruling:** *Which undefended sinks are in
scope* — the production report is the sharper case; the Markdown primitives are promoted above
`experiment/` **carrying `_code()`**; stderr sinks are fixed at the composition sites (never joined
at a boundary — `diagnostics()`'s docstring says why); the whole path-join class went to Task 3.

**Sites (re-read):** `ai_rfc/report.py:148` (`` `{manifest.rfc}` ``), `:192` (`` `{structure.id}`
``, plus `structure.kind.value`, `.title`, `.section` in the same line, unescaped in prose);
`experiment/markdown.py` (exports `fmt`, `cell`, `separator`; docstring scoped to "this package");
`experiment/report.py:13` `_code()` (private; consumers at `:250-257`), `:10` import;
`experiment/quality.py:36` import; `server/core/gates.py:47,144,216`, `server/core/build.py:64,151`
(`diagnostics(f"error: {error}")` — the MCP tool arm's composition, the one in-range regression:
CLI-3's `5f2f256` fixed the CLI arm and left this one); `forge/cli.py:173` (git's stderr
interpolated raw into an `error:` line).

- [ ] **Step 1 — RED (#14).** A manifest whose `rfc` is `` x`</code><b>bold `` and a structure whose
      id carries a backtick: `to_markdown(report)` must render both inside intact code spans (the
      CommonMark longer-fence rule) and the title/section through `printable`. Assert the rendered
      text contains no raw `<b>` outside a code span — assert the *shape*, not a needle.
- [ ] **Step 2 — RED (#16).** For each composition site: an error whose message carries `\n` +
      `note: checkpoint written to /forged` must reach the tool result as **one** element whose line
      break is a visible escape, not two elements. Build the newline by concatenation.
- [ ] **Step 3 — promote.** `git mv ai_rfc/experiment/markdown.py ai_rfc/markdown.py`; move
      `_code` in as public `code(value)`; rewrite the module docstring's scope; re-point
      `experiment/report.py` and `experiment/quality.py` (**peer check first**: both are SP7d
      files). `ai_rfc/report.py` imports `code` and `printable` from it.
- [ ] **Step 4 — stderr sites.** Route the five `diagnostics(f"error: {error}")` calls and
      `forge/cli.py:173` through the existing escaping (`printable`, or the `lifecycle/common.report`
      family) **at the site**.
- [ ] **Step 5 — the measurement (#17).** Re-count the undefended sinks at HEAD with the same five
      classes R2 used (stderr, Markdown, path joins, shell words, encoders), name the scope (package
      only, or package + tests), and record the figure and the SHA in the ledger. Do not quote 26 or
      28.
- [ ] **Step 6 — verify**: `pytest tests/substrate tests/server tests/experiment -n 4`; the SP7d
      goldens under `tests/experiment/` byte-identical. **Check (#14):** Step 1 green.
      **Check (#15):** `grep -rn "from .markdown\|experiment.markdown" ai_rfc` → zero; `grep -rn
      "from ai_rfc.markdown\|from \.\.markdown\|from \.markdown" ai_rfc` → the three consumers.
      **Check (#16):** Step 2 green at all six sites. Record **C-3 → Important** in the deviation
      log and on the map.
- [ ] **Step 7 — commit**, three commits: `refactor: share one Markdown escaper above the
      experiment package`, `fix: escape every value the production report interpolates`,
      `fix(server): compose an error line that its own message cannot forge`.

---

## Task 5: SP4 closure — route the two window-blind readers through the ledger's reducer

**Rows:** #46, #47, #48, #49, #50, #43; #51, #52 as ledger checks. **Ruling:** *Two HOLDS rows a
later finding implicates* — F-1 is fixed now by **routing every reader through `ledger.counts()` or
the flag-aware `done` property**, the only remedy that reaches `completeness`'s `totals`; a
narrowed-window fixture ships with the fix; the state docstring stops asserting an agreement that
does not hold.

**Sites (re-read):** `pipeline/state.py:216` `_checkpoint()` — after `ledger.clusters(ws.root)` it
recomputes `total = len(states)` and a raw `state.checkpoint` sum (re-locate, ~`:236-246`); its
docstring at `:225-228` claims "the three agree"; `draft/completeness.py:274` (`states =
ledger.clusters(...)`), `:280-282` (`unprocessed_clusters` filters raw `state.checkpoint`),
`:291-297` (`totals` from `attribute_claims` → `load_clusters`, **never the ledger**);
`tests/ledger/test_ledger.py:204` (`test_the_five_old_readers_agree_with_the_ledger`; its fixture
writes `{"window": [1, 2]}` over two clusters, so `total == in_window` by construction — the
defect's shelter); `ledger.py:271` `counts()` (the correct reducer, `in_window and not pre_seeded`).

- [ ] **Step 1 — RED.** A new case in `test_ledger.py`: the same two-cluster fixture with
      `init.json` `{"window": [1, 1]}` and cluster 1 finished. Assert `_stage().state is State.DONE`
      with "1 of 1" in its reason (today: PARTIAL, "1 of 2"); `completeness.build(...).totals
      ["clusters_total"] == 1` and `unprocessed_clusters == ()` (today: 2 and `(second,)`); and
      `ai-rfc verify --strict` on that workspace exits **0** (today 3 — a finished windowed
      reconstruction cannot pass, per the ruling's residual table). Add a pre-seeded variant
      (`harness.json` under cluster 2's checkpoint) asserting the same.
- [ ] **Step 2 — implement.** `_checkpoint` and both halves of `completeness.build` consume
      `ledger.counts(states)` (`total`, `done`) or `state.done`; `totals` stops reading
      `load_clusters` for its denominators. Rewrite the `state.py` docstring to state what is now
      true.
- [ ] **Step 3 — rename** `test_the_five_old_readers_agree_with_the_ledger` →
      `test_the_old_readers_agree_with_the_ledger` (#43); **the docstring's "six" is correct and
      stays.** Own commit.
- [ ] **Step 4 — the two owed checks (#51, #52)**, recorded in the ledger with the SHA: (a)
      `experiment/per_cluster.partial_reason` calls module-level `ledger.partial_reason`, safe only
      because `progress.py:57` pre-filters — still true? (b) `server/core/queries.py:126-130`
      derives `processed` from `state.done` (flag-aware) but `clusters_total` from `_clusters(ctx)`
      (window-blind) — a third semantics; what `test_ledger.py:254` actually pins is
      `composite["clusters_processed"] == summary["done"]`, not a `clusters_total` equality as the
      ticket's wording suggests (D-13). Still true? Neither is a defect today; if either changed,
      say so.
- [ ] **Step 5 — verify**: `pytest tests/ledger tests/substrate tests/cli tests/server -n 4`; the
      MARK-conditional test still passes where the sealed copy exists. **Check (#46–48):** Step 1
      green. **Check (#49):** the narrowed-window case exists. **Check (#50):** the docstring no
      longer says "the three agree". **Check (#43):** the rename.
- [ ] **Step 6 — commit**, two commits: `fix: read the ledger's own reducer where two callers
      recomputed a window-blind total`, `test: drop the dead numeral from the old-readers test name`.

---

## Task 6: Nothing claims a run directory — make the existing guard true

**Rows:** #32, #33, #34, #35, #36. **Ruling:** *Nothing claims a run directory* — `_write_once`
becomes an exclusive create (the record **is** the claim; no lock, no PID file); a second launch
refuses, naming the holder and the §5 move-aside remedy; a transcript is never truncated; the
campaign path gets the guard it never had (its ids are deterministic — `A1` — so its exposure is
higher); a stale claim releases through the existing `<id>.interrupted-<cause>/` move-aside;
**Important**, the only open finding that costs money when it fires (`mark-dry-49-51`: $28.51 against
an $8 cap).

**Sites (re-read):** `driver/record.py:178` `_write_once` (docstring promises "atomically, and
only if it is not already there"; `:193` is `if path.exists(): raise` — check-then-act; the
temporary-then-rename below it is the atomic half); `driver/spawn.py:79` `mode = "ab" if append
else "wb"`; `experiment/runner.py:86` (`RunRef(run_id, arm, repeat, campaign.runs_dir / run_id)` —
the campaign path mints deterministic ids and never calls `write_run_record`/`_write_once`: zero
hits).

- [ ] **Step 1 — RED (#32, #36): two writers.** A test that starts **two processes** (not threads;
      `subprocess` with the venv interpreter) racing to `write_run_record` the same `run_dir`, with a
      barrier so both pass the `exists()` check before either publishes. Exactly one succeeds; the
      other raises `DriverError` naming the holding record's path and the move-aside command. Today:
      both succeed, or the second overwrites.
- [ ] **Step 2 — RED (#34).** `spawn()` with `append=False` against an `events_path` that already
      holds bytes: refused (or appended — decide: the ruling says "never truncate"; refusing is the
      stricter reading and matches "the second launch refuses"). Today: truncated.
- [ ] **Step 3 — RED (#35).** Two `experiment run` launches of the same campaign run id: the second
      refuses **at its first `spawn`, before any process starts** (nothing spent); `events.jsonl`
      line count unchanged; the refusal names the transcript as the holder.
- [ ] **Step 4 — implement** per **R0.8**: write the temporary, `os.link(temporary, path)`, unlink
      the temporary; on `FileExistsError` raise `DriverError(f"{path} already exists — another run
      holds this directory; if it is dead, move it aside: mv <dir> <dir>.interrupted-<cause>")`.
      `spawn.py`: `"ab"` only when `append`, otherwise **`"xb"`** (exclusive), so an existing
      transcript is never destroyed. **The campaign path's claim is that exclusive transcript**
      (D-10): every caller passes `append=False` for a run's first session and `True` after —
      `sweep.py:1071 append=swept.sessions_run > 0`, `per_cluster.py:542 append=sessions > 0`,
      `runner.py:145`, and `per_cluster.py:270 append=True` for a consolidation appended to a
      finished run — so `"xb"` on the first session claims a campaign run directory with no new
      file. **Do not write the driver's `run.json` into a campaign run directory**: the campaign
      layout (`status.json` written once at the end, `events.jsonl`, `arfc.json`, `workspace/`) is
      what `audit_run`, `analyze_run` and the archived-run inventory describe, and a foreign record
      there is a shape change nothing asked for.
- [ ] **Step 5 — verify**: `pytest tests/driver tests/experiment -n 4`; the CLI-2 gate scenarios
      (`tests/driver/test_gate.py`) still complete and resume. **Check (#32):** `grep -rn "O_EXCL\|os.link\|open([^)]*\"x" ai_rfc/driver` → ≥ 1 hit; the two-writer test green.
      **Check (#33):** the refusal names both. **Check (#34):** Step 2 green. **Check (#35):** Step 3
      green. **Check (#36):** the test spawns two processes.
- [ ] **Step 6 — commit**, two commits: `fix(driver): claim a run directory with an exclusive
      create and never truncate a transcript`, `fix(experiment): claim the campaign run directory the
      same way` (**peer check first**).

---

## Task 7: The coverage detector — one predicate in `driver/`, two callers, keyed on the receipt

**Rows:** #6, #7, #8, #9, #10, #11, #12, #13. **Ruling:** *Fix shape for the self-certifying
checkpoint digest* + *What shape the transcript fallback takes* — a checkpoint is **covered** by a
`sessions.jsonl` row carrying its `cluster_id`, OR a `harness.json` pre-seed marker, OR a transcript
receipt (`note: checkpoint written to …/checkpoints/<cid>`) whose invoking `tool_use` is a
checkpoint-write call that passes `driver/enforcement.command_groups` (a compound command is never a
write). Uncovered means **unverified, never forged**. The detector **extends `ai-rfc verify`**; an
uncovered checkpoint is a finding, exit 3 under `--strict`. The predicate takes its candidate
transcripts from the caller; verify supplies `<workspace>/runs/*/events.jsonl`, the campaign audit
supplies the run's siblings across **both** experiments roots joining on the suffix
`runs/<R>/workspace/checkpoints/<cid>`. The route that covered each checkpoint is **recorded, not
ranked**, frozen to a JSON record after `write_gate_report`'s precedent. A missing or damaged
transcript covers nothing, names the damage, and is never itself a finding nor an error (strict
parse, caught, rendered "cannot adjudicate"). The two-era alias table (`mcp__arfc__arfc_checkpoint` /
`arfc checkpoint` → today's spellings) is ADR 0002's one bounded exception: dated, naming the
`testers/a_rfc → ai_rfc` rename as what closed era 1. **C-2 → Important once this ships.**

**Sites (re-read):** `experiment/metrics.py:172-215` (`_cluster_of_call`, `checkpoint_calls`: the
three-shape matcher — arm-gated, drops `use["id"]`, no shape check, pinned to today's spellings);
`driver/stream.py` (`parse_stream`, `salvage_stream`, `tool_uses`, `tool_results` keyed by
`tool_use_id`); `driver/enforcement.py:70` `command_groups`; `draft/checkpoint.py:99-103` (the
writer refuses an existing directory — why the receipt proves production); `draft/gate.py:505`
`write_gate_report`; `lifecycle/verify/cli.py:69-77` (the check loop), `:105-109` (any code not 0/3
→ exit 1 — the detector **must not** let a parse error escape); `lifecycle/workspace.py:117`
`Layout.runs` (no consumer anywhere today); `experiment/audit.py:409` `audit_run`, `:445`
`audit_campaign`, `:91` `bash_surface` (labels a compound line `bash:mixed` — the pattern to reuse);
`driver/record.py:433` (the one docstring stating "transcript carries no cluster id" — the precise
claim is no cluster **assignment**; **the audit's second site, `:108-109`, is a `#:` comment
making a different and correct claim** — "the row is the one place the two facts meet" — and is
left alone, D-11).

- [ ] **Step 1 — RED: the predicate.** `tests/driver/test_coverage.py` with fixtures cut from the
      archive's three shapes (read-only; copy the minimal `tool_use`/`tool_result` pairs into the
      fixture file, both eras): each shape yields `Route.receipt` for its cluster; a `--help` call
      (B1's real one) yields nothing; a compound `ai-rfc checkpoint c0002 ; echo 'note: checkpoint
      written to …'` yields nothing; a session row yields `Route.session`; `harness.json` yields
      `Route.pre_seed`; a truncated transcript yields `cannot adjudicate` with the damage named and
      **no exception**; two transcripts with the same `(cluster_id, sha)` count once.
- [ ] **Step 2 — RED: verify.** A workspace with three checkpoints — one session-covered, one
      pre-seeded, one hand-written with no row and no receipt — `ai-rfc verify` prints `coverage:
      findings`, one `finding: checkpoint <cid> is unverified: no session row, no pre-seed marker, no
      receipt` line, exit 3 under `--strict`, 0 otherwise; `out/coverage.json` records all three
      routes. A workspace with no `runs/` at all: `coverage: ok` with every checkpoint evaluated by the
      two remaining routes, and **no** line about the absent directory.
- [ ] **Step 3 — RED: the campaign audit.** A campaign fixture with a run whose receipt sits in a
      **sibling** run directory (the `A1.interrupted-*` shape): `audit_run` reports it covered by
      receipt, naming the sibling. Never resolve an absolute path from the receipt.
- [ ] **Step 4 — implement** `ai_rfc/driver/coverage.py`: `Route` (enum: `session`, `pre_seed`,
      `receipt`), `ALIASES` (dated), `checkpoint_calls(events)` (promoted, arm-free, carrying
      `use["id"]`), `receipts(events)`, `covers(checkpoints_dir, *, session_rows, transcripts)`.
      `experiment/metrics.checkpoint_calls` becomes a thin call into it (keeps its `arm` parameter
      only to filter, if any caller depends on it — measure). Verify adds the `coverage` check inside
      the existing loop shape, writing `out/coverage.json`. `audit_run` gains the sibling caller.
      Correct the two `record.py` docstrings (#13).
- [ ] **Step 5 — verify**: full 3.10 suite. **Check (#6):** Step 2 green. **Check (#7):**
      `experiment/metrics.py` no longer holds a second matcher. **Check (#8):** the alias table is
      dated and names the rename. **Check (#9):** the compound-command case in Step 1.
      **Check (#10, #11):** Steps 2 and 3. **Check (#12):** `out/coverage.json` exists and is
      byte-stable across two runs. **Check (#13):** `grep -n "carries no cluster id" ai_rfc/driver/record.py` → zero (one hit today, at `:433`).
      Record **C-2 → Important** in the deviation log and on the map.
- [ ] **Step 6 — commit**, three commits: `feat(driver): decide whether a checkpoint is covered by a
      session row, a pre-seed marker or a receipt`, `feat(verify): report an unverified checkpoint
      as a finding and freeze the route record`, `feat(experiment): cover a campaign's checkpoints
      from its sibling transcripts` (**peer check first** for the third).

---

## Task 8: The hardened `Parser` at every standalone door

**Row:** #18. **Ruling:** *A systematic remedy for the predicate-level gap* — one assertion in
`tests/substrate/test_cli_conventions.py`, which already parametrizes three checks over all 27
entry points and is tree-guarded by `test_every_cli_module_on_disk_is_registered`; today **zero of
27** standalone doors construct the hardened `Parser` (`ai_rfc/cli.py:27`, `error()` at `:67`).

- [ ] **Step 1 — RED.** `@pytest.mark.parametrize("entry", ENTRY_POINTS)` →
      `isinstance(import_module(entry.module).build_standalone_parser(), Parser)`. 27 failures.
- [ ] **Step 2 — implement** per **R0.7**: move `Parser` (and only it) to `ai_rfc/parser.py`;
      `ai_rfc/cli.py` imports it from there; each of the 27 `build_standalone_parser()` functions
      constructs `Parser(prog=…)` instead of `argparse.ArgumentParser(prog=…)`. `experiment/cli.py`
      is one of the 27 — **peer check first**, one-line change.
- [ ] **Step 3 — verify**: `pytest tests/substrate -n 4`; `test_a_malformed_invocation_exits_two_everywhere`
      still green; the `'unrecognized arguments: %s'` forgery CLI-2 recorded is now closed at every
      door (add one parametrized case: an argument carrying `\n` + `note: …` reaches stderr as one
      escaped line). **Check:** 27/27 green.
- [ ] **Step 4 — commit**: `fix: build every standalone door on the hardened parser, and assert it`.

---

## Task 9: Citations and stale lines

**Rows:** #44, #45, #59, #58. **Ruling:** *The nine spec-correction decisions* D-3 — the thirteen
`D16` citations are **correct** and gain their register's name (**never renumber to D63**, which
would repoint nine correct citations); the CLI-3 plan's survivor line is stale by five lines.

- [ ] **Step 1 (#44).** Qualify nine sites as `(CLI-3 D16)`: `README.md:137`, `docs/parity.md:46,61`,
      `docs/experiment-protocol.md:26`, `ai_rfc/server/README.md:33`, `ai_rfc/experiment/README.md:87`,
      `tests/server/test_parity.py:125,482,875`; four as `(CLI-1 D16)`: `ai_rfc/lifecycle/run/cli.py:245,262`,
      `tests/cli/test_run.py:219,443`. Re-grep first: **13 hits at `df7a87e`**, confirmed.
      **Check:** `grep -rn "D16" README.md docs ai_rfc tests` → 13 hits, every one qualified.
- [ ] **Step 2 (#45, PANTHER) — lands AFTER Task 7.** `docs/superpowers/plans/2026-09-12-arfc-one-door-cli3.md:1145`
      cites `metrics.py:182`; the audit said `:187`; at `df7a87e` the comment naming arm C's
      `ai_rfc draft checkpoint` is at **`:188`** (D-12) — and Task 7 promotes that very matcher out
      of `metrics.py`, so the comment moves a third time. Cite wherever it lands after Task 7
      (expected `ai_rfc/driver/coverage.py`), measured at commit time, never a number copied from
      a ticket.
- [ ] **Step 3 (#59, both).** `driver/stop.py`'s `_BOUND_SATISFIED` docstring cites spec D62; the
      spec's D62 parenthetical gains "(the source is `driver/stop.py`'s `_BOUND_SATISFIED`)" —
      **folded into Task 10's single spec diff**; only the code-side pointer lands here.
- [x] **Step 4 (#58, gitignored — D-15: the audit named the wrong report).** The `git log -S`
      paragraph lives in `<submodule>/.superpowers/sdd/2026-09-10-arfc-one-door-cli2/task-3-report.md`
      (`:104-117`, the claim at `:108`, never drifted), not in the CLI-1 report, which has none.
      Annotated in place with why the pickaxe was empty and that it must not be cited as precedent.
      No commit — the file is gitignored.
- [x] **Step 5 — commit**: ai_rfc `docs: name the register each D16 citation belongs to` (`ac69e95`); PANTHER
      `docs(ai_rfc): cite the arm-C comment where Task 7 moved it` (`d679296f9`; the message this
      step first named, "correct … to metrics.py:187", became false when Task 7 moved the comment
      to `ai_rfc/driver/coverage.py`, R11.8).

---

## Task 10: The spec diff — one commit in PANTHER

**Rows:** #37, #38, #39, #40, #53, #59 (spec half), #24 (spec half); #41 as the pre-commit check;
#54 **withdrawn (D-1)**. **Ruling:** *The nine spec-correction decisions* — land the proposal's
sections **1, 3, 4, 6, 7, 8** (`…/assets/ticket-12-spec-row-pass.md`), minus 2 (the wall clock
stays) and minus 9 (Task 9's job); section 5 is superseded by a broader §4 amendment. File:
`docs/superpowers/specs/2026-09-03-arfc-one-door-design.md` (231 lines, sha256
`e3e1ae5451600ca9ccf1ecc3081cd8096ba4aa20b7c63a470334357938dff474` at `df93513f6`).

- [ ] **Step 1 (#41).** `shasum -a 256` the spec; it must still be `e3e1ae54…dff474`. If not, diff
      against `df93513f6` and rebase every edit below on what changed. Repeat **immediately before
      the commit**.
- [ ] **Step 2 — the edits**, each quoted from the proposal, with these corrections:
      - §1 (`:44`, D57 d): the `AI_RFC_WORKSPACE` session-side contract sentence, as proposed.
      - §3 (`:49`, `:50`): `D62 (recorded 2026-09-14 — describes shipped behaviour)`, `D63 (recorded
        2026-09-15 — …)`; D62 additionally attributes `_BOUND_SATISFIED` (#59).
      - §4 (`:57`, **re-derived under D-1**): the twelve verbs as `experiment/cli.py`'s `add_parser`
        calls list them at commit time; drop "no ground-truth surface was built at all"; keep the
        sentence naming `optimize`, `profile`, `workspace` as arrivals the list did not anticipate.
        **D58 at `:45` is left as written** (#54 withdrawn).
      - §4 f (`:124-127`, superseding proposal section 5): the closing sentence states what
        replacement **requires** — "those callers read ledger rows *and honour `in_window` and
        `pre_seeded`*, through `ledger.counts()` or `ClusterState.done`" — and names
        `draft/completeness`'s claim-id sets as the one reader that keeps a second question (#53).
      - §6 (`:151`, `:190-191`, §7 d): the hard pre-spend toolchain refusal, as proposed.
      - §7 (`:199-205`, §8): de-numeral "five replaced readers" → "the replaced readers §4 names";
        "(37 done of 69, ordinal 38 outstanding, and no cluster half-finished)"; the fake-scenario
        mechanism by its real name; **plus** one sentence (#39): "the MARK assertion runs only where
        the sealed copy exists (`skipif` on its path), and is the suite's one machine-conditional
        verification."
      - §8 (`:213`, CLI-3 b, #40): the predicate wording, as proposed, **and** a dated deviation row
        appended to `docs/superpowers/plans/2026-09-12-arfc-one-door-cli3-deviations.md` naming
        `67052b9e0` (2026-09-14) as the commit where the predicate replaced the unreachable absolute
        — because changing a criterion is a different act from meeting it.
      - §3/§5 exit codes (#24): §3's "uniform" stands; §5's "stopped with work outstanding 1"
        gains "(one instance of 1, which means the command could not complete; 3 is the one code
        with a machine consumer, `driver/sweep.py:798` for `check`)".
      - Wall clock (#38): after Task 2, "reachable from `recon.yaml` through `sessions.deadline_s`"
        replaces the proposal's "has no `recon.yaml` surface today".
- [ ] **Step 3 — verify**: read the whole spec once end to end for a sentence the edits made false.
      **Check (#37–40, #53):** each edit present; the deviation row present; the digest re-checked.
- [ ] **Step 4 — commit** in PANTHER, one commit for the spec, one for the CLI-3 deviation row:
      `docs(ai_rfc): amend the one-door spec to describe what shipped, dated where retrospective`.

---

## Task 11: Promote the two ADRs

**Rows:** #1, #2. **Ruling:** ticket 1 (threat model) and ticket 9 (ADR 0002, "building the
mechanism is not enforcing it"); both drafts live only in the gitignored map at
`…/assets/adr-0001-threat-model-DRAFT.md` and `…/assets/adr-0002-enforce-what-you-build-DRAFT.md`.
`ai_rfc/docs/adr/` does not exist. **Each needs its own deliberate commit** (tracked directory,
shared worktree).

- [ ] **Step 1.** Create `docs/adr/0001-threat-model-for-the-agent-under-test.md` from the draft:
      drop the DRAFT banner, keep the 2026-09-15 amendment (production writability), add a `Status:
      accepted 2026-09-15, landed <date>` line.
- [ ] **Step 2.** Create `docs/adr/0002-building-the-mechanism-is-not-enforcing-it.md` from the
      draft (seven instances); **add this row's closures** to its instance table: the 27 doors (Task
      8), the Markdown module (Task 4), the composition sites (Task 4), the five joins (Task 3), the
      ledger reducer (Task 5), and the exclusive create (Task 6) — each with the commit that closed it.
- [ ] **Step 3.** `README.md` gains one line pointing at `docs/adr/`.
- [ ] **Check:** both files tracked; the map's drafts untouched. **Commit** twice:
      `docs: record the threat model for the agent under test as ADR 0001`, `docs: record "building
      the mechanism is not enforcing it" as ADR 0002`.

---

## Task 12: Whole-row review, fix wave, then the gate

- [ ] **Step 1 — whole-row review.** One reviewer over `BASE..HEAD` in ai_rfc and PANTHER,
      excluding any peer commits (list them from the ledger). One fix wave. Deferred minors go to
      the ledger with the SHA.
- [ ] **Step 2 — suites**, serial, sandbox off, pinned `-n 4`: 3.10 full (report collected /
      passed / failed / skipped); 3.11 optimize selection (expect 275/2/3 unless Task 7 touched
      `metrics.py` — then re-run is mandated by `sys.modules` after importing the targets, not by a
      grep); PANTHER door tests (expect 6).
- [ ] **Step 3 — Part A, the real draft build (#55), $0.** A **fresh** fixture workspace (never an
      archived one) built with `ai-rfc init` from a `recon.yaml` whose `toolchain:` names
      `~/ai-rfc-experiments/tools/toolchain.json` (already provisioned, `mode: native`; `make` needs
      the sandbox off — the `xcrun_db` error is the sandbox). `ai-rfc verify --strict` reports
      `build: ok`. Paste the tally line. Any other fixture in this row **declares a non-existent
      toolchain** or it silently picks up the operator's real one.
- [ ] **Step 4 — Part B, the minimal campaign (#56), ≤ $25 — STOP FOR APPROVAL.** Propose to the
      user, with the estimate: one cluster, one arm (A), `budget_usd` low (≈ $3; it binds softly per
      loop with ≈ $0.15 overshoot per session), target a re-prepared pristine
      (`~/ai-rfc-experiments/pristine/aioquic-w05-05`, both handles present), a **fresh** campaign
      directory under `~/ai-rfc-experiments/campaigns/`, `--python <worktree>/.venv/bin/python`.
      **Run exactly one loop, in the foreground, watching actual spend; never launch a second
      against the same run directory.** Pass = `exit_code 0` **and** a cluster done by the ledger's
      strict definition (record + `kind: cluster` revision + annotated tag) **and** an audit record.
      Record actual spend against the $25 ceiling and the SHA the run was made at. Reference
      actuals: guardcheck $0.33; `mark-dry A1` $28.51 against an $8 cap.
- [ ] **Step 5 — the row report** (~900 words): rows closed by number, per-task commits, deviations
      by number, the gate's commands and output verbatim with exit codes, every ruling with its cost
      if wrong, everything deferred verbatim. Record on the map: C-2 and C-3 → Important, with the
      commits.

---

## Task 13: Hand-over — asked once

- [ ] `git status -sb` both repositories; `git ls-tree HEAD panther/plugins/services/testers/ai_rfc`
      — if a peer bumped past BASE, bump only forward to the gate-tested SHA. Ask the user once:
      push ai_rfc `main`, bump the gitlink in one PANTHER commit, push PANTHER. **Submodule first.**
- [ ] Write the handoff memory; update MEMORY.md's CLI-3 line (57 → n owed).

---

## Verification (end-to-end, for the reviewer)

1. Every row #1–#59 has a line in the ledger: **landed `<sha>`**, **ledger entry** (R0.2), or
   **withdrawn (D-1)** for #54 / **moved** for #57. No row silently dropped.
2. Sentinel greps at HEAD: `signal.signal` → 1 hit (`cli.py`); `unusable input` → 0;
   `os.link\|"xb"` in `driver/` → ≥ 2; `from ai_rfc.markdown` → 3 consumers; `carries no cluster id`
   → 0; `D16` → 13, all qualified; `ai_rfc/docs/adr/` → 2 files; `Parser(` in 27 doors.
3. The three REDs that the rulings said could not exist before (two writers, SIGTERM stop, narrowed
   window) exist and are green.
4. Suites at the shape Task 0 recorded, plus this row's tests; 3.11 unchanged unless justified by
   `sys.modules`; PANTHER door 6.
5. The gate: Part A tally line; Part B's three conditions and actual spend, or the user's decision
   not to run it, pasted verbatim.

## Self-review

- **Coverage of the enumeration:** #1–2 Task 11; #3–5 Task 2; #6–13 Task 7; #14–17 Task 4; #18
  Task 8; #19–24 Task 1 (+ Task 10 for the spec half); #25–31 Task 3; #32–36 Task 6; #37–41 Task
  10; #42 Task 2; #43 Task 5; #44–45 Task 9; #46–52 Task 5; #53 Task 10; #54 withdrawn (D-1); #55–56
  Task 12; #57 closed by the map; #58–59 Task 9 (+ Task 10). **59 of 59 accounted for.**
- **Placeholders:** none. Every site carries a line number re-read at `df7a87e`, or says
  "re-locate" where the audit itself said the line had drifted.
- **What this plan deliberately does not do:** re-litigate any ruling; walk the 190-row deferred
  register (its disposition policy was executed by ticket 13 — rows above Minor became tickets and
  are in the enumeration); fix `agent/__init__.py:112`'s undetermined `except Exception` (the audit
  ruled it needs a live run); touch any file the peers hold.

---

## Outcome — executed 2026-09-21/22

Every task above ran subagent-driven with a reviewer between tasks and a whole-row review before
the gate; the deviation log carries D-1 … D-19 and the row outcome with every commit, the suite
figures and the gate evidence. All 59 enumerated rows are closed (55 landed, 2 measurements, 1
withdrawn, 1 closed by the map) plus #61 and #62 (its prompt half owed as #62b). Both review
Criticals downgraded to Important. Part A and Part B of the gate passed; Part B spent $1.40 of
the $25 ceiling. ai_rfc `main` `3406985..8581e8b`; PANTHER docs commits listed in the outcome.
Checkboxes above are left as the contract; execution is recorded in the log, not by ticking.
