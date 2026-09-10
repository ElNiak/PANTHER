# CLI-2 — the autonomous driver and the instrument split

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ai-rfc run` drives model sessions per cluster until the reconstruction is done or must
stop, resumably; `ai-rfc next` performs exactly one action; and `ai-rfc experiment …` is re-hosted
over the same session launcher so exactly one spawn path exists.

**Architecture:** A new lower-layer package `ai_rfc/driver/` owns everything that launches and reads
a `claude -p` session. `ai_rfc/experiment/` (the three-arm instrument) becomes a consumer of it and
never the reverse. `driver/session.py` is the single spawn path; `driver/sweep.py` is production's
loop over `Layout`/`ReconConfig`/`ledger`; `experiment/per_cluster.py` keeps its own campaign loop
but every `prepare_run_argv` + `spawn` + `_session_cost` triple becomes one `run_session()` call.

**Tech Stack:** Python 3.10 (`stdlib` + PyYAML only in `driver/`), argparse, pytest + pytest-xdist.

**Spec:** `docs/superpowers/specs/2026-09-03-arfc-one-door-design.md` — §5 "The driver (CLI-2)" is
the module table and state machine this plan turns into tasks; D53–D61 and the CLI-2 gate row bind.

---

## Context

An operator today gets `ai-rfc run`, which performs `history`, `timeline` and `views` and then stops
at the mining boundary printing an instruction addressed to a human. Everything past that boundary —
one model session per cluster, consolidation rounds, the final check/lint/build — has no production
driver at all. The only code that launches a session lives in the experiment harness, is reachable
only as `python -m ai_rfc.experiment`, and orphans a spending `claude` process on Ctrl-C.

CLI-2 closes that gap and, in the same row, deletes the duplication rather than adding a second copy
of it. The spec's D58 requires production and the instrument to *share* the session launcher; the
2026-09-09 user ruling requires moved code to be **moved, not copied and not shimmed**, because the
preceding row found three copies of one revision join that had already diverged in behaviour.

---

## Measured baselines (Phase 1, 2026-09-09, this session)

| Signal | Command | Result |
|---|---|---|
| ai_rfc suite, 3.10 | `SSLKEYLOGFILE= <worktree>/.venv/bin/python -m pytest tests -q -n auto -p no:cacheprovider` (from submodule root) | **1472 passed, 11 skipped** in 67.93 s |
| PANTHER door | `SSLKEYLOGFILE= .venv/bin/python -m pytest tests/unit/test_cli/test_ai_rfc_commands.py -q -p no:cacheprovider` (worktree root) | **6 passed** |
| optimize, 3.11 | `SSLKEYLOGFILE= ~/ai-rfc-experiments/venv-optimize/bin/python -m pytest tests/experiment/optimize tests/experiment/test_cli_optimize.py -q -m "not slow" -p no:cacheprovider` | **222 passed, 2 skipped, 2 deselected** in 59.98 s |

The 3.11 interpreter was proved healthy first: `import ai_rfc` succeeds from a cwd outside the
package, and the `-v -c pass … | grep -c Skipping` probe printed `0`.

**This row moves modules the 3.11 track imports (`arms`, `render`, `stream` via
`optimize/claude_cli.py` and `optimize/{apply,codec}.py`). A red in the 3.11 selection after this
row is ours, not pre-existing.** Re-measure it after Task 2, Task 3 and at the gate.

---

## Global Constraints

- **Line length 88** (Black default). `black`, `isort --profile black`, `flake8 --max-line-length=88`,
  `mypy --follow-imports=silent` — **on the task's own files only**; the repository carries lint debt
  elsewhere.
- **Google-style docstrings** (Args/Returns/Raises) on every public function.
- `from __future__ import annotations` at the top of every new module — every neighbouring module in
  `ai_rfc/` uses it.
- **No backward-compatibility shims.** No re-export stub may survive in `ai_rfc/experiment/`. A
  `grep -rn "from .spawn\|from .stream\|from .enforcement\|from .guard\|from .arms\|from .render\|from .consolidation" ai_rfc/experiment/`
  returning a hit is a gate failure.
- **Fixed dates in every fixture.** No `datetime.now()` in a test's expected value.
- **No test needle may match a fixture's own name** — a test asserting on `"cluster-a"` must not use
  a fixture literally named `cluster-a`.
- **Every RED test must fail at the exact path the change addresses**, and must be *seen* failing
  before the implementation is written. A RED test that passes against unfixed code is a stop: the
  test is wrong, and a wrong test hides a wrong fix. SP7c hit this three times in one row.
- **Interpreters.** `<worktree>/.venv/bin/python` (3.10) for everything; `~/ai-rfc-experiments/venv-optimize/bin/python`
  (3.11) only for the optimize selection. **Never a pyenv shim** — its site-packages has no editable
  `.pth`, so subprocess tests die on `ModuleNotFoundError: No module named 'ai_rfc'` and look like
  real failures.
- **Every pytest and `python -m` invocation is prefixed `SSLKEYLOGFILE=` and runs with the sandbox
  off.** So do pip, nested git and pushes.
- **Git.** Stage by explicit path — never `git add -A` or `git add .`. Run `git status --short` in
  every repository touched before every commit; a live peer session (`iut-ai-rfc-ad`) shares this
  worktree, so also `git status -sb` immediately before committing. If a file you did not touch is
  already staged, commit with `git commit --only -m "<msg>" -- <your paths>` and confirm with
  `git show --stat HEAD`. Never `git stash` in this shared worktree, never amend a commit already on
  the branch, never `--no-verify`.
- **Commit messages.** ai_rfc: `type: lowercase summary`. PANTHER: `type(scope): lowercase summary`.
  Each ends with a blank line and `Claude-Session: https://claude.ai/code/session_015hMZpbY4dV6sizex6sdSBH`
  passed as a **second `-m`**. Confirm on the first commit with `git show -s --format=%B HEAD`.
- **`docs/` is gitignored but tracked in PANTHER** — plan and deviation-log commits need `git add -f`.
- **The worktree guard refuses git inside loops, variables, compound constructs and heredocs**, and
  refuses any command whose target is computed at runtime. Run plain git commands with literal paths.
  To append long text to the ledger, write it with the Write tool and `cat` it into place.
- **`~/ai-rfc-experiments/` and `~/arfc-experiments/` are read-only evidence** — copy out, never in.
  Scratch is `/tmp/claude/cli2/`.
- **Never run** `panther docs build`, `panther_builder.py clean`, or `panther_builder.py package-dev`.
- **No agent may write `CLAUDE.md`.** Record any edit it needs verbatim in the report.
- **No Anthropic API key is used anywhere in this project.**

---

## Rulings carried into the row (deviation log entry 0)

**R1 — Scope is both halves of D60.** CLI-2 delivers the driver *and* the instrument split that
re-hosts `ai-rfc experiment` over the shared launcher. Taking both means no spec deviation is needed
and the duplicate-launcher problem the split exists to kill actually dies. *Cost if wrong:* the row
is roughly twice the size of a driver-only row; if it overruns, the natural cut line is Task 14.

**R2 — Moved code is moved, not copied and not shimmed.** No re-export stub anywhere. Every importer
is updated in the same row, including the 3.11-only GEPA track. *Cost if wrong:* a missed importer is
an `ImportError` at collection — loud, not silent — except for the four filesystem path
constructions and sixteen name-bound monkeypatches enumerated below, which fail silently and are
therefore called out per task.

**R3 — Nothing spends.** The gate is driven entirely through `fake_claude` and stubbed spawns. This
was *verified*, not assumed: `tests/experiment/fake_claude/claude` already implements `checkpoint`
(`:298`), `revision` (`:328`) and `tag` (`:355`) step kinds, which are exactly the three facts the
ledger's strict `done` requires. **The paid-run question the brief anticipated does not need to be
asked.** *Cost if wrong:* if a gate criterion turns out to need a real kill against a real `claude`,
stop, name the cost, and ask once before spending anything.

**R4 — Sharing depth: one launcher, two loops.** *(User decision, 2026-09-09.)* `driver/session.py`
is the only spawn path. `driver/sweep.py` is production's loop; `experiment/per_cluster.py` keeps its
campaign loop but calls `run_session()`. *Cost if wrong:* the two run layouts (spec risk 6) stay
separate, so a future SP7d still has to unify them; the alternative merges them now at the price of
re-threading sixteen monkeypatch sites through a hooks interface.

**R5 — Layering: `driver/` is the lower layer.** *(User decision, 2026-09-09.)* `arms.py` and
`render.py` move into `driver/` alongside the five spec-named modules; `driver/__init__.py` defines
`DriverError`; `experiment/` imports **from** `driver/`, never the reverse. This is the same fix
CLI-1's D7 applied to `toolchain.py`, and it is what `experiment/__init__.py:6` already promises.
**This is a deliberate extension of spec §5's module table**, which names only five modules — logged
because the table read literally would leave `driver/` importing the instrument it was split out of.
*Cost if wrong:* two more large modules move (186 + 700 lines) with ~24 extra import sites.

**R6 — `experiment/driver.py` is renamed to `experiment/campaign_runs.py`.** *(User decision,
2026-09-09.)* It is the campaign's frozen run-order runner, a different sense of "driver" from the
new package. Six importers update in the same task. *Cost if wrong:* a mechanical, fully greppable
rename; reverting is one `git mv` plus six lines.

