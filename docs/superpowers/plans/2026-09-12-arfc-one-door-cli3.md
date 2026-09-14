# CLI-3 "one core" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the two front doors into one — `ai_rfc/server/core/` calls the substrate
in-process instead of shelling out, the twenty parity verbs become grouped subcommands of the
`ai-rfc` root, and the `ai_rfc` console script, its `prog=` value, its parser module and the campaign
`bin/ai_rfc` shim retire.

**Architecture:** Each substrate verb's report-writing moves next to the API function that produces
the values it serialises, so `draft/cli.py` and `server/core/` become two front ends over one
implementation instead of one shelling out to the other. The parity verbs mount as D56's eleven
groups — ten new packages under `ai_rfc/agent/`, plus the existing `draft` — each group calling the
same `server.core` functions `tools.py` calls. The seven explicit-path leaf verbs are **hidden from
the operator's help, not deleted**: arm C types them through the root door.

**Tech Stack:** Python 3.10 (`.venv/bin/python`), argparse, pytest, PyYAML. A second interpreter
(Python 3.11, `~/ai-rfc-experiments/venv-optimize/bin/python`) is the only one that imports gepa and
the only way to run the optimize selection.

**Spec:** `docs/superpowers/specs/2026-09-03-arfc-one-door-design.md` — **§6 "One core (CLI-3)"** is
the work; D56, D57, D60's CLI-3 row and D61 bind it. Preceding rows:
`docs/superpowers/plans/2026-09-10-arfc-one-door-cli2{,-deviations}.md`.

---

## Global Constraints

- **Line length 88** (Black). `black`, `isort --profile black`, `flake8 --max-line-length=88`,
  `mypy --follow-imports=silent` — **on the task's own files only**; the repository carries lint debt
  elsewhere.
- **Google-style docstrings** (Args/Returns/Raises) on every public function.
- `from __future__ import annotations` where neighbouring modules use it (every module touched here
  does).
- **No backward-compatibility shims.** No re-export stubs, no dual-spelling acceptance. CLI-2's
  ruling R2 continues to govern.
- **Fixed dates in every fixture.** No `datetime.now()` in a test.
- **No test needle that matches a fixture's own name.**
- **RED tests fail at the exact path the change addresses.** A RED that passes against unfixed code
  is a stop. **And a RED must be able to go GREEN after the fix** — the review of this plan found
  three that could not (D3, D6, D9).
- Where a finding is "correct behaviour with no test", a RED is impossible by construction:
  **mutation-test instead** — write the mutant down, show the new test kills it, prove the revert.
- **Interpreters.** `.venv/bin/python` (3.10) for everything that does not import gepa;
  `~/ai-rfc-experiments/venv-optimize/bin/python` (3.11) only for the optimize selection. **Never a
  pyenv shim** — its site-packages has no editable `.pth`, so subprocess tests die on
  `ModuleNotFoundError: No module named 'ai_rfc'` and look like real failures.
- Prefix every `pytest` and `python -m` with `SSLKEYLOGFILE=`; set `TMPDIR` outside the tree
  (`.gitignore` carries `.pytest_cache/` but **not** `pytest-of-*`).
- Run pytest, pip, nested git and pushes with the **sandbox off**.
- Commits: `type: lowercase summary` in ai_rfc, `type(scope): lowercase summary` in PANTHER, each
  ending with a blank line and `Claude-Session: <session URL>` as a second `-m`.
- **Never** `git add -A`/`git add .`, `--no-verify`, `git stash` in this shared worktree, an amend of
  a commit already on the branch, or a backwards submodule pointer.
- The **twenty** parity verbs. Not sixteen.

---

## Entry 0 — rulings carried into the row

Recorded in `docs/superpowers/plans/2026-09-12-arfc-one-door-cli3-deviations.md` before Task 1 runs.

### The user's rulings (2026-09-12)

**U1 — §6's "`checkpoint` regains 3" is restated as "stops collapsing".** There is no 3 to regain:
`draft/cli.py:240-262` returns only 0 and 1; checkpoint has no findings and no `--strict`.
`server/cli.py:339` is `return 0 if result["exit_code"] == 0 else 1` while its neighbours
(`gate:342`, `citation-gate:346`) return `result["exit_code"]` raw — and `server/cli.py:4-5`'s own
docstring already promises "gate exit codes pass through untouched (0 clean, 1 unusable inputs, 2 a
usage error from argparse itself, 3 strict findings)". §6's parenthetical and §Context's twelfth
friction are both restated. *Cost if wrong:* a spec sentence changes; the code change is one line.

**U2 — CLI-2's owed spec amendments land this row.** A new D-row fixes reason, exit code and resume
verb for `StopReason.bound_reached` and `action_performed`; §5's exit-code sentence becomes "done or
bound reached 0; stopped with work outstanding 1; strict findings 3". Closes CLI-2's D22.

