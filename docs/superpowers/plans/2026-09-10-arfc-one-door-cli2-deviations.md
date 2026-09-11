# CLI-2 deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-10-arfc-one-door-cli2.md`.
Three fields each: what the plan said, what the code or the tool showed, what I did.

Entry 0 holds the rulings carried into the row. D1–D14 were written in Phase 2, **before any task
ran**, from one `review-plan` invocation plus one adversarial re-read of the plan against the tree.
Later entries are added as tasks run.

---

## 0 — Rulings carried into the row

**R1 — Scope is both halves of D60.** *(User decision, 2026-09-09.)* CLI-2 delivers the driver **and**
the instrument split that re-hosts `ai-rfc experiment` over the shared launcher with its fake_claude
scenarios. Taking both means no spec deviation is needed and the duplicate-launcher problem the split
exists to kill actually dies.
*Cost if wrong:* the row is roughly twice a driver-only row. If it overruns, the natural cut line is
Task 14 (mounting `ai-rfc experiment`), which is the only task with no downstream dependent.

**R2 — Moved code is moved, not copied and not shimmed.** *(User decision, 2026-09-09.)* No re-export
stub anywhere in `ai_rfc/experiment/`. Every importer is updated in the same row, including the
3.11-only GEPA optimize track. A re-export stub is a backward-compatibility layer, which this codebase
forbids, and the preceding row found three copies of one revision join that had already diverged in
behaviour.
*Cost if wrong:* a missed importer is an `ImportError` at collection — loud. The dangerous exceptions
are the four filesystem path constructions (D1, and `runner.py:34` / `preflight.py:217`) and the 28
name-bound monkeypatches (D5), which fail silently; both are enumerated per task.

**R3 — Nothing spends, and the anticipated paid-run question does not need asking.** *(User decision,
2026-09-09, plus a measurement.)* The brief allowed for one paid run if a stub could not prove
resumability against a real kill. Verified instead: `tests/experiment/fake_claude/claude` already
implements the `checkpoint` (`:298-310`), `revision` (`:328-354`) and `tag` (`:355-366`) step kinds,
which are exactly the three on-disk facts `ledger.ClusterState.done` requires. The whole gate is
therefore reachable through `fake_claude`.
*Cost if wrong:* if a gate criterion turns out to need a real `claude`, stop, name the cost, and ask
once before spending anything.

**R4 — Sharing depth: one launcher, two loops.** *(User decision, 2026-09-09.)* `driver/session.py` is
the only spawn path. `driver/sweep.py` is production's loop; `experiment/per_cluster.py` keeps its
campaign loop but calls `run_session()`.
*Cost if wrong:* the two run layouts (spec risk 6) stay separate, so a future SP7d must still unify
them. The alternative merges them now at the price of re-threading 28 monkeypatch sites through a hooks
interface and pulling SP7d work into this row.

**R5 — Layering: `driver/` is the lower layer. A deliberate extension of spec §5's module table.**
*(User decision, 2026-09-09.)* Spec §5 names five movers. `enforcement.py:25` imports `ArmProfile` from
`arms.py` and `render.py` is arm-keyed throughout (`SLOT_TABLES` per arm, `render_loop(arm)`,
`arm_prompt`), so the table read literally would leave `driver/` importing the instrument it was split
out of. `arms.py` and `render.py` therefore move too, `driver/__init__.py` defines `DriverError`, and
`experiment/` imports **from** `driver/`, never the reverse — the same fix CLI-1's D7 applied to
`toolchain.py`, and what `experiment/__init__.py:6` already promises.
Measured supporting fact: **no** `ai_rfc/lifecycle/` module imports `ai_rfc.experiment` today; the
dependency already runs the other way (`experiment/config.py:25`, `cli.py:23,24`, `workspace.py:25-27`,
`preflight.py:23`, three under `optimize/`). `driver/` sitting *below* lifecycle is nonetheless new.
*Cost if wrong:* two more large modules move (186 + 700 lines) with ~24 extra import sites.

**R6 — `experiment/driver.py` is renamed to `experiment/campaign_runs.py`.** *(User decision,
2026-09-09.)* It is the campaign's frozen run-order runner (`pending_runs`, `launch_pending`) — a
different sense of "driver" from the new package. Six importers update in the same task.
*Cost if wrong:* a mechanical, fully greppable rename; reverting is one `git mv` plus six lines.