**R7 — Sequencing: SP7c landed first.** CLI-2 inherits a **landed** consolidation hook, inverting
spec D55's order. Nothing in this plan may assume `next_round()` is unwritten.

**R8 — The prompt's import-map premise is corrected by measurement.** The brief states "seventeen
files import the modules you are moving — ten under `ai_rfc/` including `ai_rfc/config.py`". Measured:
**9 files under `ai_rfc/`, 9 test files, 40 import statements**, and **`ai_rfc/config.py` imports
nothing from any of them** — its `consolidation`/`arms` hits are schema help strings and
`experiment.arms` config *keys*, not module references. The measured map governs.

**R9 — Plan-mode transplant.** This plan was written under plan mode, which permits writing only the
harness plan file. On approval it is copied verbatim to
`docs/superpowers/plans/2026-09-10-arfc-one-door-cli2.md`, the deviation log is opened beside it, and
both are committed in PANTHER with `git add -f` **before Task 1 runs**. The single `review-plan`
invocation happens against the harness file and is not repeated after the transplant.

---

## Deviations found by `review-plan` and fixed in this plan (D1–D9)

One `review-plan` invocation ran against this file before Task 1. Four Criticals and five Warnings; all
nine are fixed in the task text below. Every anchor in this plan was re-verified line by line.

**D1 (Critical) — `ai-rfc init` breaks silently, and the plan never mentioned the file.**
`ai_rfc/lifecycle/workspace.py:35` is
`PROMPTS = Path(__file__).resolve().parents[1] / "experiment" / "prompts"`, read at `:223` as
`string.Template(DRAFT_SKELETON.read_text())`. `lifecycle/workspace.py` **does not move**, so moving
`prompts/` gives `ai-rfc init` a `FileNotFoundError` at scaffold — no `ImportError` to warn anyone.
Fixed in Task 2 Steps 2–3.

**D2 (Critical) — `draft-skeleton.md` is a substrate file, not an experiment prompt.** Its only reader
in the tree is `lifecycle/workspace.py:36,223`; `render.py` never touches it. `workspace.py:31-34`
already documents this as "a layering inversion the substrate cannot fix on its own", and its sibling
constant `SKELETON_REFERENCES` (`workspace.py:43`) already lives in `lifecycle/`. **It moves to
`ai_rfc/lifecycle/prompts/`, not to `driver/prompts/`** — that resolves the documented inversion
instead of relocating it. Consequence: `ai_rfc/experiment/prompts/` ends up **empty**, so
`pyproject.toml:38`'s `"ai_rfc.experiment" = ["prompts/*.md"]` line is **deleted**, not kept.

**D3 (Critical) — a byte-for-byte pin test makes the move fail loudly if the shipped skill is not
regenerated.** `render.py:81` embeds the literal `ai_rfc/experiment/prompts/loop.tmpl.md` inside
`SKILL_FRONTMATTER`, and `tests/experiment/test_render.py:35` asserts the **committed**
`plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` equals
`SKILL_FRONTMATTER + render_loop("interactive")` byte-for-byte. Update the literal without regenerating
and the test fails; skip the literal and a shipped skill documents a path that no longer exists. Both
happen in **one commit** — Task 2 Step 5.

**D4 (Critical) — four modules import `ExperimentError`, not one.** The plan named only
`stream.py:14`. Measured: `arms.py:18`, `render.py:26`, `stream.py:14` and `driver.py:15` all carry
`from . import ExperimentError`. All four move (three into `driver/`, one is Task 3's rename), so all
four must become `DriverError` or they import **upward** into `ai_rfc.experiment.__init__` and re-create
the inversion R5 exists to remove. No runtime cycle would result — that `__init__` imports no
submodules — which is exactly why this would have passed the suite unnoticed.

**D5 (Critical) — the monkeypatch count was wrong three ways, and every error fails silently.** The
plan said sixteen. Measured **28 patch sites**, and one of them is a shared helper:

| Target | Sites | Correction |
|---|---|---|
| `per_cluster.spawn` | 8 | `:130` is **not** a per-test patch — it is inside the helper `_stub_spawn` (defined `:100`), invoked from **31 call sites**. `:896` is inside helper `_record_revisions` (`:865`). Only `579, 1113, 1160, 1243, 1349, 1466` sit in single tests. |
| `per_cluster.consolidation_due` | **12**, not 2 | `946, 1161` plus **ten missed**: `975, 1004, 1045, 1074, 1203, 1245, 1275, 1310, 1350, 1383` (multi-line form — `per_cluster,` on +1, `"consolidation_due",` on +2, which is why a single-line grep missed them). |
| `per_cluster._run_consolidation` | **8**, not 6 | `480, 525, 550, 576, 626, 688` plus **two missed**: `498` and `649` (multi-line form). |

There are **zero** string-path `monkeypatch.setattr("ai_rfc.experiment…")`, `mock.patch` or
`patch.object` sites in `test_per_cluster.py`, so the enumeration above is complete under a full-file
grep.

**D6 (Warning) — four line ranges were off.** `spawn.py`'s try/except is **61–70** (`:71` is the
dedented `return`). `lifecycle/run/cli.py`'s stage loop is **67–92** (`:93` is post-loop).
`per_cluster.py`'s cluster attempt is **672–681** (`:679` is mid-kwargs). `config.py:679` is
`consolidate_every`; **`sessions.profile` re-serialises at `:680`**.

**D7 (Warning) — the conventions test has two exclusion lines.** `test_cli_conventions.py:148` excludes
the root door; **`:149`** carries `{"server", "experiment"}`. Task 14 edits `:149` only.

**D8 (Warning) — `optimize/evaluator.py:36` is a relative import**, `from ..driver import
launch_pending`, not the absolute form Task 3 assumed. Same for `optimize/{apply,codec}.py:30,25`
(`..render`) and `optimize/claude_cli.py:21` (`..stream`).

**D9 (Warning) — campaigns copy the templates, so the runtime blast radius is narrower than it looks.**
`config.py:355-383` writes `prompts_dir / TASK_TEMPLATE_FILE` with `write_bytes`, renaming `task.md` →
`task.tmpl.md`. Already-frozen campaigns are unaffected by the move; only `campaign init` reads the
package directory, and `runner.py:174,270` read only the campaign copy. Recorded so a reviewer does not
raise it as a missed breakage.

**D10 (Critical) — Task 7's original RED test was green against unfixed code.** The plan asked that
"the campaign path produces the identical argv the direct `run_session` call produces". That is already
true: both paths bottom out in `arms.claude_argv`, so argv is identical *before* any re-hosting. A RED
that passes against unfixed code is a stop, and SP7c shipped this mistake three times in one row.
**Replaced** (Task 7 Step 1): patch the name `per_cluster` will bind — `run_session`, imported by name
from `ai_rfc.driver.session` — with a recorder, drive one cluster attempt, and assert the recorder was
called with a `SessionSpec` whose `budget_usd == budget_left`. Before Task 7 that name does not exist on
`per_cluster`, so the patch raises `AttributeError` → RED; after, GREEN.

**D11 (Critical) — moving tests strands their fixtures, and one of them is `autouse`.** Measured:
`tests/experiment/test_stream.py:22` is `FIXTURES = Path(__file__).parent / "fixtures" / "stream"` and
`tests/experiment/test_enforcement_corpus.py:29` is `… .parent / "fixtures" / "enforcement"` — both break
the moment the test file moves. Worse, `tests/experiment/conftest.py:113` defines
`_toolchain_always_verifies` as **`@pytest.fixture(autouse=True)`**, which simply stops applying to a
test that has moved to `tests/driver/` — a behaviour change with no error. `test_render.py:180,195` use
`parents[2]` and are depth-safe. This is CLI-1's D8/D13/D19 class of defect. Fixed in Task 1 Step 1a.

**D12 (Critical) — Task 5's named mechanism cannot reach the child process.** `runner.build_env:87-109`
returns a **closed** environment — its docstring is "The complete environment; nothing else is
inherited". So a test that sets `AI_RFC_FAKE_SCENARIO` in its own environment never gets it into the
fake, and Task 5's RED (which spawns the fake directly) would pass while Task 15 silently falls back to
`default.json`. "Per-ordinal steps" was also unspecified: the fake replays every step on every
invocation, so a two-cluster scenario would finish both clusters in session 1. **Ruled** in Task 5.

**D13 (Critical) — production had no prompt source and no drift baseline.** `SessionSpec` takes
`prompt_file` and `task`; campaigns write both at freeze into `campaign.prompts_dir`. Nothing in the
original Tasks 10–11 said where `sweep` gets arm A's system prompt and task text, or what `run.json`'s
"prompt drift" (spec risk 5: "sessions render from the sealed prompts") is measured against. **Ruled**
in Task 10 Step 0.

**D14 (Critical) — an interrupted run must not write `status.json`.** Spec §5's resume rule keys on its
*absence*: `runs/<ts>/` without `status.json` becomes `runs/<ts>.interrupted-<cause>/`. A
`finally: write_status` in `sweep.run` would make Task 15 Criterion 2 unable to ever observe a leftover,
and the gate would pass while resumability was broken. **Ruled** in Task 10 Step 5.