**U3 — the parity `status` verb gets no `ai-rfc` verb; the MCP tool stays.** `ai-rfc status` keeps
its one meaning (the operator's ledger). `docs/parity.md`'s CLI cell for that row becomes
`— (MCP only)`, the shape `draft-render`'s arm-C cell already uses. *Cost if wrong:* arm B loses a
one-line composite — an arm-surface change, flagged in `experiment-protocol.md`.

**U4 — pre-authorised cut line: `--panther-repo` (Task 10).** It is the only scope that is not an R8
obligation (R8 is satisfied: **zero** production reads of `PANTHER_REPO`), it has no dependents
inside the row, and every §6/D56 obligation survives the cut.

### Rulings I make

**R1 — the core calls the API functions, and the report writers move beside them.** Not
`main(argv)` in-process. *Discriminator, measured:* the only reader of `out/gate-report.json` and
`out/lint-report.json` outside `draft/cli.py` is `server/core/` itself (`gates.py:177`,
`build.py:96`); `out/completeness.json` has **no reader in `ai_rfc/` at all**; and
`out/build/build-report.json` is written by the **API** (`draft/build.py:434`), not the CLI branch,
and read by a genuine substrate reader (`pipeline/state.py:283`). For the two artifacts the core
reads, the CLI branch is not shared infrastructure — it is the only other caller.

This also removes two hazards the `main(argv)` shape would create: the leaf CLIs `print()` to
**stdout**, which on the MCP path is the JSON-RPC wire (today the subprocess absorbs it), and
argparse raises `SystemExit` inside the handler. With the API shape nothing prints and nothing exits,
so no `redirect_stdout`/`redirect_stderr` — no global `sys.std*` mutation — is needed.
*Cost if wrong:* a reader of those artifacts outside `ai_rfc/` still finds them; the writers move,
they are not deleted.

**R2 — the core synthesises the `stderr` key from values, not captured output.** In-process the core
builds the same lines from the same values (`f"finding: {f}"`, `f"error: {e}"`, `f"note: …"`),
preserving byte content. Task 3's characterisation tests pin today's lines first. *Cost if wrong:*
an MCP consumer reading `stderr` sees different bytes — and `core/draft.py:116,143` folds those
lines into `tag_revision`'s own payload, so the blast radius is wider than the five sites (D9).

**R3 — the leaf verbs are hidden, not deleted. Forced, not preferred.** `render.py`'s arm-C table
types `python -m ai_rfc check` (`:137`, `:146`) and `python -m ai_rfc draft checkpoint|gate`
(`:151`, `:169`) — through the **root door**, not `python -m ai_rfc.<sub>`. Deleting the rows breaks
arm C. Mechanism: `hidden: bool = False` on `EntryPoint` (safe — all 17 constructions pass five
positional args and the field is appended last); `_epilog()` filters it; sections stay declared.
**Six verbs are hidden, not seven** — see D10.

**R4 — the `draft` collision is resolved by merging, in one change, with a function-local import.**
The two argv shapes arm C types must parse **byte-for-byte unchanged**. Measured: arm C types **no
other** `draft` sub-verb, so the three that overlap the agent forms (`build`, `lint`, `render`) are
free to change shape — their positionals and required flags become **optional**, defaulting from the
resolved context. `draft commit` joins with no clash; `draft checkpoint`, `gate` and `completeness`
keep their leaf shapes exactly. The context resolution is a **function-local import** (D13).

**R5 — the brief's claim that `check` collides is refuted; `status` collides instead.** D56's group
list is `claim, cluster, corpus, question, answer, revision, checkpoint, gate, citation-gate, draft,
structure` — no `check`. The leaf `check` verb collides with nothing and hides under R3. `status` is
the real collision, settled by U3.

**R6 — the arm-B door spelling gets one production source.** `arms.py:54` is the single source
`enforcement.bash_prefixes()` derives the guard prefix from; `audit.py:66` and `metrics.py:165` are
second and third copies. Task 9 derives both from `bash_prefixes(arm_profile("B"))` rather than
renaming three literals, so the drift class dies.

**R7 — the recorded audit key `bash:ai_rfc` does NOT change.** `audit.py:52-54` records that the
`family` field is written into `audit/<run_id>.json`; renaming it makes every existing audit record
unreadable. Only the matchers move; a comment beside the key says why.

**R8 — `AI_RFC_WORKSPACE` stops being the server's contract but keeps being exported.** Arm B and C's
rendered prompts reference `$AI_RFC_WORKSPACE` at ~20 sites (`render.py:98-192`), and
`driver/session.py:252`, `driver/arms.py:149` and `experiment/preflight.py:110` set it. Task 1
changes what `server/paths.py` **reads**, not what the driver **exports**.

**R9 — the workspace is derived from the config file's own directory, never from its `workspace:`
field.** `lifecycle/common.load_pair:129-132` already documents why: "a campaign pristine is sealed
with its own root written into `workspace:`, so reading the layout back out of the seal would send
every verb to the tree the pristine was copied from." A campaign run is a **copy**. This is the row's
largest silent-failure surface: getting it wrong operates on the wrong workspace and looks like
success — the exact failure `server/paths.py:4-6` says it exists to prevent.

**R10 — `pipeline/run.py` is not converged, deliberately.** Its five builders (`:118, 126, 142, 163,
177`) construct the same argv, and `:188-190` says so. But it is a different layer: the **operator's**
stages over explicit paths, where the core drives the **agent's** over a resolved context, and §6 asks
only that the core stop shelling out. Its three measured divergences go in the log: `_checkpoint` has
no `--consolidation`/`--base`, `_build` has no `--ref`, `_lint` has `--strict` but not `--worktree`.

**R11 — `ai_rfc/server/cli.py` is deleted in Task 8, not merely re-`prog`ged.** Leaving a second
parser tree carrying the old hyphenated verb names, reachable only from tests, *is* the
backward-compatibility layer this codebase forbids. Its four importers (`experiment/config.py:56`'s
`_SHIM`, and `tests/server/{test_cli,test_revisions,test_parity}.py`) all move in the same task: the
shim to `ai_rfc.cli:main`, the twins to the grouped verbs, `tests/server/test_cli.py` to
`tests/agent/`. *Cost if wrong:* Task 8 grows by the twenty twin re-pointings. If the row overruns
after U4's cut, the fallback is `prog="ai-rfc"` with the module kept and the debt logged.

### Measured corrections to the brief

**M1 — the captured transcript needs NO regeneration.** `tests/driver/fixtures/enforcement/run-b1-arm-b.json`
holds **zero** `ai_rfc <verb>` strings — it is recorded in the pre-rename `arfc` spelling, carries its
own `families` key (`:3`), and `test_enforcement_corpus.py:38-40` reads the prefix from the document.
Its docstring (`:8-13`) states the governing principle: *"a recording that is edited to match a later
rename is no longer evidence of anything"*, and `:141-152` says the agreement property is
spelling-independent. **The precedent is set; CLI-3 follows it.** Same for `docs/experiments/*.json`.

**M2 — "both `prog="ai_rfc"` values" is one.** Only `server/cli.py:39`.

**M3 — R8's `PANTHER_REPO` retirement is already done.** Task 10 retires the lowercase
`panther_repo`, the campaign's **provenance** field — a scope decision, not an R8 obligation.

**M4 — the brief names two door-spelling classifiers; there are three.** `metrics.py:165` is the
third. `metrics.py:171-174` already accepts both the module and dispatcher forms for arm C.

**M5 — `docs/parity.md`'s verb column is unguarded.** `tests/server/test_parity.py:85-88` asserts
only that each **MCP tool name** appears. Task 11 adds the guard.

**M6 — `--panther-repo` reaches the 3.11 track.** `optimize/evaluator.py:114,139,453`,
`optimize/fixtures.py:188,203`. The 3.11 re-run after Task 10 is not optional.

**M7 — both venvs carry a stale `bin/ai_rfc`,** plus a stale `ai_rfc.egg-info/entry_points.txt`
listing both. Retiring the entry point needs `pip install -e` in each interpreter.

### Baselines measured at Phase 1 (2026-09-12) — all three reproduce the brief's figures

| Selection | Result |
|---|---|
| ai_rfc suite, 3.10 (`pytest tests -q -n auto -p no:cacheprovider`) | **1859 passed, 11 skipped** (218.34 s) |
| PANTHER door tests (`tests/unit/test_cli/test_ai_rfc_commands.py`, sandbox **off**) | **6 passed** (27.02 s) |
| 3.11 optimize (`tests/experiment/optimize tests/experiment/test_cli_optimize.py -m "not slow"`) | **222 passed, 2 skipped, 2 deselected** (324.65 s) |

The 3.11 figure was taken only after `import ai_rfc` succeeded from a cwd outside the package and the
`python -v -c pass | grep -c Skipping` probe printed `0`. Both trees clean before and after.

---

## D1–D17 — review findings, fixed in this plan before Task 1

One `review-plan` invocation against the live tree returned **9 Critical and 5 Warning** (D1–D14); a
following adversarial read found **three more** (D15–D17), one of them an internal contradiction
between Task 5 and U3. Every one is fixed below and recorded here. Five of the seventeen are REDs
that would have passed against unfixed code or could never have gone green afterwards — the failure
class this plan's own Global Constraints name.

**D1 — Task 1 breaks every `tests/server` module; the plan named one test file.** `tests/server/conftest.py:15-16`'s
`use()` sets **only** `AI_RFC_WORKSPACE`, and `ai_rfc/server/testing.py:42 build_workspace` writes
**no `recon.yaml` and no `init.json`**. The moment `resolve_context()` requires `AI_RFC_CONFIG`, every
test using `workspace`/`make_workspace` dies at fixture setup — eight modules under `tests/server/`,
and fourteen modules repo-wide set `AI_RFC_WORKSPACE`. *Fixed:* Task 1 gains `tests/server/conftest.py`
and `ai_rfc/server/testing.py` in its Files, and a Step 0 that enumerates the fourteen.

**D2 — the toolchain rule made `AI_RFC_TOOLCHAIN` dead and `ctx.toolchain` never `None`.**
`config.py:642` is `toolchain = values["toolchain"] or root / "tools" / "toolchain.json"` — a loaded
config **never** carries none. So "fall back to `AI_RFC_TOOLCHAIN` when the config carries none" is
unreachable, and `core/draft.py:120`'s `if ctx.toolchain is not None:` becomes always true, forcing a
build on every tag. This is CLI-2's D23 defect exactly — the same `config.py:642` default. *Fixed:*
the rule keys on `is_file()`, and Task 1 gains a RED pinning `resolve_context().toolchain is None`
when the defaulted path does not exist.

**D3 — Task 3's RED could never go green.** `monkeypatch.setattr("ai_rfc.server.core.gates.subprocess.run", …)`
resolves today because `gates.py:12` imports `subprocess`; after Step 3 deletes that import the same
line raises `AttributeError` forever. *Fixed:* patch `"subprocess.run"` globally, plus a structural
pin that `gates` has neither `_run` nor `subprocess`.

**D4 — Task 4's test never reached the monkeypatched function.** `server/cli.py:254-259` resolves the
context **before** dispatch and returns 1 on `EnvError`, so the assertion was green only for
`code == 1`. *Fixed:* the test takes the `workspace` fixture.

**D5 — Task 4's mutation ceremony was redundant.** The plan claimed "a RED is impossible by
construction", but the parametrised test *is* a valid RED: `code` 2 and 3 collapse to 1 today.
*Fixed:* Steps 1 and 3 deleted; the table test is the RED.

**D6 — Task 5's twin count was arithmetically unreachable.** Only **eight** function names end in
`_parity`; `test_read_parity_adjudicate:75` does not, and `test_consolidation_checkpoint_and_revision_parity:181`
covers two verbs in one function. 8 + 10 = 18, never 20. *Fixed:* an explicit frozen
`TWINS: dict[str, str]` mapping tool name to test name, asserted equal to `ALL_TOOLS`.

**D7 — Task 6 created eleven files where the conventions suite requires thirty-one.**
`tests/substrate/test_cli_conventions.py` runs four per-entry invariants over `ENTRY_POINTS`:
`:47-58` imports `<package>.__main__` unconditionally; `:22-30` requires `main(["--version"])` to
`SystemExit(0)` printing `entry.prog` and `__version__`; `:205-212` requires `usage: {entry.prog}` in
stdout. And `pyproject.toml:34-35` uses `find`, not `find_namespace`, so every group directory needs
an `__init__.py`. *Fixed:* the File Structure is 10 × (`__init__.py`, `__main__.py`, `cli.py`) plus
`agent/__init__.py` = **31 files**, and Task 6 gains Step 3b for the `--version`/`prog` contract.

**D8 — Task 7 broke two tests the plan never named.** `tests/substrate/test_root_cli.py:30`
(`assert rendered == [entry.verb for entry in ENTRY_POINTS]`) and `tests/cli/test_root.py:26-28`
(counts each verb once in the help) both go red for the hidden verbs. And `tests/cli/test_help_sections.py`,
named in Task 7's Files, **does not exist**. *Fixed:* both real files added to Task 7; each iterates
`[e for e in ENTRY_POINTS if not e.hidden]` and gains a companion assertion that hidden verbs are
absent; the non-existent file is dropped.

**D9 — Task 3 missed `_run`'s import site, its sixth consumer, and three monkeypatch seams.**
`build.py:14` is `from .gates import _run`. `core/draft.py:71 tag_revision` reaches three shell-out
sites — `manifest_gate(ctx, strict=True)` at `:111`, `draft_build(ctx, "HEAD")` at `:121`,
`citation_gate(ctx, strict=True)` at `:133` — and folds their output into its own contract
(`"findings": manifest["stderr"]` at `:116`, `"findings": citation["findings"] or citation["stderr"]`
at `:143`), so R2's stderr re-synthesis changes `tag_revision`'s payload directly. Three tests
monkeypatch `_run` itself and lose their seam: `tests/server/test_build.py:59,111,147` (stderr pinned
at `:67`, `:116`, `:149`) and `tests/server/test_draft.py:115`. *Fixed:* both test modules added to
Task 3's Files, `tag_revision` added to the characterisation set, and a Step 3b replaces the
`_fake_run` seam with API-level fakes.

**D10 — `draft` must NOT be hidden; six verbs are, not seven.** The brief says seven leaf rows leave
the help, but `draft` is the row R4 merges the agent group into, and D56 lists `draft` as an agent
group whose verbs Task 9 renders into arm B's prompt. Hiding it would remove `ai-rfc draft render`
and `ai-rfc draft lint` from the operator's help. *Fixed:* `HIDDEN = ["check", "coverage", "history",
"forge", "timeline", "views"]`. Logged as a deviation from the brief's "seven".

**D11 — `server/cli.py` has four importers and cannot simply be deleted mid-row.** `experiment/config.py:56`
(`_SHIM`), `tests/server/{test_cli,test_revisions,test_parity}.py`, plus `_parser()` at `:253` and
`docs/parity.md:9`. *Fixed:* R11 moves all four in Task 8, in one commit, and names the fallback.

**D12 — Task 10's RED was self-contradictory.** `with pytest.raises(SystemExit)` followed by reading
the `campaign.json` the raising call never wrote. *Fixed:* split into two tests.

**D13 — Task 7 inverted the substrate/server layering.** `draft/cli.py` today imports only
`ai_rfc.{__version__,schema}` and `.`-siblings. A module-level `resolve_context` import would make
every `python -m ai_rfc.draft` load `server`, `lifecycle`, `config` and `driver`. *Fixed:* the import
is **function-local**, taken only when an optional argument is absent — the codebase's own idiom
(`pipeline/run.py:77`, `experiment/cli.py:623,1325`; CLI-2's D8 documents them).

**D14 — the ten new `cli.py` files must define no `_report`.** `test_cli_conventions.py:67`'s
`TRACKED_HELPERS = ("_report","_git","_digest","_digest_bytes")` and `_package_sources():87-92`
exclude only `server`, `experiment` and `__pycache__`, so `ai_rfc/agent/**/cli.py` **is** scanned
against the duplication table in `ai_rfc/README.md:516`. *Fixed:* Task 6 Step 3 forbids even a thin
`def _report(...)` wrapper; diagnostics go through `lifecycle/common.report`.

**D15 — Task 3 must name each site's exception family, or an out-of-family error kills the MCP
server.** Every CLI branch catches a *specific* family and returns 1 — `(CheckpointError, SchemaError,
OSError)` for checkpoint, `(GateError, OSError)` for gate, `(BuildError, OSError)` for build,
`(ValueError, OSError)` for lint — and anything outside it becomes a traceback. Today the subprocess
turns that traceback into `returncode == 1` with the traceback in `stderr`. **After Task 3 there is no
subprocess: an uncaught exception propagates into the MCP server and kills the tool call.** The
characterisation tests cannot catch this, because the fixture workspace never reaches the uncaught
path. *Fixed:* Task 3 Step 3 names the family per site and gains Step 3c — one RED per site injecting
an out-of-family exception and asserting `exit_code == 1`, not propagation. **`manifest_gate`'s family
is not yet measured: grep `ai_rfc/check/cli.py`'s `except` clause before the task runs.**

**D16 — Task 5 and Task 8 contradicted U3 about `status`, and the contradiction was arithmetic.**
Task 5 writes `test_status_parity` against `server/cli.py`'s `status` verb and maps it in `TWINS`;
Task 8 then deletes that module and re-points every twin to grouped argv — but U3 means **there is no
grouped `status`**. The Phase 4 gate's "twenty twins" would fail on counting. *Fixed:* Task 5's twin
for `status` is written tool-versus-`queries.status(ctx)` from the start — the core function both
front ends would have shared — so it survives Task 8 untouched, and `TWINS` stays complete at twenty
with a docstring naming U3 as the reason that one row is shaped differently.

**D17 — Task 8's `error()` RED has an unobserved failure mode.** `run_root(["doctor", "--config",
"x", "evil\nerror: …"])` assumes `doctor` reaches the unrecognised-arguments branch rather than
rejecting `--config x` first. A RED whose failure you have not seen is exactly the class D3, D6 and
D9 belonged to. *Fixed:* Task 8 Step 2 now begins by **running the reproduction** and pasting the
observed stderr into the step before the test is written.

**Two smaller fixes folded in.** Task 1 Step 4's workspace test gates on `config_path.name ==
sweep.CONFIG_FILE` **and** `init.json`, so a stray `init.json` beside an operator's unsealed
`recon.yaml` cannot misfire. Task 7 Step 1's arm-C pin exercises `run()` on one case, not only the
parser — the merge could preserve the parse and break the dispatch.

**Info corrections folded in silently:** the `Layout` class lives in `ai_rfc/lifecycle/workspace.py`,
not `layout.py`; `render.py:263-266` is the `revisions_since` slot that *mentions* `ai_rfc status`,
not a dedicated status slot; `arms.py:22-24`'s drift comment governs `RAW_PREFIX`/arm C (the argument
still holds, the citation did not); `metrics.py`'s dual-form comment is `:171-174`; D56's eleven
groups **include** `draft`, so `ai_rfc/agent/` holds ten.

---

## File Structure

**Created — 31 module files plus tests**

| Path | Responsibility |
|---|---|
| `ai_rfc/agent/__init__.py` | The agent-verb package; a docstring naming D56 and nothing else. |
| `ai_rfc/agent/<group>/{__init__.py,__main__.py,cli.py}` × 10 | One package per D56 group: `corpus`, `cluster`, `claim`, `question`, `answer`, `revision`, `checkpoint`, `gate`, `citation_gate`, `structure`. |
| `tests/agent/` | One module per group, plus the mount-table tests; absorbs `tests/server/test_cli.py` in Task 8. |
| `docs/superpowers/plans/2026-09-12-arfc-one-door-cli3{,-deviations}.md` | This plan, transplanted verbatim, and its log. |

Each `cli.py` exposes `configure(parser)`, `run(args) -> int`, `build_standalone_parser()` and
`main(argv=None) -> int` — the contract `entrypoints.CommandModule` declares and the four per-entry
conventions invariants require (D7). `__main__.py` is a two-line `python -m` guard; copy
`ai_rfc/lifecycle/status/__main__.py`. `build_standalone_parser()` carries `--version`; copy
`ai_rfc/draft/cli.py:214-223`.

**Modified**

| Path | Change |
|---|---|
| `ai_rfc/server/paths.py:47-72` | `resolve_context()` reads `AI_RFC_CONFIG`; workspace from the config file's directory (R9); toolchain gated on `is_file()` (D2). |
| `ai_rfc/server/testing.py:42`, `tests/server/conftest.py:15-16` | `build_workspace` seals a minimal `recon.yaml` + `init.json`; `use()` sets `AI_RFC_CONFIG` (D1). |
| `ai_rfc/draft/{gate,lint,completeness,build}.py` | Gain the report writer / toolchain resolver lifted from `draft/cli.py`. |
| `ai_rfc/draft/cli.py` | Calls the lifted writers; gains the merged group's four agent sub-verbs (R4, D13). |
| `ai_rfc/server/core/{gates,build,draft}.py` | Call the APIs in-process; `_run`, its import site and `subprocess` go (D9). |
| `ai_rfc/server/cli.py` | The collapse at `:339` goes (U1); **deleted entirely in Task 8** (R11, D11). |
| `ai_rfc/entrypoints.py` | `EntryPoint` gains `hidden`; ten group rows under `AGENT`; six leaf rows marked hidden (D10). |
| `ai_rfc/cli.py` | `_epilog()` filters hidden rows; the root parser overrides `error()`. |
| `ai_rfc/driver/{arms,render}.py` | `Bash(ai-rfc *)`; arm-B slots re-rendered to grouped verbs; `SKILL_FRONTMATTER`. |
| `ai_rfc/experiment/{audit,metrics,config,cli}.py` | Matchers derived from `bash_prefixes` (R6); `_SHIM` writes `bin/ai-rfc`; Task 10's flags. |
| `pyproject.toml:31-32` | The `ai_rfc` console script entry removed. |
| `plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` | **Regenerated**, never hand-edited. |
| `plugins/ai-rfc/commands/ai-rfc-release-revision.md:10,13,15` | Hand-edited; not rendered. |
| `tests/experiment/fake_claude/claude` | Twelve arm-B command emitters. |
| `tests/substrate/test_root_cli.py:30`, `tests/cli/test_root.py:26-28` | Iterate non-hidden entries (D8). |
| `tests/server/{test_build,test_draft,test_gates}.py` | The `_run` seams become API-level fakes (D9). |
| `docs/{parity,experiment-protocol}.md`, three `README.md` | The verb column, the arm-B surface sentences. |
| `docs/superpowers/specs/2026-09-03-arfc-one-door-design.md` *(PANTHER)* | §6 restated (U1); §5's sentence and a new D-row (U2). `git add -f`. |

**Not modified, deliberately:** `ai_rfc/pipeline/run.py` (R10);
`tests/driver/fixtures/enforcement/run-b1-arm-b.json` and `docs/experiments/*.json` (M1);
`RAW_PREFIX = "python -m ai_rfc"` and every `ai_rfc_*` MCP tool name (identifiers, not the door).

---

## Execution order

```
T1  AI_RFC_CONFIG context ............. independent (D1, D2 widen it)
T2  report writers move ............... independent; pure lift
T3  core calls APIs in-process ........ needs T2 (D9 widens it)
T4  exit codes stop collapsing ........ needs T3 (U1, D4, D5)
T5  the ten missing parity twins ...... needs T3; pins pre-fold behaviour (D6)
T6  ten agent/ groups mounted ......... needs T1, T3 (D7, D14)
T7  draft merged + leaf rows hidden ... needs T6; FORCED ATOMIC (R3, R4, D8, D10, D13)
T8  script, prog, shim AND server/cli.py retired ... needs T7 (R11, D11)
T9  arm-B rename, atomic .............. needs T7, T8; the row's largest task
T10 --panther-repo retirement ......... independent; U4's cut line (D12)
T11 docs, parity guard, spec amendments  needs T9; closes U1, U2, M5
```

T7 is forced atomic: `draft` cannot be two `add_parser("draft")` calls, so the leaf row and the group
change in the **same** commit.

---

## Task 1: `resolve_context()` reads `AI_RFC_CONFIG`

**Files:**
- Modify: `ai_rfc/server/paths.py:47-72` (and the module docstring `:1-11`, which states the old
  contract in full)
- Modify: `ai_rfc/server/testing.py:42` (`build_workspace` seals a config), `tests/server/conftest.py:15-16`
- Modify: `ai_rfc/driver/arms.py:149`
- Test: `tests/server/test_paths.py`

**Interfaces:**
- Consumes: `ai_rfc.lifecycle.common.CONFIG_ENV` (`= "AI_RFC_CONFIG"`, `common.py:23`),
  `ai_rfc.config.load_config`, `ai_rfc.lifecycle.workspace.Layout`. **Reuse these — do not write a
  second config reader.**
- Produces: `resolve_context() -> Context`, unchanged in type.

- [ ] **Step 0: Enumerate the blast radius before writing anything (D1)**

```
grep -rln 'AI_RFC_WORKSPACE' tests/
```
Fourteen modules set it (`tests/ledger`, four under `tests/driver`, four under `tests/server`, five
under `tests/experiment`). `tests/server/conftest.py:15-16`'s `use()` sets **only** that variable and
`ai_rfc/server/testing.py:42 build_workspace` writes **no `recon.yaml` and no `init.json`**, so eight
`tests/server/` modules die at fixture setup the moment the contract moves. Write the list into the
deviation log before Step 1.

- [ ] **Step 1: Write the failing test — the campaign-copy trap (R9)**

```python
def test_a_copied_workspace_resolves_to_the_copy_not_the_original(tmp_path, monkeypatch):
    """A campaign run is a copy of the pristine, and the sealed config names the pristine.

    `lifecycle/common.load_pair:129-132` records why the sealed `workspace:` field cannot
    be trusted. Deriving the workspace from it sends every tool to the tree the copy was
    made from — operating on the wrong workspace while looking like success, the failure
    `paths.py:4-6` exists to stop.
    """
    pristine = tmp_path / "pristine"
    (pristine / "out").mkdir(parents=True)
    (pristine / "init.json").write_text("{}")
    (pristine / "recon.yaml").write_text(
        "name: demo\n"
        f"workspace: {pristine}\n"
        "source:\n  repo: https://example.invalid/r.git\n  pin: deadbeef\n"
        "draft:\n  name: draft-demo\n"
    )
    copy = tmp_path / "runs" / "A1" / "workspace"
    copy.parent.mkdir(parents=True)
    shutil.copytree(pristine, copy)

    monkeypatch.delenv("AI_RFC_WORKSPACE", raising=False)
    monkeypatch.setenv("AI_RFC_CONFIG", str(copy / "recon.yaml"))
    assert resolve_context().workspace == copy.resolve()
```

The minimal YAML was verified against `load_config`: all four required fields are present,
`_infer_host` returns the legal `"none"`, and it validates.

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Expected: FAIL — `EnvError: AI_RFC_WORKSPACE must be set`. No test pins that message string.
**If it fails for any other reason, or passes, stop and report.**

- [ ] **Step 3: Write the two remaining REDs, one of them D2's**

An operator's `recon.yaml` **outside** any workspace resolves to its `workspace:` field; and:

```python
def test_a_defaulted_toolchain_path_that_does_not_exist_resolves_to_None(tmp_path, monkeypatch):
    """`config.py:642` defaults `toolchain` to a path, so a loaded config never carries
    None. Reading the field directly would make `core/draft.py:120`'s
    `if ctx.toolchain is not None:` always true and force a build on every tag."""
    ...
    assert resolve_context().toolchain is None
```

- [ ] **Step 4: Implement**

`resolve_context()` reads `os.environ[CONFIG_ENV]`. If `config_path.name == sweep.CONFIG_FILE`
(`"recon.yaml"`, `driver/sweep.py:86`) **and** the config's own directory holds `init.json`, the
workspace is `config_path.parent`; otherwise `load_config(config_path).workspace`. Both conditions
are needed: a stray `init.json` beside an operator's unsealed config would otherwise misfire. The
toolchain
is `cfg.toolchain if cfg.toolchain.is_file() else (Path(os.environ[TOOLCHAIN_ENV]) if set else None)`
(D2). Rewrite the module docstring, including R8's note that `AI_RFC_WORKSPACE` is still exported for
arm B/C prompts but is no longer what the server reads.

- [ ] **Step 5: Move the test fixtures with the contract (D1)**

`ai_rfc/server/testing.py:42 build_workspace` writes a minimal sealed `recon.yaml` and `init.json`;
`tests/server/conftest.py:15-16`'s `use()` sets `AI_RFC_CONFIG` instead of `AI_RFC_WORKSPACE`.

- [ ] **Step 6: Wire the driver**

`driver/arms.py:149`'s `env = {"AI_RFC_WORKSPACE": str(workspace)}` gains
`"AI_RFC_CONFIG": str(workspace / "recon.yaml")`. **Keep `AI_RFC_WORKSPACE`** (R8).

- [ ] **Step 7: Run `pytest tests/server tests/driver tests/ledger tests/experiment -q`; then the full suite; commit**

`feat: resolve the server context from AI_RFC_CONFIG`

---

## Task 2: Move each report writer beside the API that produces it

**Files:**
- Modify: `ai_rfc/draft/gate.py`, `lint.py`, `completeness.py`, `build.py`
- Modify: `ai_rfc/draft/cli.py:294-295, 307-320, 379-380, 402-405`
- Test: `tests/substrate/draft/test_reports.py` (new)

**Interfaces — produced for Task 3:**
- `write_gate_report(out: Path, findings: Sequence[str]) -> Path`
- `write_lint_report(out: Path, report: LintReport) -> Path`
- `write_completeness_report(out: Path, report: CompletenessReport) -> Path`
- `resolve_toolchain(explicit: Path | None) -> Toolchain` — raises `BuildError` when neither the
  argument nor `TOOLCHAIN_ENV` names one, and when `probe_toolchain` reports anything missing.

- [ ] **Step 1: Write the characterisation tests (RED by absence)**

One per writer, asserting the **bytes** on disk, copied from the CLI branch:
`json.dumps({"findings": list(findings)}, sort_keys=True, indent=2) + "\n"` (`cli.py:403-405`),
`report.to_json()` (`:380`), `completeness_json(report)` (`:295`). Pins, not new behaviour.

- [ ] **Step 2: Run; confirm each fails with `ImportError`/`AttributeError`**

- [ ] **Step 3: Lift the four blocks — move, do not copy**

`draft/cli.py` imports and calls them; the branches keep their printing and exit codes. **No behaviour
change** — `pytest tests/substrate -q` holds its count.

- [ ] **Step 4: Run the substrate suite, confirm the count, commit**

`refactor: move the draft report writers beside their APIs`

---

## Task 3: The core calls the APIs in-process; `_run` is deleted

**Files:**
- Modify: `ai_rfc/server/core/gates.py` (delete `_run:24-33`; rewrite `:90, :130, :176`; rewrite the
  module docstring `:1-8`, which describes the shell-out contract)
- Modify: `ai_rfc/server/core/build.py` (rewrite `:64, :98`; drop `:14`'s `from .gates import _run`)
- Modify: `ai_rfc/server/core/draft.py` (`tag_revision:71` folds core output into its own payload at
  `:116` and `:143` — D9)
- Test: `tests/server/test_core_in_process.py` (new), `tests/server/test_gates.py`,
  `tests/server/test_build.py:59,111,147`, `tests/server/test_draft.py:115`

**Interfaces — the five dict shapes are unchanged:** `{exit_code, stderr, manifest_sha256?}`,
`{exit_code, stderr, report}`, `{exit_code, stderr, findings}`,
`{exit_code, stderr, findings, commit, outputs}`, `{exit_code, stderr, findings, metrics}`.

- [ ] **Step 1: Write the characterisation tests FIRST, against the subprocess implementation**

For each of the five **and for `tag_revision`** (D9), capture today's returned dict on a fixture
workspace — including the exact `stderr` list — and freeze it. Run it now, green, against unchanged
code. This is the contract Step 3 must reproduce byte-for-byte (R2).

- [ ] **Step 2: Write the RED that proves no subprocess is spawned (D3)**

```python
def test_the_core_never_spawns_a_subprocess(workspace, monkeypatch):
    """Five sites shelled out through one helper; none may remain.

    The patch is global rather than module-local on purpose: after the fix
    `gates` has no `subprocess` attribute at all, so a module-qualified patch
    would raise AttributeError forever and the test could never go green.
    """
    def _refuse(*args, **kwargs):
        raise AssertionError(f"the core shelled out: {args!r}")

    monkeypatch.setattr("subprocess.run", _refuse)
    gates.manifest_gate(resolve_context())


def test_the_shell_out_helper_is_gone():
    assert not hasattr(gates, "_run") and not hasattr(gates, "subprocess")
```

Expected: the first FAILS with `AssertionError: the core shelled out: …`; the second FAILS because
both attributes exist today. **If either passes, stop** — the premise is wrong.

- [ ] **Step 3: Rewrite the five sites**

Each becomes: build the same arguments from `ctx` → call the API → call Task 2's writer → compute
`exit_code` (0, or 3 when `strict and findings`, or 1 on the exception family) → build `stderr` from
the same values (R2).

**Name the family per site, do not generalise (D15):** checkpoint catches
`(CheckpointError, SchemaError, OSError)` (`draft/cli.py:258`); citation-gate `(GateError, OSError)`
(`:398`); build `(BuildError, OSError)` (`:330`); lint `(ValueError, OSError)` (`:376`);
**`manifest_gate`'s family is unmeasured — grep `ai_rfc/check/cli.py`'s `except` clause first and
record it in the log.** Anything outside the family used to become `returncode == 1` with a traceback
in the subprocess's `stderr`; in-process it would propagate into the MCP server and kill the tool
call.

Delete `_run`, the `subprocess` and `sys`
imports, `build.py:14`'s import site, and the `cwd=ctx.workspace` argument. **Measured: nothing
depends on that cwd** — the grep for `Path.cwd()|os.getcwd|cwd=` across `ai_rfc/draft/` and
`ai_rfc/check/` returns exactly one hit, `build.py:399`'s own scratch directory.

- [ ] **Step 3b: Replace the three `_run` monkeypatch seams with API-level fakes (D9)**

`tests/server/test_build.py:59,111,147` patch `_run` itself and pin its stderr at `:67`
(`["note: fake"]`), `:116` and `:149` (`["error: nope: not a commit"]`); `tests/server/test_draft.py:115`
pins `[]`. The seam disappears with the helper. Patch `draft.build.build` / `draft.lint.lint` instead
and keep the same pinned stderr values, which R2 preserves.

- [ ] **Step 3c: One RED per site for the out-of-family exception (D15)**

```python
@pytest.mark.parametrize("site", ["write_checkpoint", "manifest_gate", "citation_gate",
                                  "draft_build", "draft_lint"])
def test_an_out_of_family_error_is_reported_not_propagated(site, workspace, monkeypatch):
    """The subprocess used to turn any traceback into returncode 1. In-process an
    uncaught exception reaches the MCP server and kills the tool call."""
    monkeypatch.setattr(_api_of(site), _raise(RuntimeError("out of family")))
    assert getattr(gates_or_build, site)(resolve_context())["exit_code"] == 1
```

Expected before Step 3: these do not apply (the subprocess absorbs it). Write them **with** Step 3
and see each fail once against a deliberately un-caught first draft, then pass.

- [ ] **Step 4: Run Step 1's characterisation tests; they must still pass**

Any byte that moved is a regression. Fix the core, never the pin.

- [ ] **Step 5: Run `pytest tests/server -q`, then the full suite; commit**

`refactor: call the substrate in-process from the server core`

---

## Task 4: Exit codes stop being reinterpreted

**Files:** Modify `ai_rfc/server/cli.py:339`. Test: `tests/server/test_cli_exit_codes.py` (new).

- [ ] **Step 1: Write the RED (D4, D5)**

```python
@pytest.mark.parametrize("code", [0, 1, 2, 3])
def test_no_verb_reinterprets_the_core_s_exit_code(code, workspace, monkeypatch):
    """server/cli.py:4-5 promises exit codes "pass through untouched"; the
    checkpoint branch alone collapsed every non-zero to 1. The `workspace`
    fixture is required: :254-259 resolves the context before dispatch and
    returns 1 on EnvError, so without it every parametrisation returns 1.
    """
    monkeypatch.setattr(
        gates, "write_checkpoint", lambda *a, **k: {"exit_code": code, "stderr": []}
    )
    assert cli.main(["checkpoint", "c0001-x"]) == code
```

- [ ] **Step 2: Run; expect FAIL for `code` 2 and 3 (each collapses to 1), PASS for 0 and 1**

- [ ] **Step 3: Make the one-line change; run green; commit**

`fix: stop collapsing the checkpoint verb's exit code`

---

## Task 5: The ten missing parity twins

**Files:** Modify `tests/server/test_parity.py`.

Twins cover **10 of 20**. The ten with none: `status`, `corpus-query`, `cluster-get`, `cluster-next`,
`question-draft`, `question-export`, `answer-record`, `gate`, `citation-gate`, `draft-build`.

- [ ] **Step 1: Write all ten, following the file's existing shape**

Each drives the MCP tool and the CLI verb against the two workspaces `make_workspace` yields and
asserts the artifacts and stdout agree. The four read-only verbs assert the **payload**; `gate`,
`citation-gate` and `draft-build` assert the artifact and the exit code.

**`status` is shaped differently, deliberately (D16).** U3 gives it no grouped verb, and Task 8
deletes `server/cli.py`, so a tool-versus-CLI twin for it would not survive this row. Write
`test_status_parity` as **tool versus `queries.status(ctx)`** — the core function both front ends
would have shared — so the row stays at twenty twins after Task 8 without an arithmetic exception.

- [ ] **Step 2: Run them; every one must pass against unchanged code**

These pin behaviour before the fold; they are **not** REDs. A failure is a real pre-existing parity
defect — stop and report rather than adjusting the test.

- [ ] **Step 3: Assert coverage with an explicit mapping (D6)**

A name-derivation expression cannot reach 20: only eight function names end in `_parity`,
`test_read_parity_adjudicate:75` does not, and `test_consolidation_checkpoint_and_revision_parity:181`
covers two verbs in one function.

```python
#: Tool name -> the test function that drives its twin. Written out rather than
#: derived: one twin covers two verbs and one does not carry the suffix, so any
#: expression over `dir()` undercounts and the assertion would pin the wrong number.
#: `ai_rfc_status`'s twin compares the tool against `queries.status` rather than a
#: CLI verb, because U3 gives the folded `status` no `ai-rfc` verb at all.
TWINS: dict[str, str] = {"ai_rfc_status": "test_status_parity", ...}

def test_every_tool_has_a_parity_twin():
    assert set(TWINS) == {tool.__name__ for tool in tools.ALL_TOOLS}
```

- [ ] **Step 4: Commit** — `test: add the ten missing parity twins`

---

## Task 6: Mount fifteen parity verbs as ten `ai_rfc/agent/` packages

**Files:**
- Create: `ai_rfc/agent/__init__.py`, and `{__init__.py, __main__.py, cli.py}` for each of `corpus`,
  `cluster`, `claim`, `question`, `answer`, `revision`, `checkpoint`, `gate`, `citation_gate`,
  `structure` — **31 files** (D7)
- Modify: `ai_rfc/entrypoints.py:84-215` (ten rows under `AGENT`, declared at `:76` with **zero rows**)
- Test: `tests/agent/`

**Mount table** (the `draft` group's four verbs land in Task 7; `status` retires per U3):

| parity verb | grouped | parity verb | grouped |
|---|---|---|---|
| `corpus-query` | `corpus query` | `revision-record` | `revision record` |
| `cluster-get` | `cluster get` | `revision-tag` | `revision tag` |
| `cluster-next` | `cluster next` | `checkpoint` | `checkpoint` |
| `claim-upsert` | `claim upsert` | `gate` | `gate` |
| `claim-adjudicate` | `claim check` (§6) | `citation-gate` | `citation-gate` |
| `claim-record-status` | `claim record-status` | `structure-upsert` | `structure upsert` |
| `question-draft` | `question draft` | `answer-record` | `answer record` |
| `question-export` | `question export` | | |

- [ ] **Step 1: Write the RED — the mount table (D6-class fix applied)**

```python
GROUPED = ["corpus query", "cluster get", "cluster next", "claim upsert", "claim check",
           "claim record-status", "question draft", "question export", "answer record",
           "revision record", "revision tag", "checkpoint", "gate", "citation-gate",
           "structure upsert"]

@pytest.mark.parametrize("verb", GROUPED)
def test_the_grouped_verb_parses(verb):
    """D56's verb tree, one row at a time. `--help` exits 0 once mounted and 2
    while unmounted, so the code must be asserted or the test can never go green."""
    with pytest.raises(SystemExit) as excinfo:
        cli.build_parser().parse_args(verb.split() + ["--help"])
    assert excinfo.value.code == 0
```

Expected: FAIL for all fifteen — `excinfo.value.code == 2`, "invalid choice".

- [ ] **Step 2: Write the parity RED that proves one core, not two**

For one verb per group, assert the grouped verb and the `ai_rfc` verb produce identical artifacts on
twin workspaces. This is the assertion that fails if a group re-implements rather than calls
`server.core`.

- [ ] **Step 3: Create the thirty-one files, lifting from `server/cli.py`'s `elif` chain**

Each `configure` lifts the matching `add_parser` block from `server/cli.py:44-237`; each `run` lifts
the matching `elif` arm. **Call `server.core`; never re-implement.** Diagnostics go through
`lifecycle/common.report`, which already escapes (`common.py:91-92` walks lines through `printable`).
**Define no `_report` helper, not even a thin wrapper** — `test_cli_conventions.py:67`'s
`TRACKED_HELPERS` scans `ai_rfc/agent/**/cli.py` against the duplication table in
`ai_rfc/README.md:516` (D14).

- [ ] **Step 3b: Satisfy the four per-entry conventions invariants (D7)**

- `__main__.py` per package — `test_importing_an_entry_point_does_not_run_it:47-58` imports it
  unconditionally. Template: `ai_rfc/lifecycle/status/__main__.py`.
- `build_standalone_parser()` carrying `--version` — `test_every_entry_point_reports_its_version:22-30`
  requires `main(["--version"])` to `SystemExit(0)` printing `entry.prog` and `__version__`. Template:
  `ai_rfc/draft/cli.py:214-223`.
- `usage: {entry.prog}` in stdout — `test_main_is_the_standalone_door…:205-212`.
- `__init__.py` per package — `pyproject.toml:34-35` uses `find`, not `find_namespace`; without it the
  ten packages are absent from the install and no test in the source tree would notice.

- [ ] **Step 4: Register the ten rows under `AGENT`, contiguously**

`test_entries_sharing_a_section_are_contiguous` requires it.
`test_every_cli_module_on_disk_is_registered` now counts ten more `cli.py` files and finds ten more
rows — **it passes unedited**.

- [ ] **Step 5: Run `pytest tests/agent tests/substrate/test_cli_conventions.py tests/cli tests/server -q`; then the full suite; commit**

`feat: mount the agent verbs as grouped subcommands of ai-rfc`

---

## Task 7: Merge the `draft` group and hide the six leaf rows — one commit

**Files:**
- Modify: `ai_rfc/entrypoints.py` (`EntryPoint` gains `hidden: bool = False`; six rows marked)
- Modify: `ai_rfc/cli.py:25-41`
- Modify: `ai_rfc/draft/cli.py`
- Modify: `tests/substrate/test_root_cli.py:30`, `tests/cli/test_root.py:26-28` (D8)

**Forced atomic (R4):** `draft` cannot be two `add_parser("draft")` calls.

- [ ] **Step 1: Run the arm-C pin FIRST — it is a pin, not a RED**

```python
ARM_C_ARGV = [
    ["check", "/w/manifest.yaml", "--out", "/w/out", "--repo", "/w/clone"],
    ["check", "/w/manifest.yaml", "--out", "/w/out", "--repo", "/w/clone", "--strict"],
    ["draft", "checkpoint", "/w/manifest.yaml", "--timeline", "/w/timeline",
     "--cluster", "c0001-x", "--out", "/w/checkpoints"],
    ["draft", "gate", "/w/draft", "--timeline", "/w/timeline", "--checkpoints",
     "/w/checkpoints", "--questions", "/w/questions.yaml", "--revisions",
     "/w/revisions.yaml", "--out", "/w/out"],
]

