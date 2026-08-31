# Phase C Unblock Implementation Plan

> **CORRECTION 2026-08-31 — the status banner below is stale; read this first.**
> The banner is preserved as what this plan concluded on 2026-08-27. It no longer
> describes the tree.
>
> - **`go` is now true.** The `PreToolUse` hook the banner calls "does not exist and
>   is not planned" was built (`experiment/guard.py`, `experiment/enforcement.py`).
>   `~/arfc-experiments/spike-report.json` records `go: true` on CLI **2.1.250**, with
>   the required `denial` check passing; only the non-required `plugin_mcp` check fails.
> - **Tasks 5–7 are done**, not blocked: `audit.py`, `metrics.py`, `report.py` and the
>   campaign CLI all exist, and the harness suite is green.
> - **The denial fixture was refreshed** from a real 2.1.247 guard denial (`2939c5e`),
>   closing the "deliberate no-op" the banner records.
> - **The pilot was launched on 2026-08-28 and aborted on its first run** (arm B,
>   repeat 1) by a guard defect since fixed in `17ba3a1` and `HEAD`.
> - Still open from the banner: no full-suite baseline was ever captured at Task 0, so
>   its "20 failures are pre-existing" remains asserted rather than proven.

> **STATUS 2026-08-27 — executed, and partly overtaken by what it found.**
> Tasks 0–4 are **done**. Task 5 is **blocked and cannot pass as written**.
>
> - Spike S0 ran. `go` is **false**, for one reason that has nothing to do with authentication or the isolated profile: **`--allowedTools` does not constrain a built-in tool that `--tools` has enabled** on CLI 2.1.247, so arms B and C are capability-identical. **The `--bare` + `ANTHROPIC_API_KEY` fallback in Task 4's interpretation table is NOT indicated** — D20 is supported, not refuted.
> - Decision taken with the user: enforce the arm boundary with a **`PreToolUse` hook**. That component does not exist and is not planned. It needs a spec amendment plus its own plan before Task 5's gate can pass.
> - Two of the three spike failures were broken instruments, fixed in `0f5707c`; the `USER` environment defect that blocked the first run is fixed in `b7e592d` / `002113689`.
> - Task 3 resolved as a deliberate no-op: the denial fixture encodes a Bash denial that cannot occur on 2.1.247, so it is left until the enforcement hook can produce a real one.
> - Task 4 Step 4 is **incomplete**: the three targeted suites are green (207 / 38 / 46), but the full `-n auto` unit run deadlocked at ~99% after 1350 passed / 20 failed, and no full-suite baseline was captured at Task 0 to compare against. The 20 failures are the pre-existing set; nothing in `a_rfc`/`ai_rfc` fails.
>
> Full verdict and evidence: `ai_rfc/docs/spike-s0.md`. Read that before this document.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (inline execution with checkpoints was chosen by the user). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cross the three gates that stand between the landed Phase C foundations and the harness plan's Task 0 — run spike S0 for the go/no-go verdict, build the real aioquic pristine workspace, bump the submodule — and correct the project memory that still claims none of the foundations were implemented.

**Architecture:** No new modules. Every capability this plan exercises is already committed in the nested `ai_rfc` repo (`experiment/spike.py`, `experiment/workspace.py`, their CLI subcommands); what is missing is that nobody has ever *run* them against the real profile and the real corpus. This plan is therefore a runbook with gates, not a construction plan: four of its five tasks execute committed code and record what it produced, and the one code-touching task (a test-fixture refresh) is conditional on what the spike captures. The runner/matrix/audit/metrics/report half stays where it already lives, in `docs/superpowers/plans/2026-08-26-arfc-phase-c-harness.md`, and is not re-planned here.

**Tech Stack:** Python ≥3.10, stdlib + PyYAML; pytest; git; Claude Code CLI 2.1.246 (spike only, never in tests).

