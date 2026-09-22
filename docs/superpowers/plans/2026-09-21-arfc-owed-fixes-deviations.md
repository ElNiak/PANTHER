# Owed-fixes row — deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-21-arfc-owed-fixes.md`. Three fields
each: what the plan (or the map) said, what the code or the tool showed, what I did.

**Entry 0 — the rulings carried in (R0.1–R0.10) and the four planning-phase deviations (D-1 … D-4)
live in the plan file itself**, under "Entry 0 — rulings carried into the row", so the two cannot
drift. This log continues from **D-5**, one entry per `review-plan` finding fixed before Task 1 and
then one per task as tasks run.

**Numbering.** This row's findings are `D-n` with a hyphen. The design spec's decisions the plan
quotes (`D57`, `D58`, `D59`, `D62`, `D63`) are written without one. The map's tickets are cited by
their file name under `.superpowers/sdd/2026-09-15-arfc-post-review-rulings/issues/`.

**State at the opening (2026-09-21 ~07:50 CEST).** PANTHER `c21a60500` on
`feat/arfc-pipeline-and-runtime-anchors`, 0/0 against origin; ai_rfc `df7a87e` on `main`, 0/0,
gitlink matching. Uncommitted in the submodule and **not this row's**: the GEPA winner
(`ai_rfc/driver/prompts/loop.tmpl.md` and four `plugins/ai-rfc/skills/*/SKILL.md`), held by the
peer session `post-sp7d-cleanup-gepa`. Untracked in PANTHER and not this row's: two executor
prompts under `docs/superpowers/plans/`.

**Baseline at the opening — RED for an environmental reason (D-2).** 3.10 full suite, `-n 4`,
sandbox off: **37 failed, 2313 passed, 12 skipped, 23 errors** in 284 s. Every failure and error
chains to `git … exited 69: You have not agreed to the Xcode license agreements`. The shell's `git`
is `/opt/homebrew/bin/git` (2.55.0); the suite's subprocesses reach `/usr/bin/git`, the Xcode shim,
because `fake_claude` and the driver scrub `PATH`. Confirmed by running two of the non-git-looking
failures alone with `--tb=short`: both surface the license text. SP7d measured 2372 passed on this
tree on 2026-09-18, so nothing in the code moved. **Task 0 waits on `sudo xcodebuild -license
accept`**, which only the user can run.

---

# Pre-execution findings (D-5 onward, from `review-plan`)

_(appended as the review returns them)_

---

# Execution-phase deviations

_(one per task, added as tasks run)_

## D-5 … D-13 — the `review-plan` pass (2026-09-21, one invocation, spent)

Verdict: **needs minor fixes** — 1 Critical, 7 Warning (D-5, D-7 … D-12), 1 Info (D-13), 7 verified clean. All fixed in the plan
before Task 1.