@pytest.mark.parametrize("argv", ARM_C_ARGV)
def test_arm_c_argv_still_parses_through_the_root_door(argv):
    """render.py:137,146,151,169 type these through `python -m ai_rfc`, not
    `python -m ai_rfc.<sub>`. Deleting the leaf rows breaks arm C outright."""
    cli.build_parser().parse_args(argv)


def test_arm_c_draft_gate_still_dispatches(workspace):
    """Parsing is not dispatching: the merge could keep the argv and break the
    branch it reaches. One case runs end to end."""
    assert cli.main(["draft", "gate", str(workspace / "draft"), ...]) in (0, 3)
```

Green today. Both must still be green at Step 6.

- [ ] **Step 2: Write the RED — six verbs leave the help and stay dispatchable (D10)**

```python
HIDDEN = ["check", "coverage", "history", "forge", "timeline", "views"]

@pytest.mark.parametrize("verb", HIDDEN)
def test_a_hidden_verb_is_absent_from_help_and_present_in_the_parser(verb):
    """§6 retires them from the operator's help. R3: hidden, not deleted, because
    arm C types them through the root door. `draft` is NOT hidden — D56 makes it
    an agent group and Task 9 renders its verbs into arm B's prompt."""
    assert f"\n  {verb} " not in cli.build_parser().format_help()
    assert verb in cli.build_parser()._subparsers._group_actions[0].choices