**R7 — Sequencing: SP7c landed before CLI-2, inverting spec D55.** *(User decision, 2026-09-09.)*
CLI-2 inherits a **landed** consolidation hook, not a planned one. Nothing in the plan may assume
`sweep.next_round()` is unwritten.
*Cost if wrong:* none identified; the inversion is recorded so a reader of D55 is not misled.

**R8 — The brief's import-map premise is corrected by measurement.** The brief states "seventeen files
import the modules you are moving — ten under `ai_rfc/` including `ai_rfc/config.py`". Measured by an
AST sweep over every `.py` in the repo: **9 files under `ai_rfc/`, 9 test files, 40 import statements**,
and **`ai_rfc/config.py` imports nothing from any of them** — its `consolidation` hit is a schema help
string (`config.py:183`) and its `arms` hits are `experiment.arms` config *keys* (`:244, 607, 687`), not
module references. The measured map governs.
*Cost if wrong:* none — the measurement is reproducible and the brief's own instruction was to verify
the count with a grep before sizing the work.

**R9 — Plan-mode transplant.** The plan was written under plan mode, which permits writing only the
harness plan file. On approval it was copied verbatim to
`docs/superpowers/plans/2026-09-10-arfc-one-door-cli2.md`, this log was opened beside it, and both were
committed in PANTHER with `git add -f` **before Task 1 ran**. The single `review-plan` invocation was
made against the harness file and is **not** repeated after the transplant.
*Cost if wrong:* none to the code; the risk is a reader assuming the docs copy was reviewed
independently. It was not — it is byte-identical to the reviewed file.

**Operational hazard noted at the Phase 0 gate.** Peer session `iut-ai-rfc-ad` is live in this same
worktree. Both repositories were clean at the gate, so no uncommitted `ai_rfc/experiment/` edits
existed. `git status -sb` is checked in both repositories immediately before every commit, and BASE is
recorded before every dispatch.

**Baselines measured at Phase 1 (2026-09-09), all three reproduced from the brief's figures.**
ai_rfc suite under 3.10: **1472 passed, 11 skipped** (67.93 s). PANTHER door tests: **6 passed**.
The 3.11 optimize selection: **222 passed, 2 skipped, 2 deselected** (59.98 s), taken only after
`import ai_rfc` succeeded from a cwd outside the package and the `grep -c Skipping` probe printed `0`.
**This row moves modules the 3.11 track imports, so a red there afterwards is this row's, not
pre-existing.**

---

## D1 — `ai-rfc init` breaks silently, and the plan never named the file

**Plan said.** Move `ai_rfc/experiment/prompts/` into `ai_rfc/driver/prompts/`, listing only
`render.py:28`'s `PROMPTS = Path(__file__).parent / "prompts"` as the consumer to check.

**Code showed.** `ai_rfc/lifecycle/workspace.py:35` is
`PROMPTS = Path(__file__).resolve().parents[1] / "experiment" / "prompts"`, and `:36`'s `DRAFT_SKELETON`
is read at `:223` by `string.Template(DRAFT_SKELETON.read_text())`. That module **does not move**, so the
bare move gives `ai-rfc init` a `FileNotFoundError` at scaffold — with no `ImportError` anywhere to warn
a reader, and no existing test covering it.

**What I did.** Added Task 2 Step 2, which rewrites `workspace.py:35-36` to
`Path(__file__).resolve().parent / "prompts"` and requires a RED test asserting `ai-rfc init` scaffolds
a draft, seen failing after Step 1 and before Step 2. Added `lifecycle/workspace.py:35` to the plan's
"fails silently" table.
*Cost if wrong:* none — the fix is a one-line path change beside its only reader.

## D2 — `draft-skeleton.md` is a substrate file, not an experiment prompt

**Plan said.** All six prompt templates move to `ai_rfc/driver/prompts/`.

