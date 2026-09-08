# CLI-1 deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-03-arfc-one-door-cli1.md` (`fa3e2df69`).
Three fields each: what the plan said, what the code or the tool showed, what I did.
Entries 0 to D22 were written in Phase 3, before any task ran, from the single `review-plan`
invocation. Full findings with evidence: `.superpowers/sdd/arfc-cli-track/cli1-review-plan-findings.md`.

---

## 0 — Rulings carried into the row

**R1 — the CLI-track brief's second "SP7b landed" artifact check is unsatisfiable as worded.**
The brief asks that the submodule README's tool list name `draft render` and `structure upsert`. It
does not, and cannot: SP7b's own deviation D15 records that the root `README.md` has no per-verb
table, so its Task 10 Step 4 named three files and exact lines instead. Substitute evidence, all
positive: `docs/parity.md:33-34` carries the `ai_rfc_structure_upsert` and `ai_rfc_draft_render`
rows; `README.md:65-66` reads "twenty workspace-level verbs" where D15 recorded "eighteen"; SP7b's
D32 records Task 10 landing as `aef9d07` with the row gate at 1300 + 11 and the MARK gate clean; the
recorded gitlink equals the checkout head and both repositories are pushed. Treated as PASS.
*Cost if wrong:* CLI-1 builds on an unfinished SP7b surface. Retired by measurement — the Phase 1
baseline came back at exactly 1300 + 11, SP7b's own gate number.

**R2 — the 3.11 hidden-`.pth` trap is live, and `chflags` is not a fix.** Both `.pth` files in
`.superpowers/venv-optimize` carry the macOS hidden flag, so Python 3.11 skips them. My first
ruling said `chflags nohidden` repaired it; **that was wrong and is retracted.** A watcher scoped to
the project directory re-hides every `.pth` under the worktree within about 90 seconds, so the repair
was gone before the runs it was meant to enable. Reported by peer session
`gepa-optimize-ai-rfc-skills`, then confirmed here: both files show `hidden` again. The decisive
extra fact is that the **3.10** venv's `.pth` files are hidden too and its suite still passes 1300 —
Python 3.10.12 does not honour the flag, 3.11.9 does. The fix is to move the 3.11 venv outside the
worktree; that is a "For the user" item, not CLI-1 work. *Cost if wrong:* none to CLI-1, whose
signal is the 3.10 suite.

**R3 — `panther_repo` / `PANTHER_REPO` retirement belongs to CLI-3. Settled by the user.**
The spec assigns "R2/R8 retirements" to CLI-3 (spec `:199`) and never mentions
`optimize run --panther-repo`; the CLI-1 plan drops the flag only from `workspace prepare` (`:1757`)
and its own self-review defers `PANTHER_REPO` to CLI-3 (`:2754`); the CLI-track brief's roadmap row
claimed CLI-1. The brief's precedence rule gives the roadmap authority over sequencing only, not
scope, so the spec wins. **Consequence: the brief's cross-track hazard paragraph is void for CLI-1 —
GEPA-PILOT's `--panther-repo <worktree>` keeps working.** Re-check at CLI-3. Surface for that row,
measured twice: 140 hits / 19 files for
`grep -rIn 'panther_repo\|panther-repo\|PANTHER_REPO' ai_rfc tests`.

**R4 — Task 7's `docs/parity.md` anchor is stale.** SP7b grew the file by 19 lines in exactly the two
regions a parity note would live. Carried into the review as focus input; resolved as D14.

---

## D1 — Registered verbs must be `<package>/cli.py`, so each lifecycle verb becomes a sub-package

**Plan said.** Register seven flat modules: `ai_rfc.lifecycle.{config_cmd, init, run, status, verify,
doctor, toolchain_cmd}`.

**Code showed.** `EntryPoint.module` is contractually "the dotted path of the `cli` module, not of
its package — the `__main__` guard test derives that name by trimming one segment"
(`ai_rfc/entrypoints.py:40-41`). Two tests enforce it:
`tests/substrate/test_cli_conventions.py:136-151` asserts **set equality** between
`{entry.module for entry in ENTRY_POINTS}` and every `cli.py` `rglob` finds (excluding the root door
and anything under `server/` or `experiment/`), and `:48-58` derives `<package>.__main__` and
imports it. All ten existing packages comply, each carrying `cli.py` and `__main__.py`. Seven flat
modules would fail both tests.

**What I did.** Put the decision to the user with three options; they chose one sub-package per verb.
Added a "Registered-verb module layout (D1)" clause to Global Constraints and rewrote the File
Structure table and Tasks 2, 4, 5 and 6 accordingly: each verb is
`ai_rfc/lifecycle/<verb>/{__init__,__main__,cli}.py`, registered as `f"{PACKAGE}.lifecycle.<verb>.cli"`,
with shared code staying as flat modules (`lifecycle/{workspace,common,profile}.py`) because they
register nothing. Intra-package imports in every code block moved one level deeper (two dots for
shared modules, three for the package). The flatter alternative `ai_rfc/<verb>/cli.py` was rejected:
`ai_rfc/config/` would collide with the `ai_rfc/config.py` module Task 1 creates.
*Cost if wrong:* about 21 small files; if flat modules are later preferred, the two tests must be
amended instead.