**Docs that go stale but do not break** (fix in Task 2 Step 6, one commit): `ai_rfc/experiment/README.md:41,119,132,133`,
`README.md:136,198,327`, `docs/experiment-protocol.md:130,269`. `ai_rfc.egg-info/SOURCES.txt` is an
**untracked** build artifact — no edit. `plugins/ai-rfc/skills/ai-rfc-editorial/` needs **no** edit: it
references no path, and `render.py:50` reaches it by tuple against a caller-supplied `plugin_root`
(`render.py:617,653`), never `__file__`.

**Verified clean, so no task touches them:** `plugins/ai-rfc/.mcp.json`, `.claude-plugin/marketplace.json`,
`plugins/ai-rfc/.claude-plugin/plugin.json`, all five `plugins/ai-rfc/commands/*.md`, every YAML, and the
outer PANTHER `pyproject.toml` (which names the submodule only in lint/mypy/coverage **exclusion** lists).
No lifecycle module imports `ai_rfc.experiment` today — the dependency already runs the other way
(`experiment/config.py:25`, `cli.py:23,24`, `workspace.py:25-27`, `preflight.py:23`, and three under
`optimize/`), so R5's direction is consistent with the tree even though `driver/` sitting *below*
lifecycle is new.

---

## File Structure

### Created

| File | Responsibility |
|---|---|
| `ai_rfc/driver/__init__.py` | `DriverError(RuntimeError)`; the package docstring stating the layering rule |
| `ai_rfc/driver/spawn.py` | *(moved)* process-group spawn; gains the SIGINT/SIGTERM handler |
| `ai_rfc/driver/stream.py` | *(moved)* transcript event reading; raises `DriverError` |
| `ai_rfc/driver/enforcement.py` | *(moved)* command families, `render_settings` |
| `ai_rfc/driver/guard.py` | *(moved)* the PreToolUse guard, run as a subprocess |
| `ai_rfc/driver/arms.py` | *(moved)* `ArmProfile`, `PROFILES`, `claude_argv`, `mcp_config` |
| `ai_rfc/driver/render.py` | *(moved)* slot tables, `render_task`, `arm_prompt`, consolidation profile |
| `ai_rfc/driver/prompts/` | *(moved)* five prompt templates — **not `draft-skeleton.md`** (D2) |
| `ai_rfc/lifecycle/prompts/draft-skeleton.md` | *(moved)* the substrate's own skeleton, beside its only reader (D2) |
| `ai_rfc/driver/consolidation.py` | *(moved)* `Due`, `consolidation_due` |
| `ai_rfc/driver/session.py` | `SessionSpec`, `SessionResult`, `run_session(spec, run_dir)` — the one spawn path |
| `ai_rfc/driver/record.py` | `run.json`, `sessions.jsonl`, `status.json`, `spent()`, `attempts()`, `move_aside()` |
| `ai_rfc/driver/stop.py` | `StopReason`, `classify(result)`, `resume_line(reason, config_path)` |
| `ai_rfc/driver/sweep.py` | `plan_next(ws, cfg, ledger) -> Action` (pure), `run(cfg, ws, *, mode, until, retry)` |
| `ai_rfc/lifecycle/next/{__init__,__main__,cli}.py` | the `next` verb (CLI-1 D1 layout) |
| `tests/driver/` | `test_spawn.py`, `test_session.py`, `test_record.py`, `test_stop.py`, `test_sweep.py` |

### Modified (the ones that fail *silently* if missed)

| File | Why it is dangerous |
|---|---|
| `ai_rfc/experiment/runner.py:34` | `GUARD = Path(__file__).parent / "guard.py"` — **breaks silently**; `guard.py` leaves, `runner.py` stays |
| `ai_rfc/experiment/preflight.py:217` | `Path(__file__).resolve().parent / "guard.py"` — same |
| `tests/experiment/test_enforcement.py:16` | `parents[2] / "ai_rfc" / "experiment" / "guard.py"`, spawned as a subprocess at `:90` |
| `tests/experiment/test_stream.py:23` | same construction, spawned at `:80` |
| `ai_rfc/lifecycle/workspace.py:35` | hardcodes `parents[1] / "experiment" / "prompts"` and does **not** move — **breaks `ai-rfc init`** (D1) |
| `tests/experiment/test_per_cluster.py` | **8× `spawn`** (`:130` and `:896` are inside shared helpers `_stub_spawn`@`:100` and `_record_revisions`@`:865`; `:130` fans out to **31 call sites**) and **12× `consolidation_due`** at `:946, 975, 1004, 1045, 1074, 1161, 1203, 1245, 1275, 1310, 1350, 1383` (D5) |
| `tests/experiment/test_cli_campaign.py` | **8× `_run_consolidation`** at `:480, 498, 525, 550, 576, 626, 649, 688` (D5) |
| `pyproject.toml:37-38` | `"ai_rfc.experiment" = ["prompts/*.md"]` is **replaced** by `"ai_rfc.driver"`, not joined by it (D2) |
| `ai_rfc/experiment/render.py:81` + `plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` | a byte-for-byte pin test (`tests/experiment/test_render.py:35`) ties the embedded path to the shipped skill (D3) |
| `tests/substrate/test_cli_conventions.py:149` | the `{"server", "experiment"}` exclusion; mounting `ai-rfc experiment` makes `on_disk != ENTRY_POINTS` (D7) |

`ai_rfc.egg-info/` is **untracked** (`git ls-files ai_rfc.egg-info` is empty), so its stale
`SOURCES.txt` needs no edit.

`tests/experiment/fixtures/stream/denied-bash.jsonl:6` carries the old absolute `guard.py` path. It is
a **frozen recorded transcript**; no test asserts on that substring. Leave it stale.
`docs/experiments/2026-08-31-pilot-aioquic.md` hand-digests `guard.py`'s SHA-256 at a fixed
timestamp — a past run's record. Do not rewrite it.

---

## Task 1: The driver package and the launcher substrate

Move the five process-layer modules plus `arms.py`. `enforcement.py:25` imports `ArmProfile`, so
`arms.py` must travel with them or the move creates the very cycle R5 forbids.

**Files:**
- Create: `ai_rfc/driver/__init__.py`, `tests/driver/__init__.py`
- Move: `ai_rfc/experiment/{spawn,stream,enforcement,guard,arms}.py` → `ai_rfc/driver/`
- Move: `tests/experiment/{test_stream,test_enforcement,test_enforcement_corpus,test_arms}.py` → `tests/driver/`
- Modify: `ai_rfc/experiment/{audit,cli,metrics,per_cluster,preflight,runner,config,campaign-adjacent}.py`,
  `ai_rfc/experiment/optimize/claude_cli.py`, and the two guard-path sites above

**Interfaces:**
- Produces: `ai_rfc.driver.DriverError`; `ai_rfc.driver.spawn.spawn(argv, *, cwd, env, events_path, stderr_path, timeout_s, append=False) -> tuple[int | None, bool]`;
  `ai_rfc.driver.arms.ArmProfile(arm, label, tools, allowed_tools, uses_mcp)`;
  `ai_rfc.driver.arms.claude_argv(*, claude_bin, prompt, this_arm, mcp_config_path, model, effort, budget_usd, prompt_file, guard_settings=None) -> list[str]`;
  `ai_rfc.driver.enforcement.render_settings(*, python: str, guard: Path, prefixes: Sequence[str]) -> dict[str, Any]`

- [ ] **Step 1: Create the package with its error type and its layering rule**

```python
"""Everything that launches and reads one ``claude -p`` session.

This package is the lower layer: :mod:`ai_rfc.experiment` imports from here,
and nothing here may import from ``ai_rfc.experiment``. The instrument was
split out over this package precisely so production and the three-arm
experiment share one spawn path rather than two that drift.
"""

from __future__ import annotations


class DriverError(RuntimeError):
    """A session could not be launched, read, or accounted for."""
```

- [ ] **Step 1a: Settle the test move BEFORE moving anything (D11)**

Moving a test file out of `tests/experiment/` strands three things, two of them measured and one that
changes behaviour with no error:

1. `test_stream.py:22` `FIXTURES = Path(__file__).parent / "fixtures" / "stream"` and
   `test_enforcement_corpus.py:29` `… .resolve().parent / "fixtures" / "enforcement"` — **both break**.
2. `tests/experiment/conftest.py:113` `_toolchain_always_verifies` is **`@pytest.fixture(autouse=True)`**
   and simply **stops applying** to a moved test.
3. Any conftest fixture the moved tests request (`campaign`, `write_scenario`, `plugin_root`,
   `pristine`, `toolchain_record`, `fixture_workspace`, `panther_repo`) is invisible from `tests/driver/`.

`test_render.py:180,195` use `parents[2]`, which resolves to the repo root at either depth — safe.

Run this first and decide from the output, do not guess:

```bash
grep -n "fixtures\|__file__\|parents\[" tests/experiment/test_stream.py tests/experiment/test_enforcement.py tests/experiment/test_enforcement_corpus.py tests/experiment/test_arms.py
grep -nE "def test_.*\(.*(campaign|write_scenario|plugin_root|pristine|toolchain_record|fixture_workspace|panther_repo)" tests/experiment/test_stream.py tests/experiment/test_enforcement.py tests/experiment/test_enforcement_corpus.py tests/experiment/test_arms.py
```