**Code showed.** `draft-skeleton.md`'s only reader in the tree is `lifecycle/workspace.py:36,223`;
`render.py` never touches it. `workspace.py:31-34` already documents the arrangement as "a layering
inversion the substrate cannot fix on its own", and its semantically-bound sibling constant
`SKELETON_REFERENCES` (`workspace.py:43`, consumed by `toolchain.py:24,116,119`) already lives in
`lifecycle/`. The other five files are genuinely render's (`loop.tmpl.md`, `consolidation.tmpl.md`,
`task.md`, `task-consolidation.md`, `task-interview.md` — the last read only at `render.py:428`).

**What I did.** Ruled that `draft-skeleton.md` moves **sideways** to `ai_rfc/lifecycle/prompts/`,
resolving the documented inversion rather than relocating it. Consequence recorded: `experiment/prompts/`
ends up empty, so `pyproject.toml:38`'s `"ai_rfc.experiment" = ["prompts/*.md"]` is **replaced** by
`"ai_rfc.driver"` and `"ai_rfc.lifecycle"` entries, not joined by them, and the empty directory is
deleted. Added `mkdir -p` before the `git mv`, which otherwise fails on a missing destination directory.
*Cost if wrong:* a wheel build would ship a glob matching nothing. No test would catch it, because
editable installs and the whole suite read the source tree directly.

## D3 — A byte-for-byte pin test ties the move to a shipped skill

**Plan said.** Nothing. The plan listed no coupling between `render.py` and the bundled plugin skills.

**Code showed.** `render.py:81` embeds the literal `ai_rfc/experiment/prompts/loop.tmpl.md` inside
`SKILL_FRONTMATTER`, and `tests/experiment/test_render.py:35` asserts the **committed**
`plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` equals
`SKILL_FRONTMATTER + render_loop("interactive")` byte-for-byte.

**What I did.** Added Task 2 Step 5: update the literal **and** regenerate the shipped skill with
`python -m ai_rfc.experiment render` in the **same commit**. Recorded the two failure modes — update
without regenerating and the pin test fails; skip the literal and the test passes while a shipped skill
documents a path that no longer exists. Also recorded that
`plugins/ai-rfc/skills/ai-rfc-editorial/` needs **no** edit: it names no path, and `render.py:50` reaches
it by tuple against a caller-supplied `plugin_root` (`render.py:617,653`), never `__file__`.

## D4 — Four modules import `ExperimentError`, not one

**Plan said.** "`stream.py:14` `from . import ExperimentError` → `from . import DriverError`."

**Code showed.** `arms.py:18`, `render.py:26`, `stream.py:14` **and** `driver.py:15` all carry
`from . import ExperimentError`. Three move into `driver/` and one is Task 3's rename.

**What I did.** Corrected Task 1 Step 3 to name `arms.py:18` and `stream.py:14`, and Task 2 Step 1 to
name `render.py:26`, each with "rename every raise in the file". Recorded **why this would have passed
the suite**: `ai_rfc/experiment/__init__.py` holds only `DEFAULT_MODEL`, `EFFORTS` and `ExperimentError`
and imports no submodules, so the upward import creates no runtime cycle and no test failure — it merely
re-creates the inversion R5 exists to remove. Added Task 1 Step 5a to convert the moved tests'
`pytest.raises(ExperimentError)` assertions, which is CLI-1's D2 class of follow-on.

## D5 — The monkeypatch count was wrong three ways, and every error fails silently

**Plan said.** "Sixteen name-bound patches": 8 `spawn`, 2 `consolidation_due`, 6 `_run_consolidation`.

**Code showed.** **28 patch sites**, and two of them are shared helpers:

| Target | Sites |
|---|---|
| `spawn` in `test_per_cluster.py` | `130, 579, 896, 1113, 1160, 1243, 1349, 1466` |
| `consolidation_due` in `test_per_cluster.py` | `946, 975, 1004, 1045, 1074, 1161, 1203, 1245, 1275, 1310, 1350, 1383` |
| `_run_consolidation` in `test_cli_campaign.py` | `480, 498, 525, 550, 576, 626, 649, 688` |

`:130` is not a per-test patch — it lives inside the helper `_stub_spawn` (defined `:100`), invoked from
**31 call sites**, so its signature governs ~31 tests. `:896` is inside `_record_revisions` (`:865`).
Ten of the twelve `consolidation_due` sites and two of the eight `_run_consolidation` sites use the
**multi-line** `monkeypatch.setattr(` form with the target on the following line, which is why a
single-line grep undercounts them. There are **zero** string-path `monkeypatch.setattr("ai_rfc…")`,
`mock.patch` or `patch.object` sites in that file, so the enumeration is complete.