```

The `_subparsers._group_actions[0].choices` accessor was executed against this Python 3.10 build and
returns a `dict` of the mounted verbs. Expected: FAIL on the first assertion for all six.

- [ ] **Step 3: Write the RED for the four merged `draft` sub-verbs**

`["draft", "commit", "-m", "msg"]`, `["draft", "build"]`, `["draft", "lint"]`, `["draft", "render"]`
— each parses with **no** positional and no required flag. Expected: FAIL — today `draft build`
requires `draftrepo`, `--out` and a toolchain.

- [ ] **Step 4: Implement**

Add `hidden: bool = False` to `EntryPoint`, last, with a docstring line saying what it means and why.
`_epilog()` skips hidden rows; **sections stay declared**, so `test_every_entry_declares_a_section`
holds. Mark the six. In `draft/cli.py`, add `commit`, and make `build`/`lint`/`render`'s positional
and required flags optional, defaulting from the context — **through a function-local import** (D13):

```python
def _context():
    """Resolve the workspace only when an argument was omitted.

    Local rather than module-level: `draft/cli.py` is substrate and imports only
    `ai_rfc.{__version__,schema}` and its siblings today. A module-level import
    would pull `server`, `lifecycle`, `config` and `driver` into every
    `python -m ai_rfc.draft`. The idiom is the codebase's own — `pipeline/run.py:77`,
    `experiment/cli.py:623,1325`.
    """
    from ..server.paths import resolve_context

    return resolve_context()