## D2 — `ToolchainError`, and the false premise the plan used to justify it

**Plan said.** Task 6 Step 4's code imports `from ..experiment import ExperimentError`, while its
trailing note instructs changing `provision`'s raises to a new `ai_rfc.toolchain.ToolchainError`
"— `experiment/config.py`'s `init_campaign` catches it the same way".

**Code showed.** Self-contradictory, and the premise is false three ways. `init_campaign` calls
`verify`, not `provision` (`experiment/config.py:295`); `config.py` has **no** `except
ExperimentError` at all (its only handler is `except OSError` at `:232`); the real `provision` call
site is `experiment/cli.py:1060`, guarded by `except (ExperimentError, OSError)` at `:1290`.
Further, `provision` calls `_git`/`_run_git`, so `ExperimentError` leaks out of it regardless, and
`verify` itself catches `ExperimentError` at `toolchain.py:349`.

**What I did.** Replaced the note with a complete ruling: define `ToolchainError(RuntimeError)` in
the moved `ai_rfc/toolchain.py`, convert its eleven raises, and land four consequences in the same
commit — `toolchain.py:349`'s internal handler, wrapping the `_git`/`_run_git` calls (which raise
`LifecycleError` after Task 4's move), `experiment/cli.py:1290` gaining `ToolchainError`, and
`tests/cli/test_toolchain.py:115,183` changing their `pytest.raises`. Deleted the
`ExperimentError` import from the new verb module. *Cost if wrong:* a missed handler turns a
reported `error:` line into a traceback; the four sites are enumerated so the fix is mechanical.

## D3 — Task 6's discovery grep misses the one importer that matters

**Plan said.** A grep pattern that finds every module to re-point after the `profile.py` move.

**Code showed.** Re-ran the plan's verbatim pattern: for `ai_rfc/experiment/optimize/claude_cli.py`
it returns **only line 5**, a docstring sentence matched because the `.` in `experiment.profile`
matches a space. Line 20, the real `from ..profile import profile_env`, scores zero.

**What I did.** Replaced the pattern with an escaped one that adds `from \.\.profile`, `profile_env`
and `default_root`, and — because a grep alone is not evidence — enumerated all four importers and
all eight toolchain importers explicitly with `file:line`. Left an instruction not to rely on the
grep. Untouched, this would have silently broken the GEPA-NO-KEY proposer.

## D4 — `profile_env` is a fourth public function the plan predates

**Plan said.** The moved module offers `{init_profile, login_command, profile_dir}`.

**Code showed.** `experiment/profile.py` defines `login_command:19`, `init_profile:24` and
**`profile_env:41`**, a GEPA-NO-KEY addition. `profile_dir` is not defined there at all — it lives in
`experiment/paths.py:16`. Importers are four, not two.

**What I did.** Corrected the Interfaces block to name `profile_env`, listed all four importers, and
noted that `profile_dir` moves into `ai_rfc/config.py` rather than travelling with the module.

## D5 — `doctor`'s profile check passes the wrong argument

**Plan said.** `init_profile(directory.parent if directory.name == "profile" else directory)` and
`login_command(directory.parent)`.

**Code showed.** Both functions take the experiments **root** and derive `root / "profile"`
themselves (`profile.py:21,33`, `paths.py:16-18`). Only `profile_env(profile)` takes the profile
directory. The plan's two calls therefore disagree whenever the profile directory is passed directly,
printing a wrong `CLAUDE_CONFIG_DIR` in user-facing login instructions.

**What I did.** Rewrote `_profile` to derive the root once and pass it to both, and to return a
warning `Check` when a configured `sessions.profile` is not named `profile` — the case neither
function can express. Explicitly forbade changing the signatures in Step 1: the move is a move.

## D6 — Moving `toolchain.py` silently blinds six monkeypatch sites

**Plan said.** "Expected: all PASS (a pure move)."

**Code showed.** `experiment/config.py:23` binds the module **object** it later calls `verify` on,
and six sites patch `verify` on `ai_rfc.experiment.toolchain`: `tests/experiment/conftest.py:178`,
`test_config.py:152, :172, :389`, `test_cli_optimize.py:703`, `test_toolchain.py:175`. Re-pointing
`config.py` without re-pointing them makes the patches invisible, so those tests run the **real**
`verify`, which builds drafts.