**Default ruling, to be overridden only by that output:** move `tests/experiment/fixtures/stream/` and
`tests/experiment/fixtures/enforcement/` along with their tests, and **append** any shared fixture the
moved tests need to `tests/conftest.py` — *append*, never overwrite: that file already holds
`pytest_addoption` registering `--update-goldens`, and losing it errors every golden test on an unknown
flag (CLI-1 D9). If a moved test needs `_toolchain_always_verifies`, replicate it in a new
`tests/driver/conftest.py`. **If any moved test requests three or more conftest fixtures, leave that
test in `tests/experiment/` with updated imports instead** — the point of the move is clarity, not
churn.

Until this step is settled, Step 8's "1472 passed — a pure move changes no count" is unproven.

- [ ] **Step 2: Move the six modules, one plain `git mv` per line**

```bash
git mv ai_rfc/experiment/spawn.py ai_rfc/driver/spawn.py
git mv ai_rfc/experiment/stream.py ai_rfc/driver/stream.py
git mv ai_rfc/experiment/enforcement.py ai_rfc/driver/enforcement.py
git mv ai_rfc/experiment/guard.py ai_rfc/driver/guard.py
git mv ai_rfc/experiment/arms.py ai_rfc/driver/arms.py
```

The worktree guard refuses chained `git` — one command per call, literal paths, no `&&`.

- [ ] **Step 3: Repoint the moved modules' own imports — three `ExperimentError` sites, not one (D4)**

`arms.py:18`, `stream.py:14` and `render.py:26` (Task 2) each carry `from . import ExperimentError`.
In this task, `arms.py:18` and `stream.py:14` become `from . import DriverError`, and **every raise in
both files is renamed**. Left alone they would import *upward* into `ai_rfc.experiment.__init__` —
which holds only `DEFAULT_MODEL`, `EFFORTS` and `ExperimentError` and imports no submodules, so there
would be **no cycle and no test failure**. That is precisely why this must be done deliberately here.

`enforcement.py:25` `from .arms import ArmProfile` is unchanged (both moved).
`guard.py:19` `from ai_rfc.experiment.enforcement import is_allowed` → `from ai_rfc.driver.enforcement import is_allowed`.
`guard.py:17`'s `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` is **unchanged** — the
depth is identical under `ai_rfc/driver/` (`driver` → `ai_rfc` → repo root).

- [ ] **Step 4: Repoint the two guard path constructions — these break silently**

`ai_rfc/experiment/runner.py:34` and `ai_rfc/experiment/preflight.py:217` both build the guard path from
their **own** `__file__`, and both modules **stay behind**, so each resolves to a nonexistent
`experiment/guard.py`. The consequence is not a crash: the bad path is written into the arm's settings
JSON at `enforcement.py:204` and handed to Claude Code as a PreToolUse hook, so **the arm B/C Bash guard
silently fails to mount**. Use `Path(__file__).resolve().parents[1] / "driver" / "guard.py"` in both;
pick that one form and do not mix it with an `importlib` variant.

`tests/experiment/test_runner.py:155` asserts `parsed[1].endswith("/guard.py") and Path(parsed[1]).exists()`
and passes only once both are right — it is the one existing test that catches this.

Also fix the two test-side constructions, which spawn the guard as a real subprocess and so fail with
`FileNotFoundError` rather than an import error: `tests/experiment/test_enforcement.py:16` (used at
`:89-90`) and `tests/experiment/test_stream.py:23` (used at `:79-80`). Anchor edits at the `GUARD = …`
line, not at the use site — the use site is mid-argument-list.

- [ ] **Step 5: Repoint every remaining importer**

Nine sites under `ai_rfc/`: `experiment/audit.py:23,25`; `experiment/cli.py` (its `.stream`/`.enforcement`
uses); `experiment/metrics.py:25`; `experiment/optimize/claude_cli.py:21` (**`..stream` → the 3.11
track**); `experiment/per_cluster.py:37,38`; `experiment/preflight.py:26,27`; `experiment/runner.py:22,23,20`;
`experiment/summary.py:25`; plus the nine `from .arms import …` sites listed in the File Structure.
Test sites move with their modules; `tests/experiment/{test_audit,test_fake_claude,test_metrics,test_per_cluster,test_preflight}.py`
keep absolute imports that must become `ai_rfc.driver.stream`.

- [ ] **Step 5a: Convert the moved tests' `pytest.raises(ExperimentError)` to `DriverError`**

`arm_profile` (`arms.py:67`), `arm_flags` (`:122-127`) and the moved modules' other guards raise what is
now `DriverError`, so every `pytest.raises(ExperimentError)` in a moved test must change with it.
Enumerate them explicitly rather than trusting one grep — this is CLI-1's D2 class:

```bash
grep -rn "ExperimentError" tests/driver tests/experiment
```

- [ ] **Step 6: Add `DriverError` to the seven `except ExperimentError` sites that now wrap driver calls**

`experiment/per_cluster.py:528,582,642`; `experiment/cli.py:1462`; `experiment/preflight.py:245`;
`experiment/optimize/claude_cli.py:226,236`. Read each: widen to `except (ExperimentError, DriverError)`
only where the guarded call reaches moved code. A missed one turns a reported `error:` line into a
traceback.

- [ ] **Step 7: Prove no shim and no stale path survives**

```bash
grep -rn "experiment.spawn\|experiment.stream\|experiment.enforcement\|experiment.guard\|experiment.arms" --include='*.py' ai_rfc tests
```
Expected: **zero hits** outside `tests/experiment/fixtures/stream/denied-bash.jsonl` (not a `.py`).

- [ ] **Step 8: Run the suite**

Run: `SSLKEYLOGFILE= <worktree>/.venv/bin/python -m pytest tests -q -n auto -p no:cacheprovider`
Expected: **1472 passed, 11 skipped** — a pure move changes no count.

- [ ] **Step 9: Commit by explicit path**

```bash
git status --short
git commit -m "refactor: move the session launcher substrate into ai_rfc/driver" -m "Claude-Session: https://claude.ai/code/session_015hMZpbY4dV6sizex6sdSBH" -- ai_rfc/driver ai_rfc/experiment tests/driver tests/experiment
git show -s --format=%B HEAD
```

---

## Task 2: Move rendering, prompts and the consolidation scheduler

**Files:**
- Move: `ai_rfc/experiment/render.py` → `ai_rfc/driver/render.py`; `ai_rfc/experiment/consolidation.py` → `ai_rfc/driver/consolidation.py`; `ai_rfc/experiment/prompts/` → `ai_rfc/driver/prompts/`
- Move: `tests/experiment/{test_render,test_consolidation}.py` → `tests/driver/`
- Modify: `pyproject.toml:38`; `ai_rfc/experiment/{config,cli}.py`, `ai_rfc/experiment/optimize/{apply,codec}.py`, `ai_rfc/experiment/per_cluster.py`

**Interfaces:**
- Consumes: `ai_rfc.driver.DriverError` (Task 1)
- Produces: `ai_rfc.driver.render.{SLOT_TABLES, TEMPLATE, SLOT_RE, SKILL_FRONTMATTER, TASK_PROFILES, task_profile, task_template_path, render_loop, render_consolidation, render_task, arm_prompt, consolidation_prompt, write_plugin_skill, unified_diff}`;
  `ai_rfc.driver.consolidation.{Due, consolidation_due}`

- [ ] **Step 1: Move `render.py`, `consolidation.py`, and five of the six prompts**

One plain `git mv` per call. `consolidation.tmpl.md`, `loop.tmpl.md`, `task-consolidation.md`,
`task-interview.md` and `task.md` go to `ai_rfc/driver/prompts/`. **`draft-skeleton.md` does not** — see
Step 2. `render.py:26`'s `from . import ExperimentError` becomes `DriverError` (D4), completing the three
sites Task 1 began.

- [ ] **Step 2: `draft-skeleton.md` moves to `lifecycle/`, and `lifecycle/workspace.py:35` is the reason (D1, D2)**

`ai_rfc/lifecycle/workspace.py:35` reads
`PROMPTS = Path(__file__).resolve().parents[1] / "experiment" / "prompts"`, and `:36`'s
`DRAFT_SKELETON` is consumed at `:223` by `string.Template(DRAFT_SKELETON.read_text())`. That module
**does not move**, so the bare move gives `ai-rfc init` a `FileNotFoundError` at scaffold with no
`ImportError` anywhere to warn a reader.

`render.py` never reads `draft-skeleton.md` — its only reader in the tree is this one — and
`workspace.py:31-34` already documents the arrangement as "a layering inversion the substrate cannot fix
on its own", with its sibling constant `SKELETON_REFERENCES` (`:43`) already living in `lifecycle/`. So:

```bash
mkdir -p ai_rfc/lifecycle/prompts
git mv ai_rfc/experiment/prompts/draft-skeleton.md ai_rfc/lifecycle/prompts/draft-skeleton.md
```

(`git mv` fails with "destination directory does not exist" without the `mkdir`.)

and rewrite `workspace.py:35-36` to `Path(__file__).resolve().parent / "prompts"`. This resolves the
documented inversion rather than relocating it. **Write a RED test first**: assert `ai-rfc init`
scaffolds a draft, and see it fail after Step 1 and before this step — that failure is the whole point
of the step and is invisible to every existing test.