```

`checkpoint`, `gate` and `completeness` keep their leaf shapes exactly.

- [ ] **Step 5: Re-point the two help tests (D8)**

`tests/substrate/test_root_cli.py:30` (`assert rendered == [entry.verb for entry in ENTRY_POINTS]`)
and `tests/cli/test_root.py:26-28` (each verb counted once) iterate
`[e for e in ENTRY_POINTS if not e.hidden]`, and each gains a companion assertion that the hidden
verbs are **absent** — so the change tightens what they cover rather than loosening it.

- [ ] **Step 6: Run Step 1's pins; they must still pass. Then the conventions suite, unedited**

`pytest tests/substrate tests/cli tests/agent -q`, then the full suite.

- [ ] **Step 7: Commit** — `feat: fold the draft verbs and retire the leaf verbs from the help`

---

## Task 8: Retire the console script, the `prog` value, the shim and `server/cli.py`

**Files:** `pyproject.toml:31-32`; `ai_rfc/experiment/config.py:55-57,406`; `ai_rfc/cli.py`;
**delete** `ai_rfc/server/cli.py`; move `tests/server/test_cli.py` → `tests/agent/`; re-point
`tests/server/{test_parity,test_revisions}.py`. Test: `tests/cli/test_root_errors.py` (new).

- [ ] **Step 1: Write the RED that actually EXECS the renamed shim**

The brief's blind spot, and the user's third ruling. `test_campaign_init_run_audit_analyze_round_trip`
never execs `bin/ai_rfc` — `fake_claude` mutates the workspace by importing the core in-process and
emits the shim's name only as a string for the classifier. Renaming the shim would pass that test
even if the shim were broken.

```python
def test_the_campaign_shim_actually_runs(campaign):
    """The round-trip gate emits the shim's name without ever executing it."""
    shim = campaign.bin_dir / "ai-rfc"        # bin_dir: experiment/config.py:186
    assert shim.is_file() and os.access(shim, os.X_OK)
    done = subprocess.run([str(shim), "--help"], capture_output=True, text=True)
    assert done.returncode == 0
    assert done.stdout.startswith("usage: ai-rfc <verb> [args]")