**What I did.** Replaced Task 7 Step 4 with the full table, flagged the two helpers as the place to
start, and required that `per_cluster` import the **name** `run_session` rather than a module alias —
a module-qualified access silently detaches all 28.
*Cost if wrong:* a detached patch runs the **real** spawner while the test still passes its other
assertions. This is the single largest silent-failure surface in the row.

## D6 — Four line ranges were off by one or more

**Plan said.** `spawn.py:61-71`; `lifecycle/run/cli.py:67-97`; `per_cluster.py:672-679`;
`config.py:679` re-serialises `sessions.profile`.

**Code showed.** `spawn.py`'s try/except is **61–70** (`:71` is the dedented `return`; `grep -n finally`
returns zero, so the "no finally" claim itself is correct). `run/cli.py`'s stage loop is **67–92**
(`:93` is post-loop). `per_cluster.py`'s cluster attempt is **672–681** (`:679` is mid-kwargs, inside
`spawn(`'s argument list). `config.py:679` is `consolidate_every`; **`sessions.profile` re-serialises at
`:680`**.

**What I did.** Corrected all four in place. Also recorded that `tests/experiment/test_enforcement.py`
and `test_stream.py` build the guard path at `:16`/`:23` but *use* it at `:89-90`/`:79-80`, and instructed
anchoring edits at the `GUARD = …` line — an edit anchored at the use site lands inside an argument list.

## D7 — The conventions test has two exclusion lines

**Plan said.** "`tests/substrate/test_cli_conventions.py:145-151` — its rglob excludes `experiment/`."

**Code showed.** `test_every_cli_module_on_disk_is_registered` spans `136-151`. `:148` excludes the root
door (`path != PACKAGE_ROOT / "cli.py"`); **`:149`** carries
`{"server", "experiment"} & set(path.relative_to(PACKAGE_ROOT).parts)`. The assert is `:151`.

**What I did.** Narrowed Task 14 to edit `:149` only, to `{"server"}`, with an instruction to say why in
the test's docstring. Also recorded that `experiment/cli.py` carries `prog="experiment"` at `:708` and
dispatches with a hand-written `elif` chain from `:1213`, and that `configure`/`run`/`main` wrap that
chain rather than rewriting it into a table in this task.

## D8 — Three optimize-track imports are relative, not absolute

**Plan said.** Task 3 would find `optimize/evaluator.py:36` by the absolute dotted path.

**Code showed.** `optimize/evaluator.py:36` is `from ..driver import launch_pending`;
`optimize/apply.py:30` and `optimize/codec.py:25` are `from ..render import …`;
`optimize/claude_cli.py:21` is `from ..stream import …`. `experiment/cli.py:1325` is `from .driver
import launch_pending`, relative **and** function-local. `experiment/cli.py:623` is a function-local
`from .consolidation import consolidation_due`.

**What I did.** Named every one explicitly in Tasks 1–3, and flagged the two function-local imports as
invisible to a header-only scan. A grep for the absolute dotted form finds none of them.

## D9 — Campaigns copy the templates, so the runtime blast radius is narrower than it looks

**Plan said.** Nothing; the plan treated the package prompt directory as the runtime source.

**Code showed.** `experiment/config.py:355-383` writes `prompts_dir / TASK_TEMPLATE_FILE` with
`write_bytes`, renaming `task.md` → `task.tmpl.md` and `task-consolidation.md` →
`task-consolidation.tmpl.md`. `campaign.prompts_dir` (`config.py:168-170`) is `self.dir / "prompts"`, a
per-campaign directory. `runner.py:174,270` read only the campaign copy.

**What I did.** Recorded it so a reviewer does not raise it as a missed breakage: already-frozen
campaigns are **unaffected** by the move, and only `campaign init` reads the package directory.

## D10 — Task 7's RED test was green against unfixed code

**Plan said.** Task 7 Step 1: "one session launched through the campaign path must produce the identical
argv the direct `run_session` call produces for the same inputs. This is the assertion that fails if a
second launcher survives."