- [ ] **Step 3: Move the package-data entry, do not add a second one (D2)**

`ai_rfc/experiment/prompts/` is **empty** once Steps 1 and 2 finish, so `pyproject.toml:38` is
*replaced*:

```toml
[tool.setuptools.package-data]
"ai_rfc.driver" = ["prompts/*.md"]
"ai_rfc.lifecycle" = ["prompts/*.md"]
```

Delete the now-empty `ai_rfc/experiment/prompts/` directory. Keeping the old line would ship a glob
matching nothing — and because editable installs and the whole test suite read the source tree
directly, **no test would catch it**; only a wheel build would.

- [ ] **Step 4: Repoint importers**

`experiment/config.py:28` (`from .render import (…)`), `experiment/cli.py:1237,1436` (both
function-local), `experiment/optimize/apply.py:30`, `experiment/optimize/codec.py:25` (**both
3.11-track, both relative `..render`**), `experiment/per_cluster.py:33` (`from .consolidation import
Due, consolidation_due`), **`experiment/cli.py:623`** (`from .consolidation import consolidation_due` —
**function-local, inside the `_run_consolidation` path, invisible to a header-only scan**), and the six
test modules listed in the File Structure.

`experiment/config.py:93` is a `#:` Sphinx attribute comment, not a docstring — grep for the literal
`ai_rfc.experiment.render.TASK_PROFILES`, not for a docstring. A stale cross-reference is a comment
that is now wrong, which the "don't remove comments" rule does not protect.

- [ ] **Step 5: Regenerate the shipped skill in this same commit (D3)**

`render.py:81` embeds the literal `ai_rfc/experiment/prompts/loop.tmpl.md` inside `SKILL_FRONTMATTER`,
and `tests/experiment/test_render.py:35` asserts the **committed**
`plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` equals
`SKILL_FRONTMATTER + render_loop("interactive")` byte-for-byte. Update the literal to
`ai_rfc/driver/prompts/loop.tmpl.md`, then regenerate:

```bash
SSLKEYLOGFILE= <worktree>/.venv/bin/python -m ai_rfc.experiment render
```

Both edits land in one commit. Update the literal without regenerating and the pin test fails; skip the
literal and the pin test passes while a shipped skill documents a path that no longer exists. The render
verb itself (`experiment/cli.py:1237`) stays in `experiment/` and is unaffected.

`plugins/ai-rfc/skills/ai-rfc-editorial/` needs **no** edit — it names no path, and `render.py:50`
reaches it by tuple against a caller-supplied `plugin_root` (`render.py:617,653`), never `__file__`.

- [ ] **Step 6: Update the stale prose references**

`ai_rfc/experiment/README.md:41,119,132,133`, `README.md:136,198,327`,
`docs/experiment-protocol.md:130,269`. None break a build; all ship. `ai_rfc.egg-info/SOURCES.txt` is
an **untracked** artifact — do not edit it.

- [ ] **Step 7: Prove no stale reference**

```bash
grep -rn "experiment.render\|experiment.consolidation\|from .render\|from ..render" --include='*.py' ai_rfc tests
grep -rn "experiment/prompts" ai_rfc tests plugins docs
```
Expected: zero hits from both.

- [ ] **Step 8: Run both interpreters**

3.10 suite: expect **1472 passed, 11 skipped**, plus the one new `ai-rfc init` test from Step 2 →
**1473 passed**.
3.11 selection: expect **222 passed, 2 skipped, 2 deselected**. This is the first task that can break
the GEPA track — `optimize/apply.py:30`, `optimize/codec.py:25` and `optimize/claude_cli.py:21` are all
**relative** imports (`..render`, `..stream`), not the absolute form (D8).

- [ ] **Step 9: Commit**

---

## Task 3: Rename `experiment/driver.py` to `experiment/campaign_runs.py`

Two unrelated `driver` names must not coexist (R6).

**Files:**
- Move: `ai_rfc/experiment/driver.py` → `ai_rfc/experiment/campaign_runs.py`; `tests/experiment/test_driver.py` → `tests/experiment/test_campaign_runs.py`
- Modify: `ai_rfc/experiment/cli.py:1325`, `ai_rfc/experiment/optimize/evaluator.py:36`, `tests/experiment/{test_audit.py:12, test_metrics.py:4, test_per_cluster.py:10}`

**Interfaces:**
- Produces: `ai_rfc.experiment.campaign_runs.{pending_runs, launch_pending}` — signatures unchanged.

- [ ] **Step 1:** `git mv` both files (one call each).
- [ ] **Step 2:** Update the six importers. `optimize/evaluator.py:36` is `from ..driver import
launch_pending` — a **relative** import on the **3.11-only** path (D8), so a grep for the absolute
dotted form finds nothing. `experiment/cli.py:1325` is `from .driver import launch_pending`, also
relative and **function-local** inside the `run` dispatch.
- [ ] **Step 3:** `grep -rn "experiment.driver\|from .driver import" --include='*.py' ai_rfc tests` → zero hits.
- [ ] **Step 4:** Both suites at baseline. Commit.

---

## Task 4: `spawn` must kill its group on interrupt, not orphan it

Spec risk 1 and the §5 module table both name this. `spawn.py:61-70` has no `finally` (`:71` is the
dedented `return`; `grep -n finally` over the file returns zero), so a `KeyboardInterrupt` out of
`process.wait()` at `:62` unwinds past the group kill and leaves `claude` plus its MCP server
**spending money** with no parent.

**Files:**
- Modify: `ai_rfc/driver/spawn.py`
- Test: `tests/driver/test_spawn.py`

- [ ] **Step 1: Write the failing test**

```python
def test_an_interrupt_kills_the_group_it_started(tmp_path, monkeypatch):
    """Ctrl-C must reach the session, not just the process that launched it.

    ``start_new_session=True`` puts the child in its own process group, so the
    terminal's SIGINT never reaches it. Without an explicit group kill the
    session and its MCP server outlive the driver and keep spending.
    """
    killed: list[tuple[int, int]] = []

    class _Interrupting:
        """Interrupt the first wait, then reap cleanly on the group-kill wait.

        Raising on every call would make the cleanup's own
        ``process.wait(timeout=KILL_GRACE_S)`` raise inside the handler, so the
        implementer would never see the full SIGTERM -> grace -> reap path run.
        """

        pid = 4242
        calls = 0

        def wait(self, timeout=None):
            type(self).calls += 1
            if type(self).calls == 1:
                raise KeyboardInterrupt
            return 0

    monkeypatch.setattr(spawn_module.subprocess, "Popen", lambda *a, **k: _Interrupting())
    monkeypatch.setattr(spawn_module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(KeyboardInterrupt):
        spawn_module.spawn(
            ["true"],
            cwd=tmp_path,
            env={},
            events_path=tmp_path / "events.jsonl",
            stderr_path=tmp_path / "stderr.log",
            timeout_s=30,
        )

    assert killed and killed[0] == (4242, signal.SIGTERM)
```

- [ ] **Step 2: Run it and see it fail**

Run: `SSLKEYLOGFILE= <worktree>/.venv/bin/python -m pytest tests/driver/test_spawn.py::test_an_interrupt_kills_the_group_it_started -v -p no:cacheprovider`
Expected: **FAIL** — `killed` is empty, because today nothing between `:61` and `:71` runs on
`KeyboardInterrupt`. If this test passes, stop: the premise is wrong and so is the fix.

- [ ] **Step 3: Implement**

Wrap the wait so the interrupt path takes the same `SIGTERM → KILL_GRACE_S → SIGKILL → reap` walk the
timeout path already takes, then re-raise. Do not swallow the `KeyboardInterrupt` — the caller must
still stop. `subprocess.TimeoutExpired` keeps its existing branch and its `timed_out = True`.

- [ ] **Step 4:** Test passes. Full 3.10 suite: **1474 passed, 11 skipped** — 1472 baseline, +1 from
Task 2 Step 2's `ai-rfc init` test, +1 here. Record the measured number; if it differs, measure and
record the difference rather than reconciling it by skipping or weakening a test.
- [ ] **Step 5:** Commit.

---

## Task 5: `fake_claude` gains scenario selection and per-ordinal steps

Spec §8 requires this and two measured facts make it a blocker for every later driver test.

**Files:**
- Modify: `tests/experiment/fake_claude/claude`, `tests/experiment/conftest.py:136-147`

- [ ] **Step 0: The two rulings this task needs (D12)**

**Ruling A — no env var; the scenario is found by directory name.** `runner.build_env:87-109` returns a
**closed** environment ("The complete environment; nothing else is inherited"), so `AI_RFC_FAKE_SCENARIO`
set by a test would never reach the child. Making it work would require `build_env` to forward it, i.e.
a test hook in production code. Instead, keep the existing derivation at `claude:464`
(`run_id = workspace.parent.name`) and have the **driver tests name the parent directory** so the lookup
lands: production's `spec.workspace` is `<ws>` and its parent is the reconstructions directory, so the
gate's fixture creates the reconstruction under a directory named for the scenario. *Cost if wrong:* if a
later task genuinely needs per-session scenario selection, `build_env` gains one explicitly-named
pass-through and this ruling is revisited — spec §8 mentions the env var, so record this as a deviation
from §8's letter, not from a decision.