**What I did.** Enumerated all six in Step 1 with a re-point instruction, added the three test files
to Task 6's Files and staging lists, and added a proof step: a grep for the old dotted path must
return zero hits before committing.

## D7 — The move inverts the layering it exists to fix

**Plan said.** Moving `toolchain.py` out of `experiment/` is "the first step of the D58 split".

**Code showed.** The module reaches back into the instrument twice: `toolchain.py:23`
`from . import ExperimentError` and `:24`
`from .workspace import TEMPLATE_COMMIT, TEMPLATE_URL, _git, _run_git`. Left alone, a top-level
`ai_rfc/toolchain.py` would import `ai_rfc.experiment`, contradicting
`experiment/__init__.py:6` ("Nothing here is imported by the plugin or the substrate").

**What I did.** Pointed `:24` at `ai_rfc/lifecycle/workspace.py`, where Task 4 already moves those
four names — production to production, and no cycle, since `lifecycle/workspace.py` does not import
`toolchain`. `:23` is removed by D2.

## D8 — `tests/experiment/test_per_cluster.py` breaks and is in no list

**Plan said.** Task 4 replaces `fixture_target` and drops `prepare`'s `panther_repo`, listing
`tests/experiment/{conftest,test_workspace}.py`.

**Code showed.** `fixture_target` is a plain module function (`conftest.py:80`), not a fixture, with
**16 call sites across three files**. The third is `tests/experiment/test_per_cluster.py`, which
imports it at `:15` and calls it at `:30` inside
`prepare(..., panther_repo=panther_repo, ...)` — both of which this task changes. The file is in
neither the Files list nor the staging list.

**What I did.** Added it to both, enumerated all 16 call sites by line, specified the rewritten
`wide_pristine` call, and added a `grep` verification for `fixture_target` and `panther_repo`.

## D9 — `tests/conftest.py` already exists

**Plan said.** "move both into a shared `tests/conftest.py` at the repository root", which reads as
creating it.

**Code showed.** The file exists and holds `pytest_addoption` registering `--update-goldens`.

**What I did.** Changed the instruction to **append**, in both Task 4 and Task 5, and said why:
overwriting removes the option and errors every golden test on an unknown flag.

## D10 — The dispatcher tests are in a file the plan misnames and never stages

**Plan said.** SP1's `test_help_lists_every_verb_in_registration_order`,
`test_an_unknown_verb_exits_two` and `test_a_verb_forwards_its_arguments_untouched` are "in
`tests/cli/` or `tests/substrate/test_cli_conventions.py`".

**Code showed.** All three are in `tests/substrate/test_root_cli.py` at `:13`, `:33` and `:44`. That
file appears in neither Task 2's Files list nor its staging list.

**What I did.** Named the real file with line numbers, added it to both lists, and additionally
documented the two conventions tests every new row must satisfy unweakened
(`test_every_entry_point_reports_its_version`, `test_a_malformed_invocation_exits_two_everywhere`),
with the instruction that a failure there is fixed in the new module, never in the test.

## D11 — The README edit target does not exist

**Plan said.** "replace the Environment contract table's `PANTHER_REPO` row with `AI_RFC_CONFIG`".

**Code showed.** `## Environment contract` is a heading (`README.md:38`) whose body `:40-58` is
**prose, not a table**, and `PANTHER_REPO` appears **nowhere** in the file — it is already retired,
and `tests/server/test_plugin_manifest.py:15-22` asserts its absence from command documentation.

**What I did.** Rewrote the step to **add** `AI_RFC_CONFIG` to the prose and extend the existing
`AI_RFC_WORKSPACE` sentence at `:42`, with an explicit instruction not to introduce a
`PANTHER_REPO` row. Consistent with R3, which leaves that retirement to CLI-3.

## D12 — `unprocessed_clusters` is a field, not a function

**Plan said.** Task 3 Files: `ai_rfc/draft/completeness.py` (`unprocessed_clusters`).

**Code showed.** It is a dataclass field of `CompletenessReport` (`completeness.py:223`, populated
`:269`). The task's own Interfaces block already names the right anchors, `checkpoint_records:60`
and `build:231`.

**What I did.** Corrected the Files entry to name the field and redirect re-anchoring to the two
functions.

## D13 — `tests/experiment/test_profile.py` is orphaned by the move

**Plan said.** Task 6 moves `test_toolchain.py` but not this file.

**Code showed.** It imports all three names from `ai_rfc.experiment.profile` at `:5`.

**What I did.** Added `git mv tests/experiment/test_profile.py tests/cli/test_profile.py` to the move
list, its new import to the rewrite enumeration, and the file to the staging list.

## D14 — `docs/parity.md`'s anchor is ambiguous, not merely stale (closes R4)

**Plan said.** "one sentence under the table".

**Code showed.** SP7b grew the file to 75 lines. "Under the table" now resolves to either line 34
(end of the 20-row tool table) or line 42 (end of the arm-C paragraph that SP7b inserted between).