**Code showed.** It is not. Both paths already bottom out in `arms.claude_argv` (`runner.py:171` →
`arms.py:165`), so the argv is identical **before** any re-hosting. The test would have passed against
unfixed code, which the brief defines as a stop — and SP7c shipped exactly this mistake three times in
one row.

**What I did.** Replaced the test: patch the name `per_cluster` will bind (`run_session`, imported by
name from `ai_rfc.driver.session`) with a recorder, drive one cluster attempt, and assert the recorder
was called with a `SessionSpec` whose `budget_usd == budget_left`. Before Task 7 that attribute does not
exist on `per_cluster`, so `monkeypatch.setattr` raises `AttributeError` — a real RED — and the
remaining-budget assertion is something only the shared path can satisfy. Added an explicit instruction
to stop if it fails for any other reason or passes.

## D11 — Moving tests strands their fixtures, and one of them is `autouse`

**Plan said.** Task 1 and Task 2 move six test modules into `tests/driver/` with no further conditions.

**Code showed.** `tests/experiment/test_stream.py:22` is
`FIXTURES = Path(__file__).parent / "fixtures" / "stream"` and `test_enforcement_corpus.py:29` is
`… .resolve().parent / "fixtures" / "enforcement"` — **both break on the move**. Worse,
`tests/experiment/conftest.py:113` defines `_toolchain_always_verifies` as
**`@pytest.fixture(autouse=True)`**, which simply stops applying to a test that has moved — a behaviour
change with no error. `test_render.py:180,195` use `parents[2]`, which resolves to the repo root at
either depth and is safe. This is CLI-1's D8/D13/D19 class of defect.

**What I did.** Added Task 1 Step 1a: run two named greps *first* and decide from the output. Default
ruling — move `fixtures/stream/` and `fixtures/enforcement/` with their tests and **append** any needed
shared fixture to `tests/conftest.py` (append, never overwrite: it already holds `pytest_addoption` for
`--update-goldens`, and losing it errors every golden test on an unknown flag, CLI-1 D9). If a moved test
needs the autouse fixture, replicate it in a new `tests/driver/conftest.py`. If any moved test requests
three or more conftest fixtures, **leave it in `tests/experiment/`** with updated imports. Recorded that
Task 1 Step 8's "a pure move changes no count" is unproven until this step is settled.

## D12 — Task 5's named mechanism cannot reach the child process

**Plan said.** Task 5 asserts "`AI_RFC_FAKE_SCENARIO=<path>` is honoured ahead of the derived path",
following spec §8, and adds "per-ordinal steps" without saying how the fake learns the ordinal.

**Code showed.** `runner.build_env:87-109` returns a **closed** environment — its docstring is "The
complete environment; nothing else is inherited". A test setting `AI_RFC_FAKE_SCENARIO` in its own
environment therefore never gets it into the fake. Task 5's RED (which spawns the fake directly) would
pass while Task 15 silently fell back to `default.json`. Separately, the fake replays every step on
every invocation (`claude:205`), so a two-cluster scenario would finish both clusters in session 1 —
making Task 15 Criterion 1 pass for the wrong reason.

**What I did.** Two rulings in a new Task 5 Step 0. **Ruling A — no env var:** keep the existing
derivation at `claude:464` (`run_id = workspace.parent.name`) and have the driver tests name the parent
directory so the lookup lands; making the env var work would require `build_env` to forward it, i.e. a
test hook in production code. Recorded as a deviation from spec §8's **letter**, not from a decision.
**Ruling B — the fake derives its ordinal from the workspace**, via `ledger.next_cluster(workspace)`,
exactly as a real agent would from its prompt; the fake already holds `self.ctx` over the workspace and
mutates it through `ai_rfc.server.core`. Rewrote Task 5's first RED to assert exactly one cluster is done
after the first invocation, and required `tests/experiment/` to be run before the full suite to confirm
existing one-ordinal scenarios are unaffected.

## D13 — Production had no prompt source and no drift baseline

**Plan said.** `SessionSpec` takes `prompt_file` and `task`; nothing said where `sweep` gets them, and
`record.py`'s `run.json` was to record "prompt drift" against nothing named.