**Ruling B — the fake derives the current ordinal from the workspace, as a real agent does.** The fake
already holds `self.ctx` over the workspace and mutates it through `ai_rfc.server.core`, so it can call
`ledger.next_cluster(workspace)` to learn which cluster *this* session is for and replay only that
ordinal's steps. Without this the fake replays every step on every invocation and a two-cluster scenario
finishes both clusters in session 1 — which would make Task 15 Criterion 1 pass for the wrong reason.

- [ ] **Step 1: Write the failing tests** — two, one per defect.

*Defect A, `claude:464-469` + Ruling B.* A scenario with steps for two ordinals must complete **one**
cluster per session. Assert that after the first invocation exactly one cluster is done — today the fake
replays everything and both are, so this fails.

*Defect B, `claude:499,524`.* `session_id` is the constant `f"fake-{run_id}"` at **both** sites, so
`per_cluster.py:685-689`'s `if session not in known_sessions` filter yields `[]` from the second session
onward and `sessions.jsonl` rows 2+ carry `session_id: null`. Assert two sessions of one run report
distinct ids.

- [ ] **Step 2: Run both, see both fail.**
- [ ] **Step 3: Implement** per the two rulings. Give `session_id` a per-invocation suffix at both `:499`
and `:524`. Existing campaign scenarios must keep working unchanged — they have one ordinal each, so
Ruling B is a no-op for them; confirm that by running `tests/experiment/` before the full suite.
- [ ] **Step 4:** Full suite green, count recorded. **Commit.**

---

## Task 6: `driver/session.py` — the one spawn path

**Files:**
- Create: `ai_rfc/driver/session.py`, `tests/driver/test_session.py`

**Interfaces:**
- Consumes: `driver.arms.claude_argv`, `driver.arms.mcp_config`, `driver.arms.arm_profile`,
  `driver.enforcement.{bash_prefixes, render_settings}`, `driver.spawn.spawn`,
  `driver.stream.{salvage_stream, result_events, session_ids, init_event, ai_rfc_connected, mcp_servers}`
- Produces:

```python
@dataclass(frozen=True)
class SessionSpec:
    claude: str
    model: str
    effort: str
    budget_usd: float
    timeout_s: int
    profile: Path
    python: str
    workspace: Path
    toolchain: Path | None
    prompt_file: Path
    task: str
    surface: ArmProfile
    append: bool = False


@dataclass(frozen=True)
class SessionResult:
    exit_code: int | None
    timed_out: bool
    cost_usd: float
    results_seen: int
    session_ids: tuple[str, ...]
    wall_s: float
    argv: tuple[str, ...]
    events: tuple[dict[str, Any], ...]
    damaged: int


def run_session(spec: SessionSpec, run_dir: Path, *, seen: int = 0) -> SessionResult: ...
```

`surface` is an `ArmProfile`, not an arm letter: `arms.arm_flags:122-127` raises when `uses_mcp` and
the mcp path disagree, and production is arm A. `append` is load-bearing — a run made of several
sessions must leave **one** transcript. `seen` carries `_session_cost`'s "count from here, not from
the tail" contract; without it a re-read double-counts every earlier result event.

- [ ] **Step 1: Write the failing tests** — four, each naming one thing the two existing call sites do
differently today:
  1. it writes `ai_rfc.json` and `guard.json` into `run_dir` and passes both on the argv;
  2. `--max-budget-usd` carries the *given* budget, not the campaign's, so a caller can pass a remainder;
  3. the returned `cost_usd` counts only result events at or after `seen`;
  4. `env` is exactly the six/seven keys `build_env` produces, `USER` included — dropping it makes the
     CLI answer "Not logged in" however valid the profile (measured on Claude Code 2.1.247; spike S0
     failed on exactly this).

- [ ] **Step 2: Run, see all four fail** (`ModuleNotFoundError: ai_rfc.driver.session`).
- [ ] **Step 3: Implement**, drawing `build_env` and the argv assembly from `experiment/runner.py:87-183`.
Resolve `spec.profile` with the `doctor/cli.py:81-85` pattern — `configured or profile_dir(experiments_root())`
— because `sessions.profile` has **no declared default** (`config.py:187-193`) and `load_config:594`
passes the raw `None` straight into `SessionsConfig`.
- [ ] **Step 4:** Tests pass; full suite green. **Commit.**

---

## Task 7: Re-host the campaign over `run_session`

This is where "one spawn path" is actually earned, and where the sixteen silent monkeypatches live.

**Files:**
- Modify: `ai_rfc/experiment/runner.py` (`launch`), `ai_rfc/experiment/per_cluster.py` (cluster attempt
  at **`:672-681`** — `:679` is mid-kwargs, D6 — and `_run_consolidation` at `:401-416`),
  `ai_rfc/experiment/cli.py:680-688`
- Modify: `tests/experiment/test_per_cluster.py`, `tests/experiment/test_cli_campaign.py`

- [ ] **Step 1: Write the failing test (D10 — the original one was green against unfixed code)**

Do **not** assert "the campaign path produces the same argv as `run_session`" — that is already true,
because both paths bottom out in `arms.claude_argv`. Instead:

```python
def test_a_cluster_attempt_launches_through_the_shared_session(campaign, monkeypatch):
    """The campaign must spend through run_session, not a second launcher.

    Asserting on argv cannot catch a surviving second launcher: both paths end
    in ``arms.claude_argv``, so the vector is identical either way. What only
    the shared path can satisfy is that ``per_cluster`` binds ``run_session``
    at all, and hands it the remaining budget rather than the whole cap.
    """
    seen: list[SessionSpec] = []

    def _record(spec, run_dir, *, seen_results=0):
        seen.append(spec)
        return SessionResult(exit_code=0, timed_out=False, cost_usd=0.25, ...)

    monkeypatch.setattr(per_cluster, "run_session", _record)
    ...
    assert seen and seen[0].budget_usd == pytest.approx(expected_remaining)
```

Before this task `per_cluster` has no `run_session` attribute, so `monkeypatch.setattr` raises
`AttributeError` — that is the RED.

- [ ] **Step 2: Run, see it fail with `AttributeError`.** If it fails for any other reason, or passes,
stop: the test is wrong, and a wrong test hides a wrong fix.
- [ ] **Step 3: Implement.** Delete `prepare_run_argv` and the `spawn` import from `runner.py`; delete
`_session_cost`'s call sites in `per_cluster.py`. `runner.launch`'s `exit_code=None if timed_out else exit_code`
(`:320`) is now redundant with `SessionResult` — remove the second normalisation, do not keep both.
- [ ] **Step 4: Re-target the twenty-eight name-bound patches — they fail SILENTLY (D5).**

`per_cluster.spawn` stops existing, so `monkeypatch.setattr(per_cluster, "spawn", …)` becomes a no-op
that **runs the real spawner** while the test still passes its other assertions. `per_cluster.py` must
therefore keep importing the *name* — `from ai_rfc.driver.session import run_session` — and never a
module alias, or every one of these detaches without a single failure.

The full enumeration, measured (the plan originally said sixteen and named two of the three groups
incompletely):

| Target | Sites |
|---|---|
| `spawn` in `test_per_cluster.py` | `130, 579, 896, 1113, 1160, 1243, 1349, 1466` |
| `consolidation_due` in `test_per_cluster.py` | `946, 975, 1004, 1045, 1074, 1161, 1203, 1245, 1275, 1310, 1350, 1383` |
| `_run_consolidation` in `test_cli_campaign.py` | `480, 498, 525, 550, 576, 626, 649, 688` |

**Two of these are shared helpers, not per-test patches — start with them.** `:130` is inside
`_stub_spawn` (defined `:100`), invoked from **31 call sites** (`141, 165, 192, 221, 344, 369, 386, 417,
442, 538, 605, 639, 670, 690, 707, 736, 757, 912, 940, 972, 1002, 1038, 1069, 1196, 1232, 1273, 1308,
1340, 1380, 1419, 1495`), so its signature governs ~31 tests. `:896` is inside `_record_revisions`
(defined `:865`). The remaining six `spawn` sites sit in single test functions.

Ten of the twelve `consolidation_due` sites and two of the eight `_run_consolidation` sites use the
**multi-line** `monkeypatch.setattr(` form with the target on the following line — which is why a
single-line grep undercounts them. Verify with a grep that spans lines, or by reading each `+1` line.

- [ ] **Step 5: Prove the patches still bite.** Add one assertion that the stub was *called* — a patch
that no longer intercepts is exactly the failure this step exists to catch.
- [ ] **Step 6:** Both suites. `_run_one_consolidation` (`cli.py:684`) passes `campaign.budget_usd`, the
whole-run cap rather than a remainder, because no sweep surrounds it — `SessionSpec` must keep
accepting an absolute cap. **Commit.**

---

## Task 8: `driver/record.py`

**Files:** Create `ai_rfc/driver/record.py`, `tests/driver/test_record.py`

**Interfaces — produces:**

```python
def write_run_record(run_dir: Path, record: dict[str, Any]) -> Path: ...
def append_session(run_dir: Path, row: dict[str, Any]) -> None: ...
def write_status(run_dir: Path, status: dict[str, Any]) -> Path: ...
def spent(workspace: Path) -> float: ...
def attempts(workspace: Path, cluster_id: str) -> int: ...
def move_aside(path: Path, cause: str) -> Path: ...
```