**Spec:** `docs/superpowers/specs/2026-08-26-arfc-phase-c-experiment-harness-design.md` §2 (D20, spike S0) and §3 (D27, pristine workspaces). Completes `docs/superpowers/plans/2026-08-26-arfc-phase-c-foundations.md` (its Task 5 Steps 8–9 and its Task 10), which `docs/superpowers/plans/2026-08-27-arfc-phase-c-workspace.md` already completed through Task 9.

## Global Constraints

- Paths (every command below assumes these shell variables):
  - `W=/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc` (PANTHER worktree root; run PANTHER commands from here)
  - `R=$W/panther/plugins/services/testers/a_rfc/ai_rfc` (the nested `ai_rfc` git repo — its own history, commits styled `feat: …`/`test: …`/`docs: …`/`fix: …` with no scope)
  - `S=$R/plugins/ai-rfc/server` (the MCP server + `arfc` CLI package)
  - `PY=/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.venv/bin/python`
  - `M=/Users/elniak/.claude/projects/-Users-elniak-Documents-Documents-Work-Project-Protocol-Testing-Security-PANTHER-master/memory`
- **NEVER run `panther_builder.py package-dev`/`clean` in this tree** — it `rm -rf`s `docs/`, which holds every spec and plan this work depends on.
- Pytest needs the `SSLKEYLOGFILE=` prefix (the env var trips the sandbox at aiohttp import).
- Writes into a nested `.git` (commits inside `$R`) and anything under `~/arfc-experiments` need the sandbox disabled (`dangerouslyDisableSandbox: true`). So does every `claude` launch in Task 2.
- Two repos, two commit targets: PANTHER commits use `chore(a_rfc): …`/`docs(a_rfc): …`; nested-repo commits use `git -C $R add <explicit paths> && git -C $R commit -m "…"`. Never `git add -A` or `git add .`. The submodule pointer is bumped exactly once, in Task 4.
- `docs/` is gitignored in PANTHER: doc commits there need `git add -f`. `docs/` is **not** gitignored in the nested repo.
- **Never push either repo.** PANTHER's `feat/arfc-progressive-rfc` has no upstream and the nested repo is 13 commits ahead of `origin/main`; both stay that way unless the user asks.
- The environment contract everywhere: `PANTHER_REPO=$W`, `ARFC_WORKSPACE=<one workspace>`, runs root `~/arfc-experiments` (always outside the PANTHER tree).
- Suite gates, and the authority for their expected counts: PANTHER `a_rfc` **207** and server **38** and experiment **46**, per foundations plan Task 10 Step 4 as amended by `8877222ba`. A deviation is reconciled before proceeding, never assumed to be breakage.

---

### Task 0: Baseline

Nothing below is safe to interpret without knowing the tree matches what this plan was written against. Every expected value here was read off the repository while writing the plan; none of the suites were re-run, so this task is where they are proven rather than assumed.

**Files:**
- Create (PANTHER): `docs/superpowers/plans/2026-08-27-arfc-phase-c-unblock.md` (this plan)

- [ ] **Step 1: Save and commit this plan**

`docs/` is gitignored in PANTHER, so the add needs `-f`.

```bash
cd $W && git add -f docs/superpowers/plans/2026-08-27-arfc-phase-c-unblock.md
git commit -m "docs(a_rfc): Phase C unblock implementation plan"
```

- [ ] **Step 2: Confirm both repositories are where the plan expects**

Run: `cd $R && git log --oneline -1 && git status --short && cd $W && git status --short && git log --oneline -1`
Expected: nested HEAD is `9e20d2d feat: prepare pristine workspaces behind a workspace prepare command` with a clean tree; PANTHER shows exactly one line, ` M panther/plugins/services/testers/a_rfc/ai_rfc` (the deliberately deferred pointer), with HEAD at `23183e939`.
Anything else: STOP and report. Uncommitted work in either repo is somebody else's, and this plan does not stage it.

- [ ] **Step 3: Confirm the three suites**