```

Expected: FAIL — `bin/ai-rfc` does not exist; `config.py:406` writes `bin/ai_rfc`.

- [ ] **Step 2: Reproduce the forge FIRST, then write the RED (D17)**

CLI-2 left this open and named the remedy as **one site**: argparse's `'unrecognized arguments: %s'`
uses `%s` not `%r`, reproduced door-wide on `doctor`, `pipeline` and `experiment`. **Run the
reproduction and paste the observed stderr into this step before writing the test** — the assertion
below assumes `doctor` reaches the unrecognised-arguments branch rather than rejecting `--config x`
first, and a RED whose failure mode you have not seen is the class D3, D6 and D9 belonged to. If the
observed forge needs a different verb or argv, use that one.

```python
def test_an_unrecognised_argument_cannot_forge_a_stderr_line():
    """argparse interpolates the token with %s; a newline in it then writes a
    second line that reads as the tool's own diagnostic."""
    done = run_root(["doctor", "--config", "x", "evil\nerror: workspace destroyed"])
    assert "\nerror: workspace destroyed" not in done.stderr
```

- [ ] **Step 3: Implement (R11, D11)**

Delete `pyproject.toml:31-32`'s `ai_rfc` entry and its comment. `config.py:55-57`'s `_SHIM` body
becomes `from ai_rfc.cli import main`; `:406`'s `bin_dir / "ai_rfc"` becomes `"ai-rfc"`. Subclass
`ArgumentParser` in `ai_rfc/cli.py`, overriding `error()` to route through `lifecycle/common.report`.
**Delete `ai_rfc/server/cli.py`** and move its four importers: `tests/server/test_cli.py` becomes
`tests/agent/test_verbs.py` driving `ai_rfc.cli.main`; `tests/server/test_parity.py`'s twins
re-point from `server.cli.main` to `ai_rfc.cli.main` with the **grouped** argv — **nineteen of them;
`test_status_parity` needs no change** because Task 5 wrote it against `queries.status` (D16);
`tests/server/test_revisions.py` likewise. This is the task's bulk — size it accordingly.
*Fallback if the row overruns:* keep the module with `prog="ai-rfc"`, log the debt, and cut nothing
else (U4 governs the real cut line).

- [ ] **Step 4: Reinstall in BOTH interpreters and prove the scripts are gone (M7)**

```
SSLKEYLOGFILE= .venv/bin/python -m pip install -e . -q
SSLKEYLOGFILE= ~/ai-rfc-experiments/venv-optimize/bin/python -m pip install -e . -q
test ! -e .venv/bin/ai_rfc && test ! -e ~/ai-rfc-experiments/venv-optimize/bin/ai_rfc
```

- [ ] **Step 5: Run the full suite; commit** — `feat: retire the ai_rfc console script, shim and parser`

---

## Task 9: The arm-B rename — one atomic change

**Files:** `ai_rfc/driver/arms.py:54`, `ai_rfc/driver/render.py:77,185-315`,
`ai_rfc/experiment/audit.py:66`, `ai_rfc/experiment/metrics.py:165`,
`plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` (**regenerated**),
`plugins/ai-rfc/commands/ai-rfc-release-revision.md:10,13,15` (hand-edited),
`tests/experiment/fake_claude/claude` (12 emitters: `344,359,377,402,433,453,496,508,520,532,581,586`),
~60 test literals across `tests/driver/test_enforcement{,_corpus}.py`,
`tests/experiment/{test_audit,test_fake_claude,test_runner,test_preflight,test_metrics}.py`,
`tests/driver/test_arms.py`.

**The row's largest task**, atomic because the round-trip gate (`test_cli_campaign.py:74-97`, which
asserts `integrity=True`) goes red the moment the emitted spelling and the classifier disagree.

- [ ] **Step 1: Write the RED — one prefix, three readers (R6)**

```python
def test_the_audit_and_the_guard_read_one_prefix():
    """A drifted second copy silently reclassifies a legitimate call as an
    integrity violation. audit.py:66 and metrics.py:165 are that second and
    third copy of arms.py:54."""
    prefix = bash_prefixes(arm_profile("B"))[0]
    assert audit._stage_surface(f"{prefix}status") == "bash:ai_rfc"
    assert audit._stage_surface("ai_rfc status") == "bash:other"