- [ ] **Step 1: Write the failing tests.** The two that matter:

*`spent()` is a lifetime cap and must include moved-aside runs.* Spec §5: it sums result events across
`runs/*/events.jsonl`, **moved-aside directories included**, because the `sessions.jsonl` row is
appended only after the process returns — a kill in between loses the row but not the transcript. So
the glob must also match `runs/<ts>.interrupted-<cause>/`. Assert a moved-aside directory's cost is
counted; a naive `runs/*/events.jsonl` already does match that shape, so the RED test must assert the
**sum**, not the glob.

*`move_aside` names the cause and never deletes.* `runs/<ts>/` without `status.json` →
`runs/<ts>.interrupted-<cause>/`; `checkpoints/<id>/` without `checkpoint.json` →
`checkpoints/<id>.interrupted-<ts>/`. Assert the original path is gone and the renamed one holds the
same bytes.

- [ ] **Step 2-5:** RED seen failing, implement, suite green, commit.

---

## Task 9: `driver/stop.py`

**Files:** Create `ai_rfc/driver/stop.py`, `tests/driver/test_stop.py`

**Interfaces — produces:** `StopReason` (enum: `needs_init`, `stage_failed`, `stale_substrate`,
`cluster_halted`, `budget`, `wall_clock`, `surface_shortfall`, `build_failed`, `done`),
`classify(result: SessionResult) -> str`, `resume_line(reason: StopReason, config_path: Path) -> str`.

- [ ] **Step 1: Write the failing tests** for the four session classifications from spec §5, each of
which is a *different* fact about the same result event:
  - **refused** — the session worked, the cluster is not done → **consumes an attempt**;
  - **errored** — `is_error` and at most one turn, i.e. a launch or API failure → stop with the resume
    line, **no attempt consumed**. D61 records why: MARK's ordinal 38 halted on a $0, one-turn launch
    error with $12.62 left, *not* on budget as D38 had recorded;
  - **killed** — timeout or interrupt;
  - **budget_hit**.

Assert the attempt-consumption difference explicitly — it is the whole reason the four exist.

- [ ] **Step 2:** `resume_line` must reproduce exactly, including `--retry <id>` for `cluster_halted`.
- [ ] **Steps 3-5:** implement, suite, commit.

---

## Task 10: `driver/sweep.py`

**Files:** Create `ai_rfc/driver/sweep.py`, `tests/driver/test_sweep.py`

**Interfaces — produces:** `Action` (a frozen dataclass naming one row of the state machine),
`observe(ws: Path, cfg: ReconConfig) -> Observation` (every disk and clock read),
`plan_next(obs: Observation, cfg: ReconConfig) -> Action` (**pure — no I/O**),
`run(cfg: ReconConfig, ws: Path, *, mode: str = "all", until: str | None = None, retry: str | None = None) -> int`,
and the `next_round()` hook SP7c landed.

**Deviation from spec §5's literal signature.** §5 writes `plan_next(ws, cfg, ledger)`, but a function
handed a `Path` and called pure will read disk, and then the state-machine table below cannot be unit
tested without a workspace per row. Splitting `observe` off is what makes Step 1's nine table-driven
tests real. Log it; it changes no spec decision.

- [ ] **Step 0: The two rulings this task needs (D13, D14)**

**Ruling C — where production's prompts come from, and what "drift" means.** Campaigns write
`prompt_file` and `task` at freeze into `campaign.prompts_dir`; production has no freeze step, so
`sweep` renders on each invocation from the package templates: `render.arm_prompt("A", plugin_root)` for
the system prompt and `render.render_task(...)` for the task, writing the system prompt to
`run_dir / "prompt.md"`. `run.json` records the **sha256 of both**, and *prompt drift* means those
digests differ from the previous run's `run.json` — which is what spec risk 5 ("sessions render from the
sealed prompts and `run.json` notes drift") asks for without saying how. `plugin_root` for production is
`Path(driver.render.__file__).resolve().parents[2] / "plugins" / "ai-rfc"`, mirroring
`experiment/cli.py:187`'s `parents[2]`. The `python` in `mcp_config` is `sys.executable`.
*Cost if wrong:* a deliberate prompt change is noted rather than refused; the spec reserves
`--reseal-prompts` for making it refusable, which is not this row's work.

**Ruling D — `status.json` is never written on an interrupt.** Spec §5's resume rule keys on its
*absence*: `runs/<ts>/` without `status.json` becomes `runs/<ts>.interrupted-<cause>/`. So `sweep.run`
must **not** wrap its loop in `finally: write_status`. Write it only on a normal exit or a
stop-classified one. A `finally` here would make Task 15 Criterion 2 structurally unable to observe a
leftover, and the gate would pass while resumability was broken.

- [ ] **Step 1: Write the failing tests — one per row of spec §5's state machine.** `plan_next` being
pure is what makes each row a table-driven unit test rather than a subprocess run. The rows:

| Condition | Action |
|---|---|
| `pin` pending | stop `needs_init` |
| `history`/`timeline`/`views` pending | perform via `DISPATCH`; non-zero → stop `stage_failed` |
| `timeline`/`views` stale **and** any checkpoint exists | stop `stale_substrate` |
| views done, `next_cluster()` = c, `attempts(c) < N`, budget and clock left | a session for c, then re-read the ledger |
| `attempts(c) ≥ N` and c not done | stop `cluster_halted`; resume line carries `--retry c` |
| budget or wall clock reached | stop `budget` / `wall_clock` |
| first judgeable session mounted no `ai_rfc` MCP | stop `surface_shortfall` + a doctor hint |
| `next_round()` due | consolidation session; **mid-sweep failure noted, sweep continues; sweep-end failure → exit 1** |
| no cluster outstanding, no round due | `check --strict`, `lint`, `build` (skipped without a toolchain); findings → `build_failed`, exit 1; else `done`, exit 0 |

**Never skip a cluster** (D59). Exit codes: done 0, stopped with work outstanding 1, strict findings 3.

- [ ] **Step 2:** Every row seen failing before any implementation.
- [ ] **Step 3: Implement**, reading `experiment/per_cluster.run_per_cluster` for the loop shape but
writing against `Layout`/`ReconConfig`/`ledger`, not `Campaign`/`RunRef`.
- [ ] **Step 4: On resume, rename leftovers before planning** — `record.move_aside` from Task 8. A dirty
draft worktree is **named and left to the retry**, not cleaned.
- [ ] **Step 5: Honour Ruling D.** No `finally: write_status`. Add a test that a `KeyboardInterrupt`
mid-sweep leaves `runs/<ts>/` **without** `status.json` — that absence is the resume contract, so it is
worth its own assertion rather than being implied by Task 15.
- [ ] **Step 6:** Suite green. **Commit.**

---

## Task 11: `run` continues past the boundary

**Files:** Modify `ai_rfc/lifecycle/run/cli.py` — the stage loop is **67-92** (`:93` is post-loop, D6)
and the boundary report is `103-118`; test `tests/cli/test_run.py`

- [ ] **Step 1: Write the failing test.** With a `sessions:` block configured, `run` drives a cluster
session; without one it stops at the boundary and prints the instruction **exactly as today** — a
hand-mined workspace stays possible (spec §"Undecided → settled").
- [ ] **Step 2:** See it fail — today the `mining` break at `:69-70`/`:72-73` is unconditional and the
`if given.sessions` ternary at `:112-117` only *prints*.
- [ ] **Step 3: Implement.** The two `break`s become the boundary only when `cfg.sessions is None`;
otherwise control passes to `sweep.run`. Delete the "CLI-2 lands" placeholder text at `:113` and the
`is_optional` comment at `:74-75` that defers `build` — `sweep` now owns `build`.
- [ ] **Step 4:** Suite. **Commit.**

---

## Task 12: the `next` verb

**Files:** Create `ai_rfc/lifecycle/next/{__init__,__main__,cli}.py`; modify `ai_rfc/entrypoints.py`;
test `tests/cli/test_next.py`

CLI-1's D1 is binding: a registered verb is `<package>/cli.py` with `configure`/`run`/`main`, because
`test_cli_conventions.py:136-151` asserts **set equality** between `ENTRY_POINTS` modules and every
`cli.py` the rglob finds. And `test_entries_sharing_a_section_are_contiguous` requires the new
`Lifecycle` row to sit **immediately after `run`**, since declaration order is help order.

`ai_rfc/lifecycle/next/` shares its name with the `next` builtin. This is harmless — the package is
never imported bare, only as `ai_rfc.lifecycle.next.cli` via the registry's dotted string — and CLI-1's
D1 forces the layout. **Note it in the module docstring; do not rename to avoid it.**

- [ ] **Step 1:** Failing test — `ai-rfc next` performs exactly one action and returns; `--until <stage>|cluster:<id>|ordinal:<n>` bounds it.
- [ ] **Steps 2-5:** fail, implement over `sweep.run(..., mode="one")`, suite, commit.

---

## Task 13: thread `sessions.consolidate_every`

SP7c's hand-off names this as CLI-2's own work: the value is loaded at `config.py:593`, re-serialised
at `:679`, and **consumed nowhere**, so an operator who writes `sessions.consolidate_every: 3` gets a
campaign frozen at 10. Ruling R10 of that row unified the *literal* across three homes; it did not
thread the *value*.