Run: `cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc -n auto -q 2>&1 | tail -1; cd $S && SSLKEYLOGFILE= $PY -m pytest -q 2>&1 | tail -1; cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q 2>&1 | tail -1`
Expected: `207 passed`, `38 passed`, `46 passed`.
A lower experiment count means the tree is behind `9e20d2d`; a higher one means uncommitted tests. Either way: STOP and reconcile.

- [ ] **Step 4: Confirm the three gates really are uncrossed**

Run: `ls -a ~/arfc-experiments/profile/; ls ~/arfc-experiments/spike-report.json ~/arfc-experiments/pristine 2>&1; ls $R/docs/`
Expected: the profile directory holds `README-arfc.txt` and nothing else (no credential file); both `ls` targets report *No such file or directory*; `$R/docs/` lists `experiment-protocol.md` and `parity.md` only (no `spike-s0.md`).
If any of these already exist, someone ran part of this work: STOP, read what is there, and re-plan around it rather than overwriting it — `prepare` refuses a pristine directory that exists, by design.

---

### Task 1: Correct the stale project memory

`MEMORY.md` and `handoff-2026-08-26-arfc-phase-c-plans.md` both assert Phase C is "PLANNED, not executed". Thirteen nested-repo commits (`37987d6`..`9e20d2d`) contradict that. This task runs before the blocking wait in Task 2 because it depends on nothing but what Task 0 just proved, and because if the session ends waiting on the login, the stale memory is what costs the next session the most.

Per `feedback_late_findings_to_handoff_not_audit`, a signed memo is not retro-edited. The 2026-08-26 handoff gets a one-line superseded pointer only; the new facts go in a new handoff.

**Files:**
- Create: `$M/handoff-2026-08-27-arfc-phase-c-foundations-landed.md`
- Modify: `$M/MEMORY.md` (the Active Work bullet), `$M/handoff-2026-08-26-arfc-phase-c-plans.md` (one pointer line)

**Interfaces:**
- Produces: the handoff slug `handoff-2026-08-27-arfc-phase-c-foundations-landed`, referenced from `MEMORY.md` and linked as `[[…]]` from the 2026-08-26 handoff.

- [ ] **Step 1: Write the new handoff**

Frontmatter `name`/`description`/`metadata.type: project` per the memory contract. Body records: foundations Tasks 1–9 and workspace-plan Tasks 1–5 landed as `37987d6`..`9e20d2d`; the workspace plan `8e09af7be` executed in full; the experiment suite at 46; the three gates still uncrossed (spike run, aioquic pristine, harness plan 0/9); both repos unpushed with the submodule pointer parked at `51bdcb9`; and the two Task-4 landmines (`forge_snapshot=None` in every test, unverified `TEMPLATE_COMMIT`). Link `[[handoff-2026-08-26-arfc-phase-c-plans]]` and `[[handoff-2026-08-25-arfc-progressive-rfc]]`.

- [ ] **Step 2: Mark the 2026-08-26 handoff superseded**

Append one line under its `## Next` section, editing nothing else:

```markdown
> **Superseded on 2026-08-27.** "Next" below was executed: foundations Tasks 1–9 and the whole workspace plan landed as `37987d6`..`9e20d2d`. See [[handoff-2026-08-27-arfc-phase-c-foundations-landed]].
```

- [ ] **Step 3: Repoint the MEMORY.md index line**

Replace the "Phase C experiment harness — PLANNED, not executed" bullet with one pointing at the new handoff, naming what landed and what remains. Index lines carry a hook, never content.

- [ ] **Step 4: Verify**

Run: `grep -rn "PLANNED, not executed\|nothing implemented" $M/MEMORY.md $M/handoff-2026-08-26-arfc-phase-c-plans.md`
Expected: no hit outside the superseded-pointer line. Memory files are not under git; there is nothing to commit.

---

### Task 2: Authenticate the isolated profile and run spike S0