```

Verified: `bash_prefixes` (`enforcement.py:37-52`) strips the trailing `*`, yielding `"ai_rfc "`
today, and `_stage_surface`'s fallthrough is literally `return "bash:other"` (`audit.py:74`) — so both
assertions collide today and both hold after the rename. Expected: FAIL on the second.

- [ ] **Step 2: Change `arms.py:54` to `Bash(ai-rfc *)`; derive both matchers from it**

`audit.py:66` and `metrics.py:165` import `bash_prefixes`/`arm_profile` instead of carrying literals.
**The recorded key `bash:ai_rfc` does not change (R7)** — add a comment beside it saying so and why.

- [ ] **Step 3: Re-render the arm-B slot table to GROUPED verbs**

`render.py:260-315`'s slots become `ai-rfc cluster next`, `ai-rfc claim upsert`, `ai-rfc gate --strict`,
`ai-rfc checkpoint <id>`, `ai-rfc draft render` — the grouped forms Tasks 6 and 7 mounted, not the old
hyphenated ones. The `revisions_since` slot (`:263-266`) mentions `ai_rfc status`; re-render it per
U3 without a CLI status form. `render.py:77`'s `SKILL_FRONTMATTER` allowed-tools becomes
`Bash(ai-rfc *)`. **Arm C's `_RAW` table (`:120-180`) and `RAW_PREFIX` do not change.**

- [ ] **Step 4: Regenerate the shipped skill IN THE SAME COMMIT**

`tests/driver/test_render.py:33-35` asserts the committed SKILL.md equals
`SKILL_FRONTMATTER + render_loop("interactive")` byte-for-byte.

```
SSLKEYLOGFILE= .venv/bin/python -m ai_rfc.experiment render
```

Never hand-edit that file. Then hand-edit `plugins/ai-rfc/commands/ai-rfc-release-revision.md`
(lines 10, 13, 15) — it is **not** rendered.

- [ ] **Step 5: Update the twelve emitters and the ~60 test literals**

Including `test_enforcement_corpus.py:31`'s `ARM_B = ("ai_rfc ",)` and its constructed command
strings. **Do not touch `tests/driver/fixtures/enforcement/run-b1-arm-b.json` (M1).** Two assertions
go **vacuous** on a bare rename and must be re-pointed, not left: `test_render.py:52` and `:105` are
negative assertions that pass trivially once the spelling changes.

- [ ] **Step 6: Run the round-trip gate, then the full suite**

`pytest tests/experiment/test_cli_campaign.py::test_campaign_init_run_audit_analyze_round_trip -q`
must pass with `integrity=True`. Then `pytest tests -q -n auto`.

- [ ] **Step 7: Commit** — `feat: rename arm B's Bash family to ai-rfc`

---

## Task 10: Retire `--panther-repo` *(U4's pre-authorised cut)*

**Files:** `ai_rfc/experiment/cli.py:969,1111,1247` (flags), `:608,1419,1531` (consumers),
`ai_rfc/experiment/config.py:81,127,305,426,435,476`, `optimize/evaluator.py:114,139,453`,
`optimize/fixtures.py:188,203`; ~142 test-line touches in `tests/experiment/test_config.py` (56),
`test_cli_campaign.py` (45), `test_fake_claude.py` (21).

- [ ] **Step 1: Write two REDs, not one (D12)**

A single test cannot both assert the flag raises and read the `campaign.json` the raising call never
wrote.

```python
def test_the_panther_repo_flag_is_gone():
    with pytest.raises(SystemExit):
        cli.main(["campaign", "init", *BASE_ARGV, "--panther-repo", "/tmp/x"])


def test_campaign_init_records_provenance_without_the_flag(tmp_path):
    """`optimize run`'s flag already documents the replacement: "Default: the
    repository this package is installed from" (cli.py:1250-1251)."""
    assert cli.main(["campaign", "init", *BASE_ARGV]) == 0
    assert json.loads(campaign_json)["git"]["panther"] != "unknown"
```

`git_describe` (`config.py:236-250`) returns `"unknown"` when git fails, so the second is not vacuous.

- [ ] **Step 2: Delete the three flags; point all three consumers at `_repo_root()`**