**Code showed.** Campaigns write both at freeze into `campaign.prompts_dir` (`config.py:355-383`).
Production has no freeze step, and spec risk 5 requires "sessions render from the sealed prompts and
`run.json` notes drift" without saying against what.

**What I did.** Ruling C in Task 10 Step 0: `sweep` renders `render.arm_prompt("A", plugin_root)` and
`render.render_task(...)` from the package templates on each invocation, writes the system prompt to
`run_dir / "prompt.md"`, and `run.json` records the sha256 of both — *drift* means those digests differ
from the previous run's `run.json`. `plugin_root` for production is
`Path(driver.render.__file__).resolve().parents[2] / "plugins" / "ai-rfc"`, mirroring
`experiment/cli.py:187`. The `python` in `mcp_config` is `sys.executable`.
*Cost if wrong:* a deliberate prompt change is noted rather than refused; the spec reserves
`--reseal-prompts` for making it refusable, which is not this row's work.

## D14 — An interrupted run must not write `status.json`

**Plan said.** Nothing about when `status.json` is written.

**Code showed.** Spec §5's resume rule keys on its **absence**: `runs/<ts>/` without `status.json`
becomes `runs/<ts>.interrupted-<cause>/`. `runner.launch` writes it once at `:326-328` on the normal
path.

**What I did.** Ruling D in Task 10 Step 0: `sweep.run` must **not** wrap its loop in
`finally: write_status`; it writes only on a normal or stop-classified exit. Added Task 10 Step 5
requiring a test that a `KeyboardInterrupt` mid-sweep leaves the run directory **without**
`status.json`.
*Cost if wrong:* a `finally` would make Task 15 Criterion 2 structurally unable to observe a leftover,
and the gate would pass while resumability was broken.

---

## Deviation from spec §5's literal `plan_next` signature

**Spec said.** `plan_next(ws, cfg, ledger) -> Action`, described as pure.

**Reasoning.** A function handed a `Path` and called pure will read disk, and then the nine-row state
machine cannot be unit tested without a workspace per row.

**What I did.** Split it: `observe(ws, cfg) -> Observation` performs every disk and clock read
(stage states, ledger rows, `spent`, `attempts`), and `plan_next(obs, cfg) -> Action` is the pure table.
This is what makes Task 10 Step 1's nine table-driven tests real. Changes no spec decision.

---

# Execution-phase deviations (D15 onward)

D1–D14 above were written in Phase 2 from the single `review-plan` invocation, before any task ran.
What follows is the execution record: 15 tasks, 42 commits, `f24a16d..51033cc`. The full per-task
ledger — 59 rulings, 43 deferred minors, every RED and mutation — is the row's SDD workspace at
`panther/plugins/services/testers/ai_rfc/.superpowers/sdd/2026-09-10-arfc-one-door-cli2/progress.md`
(gitignored, deliberately kept).

## D15 — The row's central claim, earned and verified three ways

`grep -rnE "from \.(spawn|stream|enforcement|guard|arms|render|consolidation) import|experiment\.(spawn|stream|enforcement|guard|arms|render|consolidation)\b" ai_rfc/experiment/ --include='*.py'`
returns **zero**. The whole-branch review confirmed independently: `spawn(` has exactly **one** caller
(`driver/session.py:408`); `run_session` is the sole entry, at `sweep.py:1019`, `per_cluster.py:262,535`
and `runner.py:254`; and no `driver/` module imports `ai_rfc.experiment`. **One spawn path, no
re-export stub anywhere** — ruling R2 held.

## D16 — `driver/` ships twelve modules where spec §5's table lists eight

`arms.py` survives although the table folds it *into* `session.py`; `render.py`, `consolidation.py` and
the `printable` text predicate in `__init__.py` are absent from the table entirely. Ruling R5 chose this
before Task 1 (the instrument's rendering and arm profiles are the *lower* layer, not the instrument's),
and `enforcement.py:25`'s `ArmProfile` import made `arms.py` non-optional. The branch review judged the
result **a coherent layer, not accretion** — the import graph is acyclic and correctly tiered:
`__init__` ← `arms`/`stream`/`render` ← `enforcement` ← `session` ← `stop` ← `record` ← `sweep`.
*Unlogged until now; recorded here as a spec deviation rather than only as a ruling.*

## D17 — `StopReason` grew 9 → 13 across four tasks