Foundations Task 5 Steps 1–7 are committed (`a8a8be2`, then `1570375` which made the verdicts require their positive controls). Steps 8 and 9 — the manual run and the verdict record — have never been performed, and `report["go"]` is the go/no-go for the entire experimental design.

**Note on the source plan's stale gate.** Foundations Task 5 Step 7 expects `20 passed (3 profile + 6 arms + 6 stream + 5 spike)`. That was the count while Task 5 was the current task; Tasks 6–9 have since raised it. **46 is authoritative.** This is the same class of false-alarm halt that workspace-plan Task 5 existed to fix for the harness plan, so it is called out here rather than discovered mid-run.

**Files:**
- Create (nested repo): `$R/docs/spike-s0.md`
- Create (outside both repos): `~/arfc-experiments/spike-report.json`, `~/arfc-experiments/spike/*.jsonl`
- Modify (nested repo, only on the `plugin_mcp` branch below): `$R/plugins/ai-rfc/.mcp.json`

**Interfaces:**
- Consumes: `experiment.spike.run_spike(root, panther_repo, plugin_dir, claude_bin, model, timeout_s)` and the `spike` subcommand already registered at `experiment/cli.py:42`.
- Produces: `~/arfc-experiments/spike-report.json` with `go: bool` and a `checks` list — read by the harness plan's Task 0 gate and by its runner, which learns from it whether arm A's enforcement degrades to allowlist-only.

- [ ] **Step 1: The one-time login (the user runs this; it is interactive)**

The profile directory already exists, so `profile init` is not needed. Ask the user to run, in this session:

```
! CLAUDE_CONFIG_DIR=/Users/elniak/arfc-experiments/profile claude auth login
```

Nothing below proceeds until it returns. An interactive session must never be pointed at that profile — it exists precisely so the experiment sees no user settings, plugins or hooks.

- [ ] **Step 2: Confirm the profile gained credentials**

Run: `ls -a ~/arfc-experiments/profile/`
Expected: more than `README-arfc.txt` — a credential file now sits beside it. If nothing changed, the login did not complete: STOP and report rather than running the spike, whose `auth` invocation would burn thirteen launches on a guaranteed failure.

- [ ] **Step 3: Run the spike (sandbox OFF)**

It spawns `claude` thirteen times at roughly a $1 cap each; expect 5–10 minutes.

```bash
cd $R && $PY -m experiment spike --root ~/arfc-experiments --panther-repo $W
```

Expected: a `PASS`/`FAIL` line per check, `PASS` on every required one, exit code 0, `report: /Users/elniak/arfc-experiments/spike-report.json`, and per-call transcripts under `~/arfc-experiments/spike/*.jsonl`. Exit code 2 means `go` is false.

- [ ] **Step 4: Interpret the report against the table foundations Task 5 Step 8 already fixed**

Read `~/arfc-experiments/spike-report.json`. The verdicts and what each one means:

| Failing check | Meaning | Action |
|---|---|---|
| `auth`, `hooks`, `claude_md` | The isolated profile is not hermetic | **NO-GO.** Stop. Put the `--bare` + `ANTHROPIC_API_KEY` fallback (spec §2) to the user via AskUserQuestion. Nothing below runs. |
| `denial` with `leaked: true` | The allowlist did not hold | **NO-GO.** Stop and report; arm enforcement is the experiment's validity condition. |
| `arm_surface`, because `Bash` still appears in arm A's `tools` | `--tools` does not remove built-ins | Not a no-go. Record it: enforcement in arm A degrades to allowlist-only, and the harness runner reads that from this report. |
| `plugin_mcp` with `env_connected: false` while arm A shows `arfc: connected` | `${PANTHER_REPO}` does not expand in the plugin's `.mcp.json` | Delete the whole `"env": {…}` block from `$R/plugins/ai-rfc/.mcp.json`, re-run that one check by hand (the exact command is in foundations Task 5 Step 8, expecting `2`), and commit separately as `fix: let the arfc MCP server inherit its environment`. |
| `result_fields` missing `permission_denials` | Denials are readable from tool results only | Record it; the audit stage in the harness plan depends on knowing this. |