**What I did.** Mapped the file's current structure into the step and named line 34 as the anchor,
with an instruction to re-measure before editing.

## D15 — `completeness.build` must not gain a parameter

**Plan said.** "add the workspace root parameter … or derive the root as `checkpoints_dir.parent`".

**Code showed.** `build` takes five paths (`completeness.py:231-237`) and its only caller passes them
at `draft/cli.py:267-273`. `ai_rfc/draft/cli.py` is not in Task 3's Files list — Task 2 already
rewrote it, and two tasks editing one file is the collision the task ordering exists to prevent.

**What I did.** Made the `checkpoints_dir.parent` derivation the instruction rather than an option,
and said why.

## D16 — `--until` offers a stage the walk always skips

**Plan said.** Choices are "`history`, `timeline`, `views`".

**Code showed.** The comprehension as written yields `history, forge, timeline, views` — `forge` is a
fourth DETERMINISTIC stage at ordinal 2, before `mining` at 5. The walk skips it via `is_optional`,
so `--until forge` would never fire the stop and `run` would silently continue to the boundary.

**What I did.** Added `and not is_optional(s)` to the choices comprehension and rewrote the trailing
note to explain the interaction. Also recorded there that the walk itself is **correct** as written
(`pin` falls through the first branch, `forge` is skipped, `mining` breaks) so a later reviewer does
not "fix" it.

## D17 — Lifecycle rows must be contiguous

**Plan said.** Tasks 4, 5 and 6 say "register" without saying where.

**Code showed.** `test_entries_sharing_a_section_are_contiguous`
(`tests/substrate/test_cli_conventions.py:163-175`) requires entries sharing a section to be
adjacent, because declaration order is help order.

**What I did.** Specified the insertion point in each of the four registration instructions:
`config` first, then each new row immediately after the previous lifecycle row.

## D18 — The PANTHER test names three things that do not exist

**Plan said.** A test using a `cli_runner` fixture, a `capsys_output_of` helper and a `panther_cli`
import.

**Code showed.** `tests/unit/test_cli/test_ai_rfc_commands.py` is 57 lines, 5 tests, **zero
fixtures**; no `cli_runner` is in scope, no `capsys_output_of` exists anywhere under `tests/`, and
the module imports `cli` from `panther.cli.core.main`, constructing `CliRunner()` inline.

**What I did.** Rewrote the proposed test in the module's own style, listed the five existing test
names, and recorded that this module needs the sandbox **off** — its collection binds a socket
through `nicegui` and fails with `PermissionError: [Errno 1] Operation not permitted`, measured this
session.

## D19 — `toolchain_record` is defined twice

**Plan said.** Move the fixture up to the root conftest.

**Code showed.** Besides `tests/experiment/conftest.py:115` there is a module-local shadow at
`tests/experiment/test_workspace.py:370`. Moving only the first leaves the shadow in force for that
module.

**What I did.** Instructed deleting the shadow with the move and re-running that module specifically.

## D20 — Task 7 Step 1 is already done

**Plan said.** "If it still builds click passthroughs from `ENTRY_POINTS`, replace the body".

**Code showed.** `panther/cli/commands/ai_rfc.py` is already the 38-line single passthrough with
`import sys` at `:16`, a lazy `from ai_rfc.cli import main` at `:31` and `sys.exit(main(list(args)))`
at `:38`. `ENTRY_POINTS` has zero hits under `panther/` outside the submodule.

**What I did.** The step's condition already makes it safe; added the measurement so the implementer
confirms and reports a no-op instead of inventing an edit.

## D21 — Chained `cd … && git …` is refused by the worktree guard

**Plan said.** Task 6 Step 1 chains three `git mv` calls with `&&`; Task 7 Step 5 uses
`cd $AIRFC && git status --short`.

**Code showed.** The harness's worktree guard refuses git inside compound commands, loops, variables
and heredocs — observed twice this session on unrelated commands.

**What I did.** Split every such line into plain one-per-call commands with literal paths.

## D22 — The baseline is measured, not a placeholder

**Plan said.** Task 0 Step 2: "Write `N` into the commit message of Task 1 (baseline N)".

**Code showed.** Measured this session at `bc4a603`, sandbox off: **1300 passed, 11 skipped** in
160.21 s. PANTHER door tests: **5 passed**. The 3.11 optimize selection is **11 failed, 211 passed,
2 skipped, 2 deselected** — red before any CLI-1 work, cause identified in R2, owned by the GEPA
track, and explicitly not CLI-1's to fix.

**What I did.** Recorded all three in the track ledger. Task 1's commit message uses `baseline 1300`.
CLI-1's completion criterion for the 3.11 selection is **"no worse than the 11-failure baseline"**,
not "green", because the brief's "green" is unreachable for reasons predating this row.