`session_failed` and `consolidation_failed` (Task 10), `bound_reached` (Task 11), `action_performed`
(Task 12). Each is an event §5 names in prose but gives no table row, and each was justified against the
candidate members it could have borrowed. Task 11 set the guardrail — *the next member arrives with a
spec row or a D-number, not a docstring justification* — and Task 12's `action_performed` does **not**
meet it. See D22.

The branch review found the vocabulary coherent, with two observations: `action_performed` is decided by
**two** mechanisms (its own `_VERB = "next"`, and `stepping=True` rewriting `run → next` anyway), and six
of the thirteen members share one observable signature (exit 1 + verb `run` + resume-line-yes),
separable only by `status.json`'s `reason`. Neither has a behavioural effect.

## D18 — `plan_next` split into `observe` + a pure `plan_next`

Spec §5 writes `plan_next(ws, cfg, ledger)` and calls it pure. A function handed a `Path` and called pure
reads disk, and the nine-row table then cannot be unit-tested without a workspace per row. `observe(ws,
cfg)` takes every disk and clock read; `plan_next(obs, cfg)` is pure. Changes no spec decision.

## D19 — Three signatures beyond §5

`classify(result, *, seen=0)` — measured: without `seen`, a launch failure in a multi-session run reads
the **previous** session's success and returns `refused`, recreating D61's exact defect.
`resume_line(..., cluster_id, known_clusters)` — closed-set membership per the `_checked_cluster_id`
precedent. `exit_code(reason, *, strict_findings=False)` — §5 says both "build_failed → exit 1" and
"strict findings 3" for one reason covering three gates, and only the caller knows which fired.

## D20 — `budget_hit` consumes no attempt

The one call spec text does not settle. D61's "ended on its own" is ambiguous for a budget-capped exit,
so the tiebreaker is consequence: the sweep stops on `StopReason.budget` either way, so a consumed
attempt could only be spent against a **later, better-funded resume** — halting a cluster because the
operator's cap ran out rather than because it ever failed.

## D21 — No `AI_RFC_FAKE_SCENARIO`, against spec §8's letter

`runner.build_env` returns a **closed** environment ("nothing else is inherited"), so a variable a test
sets never reaches the child. A test spawning the fake directly would pass while the real driver fell
back to `default.json`. The existing `run_id = workspace.parent.name` derivation was kept and the tests
name the parent instead. A deviation from §8's **letter**, not from a decision.

## D22 — FOR THE USER: a spec D-row is owed, and only the user can add it

`bound_reached` and `action_performed` both exit **0**, which reinterprets §5's literal *"stopped with
work outstanding 1"* on precedent alone — the no-sessions boundary stop and CLI-1's `--until <stage>`
both already return 0 with work outstanding. And D59's *"Every stop prints the ledger and the exact
resume line"* is what **forces** `bound_reached` to be a new member: `done` is the one reason with no
resume line.

The behaviour is right and the reasoning is sound, so the code stands. **What is owed is a spec D-row
fixing reason, exit code and resume verb for both members**, plus amending §5's exit-code sentence to
"done or bound reached 0". That is a change to a decision the spec records, which this row's brief makes
a stop — so it is left to the user.

## D23 — Three further spec deviations the branch review found unlogged

- **§7 says "a missing toolchain skips `build` and says so".** That skip branch (`sweep.py:745`) **cannot
  fire**, because `config.py:642` defaults `toolchain` to a path so a loaded config never carries `None`.
  Fixed in the final wave by refusing an unprovisioned toolchain **before** any session spends
  (`sweep._require_toolchain`), and `doctor`'s now-untrue "draft builds will be skipped" corrected with
  it. `config.py:642` is **not in this row's diff** — the row *exposed* a pre-existing CLI-1 default by
  putting sessions inside `run`.
- **§8 names six fake_claude scenarios**; three are fake_claude-driven and three are unit-level only.
- **D59 names wall clock a stop condition**; `wall_clock` is implemented and tested but has **no
  production producer**, because spec §2's `sessions` table declares no wall-clock field. Wiring one
  would have invented config. Reachable through `sweep.run(deadline=…)`.

## D24 — §5's SIGTERM half is unimplemented