**Checkpoint.** Report the full check table and the verdict before writing anything. A no-go changes the shape of the remaining work and is the user's decision, not this plan's.

- [ ] **Step 5: Record the verdict**

Write `$R/docs/spike-s0.md`: date, `claude --version`, model, a table of check → PASS/FAIL → one-line evidence, the decisions taken (whether the `.mcp.json` env block was kept or dropped, the enforcement mode per arm, the denial source), and the exact commands run.

- [ ] **Step 6: Commit**

Foundations Task 5 Step 9 lists the spike's code files in its commit command, but those already landed in `a8a8be2`, so this is a documentation-only commit.

```bash
git -C $R add docs/spike-s0.md
git -C $R commit -m "docs: spike S0 verdict"
```

---

### Task 3: Refresh the denial fixture from the real transcript (conditional)

Foundations Task 5 Step 8 item 4 permits replacing the committed fixture with the captured transcript. That is a live capture rewriting a committed test fixture *and* the assertions that check it, so it is a task with its own reviewer gate rather than a sub-bullet of the spike. **If the captured denial parses cleanly against the existing fixture's assertions, this task is a no-op — skip to Task 4.**

**Files:**
- Modify: `$R/experiment/tests/fixtures/stream/denied-bash.jsonl`, `$R/experiment/tests/test_stream.py`

- [ ] **Step 1: Compare the real transcript to the fixture**

Run: `diff <($PY -c "import json,sys;[print(json.dumps(json.loads(l),sort_keys=True)) for l in open('$HOME/arfc-experiments/spike/denial.jsonl')]") <($PY -c "import json,sys;[print(json.dumps(json.loads(l),sort_keys=True)) for l in open('$R/experiment/tests/fixtures/stream/denied-bash.jsonl')]")`
Expected: either no structural difference (skip this task), or a diff whose shape tells you whether the stream readers can parse the real event.

- [ ] **Step 2: Decide which side is wrong**

If the readers in `experiment/stream.py` cannot parse the real shape, **fix the readers, not the fixture** — the fixture is a stand-in for reality, and reality just spoke. Only if the readers parse it fine does the fixture get refreshed.

- [ ] **Step 3: Checkpoint before touching anything**

Show the user the fixture diff and every assertion that would change (token totals and event indices are the fixture-specific ones). Proceed only on an explicit yes. The semantics of each assertion must survive; only the captured values move.