**Files:** Modify `ai_rfc/driver/sweep.py`, `ai_rfc/experiment/cli.py:938-948,1314`; tests in both suites.

- [ ] **Step 0: Check whether `campaign init` has a recon-config input at all.** Its `--help` says "a
value configured there is not read", which may mean the verb takes no `recon.yaml` — in which case
threading the value needs a **new input**, not a changed lookup, and this task is bigger than it looks.
Read `experiment/cli.py:830-948` (the `init` parser) before sizing, and record what you find. If there
is no such input, add `--config` to `campaign init` and say so as a deviation.

- [ ] **Step 1: Write the failing test** — a `recon.yaml` carrying `sessions.consolidate_every: 3`
produces a round after the third cluster, and a `campaign init` from that config freezes 3, not 10.
- [ ] **Step 2:** See it fail. **A test that compares two literals while they agree is not this test** —
SP7c's Task 8 shipped exactly that mistake. Use a value that differs from the schema default.
- [ ] **Step 3: Implement.** `sweep.next_round()` reads `cfg.sessions.consolidate_every`;
`campaign init` reads the recon config it initialises from instead of `field_default`. Update
`--consolidate-every`'s help string, which currently says "a value configured there is not read".
- [ ] **Steps 4-5:** suite, commit.

---

## Task 14: mount `ai-rfc experiment …`

**Files:** Modify `ai_rfc/experiment/cli.py` (add `configure`/`run`/`main`), `ai_rfc/entrypoints.py`,
`ai_rfc/experiment/__main__.py`, `tests/substrate/test_cli_conventions.py` (**line 149 only** — `:148`
excludes the root door, `:149` carries `{"server", "experiment"}`, D7), `pyproject.toml`

- [ ] **Step 1: Write the failing test** — `ai-rfc experiment preflight --help` succeeds, and
`python -m ai_rfc.experiment` still works unchanged (the server core and the raw arm invoke it until
CLI-3, spec §3).
- [ ] **Step 2:** See it fail.
- [ ] **Step 3: Implement**, and amend the conventions test's exclusion.
`test_every_cli_module_on_disk_is_registered` (`:136-151`) excludes at `:149` any path with `experiment`
in its parts, so registering `ai_rfc.experiment.cli` makes `ENTRY_POINTS` a strict superset of `on_disk`
and the `:151` set equality fails. **Narrow `:149` to `{"server"}` and say why in the test's docstring** —
weakening an assertion silently is the failure mode this suite's own comments are written against.

`ai_rfc/experiment/cli.py` currently carries `prog="experiment"` at `:708` and dispatches with a
hand-written `elif` chain on `args.command` from `:1213`. `configure`/`run`/`main` wrap that chain; do
not rewrite it into a table in this task.
- [ ] **Step 4:** Suite. **Commit.**

---

## Task 15: the gate

Spec's CLI-2 row: *a two-cluster MARK sweep completes and resumes after a kill; a budget stop
reproduces the resume line.* All three are driven by `fake_claude` (R3) — no spend.

**Files:** Create `tests/driver/test_gate.py`

- [ ] **Criterion 1 — a two-cluster sweep completes.** A scenario whose per-ordinal steps issue
`claim` → `record_status` → `checkpoint` → `revision` → `tag` for two ordinals. Assert
`ledger.counts()` reports both done by the **strict** definition (checkpoint **and** a `kind: cluster`
revision entry **and** its annotated tag) and `run` exits 0.

- [ ] **Criterion 2 — resume after a kill.** Drive `ai-rfc run` in a subprocess against a scenario with
a `sleep`, `os.kill(pid, SIGINT)` from the test, then re-run. Assert the leftover became
`runs/<ts>.interrupted-<cause>/`, that the second run **did not** re-do the finished cluster, and that
`spent()` still counts the killed run's transcript.

- [ ] **Criterion 3 — a budget stop reproduces the resume line.** Two clusters at `cost: 0.5` against
`budget_usd: 0.6`. Assert exit 1, `StopReason.budget`, and that the printed resume line is
byte-identical to `stop.resume_line(...)`.

- [ ] **Report, all measured, none estimated:**
  - 3.10 suite vs the 1472/11 baseline;
  - 3.11 optimize vs 222/2/2 — **a red here is this row's, not pre-existing**;
  - PANTHER door tests vs 6 passed;
  - `grep -rn "from .spawn\|from .stream\|from .enforcement\|from .guard\|from .arms\|from .render\|from .consolidation" ai_rfc/experiment/` → **zero**, proving no re-export stub survives.

A gate failure gets **one** fix wave and **one** scoped re-review. If it still fails, write the resume
point, report the failing output verbatim, and end the turn.

---

## The standing review question

Every review brief in this row — per task and whole-branch — additionally asks: **which character or
value under an author's or an agent's control reaches a produced artifact unescaped, and what does the
grammar of that artifact do with it?** On the preceding row this found five real defects no
brief-shaped review caught. CLI-2's artifacts for that question are **the session argv**, **`run.json`
and `sessions.jsonl`**, **the resume line**, and **the transcript the launcher streams**.

Two carried facts sharpen it. The guard is **closed-set membership, not a character filter** — YAML
implicit typing yields `'1'`, `'True'`, `'None'`, `"['a','b']"`, none of which holds a control
character and none of which names a cluster. And `per_cluster._checked_cluster_id` already proves the
pattern in this codebase: a `cluster_id` read back from agent-written YAML is validated against the
timeline's real ordinals **before** it reaches a prompt, a path, or a report line.

**Adjacent, deliberately out of scope:** `ai_rfc/draft/gate.py:224` joins an unvalidated `cluster_id`
into a filesystem path while `:223` sanitises; `:96` sorts raw mapping keys before validating; and
`REVISION_TAG` accepts a trailing newline. SP7c left these because no task of that row edited
`gate.py`. **If a task of this row edits `gate.py`, the small fix rides along** — a `\Z`-anchored shape
check inside `load_revisions` closes all three.

---

## Self-review

**Spec coverage.** §5's module table → Tasks 1, 2, 6, 8, 9, 10 (`spawn`/`stream`/`enforcement`/`guard`
verbatim; `session.py` from `arms` + `runner.build_env`/`prepare_run_argv` + `per_cluster`'s event
reading; `sweep.py` from `run_per_cluster` minus campaign summaries; `record.py`; `stop.py`). The
SIGINT handler the table names → Task 4. §5's state machine, all nine rows → Task 10 Step 1. Exit codes
0/1/3 → Tasks 10, 11, 12. The four classifications → Task 9. Lifetime budget over `runs/*/events.jsonl`
with moved-aside included → Task 8. Leftover renaming → Tasks 8, 10. `next` and `--until` → Task 12.
D60's instrument split → Tasks 7, 14. §8's fake_claude scenarios → Tasks 5, 15. The CLI-2 gate row →
Task 15.

**Gaps accepted and logged.** Spec §5 lists five movers; R5 moves seven, plus `draft-skeleton.md`
sideways into `lifecycle/` (D2). Spec D55 orders SP7c after CLI-2; R7 records that it landed before.
All are logged deviations; none changes a spec *decision*.

**Review outcome.** One `review-plan` invocation plus one adversarial re-read, both before Task 1:
**9 Critical, 5 Warning**, all fourteen fixed in this file as D1–D14.

The Criticals, and what each would have cost: **D1** a non-moving module's hardcoded path breaks
`ai-rfc init` with no import error; **D2** `draft-skeleton.md` belongs to the substrate, not the
instrument; **D3** a byte-for-byte pin test ties the move to a shipped skill; **D4** four
`ExperimentError` importers, not one; **D5** 28 monkeypatch sites, not 16, two of them shared helpers,
one fanning out to 31 tests; **D10** Task 7's RED test passed against unfixed code; **D11** moving tests
strands two `FIXTURES` constants and silently detaches an `autouse` fixture; **D12** Task 5's named
mechanism (`AI_RFC_FAKE_SCENARIO`) cannot reach the child, because `build_env` is closed; **D13**
production had no prompt source and no drift baseline; **D14** a `finally: write_status` would make the
gate's resume criterion structurally unobservable.

**Seven of the nine fail silently** — no `ImportError`, no red test, and in three cases a *green* test
that proves nothing (D5, D10, D12). That is the pattern to carry into every task review in this row, and
it is why the standing review question above is asked of every brief.

**Type consistency.** `SessionSpec`/`SessionResult`/`run_session` are declared once in Task 6 and
consumed by Tasks 7, 9, 10 under those exact names. `spent`/`attempts`/`move_aside` are declared in
Task 8 and consumed in Task 10. `StopReason`/`classify`/`resume_line` declared in Task 9, consumed in
Tasks 10, 11, 15. `plan_next`/`run` declared in Task 10, consumed in Tasks 11, 12.

**Ordering.** Every task leaves the suite green, so a partial landing is coherent. Tasks 1-3 are pure
moves at a fixed count (1472); Task 4 is the first that adds a test; Tasks 5-6 build the launcher
before anything depends on it; Task 7 is the only task that touches the sixteen silent patches; Tasks
8-10 build the driver bottom-up; Tasks 11-14 wire the doors; Task 15 measures.