Task 4 closed the **SIGINT** orphan: `spawn` now walks SIGTERM → grace → SIGKILL → reap on an interrupt
and re-raises, so Ctrl-C no longer leaves a spending session. An **outside** `kill <pid>` still orphans
one: Python's default SIGTERM disposition terminates without unwinding, so no `except` or `finally`
inside `spawn` can run. The only real fix is a process-global `signal.signal` handler, which would mutate
any importing process's signal disposition as a side effect of a library call — it belongs at the CLI
entry point, and none exists.

## D25 — The standing question found a real defect in nine of fifteen tasks

Each was pre-existing code this row inherited rather than wrote, and **each was fixed with the grammar's
own emitter rather than a character filter**:

| Where | What the grammar did |
|---|---|
| `enforcement.py` | a space in a path word-split the guard hook's command → exit 127; since **exit 2 is the only blocking value**, the arm B/C Bash guard then silently permitted every call. Fixed with `shlex.join`. |
| `lifecycle/workspace.py` | the draft's title reached YAML frontmatter raw — a quote broke the build, a newline forged `obsoletes`/`submissiontype`. Fixed with `yaml.safe_dump`; 27 scalar shapes round-trip. |
| `campaign_runs.py` | `run_id` reached a path join **and** an operator line; measured to reach both, stopped only by an unrelated later guard. Fixed with `re.fullmatch` and an ASCII class. |
| `stop.py` | `shlex.quote` keeps a newline **inside** the quotes; then C0+DEL missed NEL, LS, PS, RLO, ZWSP. Fixed with `isprintable()`. |
| `sweep.py` | agent-written cluster ids reached four progress sinks; fixed at the **boundary**, one predicate covering all four. |
| `run/cli.py` | a `cluster:` bound forged `resume: ai-rfc run --config /tmp/evil.yaml`; and the sessionless refusal offered an **unquoted** path that the root parser rejects. |
| `experiment/cli.py` | `_arms`' unknown-arm branch joined operator text raw where its three siblings use `!r`. |

**The generalisation, from Task 9:** `shlex.quote` and then C0+DEL were both *enumerations of characters
someone thought of*; `isprintable()` is a **predicate over the category**. And from Task 11: **an
`except` clause is the wrong granularity for this decision — a clause catches a family, but "these line
breaks are mine" is a property of a raise site.**

**Still open, and deliberately not fixed here:** argparse's own `'unrecognized arguments: %s'` uses `%s`
not `%r` and forges a stderr line — reproduced on `doctor` and `pipeline` as well as `experiment`, so
**door-wide and pre-existing**. The remedy is **one site** (override `error()` on the root parser in
`ai_rfc/cli.py`), not a sweep. And ten sibling `_report` helpers are bare `print(..., file=sys.stderr)`
with no escaping, `forge/cli.py:173` interpolating `head.stderr.strip()` raw. This row hardened two
boundaries and left ten.

## D26 — The gate PASSES, with one qualification stated rather than implied

All three of spec D60's criteria, driven through the production door (`ai-rfc init` then `ai-rfc run`),
every session on `fake_claude`, **nothing spent** — ruling R3 held end to end.

Criterion 2 kills **session 2**, not session 1, because cost only reaches the transcript in a result
event: killing during session 1 would have made *"`spent()` still counts the killed run"* vacuous.
Criterion 1 verifies the tag is **annotated** via `git cat-file -t`, because `ledger._tags` accepts a
lightweight one. Criterion 3 checks the resume line byte-for-byte **and** round-trips it through
`cli.build_parser()`.

**The qualification:** `check --strict` and `lint --strict` ran the substrate's real checks — lint failed
first and had to be earned — but `build` ran against a no-op `make`/`kramdown-rfc`, so **"build: clean"
certifies the gate's wiring, not a compiled draft.**

## D27 — A method correction worth keeping

The gate's first account of D23's toolchain defect ("every session fails at launch as `session_failed`")
**was measured** — but against `fake_claude`, which resolves context in `Session.__init__` and dies
before emitting. The real MCP server resolves **per call**, so it advertises its tools and then fails
each one. `server/cli.py:256` *does* resolve at startup, but that is the CLI verb arm, not the MCP arm —
**which is precisely why naming the binary that produced an observation matters.**
