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