| # | Sev | The plan said | The tree showed (at `df7a87e`) | What I did |
|---|---|---|---|---|
| **D-5** | W | Row #24's "module docstring claiming distinguishability" is `driver/stop.py:27`. | `grep -rn "unusable input" ai_rfc README.md docs` → only `README.md:138` and `ai_rfc/server/README.md:58`. No module docstring carries the phrase; the nearest is `ai_rfc/cli.py:157`, "0/1/3 per the package table", which points at the README taxonomy. | Task 1 names `cli.py:157` and drops the guess. |
| **D-6** | **C** | Task 2 Step 3: catch `KeyboardInterrupt` in `lifecycle/run/cli.py` and "let the sweep's `_finish` write the stop". | `sweep.py:1355` docstring: `KeyboardInterrupt: Straight through. An interrupted run writes no …`; `_finish` is `sweep.py:1240`, reachable only inside the sweep. A CLI-level clause can never produce `status.json`; Step 1's RED could never go green. | The catch moves inside `sweep.run` around the session loop; the docstring is rewritten; `run`/`next` gain no clause. |
| **D-7** | W | Install the SIGTERM handler in `main()`. | `main()` is called in-process by the parity tests and by `panther ai-rfc`; a handler left in a pytest-xdist worker changes its shutdown. | Install only when the disposition is `SIG_DFL`; restore in `finally`. |
| **D-8** | W | Row #30 has one site, `server/paths.py:297`. | `lifecycle/init/cli.py:58` (`Layout(dest or config.workspace)`) and `lifecycle/doctor/cli.py:181` also take `config.workspace` raw. | Task 3 records the two siblings and offers anchoring once in the loader as a ruling, minimum the ruled site. |
| **D-9** | W | Task 0 pre-excuses `tests/experiment/test_fake_claude.py` as the known load flake. | SP7d recorded "1 failed, load flake, passes alone" without a test name. | The plan pre-excuses nothing; ≤ 1 failed and verified passing alone. |
| **D-10** | W | Task 6: the campaign path "calls `write_run_record`" at launch. | `runner.py` never calls `spawn` or opens a transcript itself; `driver/session.py:422` passes `append=spec.append`, and every caller sets `append=False` for a run's first session (`sweep.py:1071`, `per_cluster.py:542`, `runner.py:145`; `per_cluster.py:270` is `True` for a consolidation appended to a finished run). A driver `run.json` in a campaign run directory is a layout change `audit_run`/`analyze_run` never asked for. | The campaign path's claim is the exclusive `"xb"` open of its first transcript; no `run.json` there. RED #35 asserts the refusal at the first spawn. |
| **D-11** | W | Row #13 corrects two docstrings, `record.py:108` and `:433`. | Only `:433` says "transcript carries no cluster id"; `:108-109` is a `#:` comment making a different, correct claim ("the row is the one place the two facts meet"). | Task 7 corrects `:433` only. |
| **D-12** | W | Row #45: `metrics.py:182` → `:187`. | The comment naming `ai_rfc draft checkpoint` is at `:188` today, and Task 7 moves the matcher out of `metrics.py`. | #45 lands after Task 7, citing the measured final location. |
| **D-13** | I | Row #52: the third semantics "pinned by `test_ledger.py:254`, an equality on `clusters_total`". | `:254` asserts `composite["clusters_processed"] == summary["done"]`; `queries.py:126-130` derives `processed` from `state.done` and `clusters_total` from `_clusters(ctx)`. | Task 5's ledger check reworded to what the test pins. |