- [ ] **Step 4: Refresh, then prove the suite still holds**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q 2>&1 | tail -1`
Expected: `46 passed`. A different count means an assertion was deleted rather than adjusted.

- [ ] **Step 5: Commit**

```bash
git -C $R add experiment/tests/fixtures/stream/denied-bash.jsonl experiment/tests/test_stream.py
git -C $R commit -m "test: refresh the denial fixture from the real transcript"
```

---

### Task 4: The real aioquic pristine workspace and the submodule bump

Foundations Task 10, unchanged in substance. This is the first time `prepare` runs against a real target.

> **First run of an untested branch.** Every test behind `prepare` uses a target with `forge_snapshot=None`, so the forge copy at `workspace.py:355-358` and the `--forge` argument passed to the views CLI at `workspace.py:376-377` have never executed. aioquic is the first target that exercises them. A failure around the snapshot copy or view emission is most likely the first run of that branch, not a regression. Separately, `TEMPLATE_COMMIT = "dcdd985a86afad97a50f7b5e1b613f57c194b774"` (`workspace.py:30`) is unverified; a wrong value surfaces here as a clone failure in `scaffold_draft`, not as silent drift.

**Files:**
- Create (outside both repos): `~/arfc-experiments/pristine/aioquic-w02-11/`
- Modify (PANTHER): the `ai_rfc` submodule pointer

**Interfaces:**
- Consumes: `experiment.workspace.prepare(target, root, panther_repo, template, template_commit)` via the `workspace prepare` subcommand at `experiment/cli.py:58-68`; the `AIOQUIC` target whose `source` resolves to `$W/reconstructions/aioquic` and whose `forge_snapshot` is `forge/github.com__aiortc__aioquic/snapshot-2026-08-25T15-16-59Z` beneath it. All four required parts (`clone`, `corpus`, `timeline`, and that snapshot) were confirmed present while writing this plan.
- Produces: `~/arfc-experiments/pristine/aioquic-w02-11/` with `pristine.sha256` and `pristine.json` — the digest file is half of the harness plan's Task 0 gate.

- [ ] **Step 1: Prepare (sandbox OFF: clones `github.com/ElNiak/auto-i-d-template` and writes under `~`)**

```bash
cd $R && $PY -m experiment workspace prepare aioquic --root ~/arfc-experiments --panther-repo $W
```

Expected, over 5–15 minutes (view emission plus a full re-verification pass over 342 clusters): `pristine: /Users/elniak/arfc-experiments/pristine/aioquic-w02-11` and `clusters: 342  pre-seeded: 332  window: [2, 11]`.

- [ ] **Step 2: Sanity-check the pristine tree**

Run: `P=~/arfc-experiments/pristine/aioquic-w02-11; ls $P/clusters | wc -l; ls $P/checkpoints | wc -l; ls $P/checkpoints/c0001-epoch-a80c3bdd1e02; git -C $P/draft log --oneline; git -C $P/clone rev-parse HEAD; cd $S/src && PANTHER_REPO=$W ARFC_WORKSPACE=$P $PY -m ai_rfc_server.cli cluster-next | head -5 && PANTHER_REPO=$W ARFC_WORKSPACE=$P $PY -m ai_rfc_server.cli status | grep -E '"clusters_(total|processed)"|next_cluster'`
Expected: `342`; `332`; `checkpoint.json harness.json manifest.yaml`; one scaffold commit; `6d36838d008c2202c337142fa07e8bf80e96bac8`; `cluster-next` printing `"id": "c0002-pr-60258445de47"`; status showing `clusters_total: 342`, `clusters_processed: 332`, `next_cluster: "c0002-pr-60258445de47"`.

The middle three numbers are the ones that matter: 342 clusters proves the forge-informed timeline copied intact, 332 checkpoints proves pre-seeding left exactly the ten-cluster window unprocessed, and `c0002` proves the window starts where the design says it does.

- [ ] **Step 3: Bump the submodule pointer (PANTHER)**

```bash
cd $W && git -C $R log --oneline -1
git add panther/plugins/services/testers/a_rfc/ai_rfc
git commit -m "chore(a_rfc): bump ai_rfc submodule to the Phase C foundations commit"
git submodule status panther/plugins/services/testers/a_rfc/ai_rfc
```

Expected: the status line shows the nested repo's HEAD with no `+` or `-` prefix. Stage the submodule path explicitly and nothing else.

- [ ] **Step 4: Full verification**

Run: `cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc -n auto -q 2>&1 | tail -1; cd $S && SSLKEYLOGFILE= $PY -m pytest -q 2>&1 | tail -1; cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q 2>&1 | tail -1; cd $W && SSLKEYLOGFILE= $PY -m pytest tests/ -n auto -m unit -q 2>&1 | tail -1`
Expected: `207 passed`; `38 passed`; `46 passed`; the full unit suite at its Task-0 baseline. The 19 failures and 4 errors outside `a_rfc` (webapp observer, docker templates, panther_ivy collection) are pre-existing — report them, do not touch them.

- [ ] **Step 5: Report**

Both repos' SHAs, the spike verdict from `docs/spike-s0.md`, the contents of `pristine.json`, and anything deferred. Do not push.

---

### Task 5: Open the harness plan

**Files:** none — this task only proves the handover is clean.

- [ ] **Step 1: Run the harness plan's own Task 0 gate, verbatim**

Run: `cd $R && git log --oneline -1 && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q 2>&1 | tail -1 && ls ~/arfc-experiments/pristine/aioquic-w02-11/pristine.sha256 && python3 -c "import json;r=json.load(open('$HOME/arfc-experiments/spike-report.json'));print('go' if r['go'] else 'NO-GO')"`
Expected: the foundations commits through `feat: prepare pristine workspaces behind a workspace prepare command`, `46 passed`, the digest file listed, `go`.

This is the single check that all three blocked gates were genuinely crossed. If it passes, `docs/superpowers/plans/2026-08-26-arfc-phase-c-harness.md` opens at its Task 1 and this plan is complete. Its Tasks 1–7 are entirely offline — that plan forbids a real `claude` in tests — and its Task 8, the six-run pilot, is a confirmation point requiring an explicit yes before the first launch.

---

## Corrections to the foundations plan

Two defects were found by reading foundations Task 5 against the tree. Neither is fixed in that document by this plan; both are handled inline above.

1. **Task 5 Step 7's expected count is stale.** It reads `20 passed (3 profile + 6 arms + 6 stream + 5 spike)`, computed when Task 5 was current. Tasks 6–9 raised the suite to 46. Task 2 above states the authoritative number so its executor does not halt on a false alarm.
2. **Task 5 Step 9's commit command is already spent.** It stages `experiment/stream.py`, `experiment/spike.py`, `experiment/cli.py`, two test modules, the fixture and `docs/spike-s0.md` in one commit, but everything except `docs/spike-s0.md` landed in `a8a8be2`. Task 2 Step 6 above commits the documentation alone, and Task 3 commits the fixture separately if it changes at all.

## Self-review

**Spec coverage.** §2/D20 (isolated profile, hermeticity spike, `--bare` fallback) → Task 2. §3/D27 (the real pristine workspace, window pre-seeding, digest) → Task 4. The memory correction is not a spec requirement; it is a standing obligation from `~/.claude/rules/memory-best-practices.md`, and it is Task 1. Deliberately not in this plan: everything in the harness plan (runner, matrix, audit, metrics, report, pilot), which Task 5 hands over to intact.

**Placeholder scan.** No TBD or TODO. Every command is spelled out with its expected output, including the one command the user must run. The only conditional task, Task 3, states its skip condition in its first sentence.

**Type consistency.** `prepare`'s parameters, `Target.forge_snapshot`, `HARNESS_MARKER`/`DIGEST_FILE`/`RECORD_FILE` and `report["go"]` are spelled here exactly as they are defined in `experiment/workspace.py` and `experiment/spike.py`, and exactly as the harness plan's Global Constraints list them among the interfaces it consumes. The pristine directory name `aioquic-w02-11` is derived, not typed: it comes from `Target.pristine_name` given `window=(2, 11)`.

**Known judgement calls.** Task 1 runs before the blocking login rather than after the work it describes, because it depends only on what Task 0 proves and it is the piece most likely to be lost if the session ends waiting. Task 3 is a task rather than a step because it mutates a committed fixture from a live capture. Task 5 writes no files; it exists so the handover has an explicit gate instead of an assumption.

**Accepted risk.** A no-go from Task 2 does not waste Tasks 0 and 1, but it does force the `--bare` + API-key fallback and changes the runner's launch environment in harness Task 3. Running the spike before the harness rather than after is the whole reason this plan is ordered as it is.

## Execution handoff

Inline execution with checkpoints, per the user's choice — **REQUIRED SUB-SKILL: superpowers:executing-plans**. Task boundaries are the checkpoints, plus two explicit in-task stops: the spike verdict in Task 2 Step 4, and the fixture diff in Task 3 Step 3.