`_repo_root()` is `experiment/cli.py:239-241`, "The repository this package is installed from" —
already the fallback at `:608`. `:1419` and `:1531` do `args.panther_repo.resolve()` unconditionally
because their flags are `required=True`.

- [ ] **Step 3: Sweep the test literals; run BOTH interpreters**

`pytest tests -q -n auto` under 3.10, and the optimize selection under 3.11 — **M6: this task moves
modules the 3.11 track imports, so a red there is this task's, not pre-existing.** Decide whether the
3.11 re-run is needed by inspecting `sys.modules` after importing the targets, **never by a grep**,
which was measured wrong twice on the previous row.

- [ ] **Step 4: Commit** — `refactor: derive campaign provenance from the installed package root`

---

## Task 11: Docs, the parity guard, and the spec amendments

**Files:** `docs/parity.md`, `docs/experiment-protocol.md:14,24,30,121,156`, `README.md:104,106,142`,
`ai_rfc/experiment/README.md:29,74`, `ai_rfc/server/README.md:22,26,44`,
`tests/server/test_parity.py`, and in **PANTHER**
`docs/superpowers/specs/2026-09-03-arfc-one-door-design.md`.

- [ ] **Step 1: Write the RED that guards the verb column (M5)**

`test_every_tool_is_in_the_parity_table:85-88` asserts only the MCP tool name, so the middle column is
unguarded documentation.

```python
def test_the_parity_table_names_the_grouped_verb_for_every_tool():
    """The table's middle column was documentation nothing checked."""
    for tool in tools.ALL_TOOLS:
        verb = _verb_cell(table, tool.__name__)
        assert verb.startswith("`ai-rfc ") or verb == "— (MCP only)"
```

- [ ] **Step 2: Rewrite the twenty rows' middle column to the grouped verbs**

`ai_rfc_status`'s cell becomes `— (MCP only)` per U3. `docs/parity.md:36`'s "The `ai_rfc` verbs are
unchanged by CLI-1; CLI-3 folds them into `ai-rfc`" goes to the past tense; `:9`'s reference to the
deleted module goes with it (D11).

- [ ] **Step 3: Update the protocol and the three READMEs**

`experiment-protocol.md:14,24,30,121,156` name arm B's surface; `:24`'s parity-suite sentence stays
true and gains the twenty-twin count. Record U3's arm-surface change explicitly.

- [ ] **Step 4: Amend the spec in PANTHER (U1, U2)**

§6's "`checkpoint` regains 3" → "stops collapsing every non-zero code to 1 and reports the substrate's
code as its neighbours do"; §Context's twelfth friction restated; §5's exit-code sentence → "done or
bound reached 0; stopped with work outstanding 1; strict findings 3"; and a new D-row fixing reason,
exit code and resume verb for `bound_reached` and `action_performed`. `docs/` is gitignored but
tracked — **`git add -f`**.

- [ ] **Step 5: Commit in each repository separately, staging by explicit path**

---

## Gate (Phase 4)

The spec's own criterion — "parity twins byte-identical; no `ai_rfc` command remains in prompts or
docs; a campaign runs end to end" — plus the user's strengthening. **Nothing spends**;
`test_campaign_init_run_audit_analyze_round_trip` is unmarked and runs in the default selection.

1. `pytest tests/server/test_parity.py -q` — twenty twins, green.
2. `pytest tests/experiment/test_cli_campaign.py::test_campaign_init_run_audit_analyze_round_trip -q`
   — `integrity=True`.
3. The exec-the-shim test (Task 8 Step 1) — green.
4. The door grep, **escaped**, because an unescaped `.` matches the config key `"experiment.arms"`
   and can never go green:
   ```
   grep -rnE '(^|[^.[:alnum:]_])ai_rfc[ -][a-z]' --include='*.py' --include='*.md' \
        --include='*.json' --include='*.toml' ai_rfc/ plugins/ docs/parity.md \
        docs/experiment-protocol.md README.md | grep -v 'python -m ai_rfc'
   ```
   **This grep is not the criterion, and "zero hits" was never reachable.** Its predicate is
   `ai_rfc` + space-or-hyphen + a lowercase letter, which also matches every `from ai_rfc import …`
   and every prose noun (`the ai_rfc substrate`, `the ai_rfc plugin`). Task 9 measured **38 hits —
   16 retired verb forms in the three doc files, 12 import statements, 10 prose nouns**; Task 11
   re-ran it immediately before its own edits and got **37 (16 / 12 / 9)**, one prose line having
   moved between the two runs. Either way a gate stated as "zero hits" fails on 21 or 22 lines that
   are correct Python and correct English, so the grep is a **candidate list** and this is the
   predicate applied to it:

   > A hit is a defect when the word after `ai_rfc` **is hyphenated** (a retired leaf form such as
   > `claim-adjudicate` or `draft-render`) **or is a verb the root parser still owns** (`draft`,
   > `check`, `status`, `experiment`, …). An `import`, or a noun the parser does not own, is not.

   That flags **18** — derived, not measured: the 16 doc hits plus the two judgement lines below,
   every import and every remaining noun falling outside it. It misses none of the 16. Both
   judgement lines **stay**, so the gate's expected surviving set is exactly these two:

   - `ai_rfc/lifecycle/profile.py:10` — "the ai_rfc **experiment** harness", a prose noun colliding
     with a real verb name;
   - `ai_rfc/experiment/metrics.py:182` — a comment naming arm C's `ai_rfc draft checkpoint` with
     `python -m` elided, a genuine door reference the audit still has to match.

   Re-measured after Task 11: **21 hits, of which the predicate flags exactly those two.** Outside
   these paths, `tests/driver/fixtures/` and `docs/experiments/` are recordings and are never
   edited to match a rename (M1).
5. `test ! -e .venv/bin/ai_rfc && test ! -e ~/ai-rfc-experiments/venv-optimize/bin/ai_rfc` (M7).
6. The 3.10 suite against **2086 passed / 11 skipped** (measured 2026-09-14 at Task 11; the 1859
   written here was CLI-2's figure and did not survive the row — Task 11 alone moved it by 12
   deletions and 1 addition); the 3.11 optimize selection against 222/2/2; the PANTHER door tests
   against 6.

A gate that fails gets **one** fix wave and **one** scoped re-review. If it still fails: write the
resume point, report the failing output verbatim, end the turn.

---

## Self-review against the spec

| §6 / D56 requirement | Task |
|---|---|
| core calls `write_checkpoint`, `run_gate`, the check API, `build`, `lint` in-process | T2, T3 |
| exit codes become return values; checkpoint stops collapsing | T3, T4 (U1) |
| `paths.resolve_context()` reads `AI_RFC_CONFIG` | T1 |
| the twenty parity verbs become grouped subcommands | T6, T7 (nineteen + U3) |
| `tools.py` and the grouped verbs call the same core; twins byte-identical | T5, T6, T8 |
| `render.py`'s slot tables and the guard families re-rendered | T9 |
| `experiment/config._SHIM` writes `bin/ai-rfc` | T8 |
| `docs/parity.md` gains the new verb column | T11 |
| `experiment-protocol.md` records the change | T11 |
| `claim adjudicate` becomes `claim check` | T6 |
| the explicit-path leaf verbs leave the operator's help | T7 (R3, D10: six) |
| D56: the `ai_rfc` script, shim and `prog` value retire | T8 (R11 adds the module) |
| D56: arm B's Bash family becomes `ai-rfc *` | T9 |
| D56: MCP tool names `ai_rfc_*` stay | not changed, by design |
| §8: parity twins for every folded verb | T5, T8 |
| user scope: `--panther-repo` retired | T10 (U4's cut line) |

**Open, and deliberately deferred with reasons:** the ten sibling `_report` helpers (`draft`,
`pipeline`, `server`, `forge`, `history`, `views`, `coverage`, `timeline`, `check`, `experiment`) are
bare `print(..., file=sys.stderr)` with no escaping, `forge/cli.py:173` interpolating
`head.stderr.strip()` raw. Tasks 6 and 8 route the two front doors this row touches through
`lifecycle/common.report` and Task 6 forbids a new copy (D14); the remaining eight belong to modules
this row does not otherwise open, and sweeping them would put edits in eight files outside the File
Structure for no test this row can write. Recorded as owed.

## The standing question, in every review brief

Per task and whole-branch: **which character or value under an author's or an agent's control reaches
a produced artifact unescaped, and what does the grammar of that artifact do with it?** On CLI-2 this
found a real defect in **nine of fifteen tasks**, every one in pre-existing code. Two generalisations
to apply rather than rediscover: a character enumeration is the wrong shape — `isprintable()` is a
predicate over a category where `shlex.quote` and a C0 list were enumerations of characters someone
thought of; and an `except` clause is the wrong granularity for deciding whether output is structured
— a clause catches a family, but "these line breaks are mine" is a property of a **raise site**.

CLI-3's artifacts for that question: the nineteen grouped verbs' argv and error text, the MCP tool
output the core returns, the regenerated `SKILL.md` and arm prompts, and `campaign.json`'s provenance
record.