**Verified clean, no change:** 27 `argparse.ArgumentParser(` files = 27 `EntryPoint(`, every one
with `build_standalone_parser` (Task 8); the spec is byte-identical at sha256 `e3e1ae54…dff474`,
231 lines, and `:44`, `:45`, `:57`, `:124-127`, `:213` hold the content Task 10 edits;
`~/ai-rfc-experiments/tools/toolchain.json` exists and both `aioquic-w05-05` and `w06-06` carry
`recon.yaml` + `init.json` (Task 12); `server/core/gates.py:84` is `record_dir = out / cluster_id`
with `:98` guarding `base` (Task 3 #28); `_checked_cluster_id` at `driver/stop.py:438` and
`experiment/per_cluster.py:153` (Task 3); `driver/sweep.py:798` is the one exit-3 consumer (Task 1
#24); `driver/stream.py` exports `parse_stream`, `salvage_stream`, `tool_uses`, `tool_results`
(Task 7); `draft/checkpoint.py:99-103` refuses an existing directory (Task 7); the 13 `D16` sites
(Task 9); `experiment/markdown.py` has exactly two consumers and no test imports it (Task 4).

## D-14 — Task 1: a discharge check that could not see the site it existed for

**The plan said** row #24's check is `grep -rn "unusable input" ai_rfc README.md docs` → zero, and
named `README.md:138-139`, `ai_rfc/server/README.md:58` and `ai_rfc/cli.py:157` as the sites.

**The tool showed** (reviewer, `task-1-review.md`) the grep went to zero while the package's actual
exit-code **table** at `ai_rfc/README.md:161-170` still said 3 means "findings … and `--strict` was
given" and "every command holds to that table", and `README.md:166,221` plus `docs/parity.md:78,80`
still narrowed 1 — all paraphrases ("Inputs unusable", "unreadable input") the phrase grep cannot
match. The same review found `ai_rfc/pipeline/cli.py:288,:380` propagating a stage's 2 raw: the
defect family of row #23 at a door the plan did not name.

**What I did** — ruled both into a Task 1 fix wave (ledger T1-R1 … T1-R4): the table and the four
lines land as the docs half of #24; the pipeline door refuses 2 like `run` does, RED first; the
check for #24 becomes *"`ai_rfc/README.md`'s exit-code table states the four ruled meanings, and no
line in `README.md`, `ai_rfc/server/README.md` or `docs/parity.md` gives 1 a narrower one"* — a
statement about the taxonomy, not about one phrase. **The lesson is the row's own:** a check
written as the phrase someone remembered is an enumeration; the predicate is the table.

## D-15 — Task 9: the audit's row #58 named the wrong report, and read its own miss as drift

**The plan said** (Task 9 Step 4, copied from the enumeration's row #58) annotate
`.superpowers/sdd/2026-09-03-arfc-one-door-cli1/task-3-report.md`, whose cited `:106-109` "has
drifted".

**The tool showed** the CLI-1 report contains no `git log -S` paragraph anywhere (`grep -n "git
log"` → five hits, none with `-S`). The register row the audit was built from (DR-041,
`deferred-register.md:97`) names the row as **CLI-2**, sources it at CLI-2's `progress.md:265`, and
quotes `e24e6e8`/`launch_pending` content that appears only in
`<submodule>/.superpowers/sdd/2026-09-10-arfc-one-door-cli2/task-3-report.md:104-117`. There the
`git log --oneline -S"def execute"` claim still sits at `:108` — inside the originally cited range.
The audit looked in the wrong directory and interpreted the miss as line drift.

**What I did** — the annotation landed in the CLI-2 report (`:111-118`, gitignored, no commit),
recording why the pickaxe was empty (`-S` does not follow renames; the pre-move path was
`experiment/`) so the next reader cannot repeat the mistake; this plan's Task 9 Step 4 is corrected
to the CLI-2 path; the enumeration asset is left as written (it testifies to the audit) with this
entry as its correction. **Two lessons:** a "drifted" verdict needs the file re-read, not the line
number re-checked; and an audit row's source column is the thing to follow, not its path column.

## D-16 — Task 4: the brief named one finding string; the composition site was the boundary

**The plan said** (Task 4, from Task 3's deferral) escape "the `run_gate` finding" that
interpolates a bare agent-controlled `cluster_id`, and fix the stderr composition sites named by
row #16 (five `diagnostics(f"error: {error}")` calls and `forge/cli.py:173`).

**The tool showed** `run_gate` composes fifteen finding strings, several interpolating
agent-written values (`entry.cluster_id` at `:339` and `:370/:382`, `claim.id`,
`entry.checkpoint`, a checkpoint's load error), and the implementer's own updated test recorded
that the sibling at `:339` still forges. The real asymmetry sits one level up: the CLI arm routes
every finding through `lifecycle/common.report`, which escapes at the boundary by design
("a boundary rather than a rule each caller remembers"), while the tool arm composes
`f"finding: {finding}"` unescaped at `server/core/gates.py:234` and `server/core/build.py:66,154`.

**What I did** — ruled T4-R1: escape at the tool arm's three `finding:` compositions (the
predicate over every finding, matching the CLI arm's boundary), revert the two per-id edits inside
`run_gate` (an enumeration), and pin all three stderr elements escaped. The brief's "ONE finding
string" was the enumeration the row keeps warning about; the implementer honoured it, which is
correct behaviour for an implementer and a defect in the brief.

## D-17 — Task 4: there are no SP7d goldens under `tests/experiment/`; C-3 downgrades

**The plan said** (Task 4 Step 6) "the SP7d goldens under `tests/experiment/` byte-identical".

**The tool showed** no golden files exist there; the repository's only file-golden test is
`tests/substrate/draft/test_structures.py::test_each_kind_matches_its_golden`, untouched by the
task. The implementer established renderer byte-identity two other ways — the exact-string
assertions in `tests/experiment/test_report.py` and `test_quality.py`, and a direct sha256 of
`render_report` over the fixtures plus a hostile variant, identical before and after the move
(`c0a5b006…`, 5364 bytes) — and said so rather than claiming the check the plan named.

**What I did** — the check is restated as the two measurements above. **Severity movement, as the
plan's Step 6 requires:** with `ai_rfc/report.py` escaped at `2c768b5`, review finding **C-3
downgrades Critical → Important** (the sink triage's decision 6). The whole-branch review's own
report is not edited; the movement is recorded here and on the map. **C-2 is unchanged** until
Task 7 ships the coverage detector.

## D-18 — Task 7: the map's join instruction contradicted its own evidence; C-2 downgrades

**The plan said** (Task 7, quoting `issues/20-fallback-shape.md`) join the receipt on the suffix
`runs/<R>/workspace/checkpoints/<cid>`, and search sibling run directories across both experiments
roots.

**The tool showed** receipts name the **pre-rename** path — the same ticket says so at its `:180` —
because `record.move_aside` renames a run *after* its receipts were written: every receipt in
`mark-dry-49-51`'s `A1.interrupted-detached` and `A1.interrupted-shell-exit` transcripts names
`runs/A1/workspace/checkpoints/c0049-…` (read by the implementer and, independently, the reviewer).
A join carrying `<R>` would report the holder's own checkpoint unverified — the false-tampering
reading the ticket was raised to prevent. And a campaign lives in one root with its runs beneath
it, so "both roots" is satisfied by the suffix join working in whichever root the campaign is in;
no archived campaign spans both.

**What I did** — accepted the implementer's R2 (join on the `checkpoints/<id>` tail) and R11
(candidates are `campaign.runs_dir`'s own children, no second root literal) as corrections of an
instruction, not departures from the ruling — the ruling's *decisions* (receipt-keyed, call-shape
gated, caller-supplied candidates, nothing written, route recorded not ranked) all stand. Cost if
wrong: a cross-campaign receipt for the same cluster id would cover — bounded because the caller
supplies siblings, not the world.

**Severity movement, as the plan's Task 7 Step 5 requires:** with the coverage detector landed
(`439af29`, `49666a8`, `f3e3c94`), review finding **C-2 downgrades Critical → Important** (the
digest ruling's decision 6). The whole-branch review's report is not edited. Both Criticals are
now Important; nothing on the review is Critical.

## D-19 — Task 12: a campaign copy's `ai-rfc status` reports the pristine

**The plan said** (Task 12 Step 4) pass = exit 0 **and** a cluster done by the ledger's strict
definition **and** an audit record.

**The tool showed** the run passed all three — but `ai-rfc status --config <run>/workspace/recon.yaml`
printed "0 of 1 done, mining pending": the lifecycle verbs resolve the workspace from
`config.workspace`, which in a campaign copy still names the pristine (the hazard spec D57 records),
while the server resolves from the config file's own directory (`server/paths.resolve_context`).
Task 12's commit F anchored only *relative* values, so an absolute `workspace:` naming another
directory is still followed. The ledger, read directly on the run's workspace, gave the truth
(`done True`, `counts {in_window 1, done 1}`), and that is what the gate was judged on.

**What I did** — judged the gate on the ledger, not the verb; recorded the gap as **owed #63 for
the next row**: the lifecycle verbs adopt the server's rule (the config file's directory when it is
a sealed layout), with a campaign-copy test.

---

# Row outcome — 2026-09-22

**Every enumerated row is closed.** 59 rows: 55 landed, #17 and #41 discharged as measurements,
#54 withdrawn (D-1), #57 closed by the map; plus the two user-approved additions #61 and #62 (M's
prompt half stays owed as #62b). Both review Criticals are Important (D-17, D-18). The CLI-3 gate's
"a campaign runs end to end" is met for the first time.

**Commits.** ai_rfc `main` `3406985..8581e8b`, 52 commits, 50 this row's (the other two are peers'
`3406985` GEPA winner and `8358238` ARM-B fix, riding along by their owners' decision): Task 1
`8214c24 d791e9e 0a966ed d4430ab`; Task 2 `5b45d09 af12f64`; Task 3 `e16bff2 571355c c5e4a6c
fecd60f ebd392b`; Task 5 `d1e34c3 90700fa 68674cb`; Task 9 `ac69e95 aa90620 13e3272`; Task 4
`9c61fab 2c768b5 f714135 19a8b84`; Task 6 `ece0a87 3535fe8 5cbf6de`; Task 7 `439af29 6074fe7
49666a8 f3e3c94 eff7e91 a850bd6 7f0d1a2 382b72f 9f39e81`; Task 8 `de77863`; Task 11 `112835d
469f82f`; Task 12 wave `e741326 efabce3 824680a a77b6bc 6929ebc d67be71 fa295f8 9f0475b e4d492e
f535d21 b947711 04b4248`, second wave `08ea289 0e0062f`, docs `8581e8b`. PANTHER
`feat/arfc-pipeline-and-runtime-anchors`: `d4e5c8290` (plan), `d679296f9` (#45), `644a4bfc7`
(spec), `fdc87baea` (CLI-3 D29), `4ee8caecc` (spec Replaces), plus the closing docs commit and the
gitlink bump.

**Gate (Task 12).** Suites at `0e0062f`/`8581e8b`: ai_rfc 3.10 full **2670 collected / 2658
passed / 0 failed / 12 skipped** (twice in the wave, once in review); 3.11 optimize **275 / 2
skipped / 3 deselected**; PANTHER door **6 passed**; `mypy ai_rfc` 5 errors in 5 files (the
baseline); `black` clean over 317 files. Part A (#55, $0): a fresh fixture at
`/tmp/claude-501/owed-gate/` from the aioquic clone at pin `6d36838d…`, `ai-rfc init`, then
`ai-rfc verify --strict` with the provisioned toolchain: `build: ok` (`note: build of b51bb9d6cfe6
exited 0`, targets `txt html lint idnits`, idnits 1 warning), `coverage: ok`, rc 3 from lint's
skeleton-stub finding on an unrun workspace. Part B (#56, approved ≤ $25): campaign
`~/ai-rfc-experiments/campaigns/owed-gate-20260922` (arm A, one run, `budget_usd` 3.0, window
`[5, 5]`, pristine `aioquic-w05-05`, parity 26 passed at init), one loop launched once at 14:37:09
CEST, finished 14:40:06: **exit 0, timed_out false, budget_hit false, cost $1.3981**; the ledger on
the run's workspace: `c0005-epoch-79f631193bdf` `checkpoint True`, `revision_tag …-00`,
`tag_exists True`, **`done True`**; `audit/A1.json` `integrity true`, `bypass_attempts 0`, `errors
class1 2 / class2 0`, and the Task 7 detector's first live result — `c0005` **`route: receipt`,
`source: A1`**; `analyze` → completed 1/1, artifacts 1.000, pass^k ✓, 35 turns, $1.40.

**Deviations** D-1 … D-19 above; the two API-limit cut-offs (Task 3, Task 4) left no durable
damage because each resumed from the tree and its report.

**Deferred to the next row** (verbatim from the ledger): C-4/C-5 — five expressions of "this run's
work" in `experiment/` (`metrics.py:348,361-366`, `progress.py:51-57`, `analyze_campaign`'s
`window_ids`) and the pre-seed-inflated `window_size` denominator behind `artifacts_fraction`,
`completed_fraction` and `pass_k` (Important; changes campaign figures); #62b the `{{corpus_query}}`
prompt half (re-freezes every campaign); #63 the lifecycle verbs' workspace resolution on a
campaign copy; I's pure preconditions above `claim()` in `launch()`; T12-V2's dead anchor at
`server/paths.py:~304`; T4V-2's `_report` docstrings; `spawn.py:97-108`'s citation; D-T4-6;
`Layout.runs` without a consumer; the campaign audit's `coverage` block unread by `analyze`; #60
(peer-owned, R91/R92); the five pre-existing mypy errors; the pre-existing isort/flake8 items.
